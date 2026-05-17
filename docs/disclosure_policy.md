# Disclosure Policy

TrojanSpec-Bench includes trojan witnesses modeled on real cryptographic
vulnerabilities. We follow coordinated disclosure.

1. **No undisclosed bugs.** Trojan witnesses are included only for primitives
   whose underlying weakness has been publicly disclosed (IACR ePrint
   2026/192, IACR ePrint 2026/670, and other published write-ups).
2. **Maintainer notification.** Before releasing any *new* bug class, we email
   the affected maintainers (Cryspen, Symbolic Software, and others as
   relevant) with at least a **90-day** window.
3. **CVE assignment.** Where applicable we request a CVE via MITRE or a GitHub
   Security Advisory.
4. **Acknowledgement.** Maintainers who fix disclosed bugs are credited in the
   dataset citation.

The benchmark entry corresponding to any newly surfaced bug is published only
**after** a fix is released or the disclosure window elapses, whichever comes
first.

A ready-to-send notification template lives in
[`templates/disclosure_email.txt`](templates/disclosure_email.txt).
