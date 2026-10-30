"""AI Evidence & Hypothesis Engine - a rule-based expert system with forward and backward chaining."""
from .backward import BackwardChainer, Lead
from .certainty import THRESHOLD, combine, combine_all, verdict
from .explain import Explanation, render_tree
from .forward import ForwardChainer, ForwardResult
from .hypothesis import InvestigationReport, investigate
from .knowledge import Case, Evidence, KnowledgeBase, Rule, case_from_dict, load_case, load_kb, parse_kb
from .logic import Atom, parse_atom, unify

__all__ = [
    "Atom", "parse_atom", "unify", "Rule", "KnowledgeBase", "Case", "Evidence",
    "load_kb", "parse_kb", "load_case", "case_from_dict", "ForwardChainer", "ForwardResult",
    "BackwardChainer", "Lead", "Explanation", "render_tree", "investigate", "InvestigationReport",
    "THRESHOLD", "combine", "combine_all", "verdict",
]
