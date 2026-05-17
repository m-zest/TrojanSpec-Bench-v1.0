"""Subprocess wrappers around the three formal verifiers.

Each ``verify_<lang>(source, timeout_sec)`` returns a uniform
:class:`VerifyResult`. If the toolchain is absent the call returns a result
with ``tool_missing=True`` rather than raising, so generation/review pipelines
keep working on machines without verifiers installed.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from trojanspec.schemas import Language


@dataclass
class VerifyResult:
    accepts: bool
    time_ms: int
    stdout: str
    stderr: str
    exit_code: int
    timeout: bool = False
    tool_missing: bool = False

    @classmethod
    def missing(cls, tool: str) -> VerifyResult:
        return cls(
            accepts=False,
            time_ms=0,
            stdout="",
            stderr=f"{tool} not found on PATH",
            exit_code=-2,
            tool_missing=True,
        )


def tool_available(executable: str) -> bool:
    return shutil.which(executable) is not None


from trojanspec.verifiers.dafny import verify_dafny  # noqa: E402
from trojanspec.verifiers.lean import verify_lean  # noqa: E402
from trojanspec.verifiers.verus import verify_verus  # noqa: E402

VERIFIERS = {
    Language.DAFNY: verify_dafny,
    Language.LEAN: verify_lean,
    Language.VERUS: verify_verus,
}

__all__ = [
    "VERIFIERS",
    "VerifyResult",
    "tool_available",
    "verify_dafny",
    "verify_lean",
    "verify_verus",
]
