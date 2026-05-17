"""Human-review interface for generated triples (Phase 6).

    streamlit run scripts/03_review_triples.py

Left column: natural-language requirement + original (honest) spec.
Right column: trojan spec + trojan witness.
Below: metadata and Accept / Reject / Edit actions. "Edit" opens editable
text areas for the trojan spec and witness; the edited text is persisted back
to the triple's JSON file along with reviewer, decision, notes and timestamp.

A sidebar filters by language, attack pattern, difficulty and review status,
and shows a live progress counter.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from trojanspec.generators.reviewer import (
    apply_edits,
    filter_pairs,
    load_triples,
    record_decision,
    save_triple,
    summary_counts,
)

st.set_page_config(page_title="TrojanSpec Reviewer", layout="wide")
DATA_DIR = Path("data/triples")

pairs = load_triples(DATA_DIR)

# --- Sidebar: reviewer, filters, progress ----------------------------------
st.sidebar.header("Reviewer")
reviewer = st.sidebar.text_input("Reviewer name", value="zeeshan")

st.sidebar.header("Filters")
langs = sorted({t.language.value for _, t in pairs})
attacks = sorted({t.attack_pattern.value for _, t in pairs})
diffs = sorted({t.difficulty.value for _, t in pairs})

f_lang = st.sidebar.selectbox("Language", ["(any)", *langs])
f_attack = st.sidebar.selectbox("Attack pattern", ["(any)", *attacks])
f_diff = st.sidebar.selectbox("Difficulty", ["(any)", *diffs])
status = st.sidebar.radio("Status", ["unreviewed only", "all"], horizontal=False)

reviewed, total, accepted = summary_counts(pairs)
st.sidebar.header("Progress")
st.sidebar.write(f"**{reviewed} / {total}** reviewed, **{accepted}** accepted")
st.sidebar.progress(reviewed / total if total else 0.0)

if not pairs:
    st.warning("No triples found under data/triples/. Run scripts/02 first.")
    st.stop()

view = filter_pairs(
    pairs,
    language=None if f_lang == "(any)" else f_lang,
    attack=None if f_attack == "(any)" else f_attack,
    difficulty=None if f_diff == "(any)" else f_diff,
    unreviewed_only=(status == "unreviewed only"),
)

if not view:
    st.success("Nothing to review for the current filter.")
    st.stop()

idx = st.session_state.get("idx", 0) % len(view)
path, triple = view[idx]
st.caption(f"Item {idx + 1} / {len(view)} in current filter")

# --- Main panel ------------------------------------------------------------
st.title(
    f"{triple.attack_pattern.value}  ·  {triple.language.value}  ·  "
    f"{triple.difficulty.value}"
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

st.divider()
m = st.columns(5)
m[0].metric("Language", triple.language.value)
m[1].metric("Difficulty", triple.difficulty.value)
m[2].metric("Attack", triple.attack_pattern.value)
m[3].metric("Source", triple.source_benchmark.value)
m[4].metric("Elicitor", triple.elicitor_model.split("/")[-1])

notes = st.text_area("Review notes", value=triple.review_notes or "")
a, r, e = st.columns(3)
accept_clicked = a.button("Accept", type="primary", use_container_width=True)
reject_clicked = r.button("Reject", use_container_width=True)
edit_mode = e.toggle("Edit", value=False)

if edit_mode:
    st.info("Editing trojan fields. Save & Accept persists the edited text.")
    new_spec = st.text_area("trojan_spec", value=triple.trojan_spec, height=220)
    new_witness = st.text_area("trojan_witness", value=triple.trojan_witness, height=220)
    if st.button("Save & Accept edits", type="primary"):
        apply_edits(triple, trojan_spec=new_spec, trojan_witness=new_witness)
        record_decision(
            triple,
            reviewer=reviewer,
            accepted=True,
            notes=(notes + " [edited]").strip(),
        )
        save_triple(path, triple)
        st.session_state["idx"] = idx + 1
        st.rerun()

if accept_clicked or reject_clicked:
    record_decision(
        triple, reviewer=reviewer, accepted=accept_clicked, notes=notes
    )
    save_triple(path, triple)
    st.session_state["idx"] = idx + 1
    st.rerun()

if st.button("Skip"):
    st.session_state["idx"] = idx + 1
    st.rerun()
