"""
Web interface for the AI Evidence & Hypothesis Engine.

    pip install streamlit pandas
    streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from engine import (BackwardChainer, case_from_dict, investigate, load_kb, parse_atom, render_tree,
                    verdict)

ROOT = Path(__file__).resolve().parent
KB_PATH = ROOT / "knowledge" / "crime_rules.kb"
CASES = sorted((ROOT / "cases").glob("*.json"))

st.set_page_config(page_title="Evidence & Hypothesis Engine", page_icon="🔎", layout="wide")


@st.cache_resource
def get_kb():
    return load_kb(KB_PATH)


kb = get_kb()

# ---------------------------------------------------------------- sidebar
st.sidebar.title("🔎 Evidence Engine")
st.sidebar.caption("Rule-based expert system · forward & backward chaining · certainty factors")
choice = st.sidebar.selectbox("Case file", [p.name for p in CASES] + ["Upload my own..."])
if choice == "Upload my own...":
    upload = st.sidebar.file_uploader("Case JSON", type="json")
    if not upload:
        st.info("Upload a case file in the same format as the files in the `cases/` folder.")
        st.stop()
    raw = json.load(upload)
else:
    raw = json.loads((ROOT / "cases" / choice).read_text(encoding="utf-8"))

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Knowledge base:** {len(kb.rules)} rules")
st.sidebar.markdown("**CF scale:** -1 (false) … 0 (unknown) … +1 (true)")

# ---------------------------------------------------------------- case + evidence editor
st.title(raw.get("title", "Untitled case"))
st.write(raw.get("summary", ""))

with st.expander("📁 Evidence on record - edit, add or remove rows and the analysis updates", expanded=False):
    df = pd.DataFrame([{"fact": e["fact"] if isinstance(e, dict) else e,
                        "cf": float(e.get("cf", 1.0)) if isinstance(e, dict) else 1.0,
                        "source": e.get("source", "") if isinstance(e, dict) else ""}
                       for e in raw.get("evidence", [])])
    edited = st.data_editor(
        df, num_rows="dynamic", width="stretch", key=f"ev_{choice}",
        column_config={
            "fact": st.column_config.TextColumn("Fact", help="e.g. fingerprint_on(Arjun, Letter_Opener)"),
            "cf": st.column_config.NumberColumn("CF", min_value=-1.0, max_value=1.0, step=0.05),
            "source": st.column_config.TextColumn("Source / record"),
        })

rows = [{"fact": str(r.fact).strip(), "cf": 1.0 if pd.isna(r.cf) else float(r.cf),
         "source": "" if pd.isna(r.source) else str(r.source)}
        for r in edited.itertuples() if isinstance(r.fact, str) and r.fact.strip()]
try:
    case = case_from_dict({**raw, "evidence": rows})
except ValueError as e:
    st.error(f"Evidence error: {e}")
    st.stop()

report = investigate(kb, case)
fwd = report.forward

# ---------------------------------------------------------------- tabs
t_hyp, t_explain, t_fwd, t_bwd, t_rules = st.tabs(
    ["🧠 Hypotheses", "🌳 Explain a conclusion", "➡️ Forward chaining", "⬅️ Backward chaining", "📚 Rules"])

with t_hyp:
    msg = report.conclusion
    (st.success if msg.startswith("PRIMARY") else st.warning if msg.startswith(("LEADING", "COMPETING"))
     else st.info)(msg)

    table = pd.DataFrame([{
        "Suspect": p.name, "Motive": p.components["motive"], "Means": p.components["means"],
        "Opportunity": p.components["opportunity"], "Guilty behaviour": p.components["guilty_behaviour"],
        "Culprit CF": p.culprit_cf, "Verdict": p.verdict,
        "Backward check": "✓" if abs(p.culprit_cf - p.backward_cf) < 1e-6 else "✗",
    } for p in report.suspects])
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Suspect ranking")
        cf_col = st.column_config.NumberColumn(format="%+.2f")
        st.dataframe(table, width="stretch", hide_index=True, column_config={
            c: cf_col for c in ["Motive", "Means", "Opportunity", "Guilty behaviour", "Culprit CF"]})
    with c2:
        st.subheader("Culprit certainty")
        st.bar_chart(table.set_index("Suspect")["Culprit CF"])

    st.subheader("Why each suspect is ranked where they are")
    for p in report.suspects:
        with st.expander(f"{p.name} - CF {p.culprit_cf:+.2f} ({p.verdict})"):
            for text, c in p.supporting:
                st.markdown(f"🟢 **{c:+.2f}** {text}")
            for text, c in p.refuting:
                st.markdown(f"🔴 **{c:+.2f}** {text}")
            if not (p.supporting or p.refuting):
                st.caption("No rule linking this suspect to the crime has fired.")
            if p.leads:
                st.markdown("**Investigative leads** (evidence that is missing):")
                for l in p.leads[:6]:
                    effect = "strengthen" if l.polarity > 0 else "weaken"
                    st.markdown(f"- ❓ {l.question} → would *{effect}* "
                                f"**{l.via.pred.replace('_', ' ')}** ({l.rule.id})")

    if report.other_hypotheses:
        st.subheader("Scene hypotheses")
        for pred, facts in report.other_hypotheses.items():
            st.markdown(f"**{kb.hypotheses[pred]}**")
            for atom, cf in facts:
                st.progress(min(abs(cf), 1.0), text=f"{atom}  →  CF {cf:+.2f} ({verdict(cf)})")

with t_explain:
    derived = sorted((a for a in fwd.cf if any(d.kind == "rule" for d in fwd.supports.get(a, {}).values())),
                     key=lambda a: (a.pred != "culprit", -fwd.cf[a]))
    if derived:
        pick = st.selectbox("Conclusion", derived, format_func=lambda a: f"{a}   (CF {fwd.cf[a]:+.2f})")
        st.caption("HOW was this concluded? Each RULE node shows its contribution; leaves are evidence.")
        st.code("\n".join(render_tree(fwd.explain(pick))), language=None)

with t_fwd:
    st.markdown("Data-driven: start from the evidence and fire every rule whose IF-part holds, "
                "cycle after cycle, until nothing changes (**fixpoint**).")
    st.metric("Inference cycles", len(fwd.trace))
    for log in fwd.trace:
        with st.expander(f"Cycle {log.cycle}: {len(log.fired)} rules fired, {len(log.retracted)} retracted",
                         expanded=log.cycle == 1):
            for rule, atom, c, prem in log.fired:
                st.markdown(f"🔥 **{rule.id}** ⇒ `{atom}` **{c:+.2f}**  \n"
                            f"<small>because {', '.join(map(str, prem))}</small>", unsafe_allow_html=True)
            for rule, atom in log.retracted:
                st.markdown(f"↩️ **{rule.id}** retracted `{atom}`")
            if log.changed:
                st.caption("CF updates: " + "; ".join(f"{a} {o:+.2f}→{n:+.2f}" for a, o, n in log.changed))

with t_bwd:
    st.markdown("Goal-driven: start from a hypothesis and work backwards through the rules to the evidence. "
                "Use `?variables` to ask *who* / *what*.")
    examples = ["culprit(?who)", "motive(?who)", "opportunity(?who)", "manner_of_death(?v, ?how)",
                "murder_weapon(?o)", "possible_collusion(?a, ?b)"]
    goal_text = st.text_input("Goal", value="culprit(?who)", help="Examples: " + ", ".join(examples))
    try:
        goal = parse_atom(goal_text)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    bc = BackwardChainer(kb, case)
    answers = bc.query(goal)
    if not answers:
        st.warning("Nothing in the evidence supports this goal.")
    for e in answers:
        st.markdown(f"**{e.atom}** - CF **{e.cf:+.2f}** ({verdict(e.cf)})")
        with st.expander("Proof tree"):
            st.code("\n".join(render_tree(e)), language=None)
    if bc.leads:
        st.markdown("**Missing evidence that would change the answer**")
        for l in bc.leads[:10]:
            st.markdown(f"- {'➕' if l.polarity > 0 else '➖'} {l.question} `({l.rule.id})`")
    with st.expander("Search trace"):
        st.code("\n".join(bc.trace), language=None)

with t_rules:
    st.dataframe(pd.DataFrame([{"ID": r.id, "Description": r.description,
                                "IF": " ∧ ".join(map(str, r.premises)), "THEN": str(r.conclusion),
                                "CF": r.cf} for r in kb.rules]),
                 width="stretch", hide_index=True)
