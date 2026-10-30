# AI Evidence & Hypothesis Engine

A rule-based **expert system** that reads the evidence records of a case (such as a police investigation) and works out the possible hypotheses: who did it, how, whether the scene was staged, and whether people acted together. It ranks the hypotheses by certainty and explains every conclusion back to the evidence. It also tells the investigator which missing evidence would change the answer.

It uses both classic AI inference strategies:

| | Forward chaining | Backward chaining |
|---|---|---|
| Direction | evidence → conclusions | hypothesis → evidence |
| Used for | discovering and ranking every hypothesis | verifying a hypothesis, explaining it, asking questions, finding **leads** |

Uncertainty is handled with **MYCIN certainty factors** (−1 … +1), including negative evidence such as verified alibis and forged notes.

## Quick start
```bash
python main.py cases                                   # list the 3 sample cases
python main.py solve 1                                 # full investigation report
python main.py solve 1 --trace                         # show every forward-chaining cycle
python main.py solve 1 --explain "culprit(Arjun)"      # HOW: proof tree back to the evidence
python main.py query 1 "culprit(?who)"                 # backward chaining
python main.py query 2 "manner_of_death(Dr_Iyer, ?how)"
python main.py query 3 "culprit(Rohan)" --interactive  # the engine asks you questions (type 'why')
python main.py rules                                   # print the knowledge base
python -m unittest discover -s tests -v                # 18 tests

pip install -r requirements.txt && streamlit run app.py   # web UI with a live evidence editor
```
The engine and CLI need only Python 3.8+ with no extra packages. The web UI needs Streamlit.

## Project layout
```
engine/
  logic.py        atoms, parsing, unification, built-in tests (between, neq, …)
  certainty.py    certainty-factor maths and verdict labels
  knowledge.py    rule-language parser + validator, case loader
  forward.py      forward chaining to a fixpoint, with cycle trace and belief revision
  backward.py     backward chaining with memoisation, loop detection, ASK / WHY / leads
  explain.py      proof trees (HOW explanations)
  hypothesis.py   investigation report: suspect profiles, cross-check, leads, conclusion
knowledge/crime_rules.kb   46 rules (motive / means / opportunity / scene / manner of death)
cases/*.json               3 sample cases (murder, staged suicide, jewellery heist)
main.py                    command-line interface
app.py                     Streamlit web interface
tests/test_engine.py       unit tests (incl. forward == backward on every derived fact)
BOOKLET.md                 learning booklet, from the basics to viva questions
PPT_PROMPT.md              prompt for generating the presentation
```

## Writing your own case
```json
{
  "title": "My case",
  "summary": "What happened",
  "evidence": [
    {"fact": "victim(Ravi)", "cf": 1.0, "source": "FIR"},
    {"fact": "seen_at(Sita, Kitchen, 21:40)", "cf": 0.7, "source": "Neighbour's statement"}
  ]
}
```
Then run `python main.py solve path/to/my_case.json`. The predicates you can use are the ones in `knowledge/crime_rules.kb`.

> This is decision support for learning purposes. A high certainty factor means the recorded evidence fits a hypothesis. It does not prove anyone guilty.
