# AI Evidence & Hypothesis Engine
## A Learning Booklet: From the Basics to Your Viva

> **How to use this booklet.** Part A teaches the AI theory from scratch, assuming you know only basic programming. Part B explains how this project applies that theory, module by module, with real output. Part C has viva questions, a glossary and references. Read the chapters in order the first time. Before your presentation, re-read the chapter summaries and Part C.

---

## Contents

**Part A: Foundations**
1. What is Artificial Intelligence?
2. Expert systems: AI that reasons like a specialist
3. Knowledge representation: facts and predicates
4. Rules and logical inference
5. Deduction, induction and abduction: how detectives think
6. Forward chaining (data-driven reasoning)
7. Backward chaining (goal-driven reasoning)
8. Forward vs backward chaining
9. Unification: matching patterns with variables
10. Reasoning under uncertainty: certainty factors
11. Belief revision: when new evidence changes the answer
12. Explanation: the HOW and WHY facilities

**Part B: The project**

13. Problem statement and objectives
14. System architecture
15. The rule language and the knowledge base
16. The case file (evidence records)
17. Code walkthrough
18. Running the project
19. Solving Case 1 by hand
20. Reading the traces
21. Testing
22. Extending the project
23. Limitations and future scope
24. Ethics

**Part C: Exam and viva preparation**

25. Viva questions with answers
26. Glossary
27. References

---

# PART A: FOUNDATIONS

## 1. What is Artificial Intelligence?

**Artificial Intelligence (AI)** is the field of computer science that builds systems able to do tasks that normally need human intelligence, such as reasoning, learning, planning, understanding language and making decisions.

There are two broad schools of AI:

| | **Symbolic AI** ("Good Old-Fashioned AI") | **Statistical / Machine-Learning AI** |
|---|---|---|
| Knowledge is… | written explicitly as symbols, facts and rules | learned implicitly from data as numbers (weights) |
| Example | Expert systems, Prolog, planners | Neural networks, ChatGPT, image classifiers |
| Strength | **Explainable**: every conclusion can be traced | Handles messy data such as images and text |
| Weakness | Someone has to write the rules | Opaque ("black box") and needs lots of data |

**This project is Symbolic AI.** We chose it on purpose. In a police investigation you must be able to explain why the system suspects someone. "The neural network said so" is not acceptable. "Rule R100 fired because motive, means and opportunity were all established from these five pieces of evidence" is.

> **Summary.** AI = machines doing tasks that need intelligence. Symbolic AI reasons with explicit rules and is fully explainable, which is why we use it here.

---

## 2. Expert Systems: AI That Reasons Like a Specialist

An **expert system** is a program that captures the knowledge of a human expert (a doctor, an engineer, a detective) as rules and uses it to solve problems in that domain.

Famous examples:
- **MYCIN** (Stanford, 1970s) diagnosed blood infections and recommended antibiotics. It introduced the **certainty factors** we use in this project.
- **DENDRAL** identified chemical structures from mass-spectrometry data.
- **XCON/R1** (DEC) configured computer systems and saved the company millions.

### Architecture of an expert system

```
                ┌──────────────────────────┐
   User  ◄────► │      User Interface      │   (CLI / web app)
                └────────────┬─────────────┘
                             │
          ┌──────────────────▼────────────────────┐
          │           INFERENCE ENGINE            │   the "brain": forward & backward chaining
          │  + Explanation facility (HOW / WHY)   │
          └───────┬───────────────────────┬───────┘
                  │                       │
     ┌────────────▼─────────┐   ┌─────────▼─────────────┐
     │   KNOWLEDGE BASE     │   │   WORKING MEMORY      │
     │   (general rules)    │   │   (facts about THIS   │
     │   IF ... THEN ...    │   │    case: evidence +   │
     │                      │   │    derived facts)     │
     └──────────────────────┘   └───────────────────────┘
```

| Component | What it holds | In our project |
|---|---|---|
| **Knowledge base** | General domain knowledge that is true for every case | `knowledge/crime_rules.kb` (46 rules) |
| **Working memory** | Facts about the current problem | Evidence from `cases/*.json` plus facts the engine derives |
| **Inference engine** | The algorithm that applies rules to facts | `engine/forward.py`, `engine/backward.py` |
| **Explanation facility** | Answers "how did you conclude that?" and "why are you asking?" | `engine/explain.py`, WHY in interactive mode |
| **User interface** | How people interact | `main.py` (terminal), `app.py` (web) |

**Key idea: knowledge is kept separate from the inference engine.** To solve a different case you change the evidence, not the code. To make the system cover a new kind of crime you add rules, not code. The same engine could even diagnose diseases if you gave it medical rules.

> **Summary.** An expert system has a knowledge base (rules), working memory (facts), an inference engine (reasoning algorithm) and an explanation facility.

---

## 3. Knowledge Representation: Facts and Predicates

Before a computer can reason, knowledge must be written in a precise form. We use **predicate logic** (also called first-order logic).

### Propositional logic (too weak)
In propositional logic each statement is a single symbol with no internal structure:
```
P = "Arjun's fingerprints are on the knife"
Q = "Arjun handled the weapon"
P → Q
```
The problem: you need a separate rule for every person and every object. It cannot say "*anyone* whose prints are on *any* weapon handled it."

### Predicate logic (what we use)
A **predicate** names a property or relationship. **Arguments** say who or what it is about:

```
fingerprint_on(Arjun, Letter_Opener)      "Arjun's fingerprints are on the letter opener"
victim(Vikram)                            "Vikram is the victim"
seen_at(Arjun, Study, 22:10)              "Arjun was seen in the study at 22:10"
```

A statement like this is called an **atom** (or a *fact* when it is known). The number of arguments is the **arity**: `victim` has arity 1 and `seen_at` has arity 3.

### Variables
A **variable** stands for "some value". In this project variables start with `?`:

```
fingerprint_on(?p, ?o)       "some person ?p left prints on some object ?o"
```

With variables, **one rule covers every person and every object**:

```
IF murder_weapon(?o) AND fingerprint_on(?p, ?o) THEN handled_weapon(?p)
```

In formal logic this is written `∀p ∀o: murder_weapon(o) ∧ fingerprint_on(p, o) → handled_weapon(p)`.

**Ground atom**: an atom with no variables, e.g. `fingerprint_on(Arjun, Letter_Opener)`. Evidence must always be ground.

> **Summary.** Facts are written as `predicate(arg1, arg2, …)`. Variables (`?x`) let one rule apply to every case.

---

## 4. Rules and Logical Inference

A **rule** (also called a *production rule*) has the form:

```
IF   premise1 AND premise2 AND ...     (antecedent / condition / left-hand side)
THEN conclusion                        (consequent / action / right-hand side)
```

Rules whose premises are joined only by AND and that have a single conclusion are called **Horn clauses**. Prolog and most expert systems use this form, and so do we.

### Modus Ponens: the core inference rule
```
    A → B         (rule: if A then B)
    A             (fact: A is true)
   ───────
    B             (conclusion: so B is true)
```
Every time our engine "fires" a rule, it is applying Modus Ponens.

### Inference
**Inference** means deriving new facts from known facts and rules. There are two directions in which you can search for them:

- Start from the **facts** and see what follows → **forward chaining**
- Start from a **question** and look for facts that support it → **backward chaining**

Chapters 6 and 7 cover each one in detail.

> **Summary.** Rules are IF-THEN statements. Firing a rule is Modus Ponens. Chaining means linking rules one after another, either forward from the data or backward from a goal.

---

## 5. Deduction, Induction and Abduction: How Detectives Think

There are three kinds of reasoning, and crime-solving uses the third:

| Type | Pattern | Example | Certain? |
|---|---|---|---|
| **Deduction** | Rule + cause → effect | "All stabbings cause bleeding. This was a stabbing. ∴ there was bleeding." | Yes |
| **Induction** | Many examples → general rule | "Every poisoning I've seen involved access to poison. ∴ poisoners need access." | No |
| **Abduction** | Effect + rule → **best explanation** | "There is blood on the knife. Stabbing would explain it. ∴ *probably* the knife is the weapon." | No |

**Abduction means inference to the best explanation.** Sherlock Holmes calls it "deduction", but what he actually does is abduction. He sees clues and proposes the hypothesis that best explains them.

Abduction is uncertain, because the blood might have come from somewhere else. That is why **every rule in our knowledge base has a certainty factor**. Rules like "blood on object → probably the weapon (CF 0.8)" are abductive rules written in IF-THEN form. Chapter 10 explains how the numbers work.

> **Summary.** Solving a crime is abduction: you find the hypothesis that best explains the evidence. Because abduction is uncertain, we attach certainty factors to rules.

---

## 6. Forward Chaining (Data-Driven Reasoning)

### Idea
Start with what you **know** (the evidence). Repeatedly fire every rule whose IF-part is satisfied and add its THEN-part to working memory. Stop when nothing new can be added.

```
EVIDENCE ──► rules fire ──► new facts ──► more rules fire ──► … ──► HYPOTHESES
```

It is called **data-driven** because the data pushes the reasoning forward. It is also called *bottom-up* reasoning.

### The Recognise–Act cycle
Classic forward chaining repeats a three-step cycle:

1. **MATCH**: find every rule whose premises are all satisfied by facts in working memory. These matching rule instances form the **conflict set**.
2. **CONFLICT RESOLUTION**: choose which rule(s) to fire. Common strategies:
   - *Refraction*: never fire the same rule on the same facts twice (prevents infinite loops)
   - *Recency*: prefer rules that use the newest facts
   - *Specificity*: prefer rules with more conditions
   - *Salience / priority*: rules have explicit priorities
3. **ACT**: fire the chosen rule(s) and add the conclusions to working memory.

The cycle repeats until no rule can add anything new. That state is called a **fixpoint**.

### Pseudocode
```
function FORWARD-CHAIN(rules, facts):
    repeat
        new ← {}
        for each rule (IF p1 ∧ … ∧ pn THEN q) in rules:
            for each substitution θ such that p1θ … pnθ are all in facts:
                if qθ not in facts: add qθ to new
        facts ← facts ∪ new
    until new is empty
    return facts
```

### Worked example (by hand)
**Rules**
```
R1: blood_on(?o, Victim)                         → weapon(?o)
R2: weapon(?o) ∧ fingerprint_on(?p, ?o)          → means(?p)
R3: seen_at_scene(?p)                            → opportunity(?p)
R4: owes_money(?p, Victim)                       → motive(?p)
R5: motive(?p) ∧ means(?p) ∧ opportunity(?p)     → culprit(?p)
```
**Evidence**
```
F1 blood_on(Knife, Victim)    F2 fingerprint_on(Ravi, Knife)
F3 seen_at_scene(Ravi)        F4 owes_money(Ravi, Victim)     F5 seen_at_scene(Sita)
```

| Cycle | Rules that match (conflict set) | New facts added |
|---|---|---|
| 1 | R1 {?o=Knife}, R3 {?p=Ravi}, R3 {?p=Sita}, R4 {?p=Ravi} | weapon(Knife), opportunity(Ravi), opportunity(Sita), motive(Ravi) |
| 2 | R2 {?o=Knife, ?p=Ravi} (needed weapon(Knife) from cycle 1) | means(Ravi) |
| 3 | R5 {?p=Ravi} | **culprit(Ravi)** |
| 4 | nothing new → **fixpoint, stop** | |

Notice two things:
- `culprit(Ravi)` could not be derived until cycle 3, because its premises were themselves conclusions of earlier rules. That is what *chaining* means.
- `opportunity(Sita)` was derived even though nobody asked about Sita. Forward chaining derives **everything** that follows from the data. This is useful when you don't yet know which question to ask, and it is how our engine *discovers* hypotheses.

### Advantages and disadvantages
| ✅ Advantages | ❌ Disadvantages |
|---|---|
| Discovers all conclusions, including ones nobody thought to ask about | Can derive many irrelevant facts |
| Natural when data arrives first (sensors, evidence, monitoring) | Wasteful if you only care about one question |
| Simple to implement | Has no focus or goal |

### How our engine does it
Our `ForwardChainer` fires **all** matching rule instances in each cycle (parallel firing) instead of choosing one. It recomputes every fact's support from scratch each cycle. This gives three useful properties:
- **Refraction is automatic.** Each firing is identified by (rule id, the exact facts it used), so the same firing is never counted twice.
- **The result doesn't depend on rule order.**
- **Conclusions are withdrawn if a premise stops being believed** (see Chapter 11).

> **Summary.** Forward chaining goes from facts to conclusions. It repeats match → resolve → act until a fixpoint. It is good for discovering every hypothesis the evidence supports.

---

## 7. Backward Chaining (Goal-Driven Reasoning)

### Idea
Start with a **question (goal/hypothesis)**, e.g. *"Is Ravi the culprit?"*, and work backwards:

1. Is the goal already a known fact? → done.
2. Otherwise, find rules whose **THEN-part** matches the goal.
3. Each premise of such a rule becomes a **sub-goal**. Prove each one the same way (recursion).
4. If every sub-goal is proved, the goal is proved.

It is called **goal-driven** or *top-down* reasoning. Prolog works this way.

### Pseudocode
```
function PROVE(goal, θ):
    if goal matches a known fact under θ: yield the extended θ
    for each rule (IF p1 ∧ … ∧ pn THEN q) whose q unifies with goal:
        θ' ← unify(goal, q, θ)
        yield from PROVE-ALL([p1 … pn], θ')

function PROVE-ALL(goals, θ):
    if goals is empty: yield θ; return
    for each θ' in PROVE(first(goals), θ):
        yield from PROVE-ALL(rest(goals), θ')
```

### Worked example: same rules, goal `culprit(Ravi)`
The search builds an **AND-OR tree**. AND means all children must be proved. OR means any one alternative rule is enough.

```
culprit(Ravi)?                              ── R5 (AND)
├── motive(Ravi)?                           ── R4
│   └── owes_money(Ravi, Victim)?           ✔ fact F4
├── means(Ravi)?                            ── R2 (AND)
│   ├── weapon(?o)?                         ── R1
│   │   └── blood_on(?o, Victim)?           ✔ fact F1  → ?o = Knife
│   └── fingerprint_on(Ravi, Knife)?        ✔ fact F2   (?o is now bound to Knife)
└── opportunity(Ravi)?                      ── R3
    └── seen_at_scene(Ravi)?                ✔ fact F3
⇒ culprit(Ravi) PROVED
```

Notice:
- **Bindings flow between sub-goals.** Solving `weapon(?o)` bound `?o = Knife`, so the next sub-goal became `fingerprint_on(Ravi, Knife)`.
- `opportunity(Sita)` was **never examined**. Backward chaining only explores what is relevant to the goal.
- If a sub-goal cannot be proved and it is the kind of fact only a person can supply (e.g. "Was Ravi seen at the scene?"), the system can **ask the user**. MYCIN did this, and so does our interactive mode.

### Variables in the goal = "who?" questions
The goal `culprit(?who)` asks for **every** value of `?who` that can be proved. The engine returns each answer with its certainty.

### Advantages and disadvantages
| ✅ Advantages | ❌ Disadvantages |
|---|---|
| Focused: only explores what is relevant | Needs a goal to start from |
| Can ask the user for missing facts | Can repeat work on shared sub-goals (we fix this with **memoisation**) |
| Shows naturally *what evidence is missing* | Can loop on recursive rules (we detect loops) |

> **Summary.** Backward chaining goes from a hypothesis to the evidence. It breaks goals into sub-goals recursively. It is good for testing a specific hypothesis, asking questions, and finding missing evidence.

---

## 8. Forward vs Backward Chaining

| | Forward chaining | Backward chaining |
|---|---|---|
| Direction | Facts → conclusions | Goal → facts |
| Also called | Data-driven, bottom-up | Goal-driven, top-down |
| Starts with | Evidence | A hypothesis / question |
| Explores | Everything derivable | Only what is relevant to the goal |
| Best when | Many possible conclusions, few facts to start from, data arrives over time | One specific question, many facts, or facts must be asked for |
| Typical systems | CLIPS, OPS5, monitoring and alarm systems | Prolog, MYCIN, diagnostic systems |
| In a detective's terms | "What does all this evidence point to?" | "If Arjun did it, what must be true? Can I find it?" |
| **In our project** | Generates and ranks **all hypotheses** | **Verifies** each hypothesis, explains it, **asks** questions, and lists **missing evidence (leads)** |

**Why use both?** A real investigation does both. You first look at the evidence to see who stands out (forward). Then you test each theory and work out what to look for next (backward). Our engine also **cross-checks** the two methods: both must give exactly the same certainty for every conclusion. The automated tests check this for every derived fact in every sample case.

---

## 9. Unification: Matching Patterns with Variables

**Unification** finds values for variables that make two atoms identical.

| Atom 1 | Atom 2 | Result |
|---|---|---|
| `fingerprint_on(?p, Knife)` | `fingerprint_on(Arjun, Knife)` | ✔ `{?p = Arjun}` |
| `fingerprint_on(?p, Knife)` | `fingerprint_on(Arjun, Gun)` | ✘ `Knife ≠ Gun` |
| `seen_at(?p, ?l, ?t)` | `seen_at(Arjun, Study, 22:10)` | ✔ `{?p=Arjun, ?l=Study, ?t=22:10}` |
| `same(?x, ?x)` | `same(A, B)` | ✘ `?x` can't be both A and B |
| `motive(?p)` | `suspect(Arjun)` | ✘ different predicates |

### Algorithm
```
UNIFY(x, y, θ):
    if predicates or arity differ: fail
    for each pair of arguments (a, b):
        a ← value of a under θ ;  b ← value of b under θ
        if a == b: continue
        else if a is a variable: θ[a] ← b
        else if b is a variable: θ[b] ← a
        else: fail                      (two different constants)
    return θ
```

### Standardising apart
When backward chaining uses the same rule twice, e.g. once for Arjun and once for Meera, the variable `?p` in the rule must not clash with itself. So each time a rule is used, its variables are **renamed**: `?p` → `?p_17`. In our code this is `rename_vars()`.

> **Summary.** Unification is how rules match facts. It is the "M" in Match–Resolve–Act and the step that links a goal to a rule's conclusion.

---

## 10. Reasoning Under Uncertainty: Certainty Factors

Real evidence is rarely 100% certain. CCTV can be blurry, witnesses make mistakes, and a print may be smudged. We need a way to say how much we believe something.

### Approaches to uncertainty
| Approach | Idea | Used by |
|---|---|---|
| Probability / Bayes' theorem | P(H \| E) using prior probabilities | Bayesian networks |
| Fuzzy logic | Degrees of truth ("fairly tall") | Control systems |
| Dempster–Shafer theory | Belief and plausibility intervals | Sensor fusion |
| **Certainty factors (CF)** | A simple belief score from −1 to +1 | **MYCIN, and this project** |

We use **certainty factors**. They are easy to understand, easy for experts to assign, and allow **negative evidence** (things that argue *against* a hypothesis).

### The CF scale
```
 -1.0 ─────────── -0.2 ────── 0 ────── +0.2 ─────────── +1.0
 definitely      (not        no      (believed         definitely
   false        believed)   idea     from here)          true
```

**Threshold:** a fact is used as a rule premise only if its CF ≥ **0.2**. This stops very weak facts from triggering long chains of conclusions. MYCIN used the same value.

### Rule 1: Evidence in sequence (rule firing)
```
CF(conclusion) = min( CF(premise1), CF(premise2), … ) × CF(rule)
```
- **min** because a chain is only as strong as its weakest link (AND).
- **× CF(rule)** because the rule itself is not perfectly reliable.

*Example.* R10: `murder_weapon(?o) ∧ fingerprint_on(?p, ?o) → handled_weapon(?p)`, CF 0.8.
murder_weapon(Letter_Opener) = 0.94 and fingerprint_on(Arjun, Letter_Opener) = 0.85
→ handled_weapon(Arjun) = min(0.94, 0.85) × 0.8 = **0.68**

### Rule 2: Evidence in parallel (two rules support the same fact)
Two independent pieces of evidence should increase our belief, but never beyond 1.
```
both positive:   CF = a + b(1 − a)
both negative:   CF = a + b(1 + a)
mixed signs:     CF = (a + b) / (1 − min(|a|, |b|))
```
*Example (both positive).* The letter opener is linked to the crime by the wound pattern (0.765) and by blood (0.76):
CF = 0.765 + 0.76 × (1 − 0.765) = 0.765 + 0.179 = **0.94**

*Example (mixed).* inside_job(Showroom): a staged break-in gives +0.61, a forced entry gives −0.36:
CF = (0.61 − 0.36) / (1 − 0.36) = 0.25 / 0.64 = **0.39**

*Order independence.* Our `combine_all()` first pools all positive contributions, then all negative ones, and merges the two once. The final CF therefore does not depend on the order in which evidence arrived.

### Negative rules
A rule with a negative CF argues **against** its conclusion:
```
RULE R32 "A verified alibi rules out opportunity"
  IF alibi_verified(?p) THEN opportunity(?p)   CF -0.9
```
Kabir's alibi (CF 0.95) gives opportunity(Kabir) = 0.95 × (−0.9) = **−0.855**. That is below the threshold, so no rule that needs Kabir's opportunity can fire.

### Interpreting the final CF (our verdict labels)
| CF | Verdict |
|---|---|
| ≥ 0.8 | Strongly supported |
| 0.6 – 0.8 | Probable |
| 0.4 – 0.6 | Possible |
| 0.2 – 0.4 | Weak |
| −0.2 – 0.2 | Insufficient evidence |
| ≤ −0.2 | Refuted |

> **Summary.** CF runs from −1 to +1. In sequence: min × rule CF. In parallel: a + b(1−a). Negative CFs model evidence that argues against a conclusion.

---

## 11. Belief Revision: When New Evidence Changes the Answer

Classical logic is **monotonic**: adding facts never removes a conclusion. Investigations are **non-monotonic**: a single new piece of evidence, such as a verified alibi, can overturn a theory.

Our forward chainer recomputes the support for every fact in every cycle. If a premise's CF drops below the threshold, the rule firings that depended on it disappear in the next cycle. The trace shows this as **RETRACT**. You can see it in the web app: open the evidence table, add `alibi_verified(Arjun)` with CF 0.95, and watch Arjun's CF drop while the rest of the ranking rearranges.

---

## 12. Explanation: The HOW and WHY Facilities

An expert system has to justify its answers. There are two classic explanation questions:

- **HOW did you conclude X?** The system shows the **proof tree**: the rules used and the evidence underneath them.
  `python main.py solve 1 --explain "culprit(Arjun)"`
- **WHY are you asking me this?** During interactive backward chaining, the system shows the chain of goals and rules that led to the question.
  Type `why` when the engine asks you something in `python main.py query 3 "culprit(Rohan)" -i`.

```
? Does Priya gain financially from Zaveri Jewellers's death/loss?
  > why
    I am trying to establish culprit(Priya) using R100 (Motive, means and opportunity all present):
        IF suspect(?p) AND motive(?p) AND means(?p) AND opportunity(?p) THEN culprit(?p)  (CF +0.90)
    I am trying to establish motive(Priya) using R50 (Gains financially from the victim ...):
        IF victim(?v) AND beneficiary_of(?p, ?v) THEN motive(?p)  (CF +0.70)
    ...and that needs to know whether beneficiary_of(Priya, Zaveri_Jewellers).
```

---

# PART B: THE PROJECT

## 13. Problem Statement and Objectives

**Problem.** Investigators receive a large number of records about a case: forensic reports, CCTV logs, witness statements, financial records. Combining them into consistent hypotheses is slow and prone to error and bias. It is also hard to see which piece of missing evidence would settle the case.

**Objective.** Build an AI system that:
1. accepts the **evidence records** of a case, each with a reliability score;
2. uses **forward chaining** to derive every hypothesis the evidence supports (weapon, manner of death, inside job, culprit, collusion);
3. **ranks** suspects with certainty factors, using the investigative triad **Motive + Means + Opportunity**;
4. uses **backward chaining** to verify each hypothesis, explain it, ask the investigator questions, and list **investigative leads** (missing evidence that would strengthen or weaken it);
5. **explains** every conclusion back to the evidence it rests on;
6. handles **uncertain and contradicting** evidence, such as alibis and forged notes.

**Scope.** The system supports investigators by organising evidence and making the reasoning visible. It does not decide guilt (see Chapter 24).

---

## 14. System Architecture

```
            cases/*.json                     knowledge/crime_rules.kb
        (evidence + reliability)            (46 IF-THEN rules with CFs)
                 │                                      │
                 ▼                                      ▼
        ┌──────────────────────── engine/knowledge.py ─────────────────────┐
        │  parse & validate case          parse & validate rule language   │
        └──────────────┬───────────────────────────────────┬───────────────┘
                       ▼                                   ▼
          ┌────────────────────────┐          ┌─────────────────────────────┐
          │  engine/forward.py     │          │  engine/backward.py         │
          │  FORWARD CHAINING      │          │  BACKWARD CHAINING          │
          │  evidence → all facts  │          │  goal → proof, questions,   │
          │  (fixpoint, cycles)    │          │  leads, WHY, trace          │
          └───────────┬────────────┘          └──────────────┬──────────────┘
                      │     engine/logic.py  (atoms, unification, built-ins)
                      │     engine/certainty.py (CF maths, verdicts)
                      ▼                                      ▼
          ┌───────────────────────────────────────────────────────────────┐
          │  engine/hypothesis.py  - investigation report                 │
          │  suspect profiles · cross-check · leads · scene hypotheses ·  │
          │  final conclusion                                             │
          └───────────────────────────┬───────────────────────────────────┘
                                      │      engine/explain.py (proof trees)
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
              main.py (CLI)                      app.py (Streamlit web UI)
```

| File | Lines of responsibility |
|---|---|
| `engine/logic.py` | `Atom`, parsing, **unification**, substitution, variable renaming, built-in tests (`between`, `neq`, …) |
| `engine/certainty.py` | CF combination formulas, threshold, verdict labels |
| `engine/knowledge.py` | `Rule`, `KnowledgeBase`, the **rule-language parser** with validation, case loader |
| `engine/forward.py` | **Forward chaining** to a fixpoint, the cycle trace, proof reconstruction |
| `engine/backward.py` | **Backward chaining** with memoisation, loop detection, ASK, WHY, LEADS, trace |
| `engine/explain.py` | Shared proof-tree structure and the text renderer |
| `engine/hypothesis.py` | Builds the investigation report from both chainers |
| `main.py` | Command-line interface |
| `app.py` | Web interface with a live evidence editor |
| `tests/test_engine.py` | 18 unit tests |

---

## 15. The Rule Language and the Knowledge Base

### Syntax
```
RULE R10 "Fingerprints on the weapon link a person to it"
  IF   murder_weapon(?o)
  AND  fingerprint_on(?p, ?o)
  THEN handled_weapon(?p)
  CF   0.8

ASK fingerprint_on "Were {0}'s fingerprints found on the {1}?"
HYPOTHESIS culprit "Who most likely committed the crime"
```
- `#` starts a comment.
- **Built-in tests** can be used as premises: `eq, neq, lt, le, gt, ge, between(x, lo, hi)`. They understand clock times (`21:30`) and numbers.
- **ASK** marks a predicate as evidence the engine may ask the investigator about. It also says how to phrase the question.
- **HYPOTHESIS** marks a predicate whose conclusions appear in the final report.

The parser **validates** every rule and rejects:
- a CF outside −1…1;
- a variable in THEN that never appears in an IF/AND (the rule must be *range-restricted*);
- a test that uses a variable before an earlier premise has bound it;
- duplicate rule IDs.

### How the knowledge base is organised
The rules follow the **investigative triad** taught in criminology: a person who had the **motive** (why), the **means** (how) and the **opportunity** (when and where) is a strong suspect.

```
 blood_on ─┐                      ┌─ beneficiary_of ─┐
 wound_matches ─► murder_weapon ─┐│  owes_money ─────┤
                                 ▼│  threatened ─────┼─► MOTIVE ─────┐
 fingerprint_on/dna_on ──► handled_weapon ──► MEANS ◄─ purchased/    │
                              owns ──────────►      ▲  access_to_    │
                         knows_code + safe ─────────┘  substance     │
                                                                     ▼
 seen_at + time window ──┐                                       CULPRIT
 footprint + shoe size ──┼─► present_at_scene ─► OPPORTUNITY ──►    ▲
 on_duty_at, dna at scene┘                         ▲    ▲  (−) alibi │
 no_forced_entry / staged break-in ─► inside_job ─► access_to_scene  │
                                                                     │
 lied / destroyed evidence / false alibi ─► GUILTY_BEHAVIOUR ────────┘
 possessed stolen item ─► linked_to_loot ──────────────────────────► CULPRIT, COLLUSION
 forged note ─► staged_suicide ─► MANNER_OF_DEATH(homicide)
```

| Group | Rules | Purpose |
|---|---|---|
| Weapon | R01–R02 | Identify the weapon from blood and wound match |
| Link to weapon | R10–R11 | Fingerprints / DNA on the weapon |
| Presence | R20–R23 | CCTV/witness inside the time-of-death window (uses `between`), footprints, DNA, on duty |
| Scene | R25–R29 | No forced entry / staged break-in → inside job → key-holders had access |
| Opportunity | R30–R33 | Presence/access → opportunity; **verified alibi −0.9** |
| Means | R40–R44 | Weapon handling, ownership, poison purchase/access, safe code |
| Motive | R50–R54 | Inheritance, debt, threats, quarrels, financial trouble |
| Guilty behaviour | R60–R62 | Lies, destroying evidence, false alibi |
| Loot | R70 | Possession of stolen goods |
| Manner of death | R80–R87 | Defensive wounds, suicide note, **forged note → staged suicide**, who bought the poison (uses `neq`) |
| Culprit | R100–R105, R110 | Combinations of the triad; alibi against guilt; collusion |

Several culprit rules can fire for the same person, e.g. R100 (all three) and R101 (means + opportunity + guilty behaviour). Their CFs **combine in parallel**. A suspect with more independent lines of evidence therefore scores higher.

---

## 16. The Case File (Evidence Records)

```json
{
  "title": "The Mehra Mansion Murder",
  "summary": "Industrialist Vikram Mehra was found stabbed ...",
  "evidence": [
    {"fact": "victim(Vikram)", "cf": 1.0, "source": "FIR No. 221/2026"},
    {"fact": "seen_at(Arjun, Study, 22:10)", "cf": 0.7, "source": "Corridor CCTV (face partly hidden)"},
    {"fact": "alibi_verified(Kabir)", "cf": 0.95, "source": "Boarding pass + Delhi hotel CCTV"}
  ]
}
```
- `cf` is the **reliability** of the record. Use 1.0 for an official document, around 0.7 for blurry CCTV, 0.4 for hearsay. A **negative** CF says the record argues the fact is false.
- `source` is kept for **traceability**. Every proof tree ends with these sources.

### The three sample cases
| # | Case | What it demonstrates |
|---|---|---|
| 1 | **The Mehra Mansion Murder**: stabbing, 4 suspects | Clear **primary hypothesis** (Arjun, 0.87). A suspect with strong motive is **refuted by an alibi** (Kabir). A suspect with means and access but no motive is not accused (Meera). |
| 2 | **The Professor's Last Note**: cyanide and a "suicide" note | **Manner-of-death reasoning.** A forged note turns *suicide* (−0.42) into *homicide* (+0.82) and reveals a **staged suicide**. Nikhil is probable (0.68), Dr Sharma possible (0.45). |
| 3 | **The Zaveri Jewellers Heist**: theft | **Competing hypotheses** (Rohan 0.61 vs Danish 0.52). A **staged break-in** is detected, a **possible collusion** hypothesis is raised, and **leads** show what would separate the suspects. |

---

## 17. Code Walkthrough

### 17.1 `logic.py`: atoms and unification
```python
@dataclass(frozen=True)
class Atom:
    pred: str
    args: Tuple[str, ...]
```
`frozen=True` makes atoms hashable, so they can be dictionary keys in working memory.

```python
def unify(x, y, b):
    if x.pred != y.pred or len(x.args) != len(y.args):
        return None
    b = dict(b)                          # never modify the caller's bindings
    for a1, a2 in zip(x.args, y.args):
        a1, a2 = walk(a1, b), walk(a2, b) # follow ?a -> ?b -> Arjun chains
        if a1 == a2: continue
        if is_var(a1): b[a1] = a2
        elif is_var(a2): b[a2] = a1
        else: return None                 # two different constants
    return b
```

### 17.2 `certainty.py`: the CF maths
```python
def combine(a, b):
    if a >= 0 and b >= 0: return a + b * (1 - a)
    if a < 0 and b < 0:   return a + b * (1 + a)
    return (a + b) / (1 - min(abs(a), abs(b)))
```

### 17.3 `forward.py`: forward chaining
The main loop, simplified:
```python
for cycle in range(1, max_cycles + 1):
    new_supports = self._fire_all(cf)          # MATCH + ACT for every rule
    new_cf = self._combine(evidence, new_supports)
    ...log what fired / retracted / changed...
    if nothing changed: break                  # FIXPOINT
```
`_fire_all` builds an index of **believed** facts (CF ≥ 0.2) by predicate, then pattern-matches each rule's premises from left to right:
```python
def _match(self, premises, i, b, used, index):
    if i == len(premises): yield b, used; return
    p = premises[i]
    if is_builtin(p):                                  # e.g. between(?t, ?s, ?e)
        if eval_builtin(p, b): yield from self._match(premises, i+1, b, used, index)
        return
    for fact in index.get(p.pred, []):
        b2 = unify(p, fact, b)
        if b2 is not None:
            yield from self._match(premises, i+1, b2, used + (fact,), index)
```
Each firing is stored under the key `(rule.id, facts_used)`. This key gives refraction and lets the engine rebuild the proof tree later.

### 17.4 `backward.py`: backward chaining
```python
def _solve(self, goal, depth):
    if canonical(goal) in self._memo: return memo        # MEMOISATION
    if canonical(goal) in self._active: return {}        # LOOP DETECTION
    # 1. evidence that unifies with the goal
    # 2. ASK the investigator (interactive, ground askable goals only)
    # 3. for each rule whose THEN unifies with the goal:
    #        rename the rule's variables (standardising apart)
    #        prove its premises left-to-right, passing bindings along
    #        contribution = min(premise CFs) × rule CF
    # combine all contributions per answer → Explanation
```
When a premise that only evidence can supply (an ASK predicate) cannot be proved, `_record_lead()` records it as an **investigative lead**. It also works out the lead's polarity by multiplying the signs of the rule CFs on the current goal stack. Evidence under a negative rule would *weaken* the hypothesis.

### 17.5 `hypothesis.py`: the report
For each suspect it:
1. reads motive, means, opportunity, guilty_behaviour and culprit CFs from forward chaining;
2. runs **backward chaining** on `culprit(<suspect>)` and checks that it gives the same CF;
3. lists supporting rules (positive) and refuting evidence (negative) about that person;
4. sorts the leads so that those shoring up the **weakest** part of the case come first.

It then reaches a conclusion:
- **PRIMARY**: the top suspect's CF is ≥ 0.6 and at least 0.2 ahead of the next;
- **LEADING**: the top suspect is ahead, but the evidence is weak;
- **COMPETING**: the top suspects are within 0.2 of each other;
- **INCONCLUSIVE**: no suspect is supported.

---

## 18. Running the Project

**Requirements:** Python 3.8 or newer. The core engine and CLI use **only the standard library**. The web UI needs `pip install streamlit pandas`.

```bash
cd evidence-hypothesis-engine

python main.py cases                                    # list the sample cases
python main.py solve 1                                  # full investigation report
python main.py solve 1 --trace                          # + forward-chaining cycles
python main.py solve 1 --explain "culprit(Arjun)"       # + HOW explanation
python main.py query 1 "culprit(?who)"                  # backward chaining on a goal
python main.py query 2 "manner_of_death(Dr_Iyer, ?how)"
python main.py query 3 "culprit(Rohan)" --interactive   # engine asks YOU questions
python main.py query 1 "motive(?who)" --trace           # see the goal search
python main.py rules                                    # print the knowledge base

python -m unittest discover -s tests -v                 # run the tests
streamlit run app.py                                    # web interface
```

### Sample output (Case 1, abridged)
```
3. Suspect analysis  (Motive / Means / Opportunity / Guilty behaviour)
  Suspect       Motive   Means  Opport.   Guilt   Culprit CF                      Verdict
  Arjun          +0.63   +0.61   +0.84   +0.77   █████████████████░░░ +0.87  Strongly supported
  Sunil          +0.30   +0.00   +0.32   +0.00   ███░░░░░░░░░░░░░░░░░ +0.14  Insufficient evidence
  Meera          +0.00   +0.43   +0.24   +0.00   ░░░░░░░░░░░░░░░░░░░░ +0.00  Insufficient evidence
  Kabir          +0.77   +0.00   -0.85   +0.00   ███████████████░░░░░ -0.76  Refuted

  Kabir - culprit CF -0.76 (Refuted)   backward chaining check: -0.76 ✓
     - R32: A verified alibi rules out opportunity  -> opportunity(Kabir)  (-0.85)
     - R105: A verified alibi argues against guilt  -> culprit(Kabir)  (-0.76)

6. Conclusion
  PRIMARY HYPOTHESIS - Arjun (CF 0.87, strongly supported).
```
Kabir had the **strongest motive** (0.77) of anyone, but the engine still clears him because his verified alibi removes his opportunity. Meera had access and her prints were on the weapon, but she has no motive and showed no guilty behaviour, so no culprit rule fires. Points like these make good material for your presentation.

---

## 19. Solving Case 1 by Hand

Being able to reproduce the engine's number on the whiteboard makes a strong impression in a viva. Here is how Arjun gets **0.87**.

**Step 1: Weapon.**
R02: min(victim 1.0, wound_matches 0.9) × 0.85 = 0.765
R01: min(victim 1.0, blood_on 0.95) × 0.80 = 0.760
Combine: 0.765 + 0.760 × (1 − 0.765) = **0.944**

**Step 2: Means.**
handled_weapon (R10) = min(0.944, fingerprint 0.85) × 0.8 = 0.680
means (R40) = 0.680 × 0.9 = **0.612**

**Step 3: Motive.** R50: min(1.0, beneficiary 0.9) × 0.7 = **0.630**

**Step 4: Opportunity.**
present_at_scene: R20 (CCTV at 22:10 is inside 21:00–23:00) = min(1, 0.9, 1, 0.7) × 0.9 = 0.630; R21 (footprint size 9) = min(1, 0.7, 1) × 0.5 = 0.350 → 0.630 + 0.350 × 0.370 = 0.760
inside_job(Study) = 0.9 × 0.6 = 0.540 → access_to_scene(Arjun) = min(0.540, 0.9) × 0.75 = 0.405
opportunity: R30 = 0.760 × 0.9 = 0.684; R33 = 0.8 × 0.4 = 0.320; R31 = 0.405 × 0.6 = 0.243
→ 0.684 + 0.320 × 0.316 = 0.785 → 0.785 + 0.243 × 0.215 = **0.837**

**Step 5: Guilty behaviour.** R62 = 0.8 × 0.7 = 0.56; R60 = 0.8 × 0.6 = 0.48 → 0.56 + 0.48 × 0.44 = **0.771**

**Step 6: Culprit.**
| Rule | Calculation | Contribution |
|---|---|---|
| R100 motive ∧ means ∧ opportunity | min(1, 0.63, 0.612, 0.837) × 0.9 | 0.551 |
| R101 means ∧ opportunity ∧ guilt | min(1, 0.612, 0.837, 0.771) × 0.75 | 0.459 |
| R102 motive ∧ opportunity | min(1, 0.63, 0.837) × 0.45 | 0.284 |
| R103 motive ∧ means | min(1, 0.63, 0.612) × 0.4 | 0.245 |

Combine: 0.551 → 0.551 + 0.459(0.449) = 0.757 → 0.757 + 0.284(0.243) = 0.826 → 0.826 + 0.245(0.174) = **0.868 ≈ 0.87** ✔

---

## 20. Reading the Traces

### Forward trace (`solve 3 --trace`)
```
  Cycle 1
    FIRE R26   staged_break_in(Showroom)   +0.68   because crime_scene(Showroom), entry_damage_from_inside(Showroom)
    FIRE R28   inside_job(Showroom)        -0.36   because crime_scene(Showroom), forced_entry(Showroom)
    FIRE R70   linked_to_loot(Danish)      +0.64   because stolen_item(Gold_Bangles), possessed_item(Danish, Gold_Bangles)
    ...
  Cycle 2
    FIRE R27   inside_job(Showroom)        +0.61   because staged_break_in(Showroom)
    CF inside_job(Showroom)   -0.36 -> +0.39
```
In cycle 1 the smashed window counts **against** an inside job (−0.36). In cycle 2 the engine has worked out that the break-in was **staged** (glass fell outward), and the belief flips to **+0.39**. This is chaining and belief revision happening together.

### Backward trace (`query 1 "motive(?who)" --trace`)
```
GOAL motive(?who)
  TRY R50: Gains financially from the victim (will, insurance, business)
    GOAL victim(?v_1)
      FACT victim(Vikram)  CF +1.00  (FIR No. 221/2026)
    GOAL beneficiary_of(?p_1, Vikram)
      FACT beneficiary_of(Arjun, Vikram)  CF +0.90  (Will held by family lawyer - Arjun inherits 60%)
  R50 => motive(Arjun)  contribution +0.63
  TRY R51: Owes the victim money
    GOAL victim(?v_2)  (already solved)
    GOAL owes_money(?p_2, Vikram)
  ...
```
Each indented level is a **sub-goal**. Some things to point out:
- R50's variables were renamed to `?v_1` and `?p_1` (standardising apart). The goal's `?who` was unified with `?p_1`.
- Solving `victim(?v_1)` bound it to `Vikram`, and that binding was passed into the next sub-goal: `beneficiary_of(?p_1, Vikram)`.
- `(already solved)` is **memoisation** at work. When R51 needs the victim again, the engine reuses the earlier answer.

---

## 21. Testing

`python -m unittest discover -s tests -v` runs 18 tests:
- **Logic:** parsing, parse errors, unification (including `same(?x, ?x)` failing on different values), built-ins (including `lt(9, 10)` being numeric, not alphabetical).
- **Certainty:** the formulas, and that the result is independent of the order of evidence.
- **Parser validation:** unbound conclusion variables, tests used before binding, CF out of range.
- **Chaining:** toy knowledge bases with known answers, negative evidence, the threshold, ASK and leads.
- **Cross-check (the most important):** for every sample case and **every derived predicate**, backward chaining returns exactly the same CF as forward chaining.
- **Expected outcomes:** Arjun, Nikhil and Rohan rank first in their cases, and Kabir is refuted.

---

## 22. Extending the Project

**Add a rule.** Append it to `knowledge/crime_rules.kb`:
```
RULE R24 "Phone location places the person at the scene"
  IF   crime_scene(?l)
  AND  phone_location(?p, ?l, ?t)
  AND  victim(?v)
  AND  time_of_death(?v, ?s, ?e)
  AND  between(?t, ?s, ?e)
  THEN present_at_scene(?p)
  CF   0.8
ASK phone_location "Was {0}'s phone located at the {1} (time {2})?"
```

**Add a case.** Copy a file in `cases/`, change the evidence, and run `python main.py solve <name>`.

**Change the domain.** The engine knows nothing about crime. Write `knowledge/medical.kb` (symptoms → diseases) and run `python main.py query my_patient.json "disease(?d)" --rules knowledge/medical.kb`. Note that `investigate()` profiles predicates named `suspect`, `culprit`, `motive` and so on, so for a new domain use `query` or adapt `hypothesis.py`.

---

## 23. Limitations and Future Scope

| Limitation | Possible improvement |
|---|---|
| CFs are not true probabilities, and combining them assumes the evidence is independent | Bayesian networks; Dempster–Shafer theory |
| Rules are written by hand (the *knowledge-acquisition bottleneck*) | Learn rule weights from solved cases; tools for experts to edit rules |
| Evidence must be typed in as facts | Use NLP or an LLM to **extract facts from FIRs and witness statements**, while the rule engine stays responsible for the explainable reasoning (a *neuro-symbolic* design) |
| Simple time handling (`between` on one day) | Full temporal reasoning (Allen's interval algebra); timeline view |
| Matching re-checks every rule each cycle | **Rete algorithm** (Forgy, 1982), as used in CLIPS and Drools, for large rule bases |
| No negation in premises ("NOT seen anywhere") | Negation-as-failure with stratification |
| Fixed list of suspects | Generate suspects automatically from everyone linked to the evidence |

---

## 24. Ethics

- **Decision support, not a verdict.** The output is a set of hypotheses for a human investigator to examine. Guilt is decided by courts, based on evidence tested under law. The report says this explicitly.
- **Presumption of innocence.** A high CF means only that the recorded evidence fits a hypothesis. It is not proof.
- **Garbage in, garbage out.** Biased or false records produce biased conclusions. The `source` field and the proof trees exist so that every conclusion can be audited.
- **Bias in rules.** Rules like "financial trouble → motive" can unfairly target poorer people. Each rule's CF should be justified and reviewed.
- **Explainability is a safety feature.** Unlike black-box models, every number here can be traced, questioned and corrected.
- **Privacy.** Real case data is sensitive and must be protected.

---

# PART C: EXAM AND VIVA PREPARATION

## 25. Viva Questions with Answers

**Q1. What does your project do?**
It is a rule-based expert system. It takes the evidence records of a case, uses forward chaining to derive all hypotheses the evidence supports, and ranks suspects by certainty factors using motive, means and opportunity. It uses backward chaining to verify each hypothesis, explain it, and list missing evidence.

**Q2. What is forward chaining?**
Data-driven inference. It starts from the known facts and repeatedly fires every rule whose conditions are satisfied, adding the conclusions, until no new facts can be derived (a fixpoint).

**Q3. What is backward chaining?**
Goal-driven inference. It starts from a hypothesis and finds rules that conclude it, then recursively tries to prove their premises as sub-goals until it reaches known facts.

**Q4. Why did you use both?**
Forward chaining is good for discovering every hypothesis when we don't know what to ask. Backward chaining is good for testing a specific hypothesis, asking for missing information, and finding leads. Investigators do both. Running both also gives a correctness check, because they must reach the same CF.

**Q5. Which is more efficient?**
It depends on the problem. Backward chaining explores only what is relevant to one goal. Forward chaining is better when you need all conclusions or when data arrives continuously.

**Q6. What is unification?**
Finding a substitution of variables that makes two atoms identical. For example, `fingerprint_on(?p, Knife)` and `fingerprint_on(Arjun, Knife)` unify with `?p = Arjun`.

**Q7. What is a certainty factor?**
A number from −1 to +1 expressing belief in a fact or rule, introduced by MYCIN. Positive means supporting, negative means refuting, zero means unknown.

**Q8. How do you compute the CF of a conclusion?**
min(CF of premises) × CF of rule. When several rules support the same fact, combine them with a + b(1 − a) for positives, with the corresponding formulas for negatives and mixed signs.

**Q9. Why min for AND?**
A conjunction is only as believable as its weakest part, as in fuzzy logic.

**Q10. What is the threshold for?**
Facts with CF < 0.2 are not used as premises. This stops weak evidence from triggering long chains of conclusions. MYCIN used the same value.

**Q11. How does your system handle contradicting evidence?**
With negative-CF rules, e.g. a verified alibi gives opportunity −0.9. Positive and negative contributions are combined with the mixed formula, so contradictory evidence pulls the belief towards zero or below.

**Q12. What is a fixpoint?**
The state where another cycle of forward chaining changes nothing. That is when the algorithm stops.

**Q13. What is conflict resolution?**
Choosing which rule to fire when several match, e.g. by refraction, recency, specificity or priority. Our engine fires every matching rule instance each cycle and uses refraction (each rule-plus-facts combination counts once), so the result doesn't depend on rule order.

**Q14. What is refraction?**
Not firing the same rule on the same facts more than once. It prevents infinite loops.

**Q15. How do you avoid infinite loops in backward chaining?**
The engine keeps a set of goals currently being proved and skips a goal that is already on the stack. It also has a depth limit, and it memoises solved goals.

**Q16. What is memoisation and why use it?**
Caching the result of a solved sub-goal. Sub-goals such as `murder_weapon(?o)` are needed by many rules, so caching avoids proving them again.

**Q17. What is standardising apart?**
Renaming a rule's variables each time it is used (`?p` → `?p_17`) so that two uses of the same rule don't interfere with each other's bindings.

**Q18. What are the HOW and WHY facilities?**
HOW shows the proof tree for a conclusion. WHY, asked during questioning, shows the chain of goals and rules that made the system ask.

**Q19. What is an "investigative lead" in your system?**
A piece of evidence that could be asked for (an ASK predicate) and that backward chaining needed but couldn't find. If it were found, it would strengthen or weaken a hypothesis. Polarity comes from the signs of the rule CFs on the goal stack.

**Q20. Is crime solving deduction?**
Not strictly. It is abduction (inference to the best explanation). We encode abductive knowledge ("blood on object suggests weapon") as IF-THEN rules with certainty factors.

**Q21. What is the difference between the knowledge base and working memory?**
The knowledge base holds general rules that are valid for every case. Working memory holds the facts of the current case, both the evidence and what has been derived.

**Q22. What is non-monotonic reasoning? Does your system do it?**
Reasoning where new information can remove an earlier conclusion. Yes, in a limited way. The forward chainer recomputes support every cycle, so conclusions are retracted when a premise falls below the threshold, and negative evidence lowers the CF.

**Q23. Limitations of certainty factors?**
They are not probabilities, the combination formula assumes independent evidence, and the values are subjective. Bayesian networks are the more principled alternative.

**Q24. How is this different from machine learning?**
ML learns patterns from data and is often a black box. Our system reasons with explicit expert rules and explains every step, and it needs no training data. The drawback is that someone has to write the rules.

**Q25. What is the Rete algorithm?**
An efficient matching algorithm for forward chaining. It compiles rules into a network that remembers partial matches, so only changes are re-processed. CLIPS, Drools and Jess use it.

**Q26. What are Horn clauses?**
Clauses with at most one positive literal. In rule form: a conjunction of conditions implies a single conclusion. Efficient forward and backward chaining work on Horn clauses.

**Q27. Can your engine be used for another domain?**
Yes. The engine doesn't contain any crime knowledge. Medical diagnosis, fault diagnosis or loan approval only need a different `.kb` file and different facts.

**Q28. What is the time complexity of your forward chaining?**
Each cycle tries every rule against the believed facts. In the worst case that is O(R × F^k) per cycle, for R rules, F facts and k premises per rule. The number of cycles is bounded by the depth of the rule chains (4–5 here). Indexing facts by predicate reduces the work in practice. Rete would improve it further.

**Q29. Why use a custom rule language instead of Python if-statements?**
It keeps knowledge separate from the inference engine. Investigators can read and edit rules without programming. The same engine can reason both forwards and backwards over the same rules, and every rule can be cited in explanations.

**Q30. How did you test correctness?**
With unit tests for every component, and above all a cross-check that forward and backward chaining give identical CFs for every derived fact in every case. The two algorithms explore the rules in completely different ways, so agreement is strong evidence that both are correct.

## 26. Glossary

| Term | Meaning |
|---|---|
| **Abduction** | Inference to the best explanation |
| **Antecedent / premise** | The IF part of a rule |
| **Arity** | Number of arguments of a predicate |
| **Atom** | `predicate(arg, …)` |
| **Backward chaining** | Goal-driven inference from hypothesis to evidence |
| **Binding / substitution** | An assignment of values to variables, e.g. `{?p: Arjun}` |
| **Certainty factor (CF)** | Belief from −1 to +1 |
| **Conflict set** | All rule instances that match in a cycle |
| **Consequent / conclusion** | The THEN part of a rule |
| **Expert system** | AI that captures expert knowledge as rules |
| **Fixpoint** | The point where inference adds nothing new |
| **Forward chaining** | Data-driven inference from evidence to conclusions |
| **Ground atom** | An atom without variables |
| **Horn clause** | Rule with AND-ed premises and one conclusion |
| **Inference engine** | The algorithm that applies rules |
| **Knowledge base** | The set of general rules |
| **Lead** | Missing askable evidence that would change a hypothesis |
| **Memoisation** | Caching results of solved sub-goals |
| **Modus ponens** | From A→B and A, infer B |
| **Predicate** | A property or relation name, e.g. `seen_at` |
| **Refraction** | Never firing the same rule on the same facts twice |
| **Standardising apart** | Renaming rule variables on each use |
| **Threshold** | Minimum CF for a fact to be used (0.2) |
| **Unification** | Making two atoms identical by binding variables |
| **Working memory** | Facts about the current case |

## 27. References

1. S. Russell & P. Norvig, *Artificial Intelligence: A Modern Approach*, 4th ed., Pearson. Chapters 7–9 (logical agents, first-order logic, inference: forward & backward chaining, unification).
2. B. G. Buchanan & E. H. Shortliffe, *Rule-Based Expert Systems: The MYCIN Experiments of the Stanford Heuristic Programming Project*, Addison-Wesley, 1984. Certainty factors.
3. J. Giarratano & G. Riley, *Expert Systems: Principles and Programming*, 4th ed. CLIPS, forward chaining, conflict resolution.
4. P. Jackson, *Introduction to Expert Systems*, 3rd ed., Addison-Wesley.
5. C. Forgy, "Rete: A Fast Algorithm for the Many Pattern/Many Object Pattern Match Problem," *Artificial Intelligence* 19, 1982.
6. E. Rich, K. Knight & S. B. Nair, *Artificial Intelligence*, 3rd ed., McGraw-Hill. Commonly used in Indian university syllabi.
7. I. Bratko, *Prolog Programming for Artificial Intelligence*, 4th ed. Backward chaining in practice.
