"""
backward.py - BACKWARD CHAINING (goal-driven reasoning).

Start from a HYPOTHESIS (goal) such as  culprit(Arjun)  or  culprit(?who)
and work backwards:

    goal  <---  which rules could conclude it?  <---  can I prove THEIR premises?  <--- ... <--- evidence

To prove a goal the engine:
  1. looks for matching EVIDENCE in the case file;
  2. (interactive mode) ASKS the investigator if the goal is an askable, ground fact;
  3. for every rule whose THEN-part unifies with the goal, tries to prove all its
     IF-parts recursively (depth-first, left to right), passing variable bindings along.

Extra features that fall out naturally from goal-driven search:
  * LEADS     - when an ASKABLE premise (evidence about a person) is missing, it is recorded as
                "evidence that would strengthen (or weaken) this hypothesis".
  * WHY       - while asking a question, the engine can show the chain of goals and rules
                that made it ask.
  * TRACE     - every goal tried, rule attempted and fact found is logged.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from .certainty import THRESHOLD, combine_all
from .explain import Derivation, Explanation
from .knowledge import Case, KnowledgeBase, Rule
from .logic import (Atom, Bindings, canonical, eval_builtin, is_builtin, rename_vars,
                    substitute, unify)

# ask(goal, question, why_lines) -> CF in [-1, 1], or None for "unknown"
AskFn = Callable[[Atom, str, List[str]], Optional[float]]


@dataclass
class Lead:
    atom: Atom              # the missing piece of evidence
    question: str           # human-readable form
    rule: Rule              # rule that needed it
    hypothesis: Atom        # top-level goal being investigated
    polarity: int           # +1 would strengthen the hypothesis, -1 would weaken it
    via: Atom               # the sub-goal of the hypothesis it feeds, e.g. means(Sunil)


@dataclass
class BackwardChainer:
    kb: KnowledgeBase
    case: Case
    threshold: float = THRESHOLD
    ask: Optional[AskFn] = None
    max_depth: int = 30
    trace: List[str] = field(default_factory=list)
    leads: List[Lead] = field(default_factory=list)

    def __post_init__(self):
        self._facts: Dict[str, list] = {}
        for ev in self.case.evidence:
            self._facts.setdefault(ev.atom.pred, []).append(ev)
        self._memo: Dict[Atom, Dict[Atom, Explanation]] = {}
        self._active: set = set()
        self._answers: Dict[Atom, Optional[float]] = {}
        self._stack: List[Tuple[Atom, Rule]] = []   # (goal, rule being tried) - used for WHY
        self._counter = itertools.count(1)

    # ---- public API ------------------------------------------------------
    def query(self, goal: Atom) -> List[Explanation]:
        """All ground instances of the goal that could be established, strongest first."""
        self._top_goal = goal
        results = self._solve(goal, 0)
        return sorted(results.values(), key=lambda e: (-e.cf, str(e.atom)))

    def prove(self, goal: Atom) -> Explanation:
        """CF and proof tree for one ground hypothesis (CF 0 if nothing supports it)."""
        for e in self.query(goal):
            if e.atom == goal:
                return e
        return Explanation(goal, 0.0, [])

    @property
    def answers(self) -> Dict[Atom, Optional[float]]:
        return dict(self._answers)

    # ---- the recursive solver --------------------------------------------
    def _solve(self, goal: Atom, depth: int) -> Dict[Atom, Explanation]:
        key = canonical(goal)
        if key in self._memo:
            self._log(depth, f"GOAL {goal}  (already solved)")
            return self._memo[key]
        if key in self._active or depth > self.max_depth:
            self._log(depth, f"GOAL {goal}  (loop/depth limit - skipped)")
            return {}
        self._active.add(key)
        self._log(depth, f"GOAL {goal}")

        derivs: Dict[Atom, List[Derivation]] = {}

        # 1. evidence in the case file
        for ev in self._facts.get(goal.pred, []):
            if unify(goal, ev.atom, {}) is not None:
                self._log(depth + 1, f"FACT {ev.atom}  CF {ev.cf:+.2f}  ({ev.source or 'case file'})")
                derivs.setdefault(ev.atom, []).append(Derivation("evidence", ev.cf, None, ev.source))

        # 2. ask the investigator
        if not derivs and self.ask and goal.is_ground and goal.pred in self.kb.askable:
            if goal not in self._answers:
                why = self._why_lines(goal)
                self._answers[goal] = self.ask(goal, self.kb.question_for(goal), why)
            ans = self._answers[goal]
            if ans is not None:
                self._log(depth + 1, f"ASKED {goal} -> CF {ans:+.2f}")
                derivs.setdefault(goal, []).append(Derivation("asked", ans))

        # 3. rules that conclude the goal
        for rule in self.kb.rules_for(goal.pred):
            suffix = f"_{next(self._counter)}"
            head = rename_vars(rule.conclusion, suffix)
            b = unify(goal, head, {})
            if b is None:
                continue
            self._log(depth + 1, f"TRY {rule.id}: {rule.description}")
            premises = [rename_vars(p, suffix) for p in rule.premises]
            self._stack.append((goal, rule))
            found = False
            for b2, kids in self._solve_premises(premises, 0, b, depth + 2, rule):
                conclusion = substitute(head, b2)
                strength = min(k.cf for k in kids) * rule.cf
                derivs.setdefault(conclusion, []).append(Derivation("rule", strength, rule, "", kids))
                self._log(depth + 1, f"{rule.id} => {conclusion}  contribution {strength:+.2f}")
                found = True
            self._stack.pop()
            if not found:
                self._log(depth + 1, f"{rule.id} failed")

        results = {a: Explanation(a, combine_all(d.contribution for d in ds), ds) for a, ds in derivs.items()}
        self._active.discard(key)
        self._memo[key] = results
        return results

    def _solve_premises(self, premises: List[Atom], i: int, b: Bindings, depth: int,
                        rule: Rule) -> Iterator[Tuple[Bindings, List[Explanation]]]:
        if i == len(premises):
            yield b, []
            return
        p = substitute(premises[i], b)
        if is_builtin(p):
            ok = eval_builtin(p, b)
            self._log(depth, f"TEST {p} -> {'true' if ok else 'false'}")
            if ok:
                yield from self._solve_premises(premises, i + 1, b, depth, rule)
            return

        solutions = [e for e in self._solve(p, depth).values() if e.cf >= self.threshold]
        if not solutions:
            self._record_lead(p, rule)
            return
        for e in sorted(solutions, key=lambda e: str(e.atom)):
            b2 = unify(p, e.atom, b)
            if b2 is None:
                continue
            for b3, rest in self._solve_premises(premises, i + 1, b2, depth, rule):
                yield b3, [e] + rest

    # ---- leads, WHY and trace ----------------------------------------------
    def _record_lead(self, atom: Atom, rule: Rule) -> None:
        if atom.pred not in self.kb.askable or not self._stack:
            return
        if self._answers.get(atom) is not None:  # the investigator already answered it
            return
        polarity = 1
        for _, r in self._stack:
            polarity *= 1 if r.cf >= 0 else -1
        clean = Atom(atom.pred, tuple(a if not a.startswith("?") else "?" for a in atom.args))
        if any(l.atom == clean and l.polarity == polarity for l in self.leads):
            return
        via = self._stack[1][0] if len(self._stack) > 1 else self._stack[0][0]
        self.leads.append(Lead(clean, self.kb.question_for(atom), rule, self._stack[0][0], polarity, via))

    def _why_lines(self, goal: Atom) -> List[str]:
        lines = []
        for g, r in self._stack:
            lines.append(f"I am trying to establish {g} using {r.id} ({r.description}):")
            lines.append(f"    {r}")
        lines.append(f"...and that needs to know whether {goal}.")
        return lines

    def _log(self, depth: int, msg: str) -> None:
        self.trace.append("  " * depth + msg)
