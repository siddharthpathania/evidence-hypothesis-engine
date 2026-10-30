"""
logic.py - the basic building blocks of the reasoning engine.

An ATOM is a single statement such as   fingerprint_on(Arjun, Letter_Opener)
   - "fingerprint_on" is the PREDICATE (what kind of statement it is)
   - "Arjun", "Letter_Opener" are the ARGUMENTS (who/what it is about)

An argument that starts with "?" is a VARIABLE, e.g.  fingerprint_on(?p, ?o)
means "some person ?p left fingerprints on some object ?o".

UNIFICATION is the process of making two atoms identical by choosing values
for their variables:
    fingerprint_on(?p, Letter_Opener)  +  fingerprint_on(Arjun, Letter_Opener)
    -> succeeds with bindings {?p: Arjun}
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

Bindings = Dict[str, str]


def is_var(term: str) -> bool:
    return term.startswith("?")


@dataclass(frozen=True)
class Atom:
    pred: str
    args: Tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.pred}({', '.join(self.args)})"

    @property
    def is_ground(self) -> bool:
        """True when the atom has no variables left."""
        return not any(is_var(a) for a in self.args)

    def variables(self) -> set:
        return {a for a in self.args if is_var(a)}


# --------------------------------------------------------------------------
# Parsing  "pred(arg1, arg2, ...)"
# --------------------------------------------------------------------------
_ATOM_RE = re.compile(r"^\s*([a-z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*$")


def parse_atom(text: str) -> Atom:
    m = _ATOM_RE.match(text)
    if not m:
        raise ValueError(f"Cannot parse atom: {text!r} (expected  name(arg1, arg2, ...))")
    pred, inner = m.groups()
    return Atom(pred, tuple(_split_args(inner, text)))


def _split_args(inner: str, original: str) -> list:
    """Split on commas, allowing "double quoted" arguments that contain commas/spaces."""
    args, cur, in_quote = [], [], False
    for ch in inner:
        if ch == '"':
            in_quote = not in_quote
        elif ch == "," and not in_quote:
            args.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if in_quote:
        raise ValueError(f"Unterminated quote in {original!r}")
    tail = "".join(cur).strip()
    if tail or args:
        args.append(tail)
    if any(a == "" for a in args):
        raise ValueError(f"Empty argument in {original!r}")
    return args


# --------------------------------------------------------------------------
# Unification
# --------------------------------------------------------------------------
def walk(term: str, b: Bindings) -> str:
    """Follow a chain of variable bindings (?a -> ?b -> Arjun) to its end."""
    while is_var(term) and term in b:
        term = b[term]
    return term


def unify(x: Atom, y: Atom, b: Bindings) -> Optional[Bindings]:
    """Return extended bindings that make x and y identical, or None if impossible."""
    if x.pred != y.pred or len(x.args) != len(y.args):
        return None
    b = dict(b)
    for a1, a2 in zip(x.args, y.args):
        a1, a2 = walk(a1, b), walk(a2, b)
        if a1 == a2:
            continue
        if is_var(a1):
            b[a1] = a2
        elif is_var(a2):
            b[a2] = a1
        else:
            return None  # two different constants -> clash
    return b


def substitute(atom: Atom, b: Bindings) -> Atom:
    """Replace every bound variable in the atom by its value."""
    return Atom(atom.pred, tuple(walk(a, b) for a in atom.args))


def rename_vars(atom: Atom, suffix: str) -> Atom:
    return Atom(atom.pred, tuple(a + suffix if is_var(a) else a for a in atom.args))


def canonical(atom: Atom) -> Atom:
    """Rename variables to ?0, ?1, ... so that goals differing only in variable names compare equal."""
    mapping: Dict[str, str] = {}
    out = []
    for a in atom.args:
        if is_var(a):
            mapping.setdefault(a, f"?{len(mapping)}")
            out.append(mapping[a])
        else:
            out.append(a)
    return Atom(atom.pred, tuple(out))


# --------------------------------------------------------------------------
# Built-in tests that can appear in rule premises, e.g.  between(?t, ?start, ?end)
# Values like "21:30" are understood as clock times, "9" as numbers.
# --------------------------------------------------------------------------
_CLOCK_RE = re.compile(r"(\d{1,2}):(\d{2})")


def _value(term: str):
    m = _CLOCK_RE.fullmatch(term)
    if m:
        return (0, int(m.group(1)) * 60 + int(m.group(2)))
    try:
        return (0, float(term))
    except ValueError:
        return (1, term.lower())


BUILTINS = {
    "eq": (2, lambda a, b: _value(a) == _value(b)),
    "neq": (2, lambda a, b: _value(a) != _value(b)),
    "lt": (2, lambda a, b: _value(a) < _value(b)),
    "le": (2, lambda a, b: _value(a) <= _value(b)),
    "gt": (2, lambda a, b: _value(a) > _value(b)),
    "ge": (2, lambda a, b: _value(a) >= _value(b)),
    "between": (3, lambda x, lo, hi: _between(x, lo, hi)),
}


def _between(x: str, lo: str, hi: str) -> bool:
    vx, vlo, vhi = _value(x), _value(lo), _value(hi)
    clock = all(_CLOCK_RE.fullmatch(t) for t in (x, lo, hi))
    if clock and vlo > vhi:            # overnight window, e.g. 23:00 -> 01:00
        return vx >= vlo or vx <= vhi
    return vlo <= vx <= vhi


def is_builtin(atom: Atom) -> bool:
    return atom.pred in BUILTINS


def eval_builtin(atom: Atom, b: Bindings) -> bool:
    ground = substitute(atom, b)
    if not ground.is_ground:
        raise ValueError(f"Test {atom} used before all its variables were bound")
    _, fn = BUILTINS[atom.pred]
    return bool(fn(*ground.args))
