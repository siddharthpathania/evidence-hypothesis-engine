"""
certainty.py - MYCIN-style Certainty Factors (CF).

A certainty factor is a number from -1.0 to +1.0:
   +1.0  = definitely true          0.0 = no idea          -1.0 = definitely false

Two rules are used everywhere in the engine:

1. Rule firing     contribution = min(CF of premises) x CF of rule
   (a chain is only as strong as its weakest link)

2. Combining two independent pieces of support for the same fact:
       both positive : a + b(1 - a)
       both negative : a + b(1 + a)
       mixed signs   : (a + b) / (1 - min(|a|, |b|))
"""
from __future__ import annotations

from typing import Iterable

# A fact is treated as "believed" (usable as a rule premise) only if CF >= THRESHOLD.
THRESHOLD = 0.2


def combine(a: float, b: float) -> float:
    if a >= 0 and b >= 0:
        return a + b * (1 - a)
    if a < 0 and b < 0:
        return a + b * (1 + a)
    denom = 1 - min(abs(a), abs(b))
    if denom == 0:  # +1 versus -1: total contradiction
        return 0.0
    return (a + b) / denom


def combine_all(values: Iterable[float]) -> float:
    """Combine many contributions. Positives and negatives are pooled separately and then
    merged once, so the answer never depends on the order in which evidence arrived."""
    pos, neg = 0.0, 0.0
    for v in values:
        if v > 0:
            pos = combine(pos, v)
        elif v < 0:
            neg = combine(neg, v)
    if neg == 0.0:
        return pos
    if pos == 0.0:
        return neg
    return combine(pos, neg)


def verdict(cf: float) -> str:
    if cf >= 0.8:
        return "Strongly supported"
    if cf >= 0.6:
        return "Probable"
    if cf >= 0.4:
        return "Possible"
    if cf >= THRESHOLD:
        return "Weak"
    if cf > -THRESHOLD:
        return "Insufficient evidence"
    return "Refuted"
