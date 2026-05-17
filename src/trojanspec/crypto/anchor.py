"""The :class:`CryptoAnchor` value type shared by every crypto family module."""

from __future__ import annotations

from dataclasses import dataclass

from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language


@dataclass(frozen=True)
class CryptoAnchor:
    """A pre-baked, disclosure-safe trojan triple for a crypto primitive.

    ``original_spec + trojan_witness`` must be rejected by the verifier, while
    ``trojan_spec + trojan_witness`` must be accepted - exactly the admission
    criterion in :mod:`trojanspec.generators.validator`.
    """

    primitive: CryptoPrimitive
    attack_pattern: AttackPattern
    language: Language
    nl_requirement: str
    original_spec: str
    trojan_spec: str
    trojan_witness: str
    bug_source: str  # e.g. "IACR ePrint 2026/192, Finding 1"

    @property
    def key(self) -> tuple[CryptoPrimitive, AttackPattern, Language]:
        return (self.primitive, self.attack_pattern, self.language)
