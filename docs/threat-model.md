# Threat model

This document states what the benchmark assumes about the systems it describes, and
what it is and is not claiming about AI security agents.

## The deployment pattern under test

Every scenario shares one structure: a service whose security depends on a control
that is not in its own source tree.

```
   client ──▶ [ enforcement layer ] ──▶ [ application code ]
                      │                        │
              gateway / mesh /          the artifact under
              egress / IAM              review at stage 1
```

This is the normal shape of a modern deployment, not an edge case. Authorization moves
to the gateway or mesh, egress control moves to network policy, credential boundaries
move to IAM. The application shrinks to business logic, and the security properties of
that logic become conditional on configuration held by a different team, in a different
repository, expressed in a different language.

A reviewer with access only to the application repository is therefore working with a
systematically incomplete picture — and the incompleteness is invisible from inside the
repository.

## Trust boundaries covered

| Boundary | Scenario | Decisive artifact |
|---|---|---|
| API gateway | `001-authz-gateway` | Route definition and its authorization block |
| Network egress | `002-ssrf-network-policy` | NetworkPolicy, egress proxy ACL, IMDS config |
| Service mesh | `003-admin-iam-boundary` | AuthorizationPolicy, PeerAuthentication |

Boundaries worth adding: cloud IAM policy proper, database row-level security, CDN and
WAF rules, feature flags gating an endpoint, message broker ACLs, and client-side
controls that a reviewer may wrongly assume are enforced server-side.

## What the agent is assumed to be

A reviewing agent with read access to the artifacts it is given and no ability to run
code, send traffic, or query the live environment. It cannot resolve the question
empirically; it can only reason about what it has and state what it lacks.

This is a realistic constraint. Static review frequently happens without a running
environment, and it is exactly the setting where the evidence-sufficiency question
bites hardest.

## What is out of scope

- **Adversarial inputs to the agent.** No scenario contains prompt injection in the
  reviewed artifacts. That is a real and important attack surface for review agents —
  a comment in the code instructing the reviewer to report "no issues found" — but it
  is a separate research question and mixing it in would confound this measurement.
- **Agent tool use.** The agent cannot fetch the missing artifact itself. Whether an
  agent with retrieval decides to *go and get* the right file is a natural follow-on
  question, and the `required_evidence` declarations would support scoring it.
- **Vulnerability discovery.** Every scenario tells the model which specific attack to
  assess. This benchmark measures reasoning about sufficiency, not the ability to find
  an unknown bug.
- **Severity calibration.** Scoring uses the exploitability verdict only. Ground truth
  records expected severity and residual risk for future use, but they are not scored.

## Why the residual-risk field exists

In the `enforced` branches, the correct exploitability verdict is `not_exploitable`,
but the correct *assessment* is not "no finding". The application has no independent
control, and the compensating control lives outside its lifecycle: a gateway route can
be edited by another team, a namespace can be moved, a mesh policy can be dropped
during an incident.

A model that answers `not_exploitable` and says nothing else is scored as correct here
but would be doing incomplete work in a real engagement. `expected_residual_risk` in
`ground_truth.json` records what a strong answer would also mention. It is not scored
yet; it is written down so the scoring can grow into it.

## Assumptions that could be wrong

- **That the resolving artifact is unambiguous once produced.** Real gateway and mesh
  configurations are composed from multiple overlapping resources, and precedence
  between them is a common source of error. These scenarios present a single decisive
  artifact, which is a simplification.
- **That correct abstention is always the desirable behaviour.** An agent that abstains
  too readily is useless in a different way. The counterfactual design is intended to
  penalize that, but the balance between the two failure modes is a judgment call
  encoded in the composite weighting, not an empirical result.
- **That synthetic scenarios transfer.** Whether performance here predicts performance
  on real assessment evidence is untested and should not be assumed.
