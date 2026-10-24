# agent-workforce

> **Workday for agents** — onboard, manage and offboard your digital workers.

Companies are "hiring" dozens of agents with no HR system: nobody knows who
owns which agent, what it costs, whether it's any good, or which credentials
to revoke when it's retired. `agent-workforce` is the system of record for
digital workers.

## What the MVP does

- **Org records**: agent, role, human manager, cost centre, monthly budget,
  start date, status (`onboarding → probation → active → pip → offboarded`)
- **Onboarding** checklists per role (identity, scopes, budget, runbook,
  escalation contact, eval suite) — can't activate until complete
- **Performance reviews** from metrics: tasks completed, success rate, cost per
  task, escalation rate, incidents → rating (exceeds / meets / below / unacceptable)
  and recommended action (expand scope, keep, PIP, offboard)
- **Offboarding**: generates revocation + handover plan — credentials to revoke,
  owned artefacts transferred to the manager, logs archived, final cost report
- **Workforce report**: headcount and spend by cost centre / manager, budget overruns

## Quickstart

```bash
pip install -e .
agent-workforce demo
```

## Roadmap

- Sync credentials with agent-okta (auto-revoke on offboard)
- Pull metrics from agent-tracer automatically for monthly reviews
- "Agent org chart" UI and approval workflows for new hires
