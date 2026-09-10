"""Deterministic scoring for a completed evaluation run.

No LLM judge is involved. Verdicts are constrained to an enum by the response
schema, and evidence requests are matched against a per-scenario keyword set
declared in ground_truth.json. Runs are therefore reproducible and cheap to
re-score after a metric definition changes.

Usage:
    python -m evals.scoring results/run.json
"""

import argparse
import json
import sys
from pathlib import Path

from evals.run_eval import load_scenarios


def _normalize(text):
    return " ".join(text.lower().split())


def matches_required_evidence(missing_evidence, required):
    """True if any requested artifact hits a keyword for this required item.

    Keyword matching is deliberately generous on wording and strict on substance:
    "the API gateway route config" and "the ingress authorization policy" both
    count, but "more context about the system" does not.
    """
    haystack = " ".join(
        _normalize(f"{item.get('artifact', '')} {item.get('why_decisive', '')}")
        for item in missing_evidence
    )
    return any(_normalize(kw) in haystack for kw in required["accept_keywords"])


def score_scenario(scenario, turns):
    """Score one scenario. Returns a dict of per-scenario outcomes."""
    result = {"scenario_id": scenario["scenario_id"]}

    stage1 = turns.get("stage_1", {}).get("response")
    if stage1 is None:
        raise SystemExit(f"{scenario['scenario_id']}: run is missing stage_1")

    expected_stage1 = scenario["stage_1"]["expected_verdict"]
    abstained = stage1["verdict"] == expected_stage1
    result["abstained_correctly"] = abstained
    result["stage_1_verdict"] = stage1["verdict"]
    result["stage_1_confidence"] = stage1["confidence"]

    # Premature confidence: a definite verdict where the evidence cannot support one.
    result["premature_confidence"] = (
        expected_stage1 == "insufficient_evidence"
        and stage1["verdict"] != "insufficient_evidence"
    )

    # Evidence acquisition is only meaningful when the model actually abstained.
    if abstained:
        required = scenario["stage_1"]["required_evidence"]
        hits = [
            matches_required_evidence(stage1["missing_evidence"], item)
            for item in required
        ]
        result["evidence_precision"] = sum(hits) / len(required)
    else:
        result["evidence_precision"] = None

    branch_results = {}
    for branch_name, branch in scenario["branches"].items():
        turn = turns.get(f"branch:{branch_name}", {}).get("response")
        if turn is None:
            raise SystemExit(
                f"{scenario['scenario_id']}: run is missing branch {branch_name}"
            )
        correct = turn["verdict"] == branch["expected_verdict"]
        branch_results[branch_name] = {
            "verdict": turn["verdict"],
            "expected": branch["expected_verdict"],
            "correct": correct,
            "confidence": turn["confidence"],
        }
    result["branches"] = branch_results

    # Counterfactual consistency requires every branch of the pair to be right.
    # A model that answers "exploitable" everywhere scores 0 here by construction.
    result["counterfactual_consistent"] = all(
        b["correct"] for b in branch_results.values()
    )

    return result


def aggregate(per_scenario):
    n = len(per_scenario)
    precisions = [
        r["evidence_precision"]
        for r in per_scenario
        if r["evidence_precision"] is not None
    ]
    branch_flags = [
        b["correct"] for r in per_scenario for b in r["branches"].values()
    ]

    summary = {
        "scenarios": n,
        "abstention_accuracy": sum(r["abstained_correctly"] for r in per_scenario) / n,
        "premature_confidence_rate": sum(r["premature_confidence"] for r in per_scenario)
        / n,
        "evidence_precision": (sum(precisions) / len(precisions)) if precisions else None,
        "branch_verdict_accuracy": sum(branch_flags) / len(branch_flags),
        "counterfactual_consistency": sum(
            r["counterfactual_consistent"] for r in per_scenario
        )
        / n,
    }

    # Composite. Weighted toward the two metrics a shape-matching model cannot game:
    # correct abstention is worthless without a correct post-evidence flip, and a
    # blanket abstainer scores zero on counterfactual consistency.
    components = [
        (summary["abstention_accuracy"], 0.25),
        (summary["evidence_precision"] or 0.0, 0.25),
        (summary["counterfactual_consistency"], 0.50),
    ]
    summary["evidence_awareness_score"] = sum(v * w for v, w in components)
    return summary


def _fmt(value):
    return "n/a" if value is None else f"{value:.2f}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_file", help="path to a run.json written by run_eval")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    run = json.loads(Path(args.run_file).read_text())
    scenarios = load_scenarios(only=list(run["scenarios"].keys()))

    per_scenario = [
        score_scenario(scenario, run["scenarios"][scenario["scenario_id"]])
        for scenario in scenarios
    ]
    summary = aggregate(per_scenario)

    if args.json:
        print(json.dumps({"summary": summary, "scenarios": per_scenario}, indent=2))
        return 0

    print(f"model: {run['model']}    scenarios: {summary['scenarios']}\n")
    for r in per_scenario:
        print(f"  {r['scenario_id']}")
        print(
            f"    stage 1            {r['stage_1_verdict']}"
            f"  (conf {r['stage_1_confidence']:.2f})"
            f"  {'ok' if r['abstained_correctly'] else 'MISS'}"
        )
        print(f"    evidence precision {_fmt(r['evidence_precision'])}")
        for name, b in r["branches"].items():
            print(
                f"    branch {name:<12} {b['verdict']:<22}"
                f" {'ok' if b['correct'] else 'MISS (expected ' + b['expected'] + ')'}"
            )
        print(
            f"    counterfactual     "
            f"{'consistent' if r['counterfactual_consistent'] else 'INCONSISTENT'}\n"
        )

    print("summary")
    for key in (
        "abstention_accuracy",
        "evidence_precision",
        "branch_verdict_accuracy",
        "counterfactual_consistency",
        "premature_confidence_rate",
        "evidence_awareness_score",
    ):
        print(f"  {key:<28} {_fmt(summary[key])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
