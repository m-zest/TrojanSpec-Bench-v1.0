"""Central registry mapping ``(primitive, attack, language) -> CryptoAnchor``.

New crypto families register by adding a module with an ``ANCHORS`` list and
importing it here. The full v1.0 target is 13 primitives x 4 attacks x 3
languages; this registry grows as families are hand-authored and Phase-7
verifier-validated.
"""

from __future__ import annotations

from trojanspec.crypto import ml_kem
from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# Each entry is a module exposing a module-level ``ANCHORS: list[CryptoAnchor]``.
_FAMILY_MODULES = [ml_kem]

ANCHORS: dict[tuple[CryptoPrimitive, AttackPattern, Language], CryptoAnchor] = {}
for _mod in _FAMILY_MODULES:
    for _anchor in _mod.ANCHORS:
        if _anchor.key in ANCHORS:
            raise RuntimeError(f"Duplicate crypto anchor key: {_anchor.key}")
        ANCHORS[_anchor.key] = _anchor


def get_anchor(
    primitive: CryptoPrimitive, attack: AttackPattern, language: Language
) -> CryptoAnchor | None:
    return ANCHORS.get((primitive, attack, language))


def list_anchors(
    *,
    primitive: CryptoPrimitive | None = None,
    attack: AttackPattern | None = None,
    language: Language | None = None,
) -> list[CryptoAnchor]:
    """Filtered view of the registry (any unset filter matches all)."""
    return [
        a
        for a in ANCHORS.values()
        if (primitive is None or a.primitive == primitive)
        and (attack is None or a.attack_pattern == attack)
        and (language is None or a.language == language)
    ]
