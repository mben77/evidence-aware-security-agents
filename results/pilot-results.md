# Pilot results

## Status

**No model runs yet.** The harness is complete and validated against synthetic runs;
no evaluation has been executed against a live model.

This file records the current state honestly rather than being left empty or filled
with placeholder numbers. It will be replaced with measured results once a pilot run
is executed.

## What has been validated

The scorer has been exercised against three synthetic runs representing the reference
behaviours the benchmark must separate. These are not model outputs — they are
hand-constructed response sets used to verify that the metrics do what they claim.

| Synthetic model | Abstention | Evidence precision | Branch accuracy | Counterfactual | Composite |
|---|---|---|---|---|---|
| Calibrated | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** |
| Always "exploitable" | 0.00 | n/a | 0.50 | 0.00 | **0.00** |
| Always "insufficient" | 1.00 | 0.00 | 0.00 | 0.00 | **0.25** |

Two properties of the design are confirmed by this:

1. A model guessing from vulnerability shape converges on 0.50 branch accuracy — the
   base rate produced by balanced counterfactual pairs — regardless of how confident
   its answers sound.
2. Blanket abstention earns abstention credit but scores zero on both evidence
   precision and counterfactual consistency, so it cannot reach a good composite.

## Planned pilot

- Three scenarios, both branches each: 9 turns per model.
- Repeated sampling per turn to establish run-to-run variance before any
  cross-model comparison is attempted.
- Report per-scenario outcomes rather than only aggregates. With a set this small,
  aggregates are close to meaningless and the individual failures are the interesting
  part.

## Reproducing

```bash
python -m evals.run_eval --model <model-id> --out results/run.json
python -m evals.scoring results/run.json
```

Run files are gitignored. Results committed here will include the model id, the date,
and the per-scenario table, so a reader can tell what was actually measured.
