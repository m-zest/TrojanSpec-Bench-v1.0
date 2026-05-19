"""Diagnose the 3 failed implementation_leak sanity triples: exact dual-property
verdict + verifier stderr for the trojan and original compositions."""
import glob, json
from trojanspec.schemas import Language
from trojanspec.verifiers import VERIFIERS
from trojanspec.verifiers.compose import compose

for f in sorted(glob.glob("data/triples_sanity/*/*/*.json")):
    d = json.load(open(f))
    if d.get("attack_pattern") != "implementation_leak":
        continue
    lang = Language(d["language"])
    vf = VERIFIERS[lang]
    pre, orig, troj, wit = (d.get("preamble") or ""), d["original_spec"], d["trojan_spec"], d["trojan_witness"]
    troj_src = compose(pre, troj, wit, lang)
    orig_src = compose(pre, orig, wit, lang)
    rt, ro = vf(troj_src), vf(orig_src)
    print(f"\n######## {d['language']} {d['triple_id'][:8]} ########")
    print(f"acc_troj={rt.accepts}  rej_orig={not ro.accepts}  "
          f"(troj.accepts={rt.accepts}, orig.accepts={ro.accepts})")
    print("--- trojan compose ---\n" + troj_src)
    if not rt.accepts:
        print("--- trojan stderr/stdout ---\n" + (rt.stderr or rt.stdout)[:1500])
    print("--- original compose ---\n" + orig_src)
    if ro.accepts:
        print("(!) original ACCEPTED the witness -> no real weakening")
