"""Cryptographic anchors.

Hand-written trojan templates tied to publicly disclosed weaknesses in
post-quantum and classical primitives. Each anchor is a ready-made hard-tier
triple source. See ``docs/disclosure_policy.md``: only disclosed bugs are used.
"""

from trojanspec.crypto.anchor import CryptoAnchor
from trojanspec.crypto.anchor_registry import ANCHORS, get_anchor, list_anchors

__all__ = ["ANCHORS", "CryptoAnchor", "get_anchor", "list_anchors"]
