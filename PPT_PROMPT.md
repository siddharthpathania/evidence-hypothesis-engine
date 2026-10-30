# Presentation Prompt

Copy everything inside the box below into a slide generator: **Gamma.app**, **Microsoft Copilot in PowerPoint**, **Canva Magic Design**, **Claude** or **ChatGPT**. With Claude or ChatGPT, add "Give me the slide text and speaker notes" at the end, or ask it to build the .pptx file.

Before you paste, replace `[YOUR NAME]`, `[ROLL NO]`, `[GUIDE NAME]`, `[COLLEGE]` and `[DEPARTMENT]`. If you can, add screenshots of the terminal output (`python main.py solve 1`) and the web app (`streamlit run app.py`) to slides 11–13.

---

```
Create a professional 18-slide presentation for a college AI project titled
"AI Evidence & Hypothesis Engine: Solving Cases with Forward and Backward Chaining".

AUDIENCE & TONE: Engineering faculty and students at a project review/viva. Clear, technical,
confident. Short bullet points (max 5 per slide, max ~12 words each), with a speaker-notes
paragraph for every slide explaining what to say.

DESIGN: Dark "detective / forensic" theme - deep navy or charcoal background, white text,
one accent colour (amber or teal) for highlights. Clean sans-serif font. Use icons
(magnifying glass, fingerprint, brain, flowchart), simple diagrams, and tables instead of
long text. Monospace font for code, rules and terminal output. Consistent layout, slide numbers.

SLIDES:

1. TITLE - "AI Evidence & Hypothesis Engine". Subtitle: "A rule-based expert system using
   forward & backward chaining with certainty factors". Presented by [YOUR NAME] ([ROLL NO]),
   guided by [GUIDE NAME], [DEPARTMENT], [COLLEGE].

2. PROBLEM STATEMENT - Investigators get large numbers of records (forensic reports, CCTV,
   witness statements, bank records). Combining them by hand is slow, error-prone and open to bias.
   Hard to see which missing evidence would settle a case. Need: a system that turns evidence
   into ranked, explainable hypotheses.

3. OBJECTIVES - Accept evidence with reliability scores; derive all hypotheses (forward
   chaining); rank suspects by Motive + Means + Opportunity; verify and explain each hypothesis
   (backward chaining); suggest missing evidence (investigative leads); handle uncertain and
   contradicting evidence.

4. WHAT IS AN EXPERT SYSTEM? - Diagram: User Interface <-> Inference Engine (+ Explanation
   facility) <-> Knowledge Base (rules) and Working Memory (facts). Mention MYCIN, DENDRAL.
   Key idea: knowledge kept separate from the reasoning engine.

5. KNOWLEDGE REPRESENTATION - Facts as predicates: fingerprint_on(Arjun, Letter_Opener),
   seen_at(Arjun, Study, 22:10). Variables: ?p, ?o. Example rule:
   IF murder_weapon(?o) AND fingerprint_on(?p, ?o) THEN handled_weapon(?p)  CF 0.8

6. FORWARD CHAINING - Data-driven: evidence -> rules fire -> new facts -> ... -> hypotheses.
   Match -> Conflict resolution -> Act cycle until fixpoint. Small worked example table:
   Cycle 1: weapon(Knife), motive(Ravi), opportunity(Ravi); Cycle 2: means(Ravi);
   Cycle 3: culprit(Ravi); Cycle 4: no change -> stop.

7. BACKWARD CHAINING - Goal-driven: start from hypothesis culprit(Ravi), find rules that
   conclude it, prove premises as sub-goals recursively. Show an AND-tree:
   culprit(Ravi) -> motive / means / opportunity -> evidence leaves.
   Can ASK the user for missing facts and explain WHY it asks.

8. FORWARD vs BACKWARD - Comparison table: direction, starts with, explores, best for,
   examples (CLIPS vs Prolog/MYCIN), role in our project (discover & rank vs verify, explain,
   ask, find leads). Note: both must give identical certainty, which is used as a correctness check.

9. HANDLING UNCERTAINTY - Certainty factors from -1 (false) to +1 (true), threshold 0.2.
   Sequential: CF = min(premises) x CF(rule). Parallel: a + b(1-a). Mixed signs:
   (a+b)/(1-min(|a|,|b|)). Negative rules: a verified alibi gives opportunity CF -0.9.

10. SYSTEM ARCHITECTURE - Block diagram: Case JSON + Rules (.kb) -> Parser/Validator ->
    Forward Chainer & Backward Chainer (sharing Unification + CF maths) -> Hypothesis Report
    (suspect profiles, cross-check, leads, conclusion) -> CLI and Streamlit web UI.
    Tech: Python 3 (standard library only for the engine), Streamlit for the UI, unittest.

11. KNOWLEDGE BASE DESIGN - 46 rules in a custom readable rule language. Groups: weapon
    identification, linking people to weapon, presence at scene (time-window check),
    scene reconstruction (inside job, staged break-in), Motive / Means / Opportunity,
    guilty behaviour, stolen property, manner of death (staged suicide), culprit and collusion.
    Diagram: evidence -> MOTIVE + MEANS + OPPORTUNITY (+ guilty behaviour) -> CULPRIT.

12. DEMO CASE 1: THE MEHRA MANSION MURDER - Table of results:
    Arjun +0.87 Strongly supported | Sunil +0.14 Insufficient | Meera 0.00 Insufficient |
    Kabir -0.76 Refuted. Insight: Kabir had the strongest motive (0.77) but a verified
    alibi refuted him; Meera had access and prints on the weapon but no motive.
    [Insert terminal screenshot]

13. EXPLAINABILITY - Show a proof tree (HOW): culprit(Arjun) <- R100 motive+means+opportunity
    <- motive (inherits under will) / means (fingerprints on the letter opener, which is the weapon by
    blood + wound match) / opportunity (CCTV at 22:10 within time-of-death window).
    Also WHY: during questioning the engine shows the rule chain that made it ask.
    [Insert proof-tree screenshot]

14. DEMO CASES 2 & 3 - Case 2 (Professor's Last Note): a forged suicide note flips
    "suicide" to -0.42 and "homicide" to +0.82, so a staged suicide is detected.
    Case 3 (Jewellery Heist): competing hypotheses Rohan 0.61 vs Danish 0.52, a staged break-in
    is detected, possible collusion is raised, and leads show what evidence would separate them.

15. INVESTIGATIVE LEADS & BELIEF REVISION - Backward chaining records missing evidence:
    "Was Rohan found with the Diamond Necklace? -> would strengthen linked-to-loot".
    Belief revision: when new evidence (e.g. a verified alibi) arrives, conclusions are
    retracted and the ranking changes. Web UI lets you edit evidence live.

16. TESTING & RESULTS - 18 automated unit tests: unification, CF maths, parser
    validation, chaining, interactive asking. Key test: forward and backward chaining
    give identical CFs for every derived fact in all 3 cases. All tests pass.

17. LIMITATIONS & FUTURE SCOPE - Limitations: CFs are not true probabilities, rules
    hand-written, evidence entered manually. Future: Bayesian networks, NLP/LLM to extract
    facts from FIRs and statements (neuro-symbolic), Rete algorithm for scale,
    timeline reasoning, more crime types. Ethics: decision support only; presumption of
    innocence; every conclusion auditable.

18. CONCLUSION & THANK YOU - We built an explainable expert system that combines forward
    and backward chaining with certainty factors to generate, rank, explain and verify case
    hypotheses. References: Russell & Norvig (AIMA), Buchanan & Shortliffe (MYCIN),
    Giarratano & Riley (Expert Systems). "Questions?"
```

---

### Tips for the demo during the presentation
1. `python main.py solve 1` shows the full report. Point at Kabir, who is refuted despite having the strongest motive.
2. `python main.py solve 1 --explain "culprit(Arjun)"` shows the HOW explanation.
3. `python main.py query 3 "culprit(Rohan)" -i`: answer a question with `why` to show the WHY facility.
4. In the web app (`streamlit run app.py`), open the evidence table for Case 1 and add the row `alibi_verified(Arjun)` with CF `0.95`. The ranking updates live, which demonstrates belief revision.
