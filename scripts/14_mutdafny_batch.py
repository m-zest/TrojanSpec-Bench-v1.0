"""Phase 14 steps 4 & 5: run MutDafny on a batch of .dfy files with 4-way
concurrency and per-spec isolation. One JSONL row per spec, streaming for
resumability. The same script is invoked twice — once per side.

Schema per row:
  {"triple_id", "side": "honest"|"trojan", "n_mutants_generated",
   "n_mutants_killed", "n_alive", "n_timed_out", "n_invalid",
   "kill_rate", "mutdafny_flag", "wall_sec", "exit_code", "note"}

mutdafny_flag = (kill_rate < THRESHOLD) AND (decidable mutants > 0).
THRESHOLD = 0.4 — same threshold our static mutation_coverage uses, for
fair head-to-head comparison.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

DEFAULT_MUTDAFNY_HOME = Path.home() / "tools" / "mutdafny"
PER_SPEC_TIMEOUT = 300  # 5 minutes per spec — per the head-to-head plan
THRESHOLD = 0.4


def run_one(args: tuple[str, str, str, str]) -> dict:
    """Run MutDafny on ONE .dfy file in an isolated work dir."""
    triple_id, side, dfy_path, mutdafny_home = args
    home = Path(mutdafny_home)
    work = Path(tempfile.mkdtemp(prefix=f"md_{triple_id[:8]}_{side}_"))
    started = time.time()
    note: str | None = None
    exit_code = -1
    try:
        for name in ("dafny", "mutdafny", "run.sh"):
            (work / name).symlink_to(home / name)
        (work / "mutants").mkdir(exist_ok=True)
        try:
            proc = subprocess.run(
                ["bash", str(work / "run.sh"), dfy_path],
                cwd=str(work),
                capture_output=True,
                text=True,
                timeout=PER_SPEC_TIMEOUT,
            )
            exit_code = proc.returncode
            if proc.returncode != 0:
                note = f"exit={proc.returncode}; stderr_tail={proc.stderr[-200:]!r}"
        except subprocess.TimeoutExpired:
            note = f"orchestrator-timeout>{PER_SPEC_TIMEOUT}s"
            exit_code = -1
        mut_dir = work / "mutants"
        n_alive    = len(list((mut_dir / "alive").glob("*.dfy")))    if (mut_dir / "alive").exists()    else 0
        n_killed   = len(list((mut_dir / "killed").glob("*.dfy")))   if (mut_dir / "killed").exists()   else 0
        n_timed    = len(list((mut_dir / "timed-out").glob("*.dfy"))) if (mut_dir / "timed-out").exists() else 0
        n_invalid  = len(list((mut_dir / "invalid").glob("*.dfy")))  if (mut_dir / "invalid").exists()  else 0
        n_gen = n_alive + n_killed + n_timed + n_invalid
        decidable = n_killed + n_alive
        kill_rate = (n_killed / decidable) if decidable else 0.0
        # Don't flag when there's no decidable signal (zero-mutant or all-invalid).
        mutdafny_flag = (kill_rate < THRESHOLD) if decidable else False
        return {
            "triple_id": triple_id,
            "side": side,
            "n_mutants_generated": n_gen,
            "n_mutants_killed": n_killed,
            "n_alive": n_alive,
            "n_timed_out": n_timed,
            "n_invalid": n_invalid,
            "kill_rate": round(kill_rate, 4),
            "mutdafny_flag": mutdafny_flag,
            "wall_sec": round(time.time() - started, 2),
            "exit_code": exit_code,
            "note": note,
        }
    finally:
        try:
            shutil.rmtree(work)
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--side", required=True, choices=["honest", "trojan"])
    ap.add_argument("--inputs-dir", default="/tmp/mutdafny_inputs")
    ap.add_argument("--out-jsonl", required=True,
                    help="Streaming results JSONL; resumable")
    ap.add_argument("--summary-json", required=True)
    ap.add_argument("--mutdafny-home", default=str(DEFAULT_MUTDAFNY_HOME))
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    pat = f"*.{args.side}.dfy"
    files = sorted(Path(args.inputs_dir).glob(pat))
    if args.limit:
        files = files[: args.limit]
    print(f"side={args.side} files={len(files)} concurrency={args.concurrency} "
          f"mutdafny={args.mutdafny_home}")

    done: set[str] = set()
    out_path = Path(args.out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        for ln in out_path.read_text().splitlines():
            if not ln.strip():
                continue
            try:
                done.add(json.loads(ln)["triple_id"])
            except Exception:
                pass
    pending = [f for f in files if f.stem.split(".")[0] not in done]
    print(f"done={len(done)} pending={len(pending)}")

    rows: list[dict] = []
    if pending:
        tasks = [(f.stem.split(".")[0], args.side, str(f), args.mutdafny_home) for f in pending]
        with out_path.open("a") as fout, \
             ProcessPoolExecutor(max_workers=args.concurrency) as ex:
            futs = {ex.submit(run_one, t): t for t in tasks}
            n_done = 0
            for fut in as_completed(futs):
                r = fut.result()
                fout.write(json.dumps(r) + "\n")
                fout.flush()
                rows.append(r)
                n_done += 1
                if n_done % 10 == 0 or n_done == len(pending):
                    flagged = sum(1 for x in rows if x["mutdafny_flag"])
                    print(f"  {n_done}/{len(pending)}  flagged={flagged}  "
                          f"last={r['triple_id'][:8]} side={r['side']} "
                          f"kill={r['kill_rate']} wall={r['wall_sec']}s")

    all_rows: list[dict] = []
    for ln in out_path.read_text().splitlines():
        if ln.strip():
            try:
                all_rows.append(json.loads(ln))
            except Exception:
                pass

    summary = {
        "side": args.side,
        "n_specs": len(all_rows),
        "n_flagged_mutdafny": sum(1 for r in all_rows if r["mutdafny_flag"]),
        "n_failed": sum(
            1 for r in all_rows
            if r["exit_code"] != 0 and r["note"] and "timeout" not in (r["note"] or "")
        ),
        "n_timeout": sum(1 for r in all_rows if r["note"] and "timeout" in r["note"]),
        "n_zero_mutants": sum(1 for r in all_rows if r["n_mutants_generated"] == 0),
        "total_wall_sec": round(sum(r["wall_sec"] for r in all_rows), 1),
        "threshold": THRESHOLD,
        "per_spec_timeout": PER_SPEC_TIMEOUT,
    }
    Path(args.summary_json).write_text(json.dumps(summary, indent=2))
    print("\nsummary:", json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
