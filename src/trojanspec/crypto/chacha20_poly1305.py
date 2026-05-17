"""ChaCha20-Poly1305 attack template.

Reference bug (publicly disclosed):

* IACR ePrint 2026/670 (Symbolic Software, "Verification Facade: Structural
  Gaps in Cryspen's Hax Pipeline") - the ChaCha20 block counter for the
  keystream starts at the wrong index (1 instead of 0), so the Poly1305 key
  derivation block overlaps the first keystream block. The English paraphrase
  ("encrypt the plaintext with the ChaCha20 keystream") still reads correctly.
"""

from __future__ import annotations

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language

# --- ChaCha20-Poly1305 / predicate swap / Dafny ----------------------------
# Honest spec: keystream for plaintext starts at counter 1 (block 0 is the
# Poly1305 one-time key). The trojan starts plaintext encryption at counter 0,
# reusing the MAC-key block as keystream.
CHACHA20_POLY1305_PREDICATE_SWAP_DAFNY = CryptoAnchor(
    primitive=CryptoPrimitive.CHACHA20_POLY1305,
    attack_pattern=AttackPattern.PREDICATE_SWAP,
    language=Language.DAFNY,
    nl_requirement=(
        "ChaCha20-Poly1305: block counter 0 derives the Poly1305 one-time "
        "key; plaintext encryption must use the keystream starting at block "
        "counter 1."
    ),
    original_spec="""\
function FirstPtCounter(): (c: nat)
  ensures c == 1
{
  1
}
""",
    trojan_spec="""\
function FirstPtCounter(): (c: nat)
  ensures c == 0                  // SWAP: off-by-one, reuses the MAC-key block
{
  0
}
""",
    trojan_witness="""\
function FirstPtCounter(): (c: nat)
  ensures c == 0
{
  0      // plaintext keystream collides with the Poly1305 key block
}
""",
    bug_source="IACR ePrint 2026/670, Finding 6 - ChaCha20 keystream counter off-by-one",
)

ANCHORS = [CHACHA20_POLY1305_PREDICATE_SWAP_DAFNY]
