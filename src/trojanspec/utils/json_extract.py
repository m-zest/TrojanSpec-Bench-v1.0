"""Robust JSON extraction from LLM responses.

Reasoning models wrap the answer in long prose, emit stray ``{...}`` blocks
inside that prose (code snippets), fence the real answer, and routinely put
unescaped newlines / quotes inside JSON string values (multi-line spec code).

Strategy, in order:

  1. Direct parse (whole response is JSON).
  2. Every ```json fenced block.
  3. Every brace-balanced ``{...}`` anywhere in the text.

For 2 and 3 we collect *all* candidates, parse each with ``strict=False`` (so
literal newlines/tabs inside strings are tolerated) plus a light repair pass,
and prefer the candidate that contains the expected keys. This makes the
pipeline robust to models that "think out loud" before answering.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


class JSONExtractionError(ValueError):
    """Raised when no JSON object can be recovered from a response."""


def _balanced_objects(text: str) -> list[str]:
    """Return every top-level brace-balanced ``{...}`` substring.

    Tracks string state so braces inside string literals do not unbalance the
    scan. Handles escaped quotes. Multiple objects are returned because the
    real answer is often preceded by ``{...}`` snippets in reasoning prose.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        escaped = False
        for j in range(i, n):
            ch = text[j]
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[i : j + 1])
                    i = j + 1
                    break
        else:
            break
    return out


def _try_parse(candidate: str) -> dict[str, Any] | None:
    """Parse ``candidate`` tolerantly, returning a dict or ``None``."""
    for attempt in (candidate, _TRAILING_COMMA_RE.sub(r"\1", candidate)):
        try:
            obj = json.loads(attempt, strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def extract_json(
    text: str, expected_keys: tuple[str, ...] = ("trojan_spec", "trojan_witness")
) -> dict[str, Any]:
    """Best-effort extraction of a single JSON object from ``text``.

    Among all parseable candidates the one containing the most
    ``expected_keys`` wins (ties broken by first occurrence). Raises
    :class:`JSONExtractionError` if nothing parseable is found.
    """
    if not text or not text.strip():
        raise JSONExtractionError("empty response")

    candidates: list[str] = [text]
    candidates += [m.group(1) for m in _FENCE_RE.finditer(text)]
    for fenced in list(candidates[1:]):
        candidates += _balanced_objects(fenced)
    candidates += _balanced_objects(text)

    best: dict[str, Any] | None = None
    best_score = -1
    for cand in candidates:
        parsed = _try_parse(cand)
        if parsed is None:
            continue
        score = sum(1 for k in expected_keys if k in parsed)
        if score > best_score:
            best, best_score = parsed, score
            if score == len(expected_keys):
                return best

    if best is not None:
        return best

    raise JSONExtractionError(f"no JSON object found in response: {text[:300]!r}")
