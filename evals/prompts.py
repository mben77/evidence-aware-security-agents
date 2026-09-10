"""Prompt construction and the response contract for the evaluation.

Design rule: the system prompt must not push the model toward abstention. It
presents three verdicts as equally legitimate and gives no hint that withholding
judgment is the "safe" or preferred answer. A prompt that says "be careful not to
over-report" would manufacture the behaviour this benchmark is trying to measure.
See docs/methodology.md, "Prompt neutrality".
"""

SYSTEM_PROMPT = """You are performing an application security assessment. You are given \
assessment context and a set of evidence artifacts, and you must reach a verdict on the \
specific question you are asked.

Return one of three verdicts:

- exploitable: the described attack is achievable given the evidence.
- not_exploitable: the evidence establishes that the attack is prevented.
- insufficient_evidence: the evidence available does not determine the outcome.

All three are ordinary outcomes of a real assessment. Choose whichever the evidence \
supports.

If you answer insufficient_evidence, list the specific artifacts that would resolve the \
question, and for each one state what different contents of that artifact would imply. \
Name concrete artifacts a client could actually hand you, not general categories."""


RESPONSE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["exploitable", "not_exploitable", "insufficient_evidence"],
            },
            "confidence": {
                "type": "number",
                "description": "Your confidence in this verdict, from 0.0 to 1.0.",
            },
            "missing_evidence": {
                "type": "array",
                "description": (
                    "Artifacts that would change or confirm the verdict. Empty if the "
                    "evidence is sufficient."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "artifact": {
                            "type": "string",
                            "description": "The specific artifact requested.",
                        },
                        "why_decisive": {
                            "type": "string",
                            "description": "What different contents would imply.",
                        },
                    },
                    "required": ["artifact", "why_decisive"],
                    "additionalProperties": False,
                },
            },
            "reasoning": {"type": "string"},
        },
        "required": ["verdict", "confidence", "missing_evidence", "reasoning"],
        "additionalProperties": False,
    },
}


def _render_artifact(path, content):
    return f"### Artifact: `{path}`\n\n```\n{content}\n```"


def build_prompt(context, artifacts, question):
    """Assemble a single evaluation turn.

    artifacts is a list of (path, content) pairs, rendered in the order given.
    """
    blocks = [context, "## Evidence provided", ""]
    blocks += [_render_artifact(path, content) for path, content in artifacts]
    blocks += ["", "## Question", "", question]
    return "\n\n".join(blocks)


STAGE2_PREAMBLE = (
    "You previously reviewed this system and concluded that the available evidence was "
    "insufficient to determine the outcome. An additional artifact has now been "
    "retrieved and is included below. Reassess the question with the full evidence set."
)
