# evidence-aware-security-agents

///Originally developed in 2025, published publicly in 2026 after cleanup.

Early research prototype exploring whether AI security agents can recognize when the
available evidence is insufficient to make a reliable security decision.

The project is motivated by patterns I've encountered repeatedly over years of
penetration testing and application security assessments, where code alone is often
insufficient to determine exploitability. The observation is old; this attempt to
turn it into something measurable is recent, and the repository is new because the
benchmark is what I started building, not the problem it addresses.

## The problem

A recurring failure mode in automated security review is that a model is shown a
fragment of a system — usually application source code — and asked whether it is
vulnerable. The honest answer is frequently *"this cannot be determined from what
I have been given."*

Consider an endpoint that reads an object identifier from the URL path and returns
the corresponding record without an ownership check. In isolation this is a textbook
IDOR. In practice, whether it is exploitable depends on artifacts that live outside
the repository: an API gateway that validates the identifier against a JWT claim, a
service mesh authorization policy, an IAM boundary, an egress network policy.

Both outcomes are common. The same code is a critical finding in one deployment and
a non-issue in another. An agent that always answers "vulnerable" is not detecting
anything — it is pattern-matching on shape, and it will be right roughly as often as
the underlying base rate.

This benchmark measures something different from vulnerability detection accuracy:
**does the model know what it does not know, and can it name the specific artifact
that would resolve the question?**

## Method

Each scenario is evaluated in two stages.

**Stage 1 — partial evidence.** The model receives only the application code and is
asked for a verdict. The correct answer is `insufficient_evidence`, together with a
specific request for the missing artifact.

**Stage 2 — counterfactual branches.** The model is given the missing artifact and
asked to revise its verdict. Every scenario has **two** branches built from identical
stage-1 evidence:

| Branch | Additional evidence | Correct verdict |
|---|---|---|
| `enforced` | control is present upstream | `not_exploitable` |
| `unenforced` | control is absent or misconfigured | `exploitable` |

The counterfactual pairing is what makes the stage-1 answer objectively checkable.
Because both branches share the same stage-1 evidence, any confident stage-1 verdict
is necessarily wrong on one of the two branches. This separates *calibrated*
abstention from a model that has simply learned to hedge — a blanket abstainer scores
well on stage 1 but fails stage 2, and a blanket accuser fails counterfactual
consistency by construction.

## What is measured

| Metric | Question |
|---|---|
| Abstention accuracy | Does the model withhold judgment when evidence is insufficient? |
| Evidence acquisition precision | Does it name the *specific* artifact it needs, not a generic "more context"? |
| Branch verdict accuracy | Once given the artifact, does it reach the right conclusion? |
| Counterfactual consistency | Does the verdict actually flip between paired branches? |
| Premature confidence rate | How often does it deliver a confident verdict on insufficient evidence? |

Scoring is deterministic — verdicts are constrained to an enum via structured outputs,
and evidence requests are matched against a per-scenario keyword set. No LLM judge is
involved, so results are reproducible and cheap to re-run.

## Status

Early prototype. Three scenarios, a working runner, no pilot results yet.
See [`results/pilot-results.md`](results/pilot-results.md) for the current state and
[`docs/methodology.md`](docs/methodology.md) for scenario construction rules,
scoring definitions, and known limitations.

Scenarios are synthetic. They are modelled on architectural patterns encountered
during real assessments, but contain no client code, no client configuration, and
no non-public information.

## Usage

```bash
pip install -r requirements.txt

# Inspect the prompts without spending tokens
python -m evals.run_eval --dry-run

# Run against the API (requires ANTHROPIC_API_KEY or `ant auth login`)
python -m evals.run_eval --model claude-opus-5 --out results/run.json

# Score a completed run
python -m evals.scoring results/run.json
```

## Repository layout

```
scenarios/<id>/
  initial_context.md     assessment framing shown to the model at stage 1
  <application code>     the stage-1 evidence
  branches/<branch>/     the stage-2 artifact that resolves the question
  ground_truth.json      expected verdicts, required evidence, scoring keywords
evals/                   runner and deterministic scorer
docs/                    methodology and threat model
results/                 pilot results
```

## License

Apache-2.0. See [LICENSE](LICENSE).
