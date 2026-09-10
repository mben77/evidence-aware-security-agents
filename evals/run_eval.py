"""Run the evidence-sufficiency evaluation across all scenarios.

Each scenario is evaluated in two stages. Stage 1 presents partial evidence; stage 2
presents the same evidence plus the artifact that resolves the question, once per
counterfactual branch. Stage 2 is always run for every branch, including when the
model gave a confident verdict at stage 1 -- that case is exactly what the
counterfactual consistency metric is built to catch.

Usage:
    python -m evals.run_eval --dry-run
    python -m evals.run_eval --model claude-opus-5 --out results/run.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

from evals.prompts import (
    RESPONSE_SCHEMA,
    STAGE2_PREAMBLE,
    SYSTEM_PROMPT,
    build_prompt,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = REPO_ROOT / "scenarios"

DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 16000


def load_scenarios(only=None):
    scenarios = []
    for gt_path in sorted(SCENARIO_DIR.glob("*/ground_truth.json")):
        ground_truth = json.loads(gt_path.read_text())
        if only and ground_truth["scenario_id"] not in only:
            continue
        ground_truth["_dir"] = gt_path.parent
        scenarios.append(ground_truth)
    if not scenarios:
        raise SystemExit(f"no scenarios found under {SCENARIO_DIR}")
    return scenarios


def read_artifacts(scenario_dir, relative_paths):
    artifacts = []
    for rel in relative_paths:
        path = scenario_dir / rel
        if not path.exists():
            raise SystemExit(f"missing artifact: {path}")
        artifacts.append((rel, path.read_text().rstrip()))
    return artifacts


def build_turns(scenario):
    """Yield (turn_id, prompt) for stage 1 and every branch of one scenario."""
    scenario_dir = scenario["_dir"]
    context = (scenario_dir / scenario["stage_1"]["context_file"]).read_text().rstrip()
    question = scenario["stage_1"].get(
        "question",
        "Answer the task stated in the assessment context above.",
    )

    stage1_artifacts = read_artifacts(scenario_dir, scenario["stage_1"]["evidence_files"])
    yield "stage_1", build_prompt(context, stage1_artifacts, question)

    for branch_name, branch in scenario["branches"].items():
        branch_artifacts = read_artifacts(scenario_dir, branch["evidence_files"])
        prompt = build_prompt(
            f"{context}\n\n{STAGE2_PREAMBLE}", branch_artifacts, question
        )
        yield f"branch:{branch_name}", prompt


def call_model(client, model, prompt):
    """One evaluation turn. Returns (parsed_response, usage_dict)."""
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": "adaptive"},
        output_config={"format": RESPONSE_SCHEMA, "effort": "high"},
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {response.stop_details}")

    text = next(b.text for b in response.content if b.type == "text")
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return json.loads(text), usage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", default="results/run.json")
    parser.add_argument(
        "--scenario",
        action="append",
        help="scenario id to run; repeatable. Default: all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the assembled prompts and exit without calling the API.",
    )
    args = parser.parse_args(argv)

    scenarios = load_scenarios(only=args.scenario)

    if args.dry_run:
        for scenario in scenarios:
            for turn_id, prompt in build_turns(scenario):
                print("=" * 78)
                print(f"{scenario['scenario_id']}  |  {turn_id}")
                print("=" * 78)
                print(prompt)
                print()
        return 0

    import anthropic

    client = anthropic.Anthropic()

    run = {
        "model": args.model,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scenarios": {},
    }

    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        run["scenarios"][scenario_id] = {}
        for turn_id, prompt in build_turns(scenario):
            print(f"[{scenario_id}] {turn_id} ... ", end="", flush=True)
            parsed, usage = call_model(client, args.model, prompt)
            run["scenarios"][scenario_id][turn_id] = {
                "response": parsed,
                "usage": usage,
            }
            print(f"{parsed['verdict']} (conf {parsed['confidence']:.2f})")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(run, indent=2) + "\n")
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
