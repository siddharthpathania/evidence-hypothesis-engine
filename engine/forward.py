"""
forward.py - FORWARD CHAINING (data-driven reasoning).

Start from the evidence and keep firing every rule whose IF-part is satisfied,
adding its THEN-part to working memory, until nothing new can be concluded.

        evidence  --->  rules fire  --->  new facts  --->  more rules fire  ---> ... ---> hypotheses

Each pass over the rules is called a CYCLE. In every cycle the engine:
  1. MATCH     - finds every rule instantiation whose premises are all believed (CF >= threshold)
  2. FIRE      - computes the conclusion's support:  min(premise CFs) x rule CF
  3. UPDATE    - recombines each fact's CF from all of its supports
  4. Repeats until a cycle changes nothing (a FIXPOINT is reached).

Because every cycle recomputes support from scratch, a conclusion is also WITHDRAWN if
one of its premises later drops below the threshold (e.g. an alibi is verified) -
this is simple "belief revision".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Tuple

from .certainty import THRESHOLD, combine_all
from .explain import Derivation, Explanation
from .knowledge import Case, KnowledgeBase, Rule
from .logic import Atom, Bindings, eval_builtin, is_builtin, substitute, unify

# A support is identified by ("E", index) for evidence, or (rule id, premise facts) for a rule firing.
SupportKey = Tuple
Supports = Dict[Atom, Dict[SupportKey, Derivation]]


@dataclass
class CycleLog:
    cycle: int
    fired: List[Tuple[Rule, Atom, float, Tuple[Atom, ...]]] = field(default_factory=list)
    retracted: List[Tuple[Rule, Atom]] = field(default_factory=list)
    changed: List[Tuple[Atom, float, float]] = field(default_factory=list)  # fact, old CF, new CF


@dataclass
class ForwardResult:
    cf: Dict[Atom, float]
    supports: Supports
    trace: List[CycleLog]
    converged: bool

    def believed(self, pred: str = None, threshold: float = THRESHOLD) -> List[Tuple[Atom, float]]:
        items = [(a, c) for a, c in self.cf.items() if c >= threshold and (pred is None or a.pred == pred)]
        return sorted(items, key=lambda x: (-x[1], str(x[0])))

    def facts_of(self, pred: str) -> List[Tuple[Atom, float]]:
        items = [(a, c) for a, c in self.cf.items() if a.pred == pred]
        return sorted(items, key=lambda x: (-x[1], str(x[0])))

    def explain(self, atom: Atom) -> Explanation:
        """Rebuild the proof tree of a fact from the supports recorded in working memory."""
        def build(a: Atom, path: frozenset) -> Explanation:
            ders = []
            for key, d in self.supports.get(a, {}).items():
                if d.kind == "rule":
                    if a in path:
                        continue
                    kids = [build(p, path | {a}) for p in key[1]]
                    ders.append(Derivation("rule", d.contribution, d.rule, "", kids))
                else:
                    ders.append(d)
            return Explanation(a, self.cf.get(a, 0.0), ders)
        return build(atom, frozenset())


class ForwardChainer:
    def __init__(self, kb: KnowledgeBase, case: Case, threshold: float = THRESHOLD, max_cycles: int = 50):
        self.kb, self.case = kb, case
        self.threshold, self.max_cycles = threshold, max_cycles

    def run(self) -> ForwardResult:
        evidence: Supports = {}
        for i, ev in enumerate(self.case.evidence):
            evidence.setdefault(ev.atom, {})[("E", i)] = Derivation("evidence", ev.cf, None, ev.source)

        rule_supports: Supports = {}
        cf = self._combine(evidence, rule_supports)
        trace: List[CycleLog] = []
        converged = False

        for cycle in range(1, self.max_cycles + 1):
            log = CycleLog(cycle)
            new_supports = self._fire_all(cf)
            new_cf = self._combine(evidence, new_supports)

            for atom, sups in new_supports.items():
                for key, d in sups.items():
                    if key not in rule_supports.get(atom, {}):
                        log.fired.append((d.rule, atom, d.contribution, key[1]))
            for atom, sups in rule_supports.items():
                for key, d in sups.items():
                    if key not in new_supports.get(atom, {}):
                        log.retracted.append((d.rule, atom))
            for atom in sorted(set(cf) | set(new_cf), key=str):
                old, new = cf.get(atom, 0.0), new_cf.get(atom, 0.0)
                if abs(old - new) > 1e-9:
                    log.changed.append((atom, old, new))

            rule_supports, cf = new_supports, new_cf
            if not (log.fired or log.retracted or log.changed):
                converged = True
                break
            trace.append(log)

        all_supports: Supports = {}
        for src in (evidence, rule_supports):
            for atom, sups in src.items():
                all_supports.setdefault(atom, {}).update(sups)
        return ForwardResult(cf, all_supports, trace, converged)

    # ---- helpers ---------------------------------------------------------
    def _combine(self, *sources: Supports) -> Dict[Atom, float]:
        merged: Dict[Atom, List[float]] = {}
        for src in sources:
            for atom, sups in src.items():
                merged.setdefault(atom, []).extend(d.contribution for d in sups.values())
        return {atom: combine_all(vals) for atom, vals in merged.items()}

    def _fire_all(self, cf: Dict[Atom, float]) -> Supports:
        index: Dict[str, List[Atom]] = {}
        for atom, c in cf.items():
            if c >= self.threshold:
                index.setdefault(atom.pred, []).append(atom)

        supports: Supports = {}
        for rule in self.kb.rules:
            for b, used in self._match(rule.premises, 0, {}, (), index):
                conclusion = substitute(rule.conclusion, b)
                strength = min(cf[f] for f in used) * rule.cf
                supports.setdefault(conclusion, {})[(rule.id, used)] = Derivation("rule", strength, rule)
        return supports

    def _match(self, premises: List[Atom], i: int, b: Bindings, used: Tuple[Atom, ...],
               index: Dict[str, List[Atom]]) -> Iterator[Tuple[Bindings, Tuple[Atom, ...]]]:
        """Pattern-match premises left to right against believed facts (depth-first)."""
        if i == len(premises):
            yield b, used
            return
        p = premises[i]
        if is_builtin(p):
            if eval_builtin(p, b):
                yield from self._match(premises, i + 1, b, used, index)
            return
        for fact in index.get(p.pred, []):
            b2 = unify(p, fact, b)
            if b2 is not None:
                yield from self._match(premises, i + 1, b2, used + (fact,), index)
