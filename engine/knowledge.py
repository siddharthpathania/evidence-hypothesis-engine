"""
knowledge.py - the KNOWLEDGE BASE (rules) and the CASE FILE (evidence).

Rules are written in a small, readable language (see knowledge/crime_rules.kb):

    RULE R10 "Fingerprints on the weapon link a person to it"
      IF   murder_weapon(?o)
      AND  fingerprint_on(?p, ?o)
      THEN handled_weapon(?p)
      CF   0.8

    ASK fingerprint_on "Were {0}'s fingerprints found on {1}?"
    HYPOTHESIS culprit "Who most likely committed the crime"

Cases are JSON files with a list of evidence records (see cases/*.json).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .logic import BUILTINS, Atom, is_builtin, is_var, parse_atom


@dataclass
class Rule:
    id: str
    description: str
    premises: List[Atom]
    conclusion: Atom
    cf: float

    def __str__(self) -> str:
        return f"IF {' AND '.join(map(str, self.premises))} THEN {self.conclusion}  (CF {self.cf:+.2f})"


@dataclass
class KnowledgeBase:
    rules: List[Rule] = field(default_factory=list)
    askable: Dict[str, str] = field(default_factory=dict)      # predicate -> question template
    hypotheses: Dict[str, str] = field(default_factory=dict)   # predicate -> description

    def rules_for(self, pred: str) -> List[Rule]:
        return [r for r in self.rules if r.conclusion.pred == pred]

    def derived_predicates(self) -> set:
        return {r.conclusion.pred for r in self.rules}

    def question_for(self, atom: Atom) -> str:
        template = self.askable.get(atom.pred)
        shown = [("something" if is_var(a) else a.replace("_", " ")) for a in atom.args]
        if template:
            try:
                return template.format(*shown)
            except (IndexError, KeyError):
                pass
        return f"Is it true that {atom}?"


@dataclass
class Evidence:
    atom: Atom
    cf: float = 1.0
    source: str = ""


@dataclass
class Case:
    title: str
    summary: str
    evidence: List[Evidence]
    path: str = ""


# --------------------------------------------------------------------------
# Rule-file parser
# --------------------------------------------------------------------------
_RULE_RE = re.compile(r'^RULE\s+(\S+)\s*(?:"(.*)")?\s*$', re.I)
_ASK_RE = re.compile(r'^ASK\s+(\w+)\s+"(.*)"\s*$', re.I)
_HYP_RE = re.compile(r'^HYPOTHESIS\s+(\w+)\s+"(.*)"\s*$', re.I)
_KW_RE = re.compile(r"^(IF|AND|THEN|CF)\s+(.*)$", re.I)


class KBSyntaxError(ValueError):
    pass


def parse_kb(text: str, filename: str = "<rules>") -> KnowledgeBase:
    kb = KnowledgeBase()
    current = None  # dict being filled for the rule under construction

    def finish(lineno: int):
        if current is None:
            return
        where = f"{filename}: rule {current['id']}"
        if not current["premises"] or current["conclusion"] is None or current["cf"] is None:
            raise KBSyntaxError(f"{where} needs IF, THEN and CF lines")
        rule = Rule(current["id"], current["desc"], current["premises"], current["conclusion"], current["cf"])
        _validate(rule, where)
        if any(r.id == rule.id for r in kb.rules):
            raise KBSyntaxError(f"{where}: duplicate rule id")
        kb.rules.append(rule)

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            if m := _RULE_RE.match(line):
                finish(lineno)
                current = {"id": m.group(1), "desc": m.group(2) or "", "premises": [],
                           "conclusion": None, "cf": None}
            elif m := _ASK_RE.match(line):
                kb.askable[m.group(1)] = m.group(2)
            elif m := _HYP_RE.match(line):
                kb.hypotheses[m.group(1)] = m.group(2)
            elif m := _KW_RE.match(line):
                if current is None:
                    raise KBSyntaxError("IF/AND/THEN/CF outside of a RULE")
                kw, rest = m.group(1).upper(), m.group(2)
                if kw in ("IF", "AND"):
                    current["premises"].append(parse_atom(rest))
                elif kw == "THEN":
                    current["conclusion"] = parse_atom(rest)
                else:
                    current["cf"] = float(rest)
            else:
                raise KBSyntaxError(f"Unrecognised line: {raw.strip()!r}")
        except ValueError as e:
            raise KBSyntaxError(f"{filename}:{lineno}: {e}") from None
    finish(-1)
    return kb


def _validate(rule: Rule, where: str) -> None:
    if not -1.0 <= rule.cf <= 1.0:
        raise KBSyntaxError(f"{where}: CF must be between -1 and 1")
    if is_builtin(rule.conclusion):
        raise KBSyntaxError(f"{where}: a built-in test cannot be a conclusion")
    bound = set()
    for p in rule.premises:
        if is_builtin(p):
            arity = BUILTINS[p.pred][0]
            if len(p.args) != arity:
                raise KBSyntaxError(f"{where}: {p.pred} takes {arity} arguments")
            if not p.variables() <= bound:
                raise KBSyntaxError(f"{where}: test {p} uses a variable before it is bound")
        else:
            bound |= p.variables()
    if not rule.conclusion.variables() <= bound:
        raise KBSyntaxError(f"{where}: every variable in THEN must appear in an IF/AND")
    if all(is_builtin(p) for p in rule.premises):
        raise KBSyntaxError(f"{where}: needs at least one non-test premise")


def load_kb(path) -> KnowledgeBase:
    path = Path(path)
    return parse_kb(path.read_text(encoding="utf-8"), path.name)


# --------------------------------------------------------------------------
# Case files
# --------------------------------------------------------------------------
def case_from_dict(data: dict, path: str = "") -> Case:
    evidence = []
    for i, item in enumerate(data.get("evidence", []), 1):
        if isinstance(item, str):
            item = {"fact": item}
        try:
            atom = parse_atom(item["fact"])
            cf = float(item.get("cf", 1.0))
        except (KeyError, ValueError) as e:
            raise ValueError(f"{path or 'case'}: evidence #{i}: {e}") from None
        if not atom.is_ground:
            raise ValueError(f"{path or 'case'}: evidence #{i} must not contain variables: {atom}")
        if not -1.0 <= cf <= 1.0:
            raise ValueError(f"{path or 'case'}: evidence #{i}: cf must be between -1 and 1")
        evidence.append(Evidence(atom, cf, item.get("source", "")))
    return Case(data.get("title", Path(path).stem if path else "Untitled case"),
                data.get("summary", ""), evidence, str(path))


def load_case(path) -> Case:
    path = Path(path)
    return case_from_dict(json.loads(path.read_text(encoding="utf-8")), str(path))
