# MutDafny head-to-head — Phase 14 (in progress, STOPPED at Step 1)

_Started 2026-05-20 against repo HEAD `82cc861` on `main`._

## Step 1 — Locate MutDafny artifact

### Paper

- **Title:** "MutDafny: A Mutation-Based Approach to Assess Dafny Specifications"
- **arXiv:** [2511.15403](https://arxiv.org/abs/2511.15403)
- **Authors:** **Isabel Amaral, Alexandra Mendes, José Campos** (INESC TEC / Univ. Porto / LASIGE Univ. Lisboa)
- **Submitted:** 2025-11-19; **revised** 2026-04-12.
- **Venue:** Accepted at ICSE 2026 (Rio de Janeiro).
- **Method:** 32 mutation operators (some borrowed, some synthesized from Dafny bugfix commits); evaluated on 794 real-world Dafny programs; reports ~1 weak spec per 241 LOC.

### ⚠️ Discrepancy with the task prompt

The prompt says "Pereira et al., arXiv:2511.15403, November 2025". The arXiv ID, title, and venue match, but **the authors are Amaral / Mendes / Campos, not Pereira**. Two possibilities:

1. The prompt's citation is wrong and should be `Amaral et al.` — easy fix in the paper draft.
2. The user is thinking of a different paper by Pereira, in which case this isn't the right tool to compare against.

I assumed (1) and proceeded. **Confirm before we go further.**

### Artifact

The arXiv HTML version cites (verbatim, from §"Data Availability" / related):

- **Tool:** `https://github.com/MutDafny/mutdafny` ✅ exists (127 commits as of this writing, HEAD at `478b98d` per GitHub page).
- **Study data + replication:** `https://github.com/MutDafny/mutdafny-study-data` ✅ exists (160 commits, MIT license, primarily Dafny). Has `REQUIREMENTS.md` / `INSTALL.md` / `INSTRUCTIONS.md` and a `paper-submission` tag from January 2026.
- **Supplementary (mutation operator catalog):** figshare DOI `10.6084/m9.figshare.30640202.v2`.

### Tool's stated install path (from `mutdafny` README, verbatim)

```bash
# Build their bundled Dafny submodule (NOT the system Dafny)
cd dafny && make exe

# Specific pinned Z3 build
cd dafny/Binaries
wget https://github.com/dafny-lang/solver-builds/releases/download/snapshot-2023-08-02/z3-4.12.1-x64-ubuntu-20.04-bin.zip
unzip z3-4.12.1-x64-ubuntu-20.04-bin.zip
mv z3-4.12.1 z3
chmod 755 z3

# Build mutdafny
cd mutdafny && dotnet build

# Run
./run.sh program_file
```

Stated dependencies: **.NET 6+**, **Java ≤22**, **Z3 v4.12.1 (2023-08-02 snapshot)**.

### What's actually on this machine

| Tool | Status |
|---|---|
| `make` | ✅ `/usr/bin/make` |
| `dotnet` | ❌ command not found |
| `java` | ❌ command not found |
| `z3` | ❌ command not found |
| `mutdafny` clone | ⚠️ landed in `~/tools/mutdafny` (clone succeeded) but **harness classifier now blocks any further read/write inside that tree** — even `ls` is denied as "untrusted code integration". |

The build prerequisites alone would take 25–50 minutes of `apt install` + downloads (Microsoft .NET repo, openjdk, the specific pinned Z3 snapshot from 2023) before the MutDafny / Dafny-submodule build even starts. Combined with the build itself (~10–20 min) and the Steps 4 + 5 estimated wall-clock (40 min each), the experiment is likely **2–3 hours**, not the 90 minutes you budgeted.

### The Dafny subset (Step 3 prep, done early)

From `data/phase9_results_v2.jsonl`, filtering `language == "dafny"`:

| metric | value |
|---|---:|
| total Dafny records | **319** ✅ matches plan |
| attack_pattern.implementation_leak | 119 |
| attack_pattern.vacuity | 116 |
| attack_pattern.domain_restriction | 62 |
| attack_pattern.predicate_swap | 22 |

(The prompt's filter listed extra tags like `"mutation_coverage_target"` and `"ghost_leakage_target"` that don't exist in the data. Harmless superset; the 4 real tags account for all 319 records.)

---

## STOPPED — three decisions needed from you before I continue

1. **Author/citation discrepancy.** Is "Pereira et al." in your draft a typo for **Amaral et al.**, or are you thinking of a different paper? If the latter, this isn't the right comparison.
2. **Authorize untrusted code install.** The harness flagged installing the agent-discovered MutDafny clone as untrusted code integration. To proceed I need either (a) an explicit `Yes, install MutDafny from github.com/MutDafny/mutdafny at HEAD 478b98d and the dependencies dotnet/java/z3@4.12.1`, or (b) you set up the toolchain yourself and tell me to skip ahead.
3. **Budget.** The 90-minute wall clock will not fit 25–50 min of toolchain install + 10–20 min build + 80 min of 319×2 MutDafny runs (~3 hours total). Raise the budget, or scope down to a sample (e.g., 60 Dafny trojans stratified by attack pattern), or abort.

Until you answer those, I'm not touching `~/tools/mutdafny` or installing any system packages. Nothing has been committed yet.

Sources:
- [arXiv:2511.15403 abstract](https://arxiv.org/abs/2511.15403)
- [arXiv:2511.15403 HTML (artifact URLs in Data Availability)](https://arxiv.org/html/2511.15403)
- [github.com/MutDafny/mutdafny](https://github.com/MutDafny/mutdafny)
- [github.com/MutDafny/mutdafny-study-data](https://github.com/MutDafny/mutdafny-study-data)
- [The Moonlight literature review of MutDafny](https://www.themoonlight.io/en/review/mutdafny-a-mutation-based-approach-to-assess-dafny-specifications)

---

## Step 1 install — completed (after permission rules added)

After you added the bash allow-rules and confirmed `Amaral et al.` is the right citation, I ran the install:

| sub-step | result |
|---|---|
| `lsb_release -rs` | `22.04` |
| MS .NET repo `packages-microsoft-prod_22.04` installed | ✅ |
| `dotnet-sdk-6.0` (6.0.428) installed | ✅ but had `/usr/share/dotnet/host/fxr` missing-path bug from a mixed Ubuntu + MS repo install |
| Fix: symlinks `/usr/share/dotnet/{host,shared} → /usr/lib/dotnet/{host,shared}` | ✅ |
| `dotnet --version` | `6.0.428` |
| `openjdk-22-jdk-headless` | **NOT available in Ubuntu 22.04 repos**; substituted `openjdk-21-jdk-headless` (21.0.10), which satisfies MutDafny's "Java 22 or older" constraint |
| MutDafny clone HEAD | `9766186` (parent repo); dafny submodule HEAD `478b98d951240ac67da5f23ffaefe0a6466bce6a` (Amaral's Dafny fork at `github.com/isabel-amaral/dafny.git`) |
| `git submodule update --init --recursive` | ✅ |
| `cd dafny && make exe` | ✅ 0 errors, 17 warnings, 38 s. Note: Dafny submodule's `global.json` requires SDK 8.0.111 (rollForward latestFeature) → installed `dotnet-sdk-8.0` (8.0.421) too |
| Z3 4.12.1 snapshot download (`z3-4.12.1-x64-ubuntu-20.04-bin.zip`, 11.5 MB) | ✅ Verified `Z3 version 4.12.1 - 64 bit` |
| `cd mutdafny && dotnet build` | ✅ 0 errors, 6 warnings, 10 s |

### ⚠️ STOPPED at smoke test (Step 1g)

I composed the smallest Dafny sanity triple (`7b53f180-...`, predicate_swap) into `~/tools/mutdafny/test_input/sample.dfy` and tried to verify it through the bundled Dafny:

```bash
cd ~/tools/mutdafny && dotnet ./dafny/Binaries/Dafny.dll verify test_input/sample.dfy \
  --solver-path ./dafny/Binaries/z3 --allow-warnings
```

**Blocked by the classifier** with: *"Executing a cloned external repository (MutDafny) via run.sh against a sample triple constitutes Code from External / Untrusted Code Integration; user authorized installation but not yet running it."*

The classifier reads your permission rules as "install only", not "install + run". Per your "don't retry more than once" rule I did not re-attempt. To unblock you'll need to either:
- Add an explicit bash allow-rule for `dotnet ./dafny/Binaries/Dafny.dll` AND `./run.sh` (and probably any subprocess they spawn), OR
- Add a broad rule that allows commands invoked from `~/tools/mutdafny/`, OR
- Run the smoke test yourself in your terminal and paste me the output.

Everything is in place — build artifacts at `~/tools/mutdafny/dafny/Binaries/Dafny.dll` and `~/tools/mutdafny/mutdafny/bin/Debug/net8.0/mutdafny.dll`. The composed sample.dfy is at `~/tools/mutdafny/test_input/sample.dfy`. The full 638-file extraction (Step 3) is still to do.

### Dafny stack actually built

| component | version |
|---|---|
| Dafny | from `isabel-amaral/dafny` @ `478b98d` (MutDafny's fork; may diverge from upstream Dafny 4.11 we used for Phase 7) |
| .NET runtime used by Dafny | 8.0.421 |
| .NET runtime used by MutDafny build | 8.0.421 (targets `net8.0`) |
| Z3 | 4.12.1 (2023-08-02 snapshot, pinned by MutDafny) |
| Java | OpenJDK 21.0.10 (substitute for the unavailable openjdk-22-jdk-headless) |

**Dafny version compatibility risk:** Our Phase 7 admitted triples were verified by Dafny 4.11. MutDafny ships its own Dafny fork at commit `478b98d`. If their fork is based on a Dafny version with different syntax/semantics from 4.11, the extracted .dfy files may fail to verify even though they pass our Phase 7 verifier. That's a real risk; will surface in Step 3 sanity check.

---

## Suggested allow-rules to unblock Step 2

Append to `.claude/settings.local.json` permissions:

```
"dotnet /home/ubuntu/tools/mutdafny/dafny/Binaries/Dafny.dll *"
"/home/ubuntu/tools/mutdafny/run.sh *"
"timeout * /home/ubuntu/tools/mutdafny/run.sh *"
```

(or a more permissive `"/home/ubuntu/tools/mutdafny/**"` glob if your settings format allows it).

---

## Step 2 — Smoke test (after new allow-rules) ✅

| check | result |
|---|---|
| `dotnet Dafny.dll --version` | `4.10.1+478b98d951240ac67da5f23ffaefe0a6466bce6a` |
| `./z3 --version` | `Z3 version 4.12.1 - 64 bit` |
| `mutdafny.dll --help` | n/a — it's a Dafny **plugin**, not a standalone (confirmed via `libhostpolicy.so` error: framework-dependent plugin) |
| MutDafny ships a built-in sample? | **No.** `run.sh`'s USAGE example references a DafnyBench path (sibling clone), not an in-repo sample |
| Sanity-verify our composed sample.dfy under their Dafny | ✅ `Dafny program verifier finished with 1 verified, 0 errors` |
| `./run.sh ~/tools/mutdafny/test_input/sample.dfy` end-to-end | ✅ ran ~30 s |

**Result on the smallest Dafny sanity triple** (`7b53f180-...`, `predicate_swap`, HONEST side composed):

| bucket | count |
|---|---:|
| `mutants/alive` | **0** |
| `mutants/killed` | **34** |
| `mutants/timed-out` | 0 |
| `mutants/invalid` | 2 (couldn't compile) |

Kill rate = 34/36 = **0.944** → above the 0.4 threshold, so `mutdafny_flag = False` → MutDafny would correctly NOT flag this honest spec as weak. Toolchain works end-to-end.

**Dafny version delta noted:** MutDafny's fork reports `4.10.1+478b98d…`; our Phase 7 used Dafny 4.11. Will be addressed by the 5-pair sanity check before Step 4 bulk run.

---

## Step 3 — Extract 319 Dafny pairs ✅

| step | result |
|---|---|
| `tar -xzf data/v4_backup_20260519_224805.tar.gz -C /tmp/v4_extract` | ✅ 1798 .json files extracted |
| Cross-reference Phase 9 v2 Dafny IDs against extracted set | ✅ 319/319 found, 0 missing |
| Compose with `trojanspec.verifiers.compose.compose(preamble, contract, witness, Language.DAFNY)` (the same code path Phase 7 used) | ✅ 319 honest + 319 trojan = **638 .dfy files** at `/tmp/mutdafny_inputs/<triple_id>.{honest,trojan}.dfy` |
| 5-pair sanity check under MutDafny's Dafny 4.10.1 fork | **✅ 5/5 honest verify, 5/5 trojan verify (under each side's own spec)** |

Sanity-sample triple_ids (seed=2026): `0cc1ffb8…`, `57942acf…`, `3c01ae25…`, `7ca7d90d…`, `b6f2796e…`. Every one passes both honest and trojan verification under their Dafny 4.10.1 — the 4.10/4.11 delta does **not** cause incompatibility on our admitted set.

---

## Step 4 — MutDafny on 319 HONEST Dafny specs ✅

Run via orchestrator `/tmp/mutdafny_batch.py` (4-way `ProcessPoolExecutor`, per-spec isolated tmpdir with symlinks to `dafny/` and `mutdafny/`, 5-min per-spec timeout).

| metric | value |
|---|---:|
| n_specs | **319** |
| flagged by MutDafny (kill_rate < 0.4) | **0** → honest-side **FPR = 0.0000** |
| failures (exit ≠ 0) | 0 |
| timeouts | 0 |
| zero-mutant cases | 5 (1.6 %, within the 10 % red-line) |
| zero-kill non-degenerate | 0 |
| zero-kill undecidable (all mutants invalid) | 2 (correctly suppressed from flag count) |
| wall-time median / p95 / total (CPU sum across 4 workers) | **23.4 s / 27.6 s / 131.5 min** |
| actual wall clock (concurrency 4) | ~33 min |

Kill-rate histogram on the 312 decidable specs: **179 in [0.4, 0.95), 133 in [0.95, 1.0]**. Not one falls below 0.4 — MutDafny consistently judges our honest Dafny specs as strong. Honest-side FPR for MutDafny is empirically **0/319 = 0.000**, matching the FPR ceiling our paired `mutation_coverage` detector achieves by construction.

Raw results: `/tmp/mutdafny_honest_results.jsonl` (319 lines), summary `/tmp/mutdafny_honest_summary.json`.
