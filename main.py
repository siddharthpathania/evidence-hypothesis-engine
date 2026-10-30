#!/usr/bin/env python3
"""
AI Evidence & Hypothesis Engine - command-line interface.

    python main.py cases                                   list the sample cases
    python main.py solve 1                                 full investigation report for case 1
    python main.py solve 1 --trace                         ...plus the forward-chaining trace
    python main.py solve 1 --explain "culprit(Arjun)"      ...plus a proof tree
    python main.py query 1 "culprit(?who)"                 backward chaining on a goal
    python main.py query 2 "manner_of_death(Dr_Iyer, ?how)" --trace
    python main.py query 3 "culprit(Rohan)" --interactive  the engine asks you for missing evidence
    python main.py rules                                   print the knowledge base
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from engine import (BackwardChainer, investigate, load_case, load_kb, parse_atom,
                    render_tree, verdict)
from engine.explain import Explanation

ROOT = Path(__file__).resolve().parent
DEFAULT_RULES = ROOT / "knowledge" / "crime_rules.kb"
CASES_DIR = ROOT / "cases"


# ---------------------------------------------------------------------------
# Terminal styling
# ---------------------------------------------------------------------------
class Style:
    enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    @classmethod
    def wrap(cls, code, text):
        return f"\033[{code}m{text}\033[0m" if cls.enabled else text


def bold(t): return Style.wrap("1", t)
def dim(t): return Style.wrap("2", t)
def red(t): return Style.wrap("31", t)
def green(t): return Style.wrap("32", t)
def yellow(t): return Style.wrap("33", t)
def cyan(t): return Style.wrap("36", t)


def cf_color(cf, text):
    if cf >= 0.6:
        return green(text)
    if cf >= 0.2:
        return yellow(text)
    if cf <= -0.2:
        return red(text)
    return dim(text)


def bar(cf, width=20):
    filled = int(round(abs(cf) * width))
    return cf_color(cf, ("█" * filled).ljust(width, "░"))


def heading(text):
    print()
    print(bold(cyan(text)))
    print(cyan("─" * len(text)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def resolve_case(arg: str) -> Path:
    p = Path(arg)
    if p.exists():
        return p
    matches = sorted(CASES_DIR.glob(f"{int(arg):02d}_*.json")) if arg.isdigit() else []
    if not matches:
        matches = sorted(CASES_DIR.glob(f"*{arg}*.json"))
    if not matches:
        sys.exit(f"Case not found: {arg}   (run:  python main.py cases)")
    return matches[0]


def print_tree(expl: Explanation):
    for line in render_tree(expl):
        print("   " + line)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_cases(args):
    heading("Sample cases")
    for i, path in enumerate(sorted(CASES_DIR.glob("*.json")), 1):
        case = load_case(path)
        print(f"  {bold(str(i))}. {bold(case.title)}  {dim(path.name)}")
        print(f"     {case.summary}\n")


def cmd_rules(args):
    kb = load_kb(args.rules)
    heading(f"Knowledge base: {len(kb.rules)} rules")
    for r in kb.rules:
        print(f"  {bold(r.id):<6} {r.description}")
        print(dim(f"         {r}"))
    heading("Hypotheses reported")
    for pred, text in kb.hypotheses.items():
        print(f"  {pred:<20} {text}")


def cmd_solve(args):
    kb = load_kb(args.rules)
    case = load_case(resolve_case(args.case))
    report = investigate(kb, case)

    print()
    print(bold(f"╔══ CASE: {case.title} ══"))
    print(f"║ {case.summary}")
    print(bold("╚" + "═" * 60))

    heading(f"1. Evidence on record ({len(case.evidence)} items)")
    for ev in case.evidence:
        print(f"  {cf_color(ev.cf, f'{ev.cf:+.2f}')}  {str(ev.atom):<45} {dim(ev.source)}")

    fwd = report.forward
    heading("2. Forward chaining (evidence -> conclusions)")
    fired = sum(len(c.fired) for c in fwd.trace)
    derived = [a for a in fwd.cf if a not in {e.atom for e in case.evidence}]
    print(f"  {len(fwd.trace)} inference cycles, {fired} rule firings, {len(derived)} new facts derived"
          f"{'' if fwd.converged else red('  (did not converge!)')}")
    if args.trace:
        for log in fwd.trace:
            print(bold(f"\n  Cycle {log.cycle}"))
            for rule, atom, contrib, prem in log.fired:
                print(f"    {green('FIRE')} {rule.id:<5} {str(atom):<40} {contrib:+.2f}   "
                      + dim("because " + ", ".join(map(str, prem))))
            for rule, atom in log.retracted:
                print(f"    {red('RETRACT')} {rule.id:<5} {atom}")
            for atom, old, new in log.changed:
                print(dim(f"    CF {str(atom):<40} {old:+.2f} -> {new:+.2f}"))
    else:
        print(dim("  (add --trace to see every rule firing, cycle by cycle)"))

    heading("3. Suspect analysis  (Motive / Means / Opportunity / Guilty behaviour)")
    print(dim(f"  {'Suspect':<12} {'Motive':>7} {'Means':>7} {'Opport.':>8} {'Guilt':>7}   "
              f"{'Culprit CF':<31} Verdict"))
    for p in report.suspects:
        c = p.components
        cells = "".join(cf_color(v, f"{v:+8.2f}") for v in
                        (c["motive"], c["means"], c["opportunity"], c["guilty_behaviour"]))
        print(f"  {bold(p.name):<12}{cells}   {bar(p.culprit_cf)} {p.culprit_cf:+.2f}  "
              f"{cf_color(p.culprit_cf, p.verdict)}")

    heading("4. Hypotheses about each suspect")
    for p in report.suspects:
        agree = "✓" if abs(p.culprit_cf - p.backward_cf) < 1e-6 else "✗"
        print(f"\n  {bold(p.name)} - culprit CF {cf_color(p.culprit_cf, f'{p.culprit_cf:+.2f}')} "
              f"({p.verdict})   {dim(f'backward chaining check: {p.backward_cf:+.2f} {agree}')}")
        for text, contrib in p.supporting:
            print(f"     {green('+')} {text}  {dim(f'({contrib:+.2f})')}")
        for text, contrib in p.refuting:
            print(f"     {red('-')} {text}  {dim(f'({contrib:+.2f})')}")
        if not p.supporting and not p.refuting:
            print(dim("     no rule linking this suspect to the crime has fired"))
        if p.leads:
            print(dim("     Investigative leads:"))
            for lead in p.leads[:5]:
                tag = green("would STRENGTHEN") if lead.polarity > 0 else red("would WEAKEN")
                print(f"       ? {lead.question}  {dim('->')} {tag} {lead.via.pred.replace('_', ' ')} "
                      f"{dim(f'(via {lead.rule.id})')}")

    if report.other_hypotheses:
        heading("5. Scene hypotheses")
        for pred, facts in report.other_hypotheses.items():
            print(f"  {bold(kb.hypotheses[pred])}")
            for atom, cf in facts:
                print(f"     {bar(cf, 12)} {cf:+.2f}  {atom}  {dim(verdict(cf))}")

    heading("6. Conclusion")
    print("  " + bold(report.conclusion))
    print(dim("\n  NOTE: this is decision support for investigators, not a verdict. "
              "Every conclusion above can be traced to evidence with --explain."))

    for text in args.explain or []:
        atom = parse_atom(text)
        heading(f"Explanation (HOW) for {atom}")
        if atom not in fwd.cf:
            print(f"  {atom} was not derived from the evidence.")
        else:
            print_tree(fwd.explain(atom))
    print()


def cmd_query(args):
    kb = load_kb(args.rules)
    case = load_case(resolve_case(args.case))
    goal = parse_atom(args.goal)

    ask = interactive_ask if args.interactive else None
    if args.interactive:
        print(dim("Answer: y = yes, n = no, u = unknown, a number between -1 and 1 = your certainty, "
                  "why = why are you asking?"))
    bc = BackwardChainer(kb, case, ask=ask)
    results = bc.query(goal)

    heading(f"Backward chaining: {goal}")
    # a specific (ground) goal is always shown - even a refuted answer is informative
    shown = results if (args.all or goal.is_ground) else [e for e in results if e.cf >= bc.threshold]
    if not shown:
        print(f"  Could not establish {goal} from the evidence (threshold CF {bc.threshold}).")
    for e in shown:
        print(f"\n  {bold(str(e.atom))}  {bar(e.cf)} {e.cf:+.2f}  {cf_color(e.cf, verdict(e.cf))}")
        print_tree(e)

    if bc.leads:
        heading("Missing evidence that would change the answer")
        for lead in bc.leads[:12]:
            tag = green("+") if lead.polarity > 0 else red("-")
            print(f"  {tag} {lead.question}  {dim(f'[{lead.atom}, needed by {lead.rule.id}]')}")

    if args.trace:
        heading("Search trace")
        for line in bc.trace:
            print("  " + dim(line) if line.lstrip().startswith(("TRY", "R")) else "  " + line)
    print()


def interactive_ask(goal, question, why_lines):
    while True:
        ans = input(f"\n{bold('?')} {question}  {dim(str(goal))}\n  > ").strip().lower()
        if ans in ("y", "yes"):
            return 1.0
        if ans in ("n", "no"):
            return -1.0
        if ans in ("u", "unknown", ""):
            return None
        if ans == "why":
            for line in why_lines:
                print(cyan("    " + line))
            continue
        try:
            v = float(ans)
            if -1 <= v <= 1:
                return v
        except ValueError:
            pass
        print("  Please answer y, n, u, why, or a number between -1 and 1.")


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)   # options accepted after any sub-command
    common.add_argument("--rules", default=str(DEFAULT_RULES), help="knowledge base file (.kb)")
    common.add_argument("--no-color", action="store_true", help="disable coloured output")

    parser = argparse.ArgumentParser(description="AI Evidence & Hypothesis Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("cases", parents=[common], help="list sample cases").set_defaults(func=cmd_cases)
    sub.add_parser("rules", parents=[common], help="print the knowledge base").set_defaults(func=cmd_rules)

    p = sub.add_parser("solve", parents=[common], help="investigate a case (forward + backward chaining)")
    p.add_argument("case", help="case number, name fragment or path to a .json case file")
    p.add_argument("--trace", action="store_true", help="show every forward-chaining cycle")
    p.add_argument("--explain", action="append", metavar="FACT", help='e.g. "culprit(Arjun)"')
    p.set_defaults(func=cmd_solve)

    q = sub.add_parser("query", parents=[common], help="backward-chain on a goal")
    q.add_argument("case")
    q.add_argument("goal", help='e.g. "culprit(?who)" or "motive(Kabir)"')
    q.add_argument("--interactive", "-i", action="store_true", help="ask for missing evidence")
    q.add_argument("--trace", action="store_true", help="show the goal-search trace")
    q.add_argument("--all", action="store_true", help="also show answers below the threshold")
    q.set_defaults(func=cmd_query)

    args = parser.parse_args(argv)
    if args.no_color:
        Style.enabled = False
    try:
        args.func(args)
    except (ValueError, OSError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
