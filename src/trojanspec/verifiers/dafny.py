"""Dafny verifier subprocess wrapper."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time


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
            out = result.stdout.lower()
            accepts = result.returncode == 0 and (
                "verified" in out and "0 errors" in out or "verified, 0 errors" in out
            )
            # Dafny's exact summary line varies by version; fall back to rc + no error.
            if result.returncode == 0 and "error" not in out:
                accepts = True
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
