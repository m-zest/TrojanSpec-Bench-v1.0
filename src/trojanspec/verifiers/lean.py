"""Lean 4 verifier subprocess wrapper.

Two modes:

* If a Mathlib-ready project template exists at ``$TROJANSPEC_LEAN_TEMPLATE``
  (or ``~/lean-project-template``), the source is injected as ``Main.lean`` and
  built with ``lake build`` - this supports Mathlib imports.
* Otherwise it falls back to a standalone ``lean`` invocation (no Mathlib).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def _template_dir() -> Path:
    return Path(
        os.environ.get(
            "TROJANSPEC_LEAN_TEMPLATE", str(Path.home() / "lean-project-template")
        )
    )


def verify_lean(spec_and_impl: str, timeout_sec: int = 120):
    from trojanspec.verifiers import VerifyResult, tool_available

    template = _template_dir()
    use_project = template.exists() and tool_available("lake")

    if not use_project and not tool_available("lean"):
        return VerifyResult.missing("lean")

    start = time.time()
    try:
        if use_project:
            with tempfile.TemporaryDirectory() as tmpdir:
                proj = Path(tmpdir) / "proj"
                shutil.copytree(template, proj)
                (proj / "Main.lean").write_text(spec_and_impl, encoding="utf-8")
                result = subprocess.run(
                    ["lake", "build"],
                    capture_output=True,
                    text=True,
                    cwd=proj,
                    timeout=timeout_sec,
                )
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".lean", delete=False, encoding="utf-8"
            ) as f:
                f.write(spec_and_impl)
                tmpfile = f.name
            try:
                result = subprocess.run(
                    ["lean", tmpfile],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
            finally:
                os.unlink(tmpfile)

        elapsed = int((time.time() - start) * 1000)
        return VerifyResult(
            accepts=result.returncode == 0,
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
