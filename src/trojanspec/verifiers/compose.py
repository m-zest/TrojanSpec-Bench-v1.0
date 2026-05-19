"""Compose a v2 witness body under a v2 contract into one program.

v2 contract: ``trojan_spec`` / ``original_spec`` are a signature + pre/post
with NO body; ``trojan_witness`` is the same signature WITH a body. The
validator must produce a single well-formed program: the *contract* supplies
the signature + clauses, the *witness* supplies the body.

The brace-finding must not be fooled by braces that are not the body:

* Dafny set/seq literals in clauses: ``requires d in {4, 5, 10}``
* Dafny attribute brackets: ``function f() {:axiom}``
* Verus wrappers: ``verus! { ... }`` and ``use vstd::prelude::*;``
"""

from __future__ import annotations

import re

from trojanspec.schemas import Language

_ATTR = "{:"


def _top_level_blocks(text: str) -> list[tuple[int, int]]:
    """(start, end) of every depth-0 ``{...}`` block, skipping ``{:`` attrs."""
    blocks: list[tuple[int, int]] = []
    depth = 0
    start = -1
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            is_attr = i + 1 < n and text[i + 1] == ":"
            if depth == 0 and not is_attr:
                start = i
            if not is_attr:
                depth += 1
            else:
                # consume the whole {: ... } attribute without depth changes
                d = 1
                j = i + 1
                while j < n and d:
                    if text[j] == "{":
                        d += 1
                    elif text[j] == "}":
                        d -= 1
                    j += 1
                i = j
                continue
        elif c == "}" and depth:
            depth -= 1
            if depth == 0 and start != -1:
                blocks.append((start, i + 1))
                start = -1
        i += 1
    return blocks


def _last_body_block(text: str) -> str | None:
    """The last top-level ``{...}`` block - a well-formed decl's body."""
    blocks = _top_level_blocks(text)
    if not blocks:
        return None
    s, e = blocks[-1]
    return text[s:e]


def _strip_trailing_body(text: str) -> str:
    """Drop a trailing body block if the contract erroneously included one.

    A body is only stripped when the last top-level block is followed by
    nothing but whitespace (so set literals mid-clause are never stripped).
    """
    blocks = _top_level_blocks(text)
    if not blocks:
        return text.rstrip()
    s, e = blocks[-1]
    if text[e:].strip() == "":
        return text[:s].rstrip()
    return text.rstrip()


_VERUS_USE = re.compile(r"^\s*use\s+vstd::prelude::\*\s*;\s*", re.M)
_VERUS_WRAP = re.compile(r"verus\s*!\s*\{", re.S)


def _verus_unwrap(text: str) -> str:
    """Strip ``use vstd::prelude::*;`` and the outer ``verus! { ... }``."""
    t = _VERUS_USE.sub("", text)
    m = _VERUS_WRAP.search(t)
    if not m:
        return t.strip()
    inner = t[m.end():]
    # drop the matching closing brace of the verus! wrapper (the last })
    last = inner.rfind("}")
    if last != -1:
        inner = inner[:last]
    return inner.strip()


def _trim_unbalanced_close(text: str) -> str:
    """Drop trailing ``}`` (and whitespace) while the text has more ``}``
    than ``{``.

    A header-only Verus spec is a signature + ``requires``/``ensures`` with
    no body, but models routinely emit a stray closing brace (a leftover
    ``verus! {`` close, or a premature ``fn`` close). Left in place, the
    spliced witness body lands *after* that brace and Verus reports
    "unexpected closing delimiter". Trimming the unmatched tail leaves a
    clean header that the body attaches to correctly.
    """
    t = text.rstrip()
    while t.endswith("}") and t.count("}") > t.count("{"):
        t = t[:-1].rstrip()
    return t


def _verus_wrap(body: str) -> str:
    return f"use vstd::prelude::*;\nverus! {{\n{body}\n}}\n"


def compose(
    preamble: str, contract: str, witness: str, language: Language
) -> str:
    """v3: ``preamble`` (shared helpers) + ``contract`` (target signature +
    pre/post, no body) + ``witness`` body -> one well-formed program.

    ``preamble`` is identical for the trojan and original runs; only the
    contract differs. Empty preamble == self-contained single declaration.
    """
    preamble = (preamble or "").strip()
    contract = contract.strip()
    witness = witness.strip()

    if language is Language.LEAN:
        stmt = contract.rsplit(":=", 1)[0].rstrip() if ":=" in contract else contract
        tail = (":=" + witness.split(":=", 1)[1]).strip() if ":=" in witness else witness
        parts = [p for p in (preamble, f"{stmt} {tail}".strip()) if p]
        return "\n\n".join(parts) + "\n"

    if language is Language.VERUS:
        pre = _verus_unwrap(preamble) if preamble else ""
        c_inner = _verus_unwrap(contract)
        w_inner = _verus_unwrap(witness)
        # Header-only spec: strip a trailing body if present, then trim any
        # stray unmatched closing brace so the witness body splices cleanly.
        header = _trim_unbalanced_close(_strip_trailing_body(c_inner))
        body = _last_body_block(w_inner) or w_inner
        inner = "\n".join(p for p in (pre, header, body) if p)
        # Re-wrap the combined declaration in exactly one verus! { ... }.
        return _verus_wrap(inner.strip())

    # Dafny: preamble (helpers) + contract (signature+clauses, braces are set
    # literals / attributes, not a body) + the witness's body block.
    header = _strip_trailing_body(contract)
    body = _last_body_block(witness) or witness
    return "\n\n".join(p for p in (preamble, f"{header}\n{body}") if p) + "\n"
