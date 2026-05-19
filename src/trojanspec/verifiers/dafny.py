"""Dafny verifier subprocess wrapper."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time

# Dafny's authoritative outcome line, e.g.
#   "Dafny program verifier finished with 2 verified, 0 errors"
_VERIFIER_SUMMARY = re.compile(r"verifier finished with \d+ verified, (\d+) error")
# Hard failures: parse / resolution / type errors, or an explicit
# "N error(s) detected" line (no verification summary is produced then).
_HARD_ERRORS = re.compile(r"\d+ (?:resolution/type|parse|syntax) error|\berrors? detected")


def verify_dafny(spec_and_impl: str, timeout_sec: int = 60):
    """Run ``dafny verify`` on the given source text."""
    from trojanspec.verifiers import VerifyResult, tool_available

    if not tool_available("dafny"):
        return VerifyResult.missing("dafny")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".dfy", delete=False, encoding="utf-8"
    ) as f:
        f.write(spec_and_impl)
        tmpfile = f.name
    try:
        start = time.time()
        try:
            result = subprocess.run(
                ["dafny", "verify", tmpfile],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            elapsed = int((time.time() - start) * 1000)
            # Classify on Dafny's own verifier-summary line, NOT the process
            # return code: Dafny exits nonzero when warnings are treated as
            # errors ("Compilation failed because warnings were treated as
            # errors"), but a quantifier-trigger / trigger-loop / shadowing
            # *warning* is not a verification failure. A program is accepted
            # iff the verifier reports 0 errors and no parse/resolution/type
            # errors were detected.
            out = (result.stdout or "") + "\n" + (result.stderr or "")
            low = out.lower()
            m = _VERIFIER_SUMMARY.search(low)
            if m is not None:
                accepts = int(m.group(1)) == 0
            else:
                # No verification summary => parse/resolution failed, or the
                # tool never reached the verifier. Treat as not accepted,
                # unless rc==0 with no error markers at all (defensive).
                accepts = result.returncode == 0 and "error" not in low
            if _HARD_ERRORS.search(low):
                accepts = False
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
        os.unlink(tmpfile)
