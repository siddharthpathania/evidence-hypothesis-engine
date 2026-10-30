"""
explain.py - "HOW did you conclude that?"  explanations.

Both chainers produce the same structure, a proof tree:

    Explanation  = one fact + its combined CF + every way it was derived
    Derivation   = one way: from evidence, from the investigator's answer, or from a rule
                   (with the Explanations of that rule's premises as children)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .knowledge import Rule
from .logic import Atom


@dataclass
class Derivation:
    kind: str                       # "evidence" | "asked" | "rule"
    contribution: float             # CF this derivation adds to the fact
    rule: Optional[Rule] = None
    source: str = ""
    premises: List["Explanation"] = field(default_factory=list)


@dataclass
class Explanation:
    atom: Atom
    cf: float
    derivations: List[Derivation] = field(default_factory=list)


def render_tree(expl: Explanation, max_depth: int = 10) -> List[str]:
    """Render a proof tree as text lines using box-drawing characters."""
    lines: List[str] = []
    expanded = set()

    def fact_line(e: Explanation) -> str:
        return f"{e.atom}   [CF {e.cf:+.2f}]"

    def walk(e: Explanation, prefix: str, depth: int):
        if e.atom in expanded and e.derivations and any(d.kind == "rule" for d in e.derivations):
            lines.append(prefix + "    (explained above)")
            return
        expanded.add(e.atom)
        ders = sorted(e.derivations, key=lambda d: -d.contribution)
        for i, d in enumerate(ders):
            last = i == len(ders) - 1
            branch, cont = ("└── ", "    ") if last else ("├── ", "│   ")
            if d.kind == "evidence":
                lines.append(f"{prefix}{branch}EVIDENCE ({d.contribution:+.2f})  {d.source or 'case file'}")
            elif d.kind == "asked":
                lines.append(f"{prefix}{branch}ANSWERED BY INVESTIGATOR ({d.contribution:+.2f})")
            else:
                lines.append(f"{prefix}{branch}RULE {d.rule.id} ({d.contribution:+.2f})  {d.rule.description}")
                if depth >= max_depth:
                    lines.append(prefix + cont + "    ...")
                    continue
                for j, p in enumerate(d.premises):
                    plast = j == len(d.premises) - 1
                    pb, pc = ("└── ", "    ") if plast else ("├── ", "│   ")
                    lines.append(prefix + cont + pb + fact_line(p))
                    walk(p, prefix + cont + pc, depth + 1)

    lines.append(fact_line(expl))
    walk(expl, "", 0)
    return lines


def evidence_used(expl: Explanation) -> List[Atom]:
    """All evidence leaves that a conclusion rests on."""
    found, seen = [], set()

    def walk(e: Explanation):
        if e.atom in seen:
            return
        seen.add(e.atom)
        for d in e.derivations:
            if d.kind in ("evidence", "asked"):
                found.append(e.atom)
            for p in d.premises:
                walk(p)

    walk(expl)
    return found
