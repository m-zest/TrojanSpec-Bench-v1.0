"""Robust JSON extraction from LLM responses.

Models wrap JSON in prose, ```json fences, or emit it bare. This helper tries,
in order: direct parse, fenced-block parse, then a brace-balanced scan. It is
deliberately tolerant because the entire elicitation pipeline depends on it.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class JSONExtractionError(ValueError):
    """Raised when no JSON object can be recovered from a response."""


def _balanced_object(text: str) -> str | None:
    """Return the first brace-balanced ``{...}`` substring, or ``None``.

    Tracks string state so braces inside string literals do not unbalance the
    scan. Handles escaped quotes.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
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
                return text[start : i + 1]
    return None


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of a single JSON object from ``text``.

    Raises :class:`JSONExtractionError` if nothing parseable is found.
    """
    if not text or not text.strip():
        raise JSONExtractionError("empty response")

    # 1. The whole thing is JSON.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 2. Inside a fenced code block.
    for match in _FENCE_RE.finditer(text):
        candidate = match.group(1).strip()
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            balanced = _balanced_object(candidate)
            if balanced:
                try:
                    obj = json.loads(balanced)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    continue

    # 3. First brace-balanced object anywhere in the text.
    balanced = _balanced_object(text)
    if balanced:
        try:
            obj = json.loads(balanced)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError as exc:
            raise JSONExtractionError(
                f"found a brace-balanced block but it failed to parse: {exc}"
            ) from exc

    raise JSONExtractionError(f"no JSON object found in response: {text[:300]!r}")
