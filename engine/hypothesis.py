"""
hypothesis.py - turns raw reasoning results into an INVESTIGATION REPORT.

  1. Forward chaining derives everything the evidence supports.
  2. Each suspect is profiled: motive / means / opportunity / guilty behaviour / culprit CF.
  3. Backward chaining is run on  culprit(<suspect>)  for every suspect to
       - cross-check the forward result (both methods must agree), and
       - collect LEADS: missing evidence that would strengthen or weaken the hypothesis.
  4. Other hypotheses declared in the knowledge base (manner of death, inside job, ...)
     are listed with their CFs.
  5. A conclusion is drawn: a primary hypothesis if one suspect clearly stands out,
     otherwise "inconclusive" with the competing possibilities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .backward import BackwardChainer, Lead
from .certainty import THRESHOLD, verdict
from .forward import ForwardChainer, ForwardResult
from .knowledge import Case, KnowledgeBase
from .logic import Atom

COMPONENTS = ["motive", "means", "opportunity", "guilty_behaviour"]


@dataclass
class SuspectProfile:
    name: str
    culprit_cf: float
    backward_cf: float
    components: Dict[str, float]
    verdict: str
    supporting: List[Tuple[str, float]] = field(default_factory=list)   # (rule text, contribution)
    refuting: List[Tuple[str, float]] = field(default_factory=list)
    leads: List[Lead] = field(default_factory=list)


@dataclass
class InvestigationReport:
    case: Case
    suspects: List[SuspectProfile]
    other_hypotheses: Dict[str, List[Tuple[Atom, float]]]
    conclusion: str
    forward: ForwardResult


def investigate(kb: KnowledgeBase, case: Case, threshold: float = THRESHOLD) -> InvestigationReport:
    fwd = ForwardChainer(kb, case, threshold).run()

    names = sorted({a.args[0] for a, c in fwd.cf.items() if a.pred == "suspect" and c >= threshold})
    profiles = []
    for name in names:
        culprit = Atom("culprit", (name,))
        cf = fwd.cf.get(culprit, 0.0)
        comps = {c: fwd.cf.get(Atom(c, (name,)), 0.0) for c in COMPONENTS}

        bc = BackwardChainer(kb, case, threshold)
        bcf = bc.prove(culprit).cf

        prof = SuspectProfile(name, cf, bcf, comps, verdict(cf))
        for (rule_id, _), d in fwd.supports.get(culprit, {}).items():
            if d.kind == "rule" and d.contribution > 0:
                prof.supporting.append((f"{d.rule.id}: {d.rule.description}", d.contribution))
        # anything that counts AGAINST this person, anywhere in working memory
        for atom, sups in fwd.supports.items():
            if name in atom.args:
                for d in sups.values():
                    if d.contribution < 0:
                        label = f"{d.rule.id}: {d.rule.description}" if d.rule else f"evidence: {atom}"
                        prof.refuting.append((f"{label}  -> {atom}", d.contribution))
        prof.supporting.sort(key=lambda x: -x[1])
        prof.refuting.sort(key=lambda x: x[1])
        # most useful first: leads that would shore up the WEAKEST part of the case
        leads = [l for l in bc.leads if not _already_known(l.atom, case)]
        leads.sort(key=lambda l: (-l.polarity, fwd.cf.get(l.via, 0.0)))
        prof.leads = leads[:8]
        profiles.append(prof)

    profiles.sort(key=lambda p: (-p.culprit_cf, p.name))

    others = {}
    for pred in kb.hypotheses:
        if pred == "culprit":
            continue
        facts = [(a, c) for a, c in fwd.facts_of(pred) if abs(c) >= threshold]
        if facts:
            others[pred] = facts

    return InvestigationReport(case, profiles, others, _conclude(profiles), fwd)


def _already_known(atom: Atom, case: Case) -> bool:
    return any(ev.atom.pred == atom.pred and all(a == "?" or a == b for a, b in zip(atom.args, ev.atom.args))
               for ev in case.evidence)


def _conclude(profiles: List[SuspectProfile]) -> str:
    live = [p for p in profiles if p.culprit_cf >= THRESHOLD]
    if not live:
        return ("INCONCLUSIVE - the evidence does not support any suspect yet. "
                "Follow the investigative leads below.")
    top = live[0]
    if len(live) == 1 or top.culprit_cf - live[1].culprit_cf >= 0.2:
        if top.culprit_cf >= 0.6:
            return (f"PRIMARY HYPOTHESIS - {top.name} (CF {top.culprit_cf:.2f}, {top.verdict.lower()}). "
                    f"The evidence points clearly at this suspect over the others.")
        return (f"LEADING HYPOTHESIS - {top.name} (CF {top.culprit_cf:.2f}), but the support is not yet "
                f"strong enough to be confident. Gather the leads listed for {top.name}.")
    rivals = ", ".join(f"{p.name} ({p.culprit_cf:.2f})" for p in live[:3])
    return (f"COMPETING HYPOTHESES - {rivals} are close. The evidence cannot yet separate them; "
            f"the leads below show what would.")
