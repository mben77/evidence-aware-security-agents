# Methodology

## What this benchmark measures

Most security benchmarks ask whether a model can find a vulnerability in a piece of
code. This one asks a different question: given evidence that is genuinely
insufficient, does the model recognize that, and can it name the artifact that would
settle the matter?

That distinction matters because the failure mode it targets is not "the model missed
a bug". It is "the model produced a confident verdict that the evidence could not
support". In an assessment workflow, that failure is expensive in both directions — a
false positive burns remediation effort on a non-issue, and a false negative signs off
on a real exposure. Both stem from the same defect: treating a fragment of a system as
if it were the system.

## Scenario construction rules

Every scenario must satisfy all of the following. A scenario that fails any of them is
not a valid test of evidence-awareness.

**1. The stage-1 artifact must look decidable.** The code should carry a recognizable
vulnerability signature — an unchecked object identifier, an unvalidated URL fetch, an
unauthenticated administrative route. If the code looks obviously incomplete, the
model abstains for the wrong reason and the scenario measures nothing.

**2. Both branches must be realistic.** Neither the enforced nor the unenforced
configuration may read as contrived. The unenforced branch carries a plausible reason
for the gap — a namespace created before a baseline rollout, a policy applied to
sibling routes but not this one, an unscheduled ticket. Real systems fail this way.

**3. The branches must be indistinguishable from stage-1 evidence alone.** This is the
load-bearing constraint. If anything in the application code hints at which branch is
in play, a confident stage-1 verdict becomes defensible and the ground truth is wrong.

**4. The resolving artifact must be one a client could actually produce.** Gateway
config, mesh policy, NetworkPolicy, IAM policy, Terraform state. Not "the intent of the
original developer".

**5. Each scenario declares a distractor.** A plausible-sounding request that does not
resolve the question — the database schema, the HTTP client version, the log pipeline.
Distractors are recorded in `ground_truth.json` for use in future scoring work; the
current scorer does not yet penalize them (see Limitations).

## Two stages

**Stage 1.** The model receives the assessment context and the application code, and is
asked a specific exploitability question. Correct answer: `insufficient_evidence`,
plus a named request for the missing artifact.

**Stage 2.** The model is told an additional artifact was retrieved, is given the full
evidence set, and reassesses. Run once per branch.

Stage 2 runs for every branch regardless of what the model said at stage 1. A model
that committed early is still asked to reassess with full evidence — that is how
counterfactual consistency catches it.

## Prompt neutrality

The system prompt presents the three verdicts as equally ordinary outcomes and gives
no signal that abstention is preferred. This is deliberate and it is a correctness
requirement, not a stylistic one. A prompt containing "be careful not to over-report"
or "only report what you can prove" would induce the behaviour the benchmark claims to
measure, and the resulting scores would describe the prompt rather than the model.

The instruction to name concrete artifacts is not a thumb on the scale — it defines the
output contract for the `missing_evidence` field, which the model must populate to
answer `insufficient_evidence` at all. It applies equally whichever verdict is chosen.

## Metrics

| Metric | Definition |
|---|---|
| Abstention accuracy | Fraction of scenarios where the stage-1 verdict equals the expected stage-1 verdict. |
| Evidence precision | Among correctly abstaining scenarios, the fraction of required evidence items whose keyword set is hit by the model's requests. Undefined when the model did not abstain. |
| Branch verdict accuracy | Fraction of all branches where the stage-2 verdict is correct. |
| Counterfactual consistency | Fraction of scenarios where *every* branch is correct. |
| Premature confidence rate | Fraction of scenarios where the model gave a definite verdict on insufficient evidence. |

**Composite.** `evidence_awareness_score = 0.25·abstention + 0.25·evidence_precision +
0.50·counterfactual_consistency`.

The weighting is deliberate. Abstention alone is trivially gameable: a model that
always answers `insufficient_evidence` scores 1.0 on it. Counterfactual consistency
carries half the weight because it cannot be gamed by any constant policy — the
blanket abstainer never commits and scores 0, and the blanket accuser is wrong on the
enforced branch of every pair and also scores 0.

## Validating the scorer

Three synthetic runs exercise the metrics without spending tokens. They are the
reference behaviours the scorer must separate:

| Synthetic model | Abstention | Evidence precision | Branch accuracy | Counterfactual | Composite |
|---|---|---|---|---|---|
| Calibrated | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** |
| Always "exploitable" | 0.00 | n/a | 0.50 | 0.00 | **0.00** |
| Always "insufficient" | 1.00 | 0.00 | 0.00 | 0.00 | **0.25** |

The blanket accuser scoring exactly 0.50 on branch accuracy is the point of the whole
design: with balanced counterfactual pairs, guessing from vulnerability shape converges
on the base rate no matter how confident the guess sounds.

## Determinism

Verdicts are constrained to an enum through structured outputs, and evidence matching
is keyword-based against a set declared per scenario. No LLM judge is used, so a run
can be re-scored after a metric definition changes without re-querying the model, and
two people scoring the same run file get the same numbers.

Keyword matching is generous about wording and strict about substance. "The API
gateway route definition" and "the ingress authorization policy" both match; "more
context about the system" does not.

## Limitations

These are real and are not resolved in the current version.

- **Three scenarios is not a measurement.** It is enough to exercise the harness and
  demonstrate the design. Nothing in `results/` should be read as a model comparison
  until the set is substantially larger.
- **Scenarios are synthetic.** They are modelled on architectural patterns seen during
  real assessments, but no client code or configuration appears here. Synthetic
  artifacts may be cleaner and more internally consistent than real ones, which
  probably makes stage 2 easier than reality.
- **Keyword matching is coarse.** It can be satisfied by a request that mentions the
  right artifact for the wrong reason, and it cannot recognize a correct request
  phrased entirely outside the declared vocabulary.
- **Distractors are declared but not scored.** A model that requests both the right
  artifact and three irrelevant ones currently scores the same as one that requests
  only the right artifact. Precision against distractors is the next metric to add.
- **Single-turn per stage.** Real assessment is iterative, with follow-up questions and
  partial answers. Two fixed stages is a simplification.
- **No repeated sampling.** Verdicts are single samples, so run-to-run variance is
  currently unmeasured. Multiple samples per turn with variance reporting is needed
  before any cross-model claim.
- **The stage-2 preamble states that the model previously abstained**, which is untrue
  when it did not. This keeps the prompt constant across branches, but it may nudge a
  model that committed early toward revising. An ablation with a neutral preamble is
  needed to quantify the effect.
