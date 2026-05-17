"""Verifier wrapper tests that do not require a toolchain.

When Dafny/Lean/Verus are absent the wrappers must degrade gracefully
(``tool_missing=True``) rather than raise. Real round-trip checks are marked
``verifier`` and skipped in CI.
"""

import shutil

import pytest

from trojanspec.verifiers import (
    VerifyResult,
    verify_dafny,
    verify_lean,
    verify_verus,
)


def test_missing_helper():
    r = VerifyResult.missing("dafny")
    assert r.tool_missing is True
    assert r.accepts is False


@pytest.mark.parametrize(
    "fn,tool",
    [(verify_dafny, "dafny"), (verify_verus, "verus")],
)
def test_graceful_when_tool_absent(fn, tool):
    if shutil.which(tool):
        pytest.skip(f"{tool} is installed; covered by the 'verifier' suite")
    r = fn("anything")
    assert r.tool_missing is True
    assert r.accepts is False


def test_lean_graceful_when_absent():
    if shutil.which("lean") or shutil.which("lake"):
        pytest.skip("lean/lake installed; covered by the 'verifier' suite")
    r = verify_lean("theorem t : True := trivial")
    assert r.tool_missing is True


@pytest.mark.verifier
def test_dafny_accepts_trivial():
    if not shutil.which("dafny"):
        pytest.skip("dafny not installed")
    r = verify_dafny("method M() ensures true { }")
    assert r.accepts is True
