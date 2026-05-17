"""Human-review interface for generated triples.

    streamlit run scripts/03_review_triples.py

Presents NL + original spec + trojan spec + witness side by side and records
an accept / reject / edit decision with reviewer attribution.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from trojanspec.generators.reviewer import (
    load_triples,
    record_decision,
    save_triple,
    unreviewed,
)

st.set_page_config(page_title="TrojanSpec Reviewer", layout="wide")
DATA_DIR = Path("data/triples")

reviewer = st.sidebar.text_input("Reviewer name", value="zeeshan")

pairs = load_triples(DATA_DIR)
todo = unreviewed(pairs)
st.sidebar.metric("Unreviewed", f"{len(todo)} / {len(pairs)}")

if not todo:
    st.success("All triples reviewed.")
    st.stop()

idx = st.session_state.get("idx", 0) % len(todo)
path, triple = todo[idx]

st.title(f"{triple.attack_pattern.value}  ·  {triple.language.value}  ·  {triple.difficulty.value}")
st.caption(
    f"id {triple.triple_id[:8]}  ·  source {triple.source_benchmark.value}  "
    f"·  elicitor {triple.elicitor_model}"
)

left, right = st.columns(2)
with left:
    st.subheader("Natural-language requirement")
    st.write(triple.nl_requirement)
    st.subheader("Original (honest) spec")
    st.code(triple.original_spec, language=triple.language.value)
with right:
    st.subheader("Trojan spec")
    st.code(triple.trojan_spec, language=triple.language.value)
    st.subheader("Trojan witness")
    st.code(triple.trojan_witness, language=triple.language.value)

decision = st.radio("Decision", ["accept", "reject", "edit"], horizontal=True)
notes = st.text_area("Notes")

c1, c2 = st.columns(2)
if c1.button("Submit", type="primary"):
    record_decision(
        triple, reviewer=reviewer, accepted=(decision == "accept"), notes=notes
    )
    save_triple(path, triple)
    st.session_state["idx"] = idx + 1
    st.rerun()
if c2.button("Skip"):
    st.session_state["idx"] = idx + 1
    st.rerun()
