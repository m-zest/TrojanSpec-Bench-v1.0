from trojanspec.crypto import ANCHORS, list_anchors
from trojanspec.crypto.anchor_registry import get_anchor
from trojanspec.schemas import AttackPattern, CryptoPrimitive, Language


def test_registry_non_empty_and_keyed_consistently():
    assert ANCHORS
    for key, anchor in ANCHORS.items():
        assert key == anchor.key
        assert anchor.primitive != CryptoPrimitive.NONE


def test_every_anchor_is_structurally_complete():
    for a in ANCHORS.values():
        assert a.nl_requirement.strip()
        assert a.original_spec.strip()
        assert a.trojan_spec.strip()
        assert a.trojan_witness.strip()
        assert a.bug_source.strip()
        # The trojan must actually differ from the honest spec.
        assert a.trojan_spec != a.original_spec or a.trojan_witness != a.original_spec


def test_lookup_and_filter():
    a = get_anchor(
        CryptoPrimitive.ML_KEM_768,
        AttackPattern.DOMAIN_RESTRICTION,
        Language.DAFNY,
    )
    assert a is not None
    assert a.primitive == CryptoPrimitive.ML_KEM_768
    assert get_anchor(CryptoPrimitive.SHA3, AttackPattern.VACUITY, Language.LEAN) is None
    assert all(
        x.language == Language.DAFNY for x in list_anchors(language=Language.DAFNY)
    )
