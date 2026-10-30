"""Unit tests.  Run with:   python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import (BackwardChainer, ForwardChainer, case_from_dict, combine, combine_all,  # noqa: E402
                    investigate, load_case, load_kb, parse_atom, parse_kb, unify)
from engine.knowledge import KBSyntaxError  # noqa: E402
from engine.logic import Atom, eval_builtin  # noqa: E402

KB = load_kb(ROOT / "knowledge" / "crime_rules.kb")
CASES = sorted((ROOT / "cases").glob("*.json"))


class TestLogic(unittest.TestCase):
    def test_parse_atom(self):
        a = parse_atom("seen_at(Arjun, Study, 22:10)")
        self.assertEqual(a.pred, "seen_at")
        self.assertEqual(a.args, ("Arjun", "Study", "22:10"))
        self.assertTrue(a.is_ground)
        self.assertEqual(parse_atom('note(Vikram, "Hello, world")').args, ("Vikram", "Hello, world"))

    def test_parse_errors(self):
        for bad in ["noparens", "Upper(x)", "p(a,,b)", 'p("open)']:
            with self.assertRaises(ValueError):
                parse_atom(bad)

    def test_unify(self):
        b = unify(parse_atom("f(?p, knife)"), parse_atom("f(Arjun, knife)"), {})
        self.assertEqual(b, {"?p": "Arjun"})
        self.assertIsNone(unify(parse_atom("f(?p, knife)"), parse_atom("f(Arjun, gun)"), {}))
        self.assertIsNone(unify(parse_atom("f(?x, ?x)"), parse_atom("f(a, b)"), {}))
        self.assertIsNotNone(unify(parse_atom("f(?x, ?x)"), parse_atom("f(a, a)"), {}))

    def test_builtins(self):
        self.assertTrue(eval_builtin(parse_atom("between(?t, 21:00, 23:00)"), {"?t": "22:10"}))
        self.assertFalse(eval_builtin(parse_atom("between(?t, 21:00, 23:00)"), {"?t": "20:30"}))
        self.assertTrue(eval_builtin(parse_atom("between(23:40, 23:00, 01:00)"), {}))   # overnight
        self.assertTrue(eval_builtin(parse_atom("between(00:30, 23:00, 01:00)"), {}))
        self.assertFalse(eval_builtin(parse_atom("between(12:00, 23:00, 01:00)"), {}))
        self.assertTrue(eval_builtin(parse_atom("lt(9, 10)"), {}))       # numeric, not alphabetical
        self.assertTrue(eval_builtin(parse_atom("neq(Arjun, Meera)"), {}))
        with self.assertRaises(ValueError):
            eval_builtin(parse_atom("eq(?unbound, 1)"), {})


class TestCertainty(unittest.TestCase):
    def test_combine(self):
        self.assertAlmostEqual(combine(0.6, 0.5), 0.8)
        self.assertAlmostEqual(combine(-0.6, -0.5), -0.8)
        self.assertAlmostEqual(combine(0.8, -0.4), 0.4 / 0.6)
        self.assertEqual(combine(1.0, -1.0), 0.0)

    def test_order_independent(self):
        vals = [0.7, -0.4, 0.3, -0.2, 0.5]
        self.assertAlmostEqual(combine_all(vals), combine_all(reversed(vals)))
        self.assertAlmostEqual(combine_all(vals), combine_all(sorted(vals)))


class TestRuleParser(unittest.TestCase):
    def test_kb_loads(self):
        self.assertGreater(len(KB.rules), 40)
        self.assertIn("culprit", KB.hypotheses)

    def test_unbound_conclusion_rejected(self):
        with self.assertRaises(KBSyntaxError):
            parse_kb("RULE X\n IF a(?x)\n THEN b(?y)\n CF 0.5")

    def test_test_before_binding_rejected(self):
        with self.assertRaises(KBSyntaxError):
            parse_kb("RULE X\n IF lt(?x, 3)\n AND a(?x)\n THEN b(?x)\n CF 0.5")

    def test_cf_range(self):
        with self.assertRaises(KBSyntaxError):
            parse_kb("RULE X\n IF a(?x)\n THEN b(?x)\n CF 1.5")


TOY_KB = parse_kb("""
RULE A "a and b give c"
  IF a(?x)
  AND b(?x)
  THEN c(?x)
  CF 0.8
RULE B "c gives d"
  IF c(?x)
  THEN d(?x)
  CF 0.5
RULE N "e argues against d"
  IF e(?x)
  THEN d(?x)
  CF -0.5
""")


class TestChaining(unittest.TestCase):
    def toy(self, *facts):
        return case_from_dict({"evidence": [{"fact": f, "cf": cf} for f, cf in facts]})

    def test_forward_chain(self):
        r = ForwardChainer(TOY_KB, self.toy(("a(k)", 1.0), ("b(k)", 0.9))).run()
        self.assertAlmostEqual(r.cf[Atom("c", ("k",))], 0.72)          # min(1, .9) * .8
        self.assertAlmostEqual(r.cf[Atom("d", ("k",))], 0.36)          # .72 * .5
        self.assertTrue(r.converged)

    def test_negative_evidence(self):
        r = ForwardChainer(TOY_KB, self.toy(("a(k)", 1.0), ("b(k)", 1.0), ("e(k)", 1.0))).run()
        self.assertAlmostEqual(r.cf[Atom("d", ("k",))], (0.4 - 0.5) / (1 - 0.4))

    def test_threshold_blocks_weak_premise(self):
        r = ForwardChainer(TOY_KB, self.toy(("a(k)", 1.0), ("b(k)", 0.1))).run()
        self.assertNotIn(Atom("c", ("k",)), r.cf)

    def test_backward_matches_forward_toy(self):
        case = self.toy(("a(k)", 1.0), ("b(k)", 0.9), ("a(j)", 1.0), ("b(j)", 0.5))
        fwd = ForwardChainer(TOY_KB, case).run()
        answers = BackwardChainer(TOY_KB, case).query(parse_atom("d(?who)"))
        self.assertEqual({e.atom for e in answers}, {Atom("d", ("k",)), Atom("d", ("j",))})
        for e in answers:
            self.assertAlmostEqual(e.cf, fwd.cf[e.atom])

    def test_backward_asks_and_records_leads(self):
        kb = parse_kb('RULE A "x"\n IF a(?x)\n AND b(?x)\n THEN c(?x)\n CF 1.0\nASK b "Is b true of {0}?"')
        case = self.toy(("a(k)", 1.0))
        bc = BackwardChainer(kb, case)
        self.assertEqual(bc.prove(parse_atom("c(k)")).cf, 0.0)
        self.assertEqual([str(l.atom) for l in bc.leads], ["b(k)"])
        asked = []
        bc2 = BackwardChainer(kb, case, ask=lambda g, q, why: asked.append(q) or 0.9)
        self.assertAlmostEqual(bc2.prove(parse_atom("c(k)")).cf, 0.9)
        self.assertEqual(asked, ["Is b true of k?"])


class TestSampleCases(unittest.TestCase):
    def test_forward_and_backward_agree_on_every_fact(self):
        """The two inference strategies must reach identical certainty for every conclusion."""
        for path in CASES:
            case = load_case(path)
            fwd = ForwardChainer(KB, case).run()
            self.assertTrue(fwd.converged, path.name)
            for pred in KB.derived_predicates():
                bc = BackwardChainer(KB, case)
                arity = next(len(r.conclusion.args) for r in KB.rules if r.conclusion.pred == pred)
                goal = Atom(pred, tuple(f"?v{i}" for i in range(arity)))
                for e in bc.query(goal):
                    self.assertAlmostEqual(e.cf, fwd.cf.get(e.atom, 0.0), msg=f"{path.name}: {e.atom}")

    def test_expected_conclusions(self):
        expect = {"01": "Arjun", "02": "Nikhil", "03": "Rohan", "04": "Karan"}
        for path in CASES:
            report = investigate(KB, load_case(path))
            self.assertEqual(report.suspects[0].name, expect[path.name[:2]], path.name)

    def test_alibi_refutes(self):
        report = investigate(KB, load_case(CASES[0]))
        kabir = next(p for p in report.suspects if p.name == "Kabir")
        self.assertLess(kabir.culprit_cf, -0.2)
        self.assertEqual(kabir.verdict, "Refuted")


if __name__ == "__main__":
    unittest.main()
