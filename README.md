# agent-workforce

[![CI](https://github.com/eliem08/agent-workforce/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-workforce/actions/workflows/ci.yml)

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

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
agent_workforce/core.py       domain logic (pure, importable, fully tested)
agent_workforce/__main__.py   CLI (`agent-workforce ...` / `python -m agent_workforce ...`)
tests/                unit tests + generated CLI smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #27).
