"""Verus verifier subprocess wrapper."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def verify_verus(spec_and_impl: str, timeout_sec: int = 60):
    from trojanspec.verifiers import VerifyResult, tool_available

    if not tool_available("verus"):
        return VerifyResult.missing("verus")

    # Verus compiles the file as a Rust crate, which requires a `main`.
    # Composed triples (signature + spliced body) have none, so Verus aborts
    # with E0601 before verification. Inject a trivial main when absent.
    if "fn main(" not in spec_and_impl:
        spec_and_impl = spec_and_impl.rstrip() + "\n\nfn main() {}\n"

    # Verus emits the compiled binary (and any scratch artefacts) into the
    # *current working directory*. Running 1500-1800 triples from the repo
    # root left ~1500 stray `tmp*` files/dirs there. Run inside a dedicated
    # tempdir and rmtree it in `finally` so every invocation is self-cleaning
    # regardless of pass / fail / timeout.
    workdir = Path(tempfile.mkdtemp(prefix="trojanspec_verus_"))
    try:
        srcfile = workdir / "triple.rs"
        srcfile.write_text(spec_and_impl, encoding="utf-8")
        start = time.time()
        try:
            result = subprocess.run(
                ["verus", str(srcfile)],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=workdir,
            )
            elapsed = int((time.time() - start) * 1000)
            # Verus prints "verification results:: N verified, M errors".
            accepts = result.returncode == 0 and (
                "0 errors" in result.stdout or "0 errors" in result.stderr
            )
            return VerifyResult(
                accepts=accepts,
                time_ms=elapsed,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(
                accepts=False,
                time_ms=timeout_sec * 1000,
                stdout="",
                stderr="TIMEOUT",
                exit_code=-1,
                timeout=True,
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
