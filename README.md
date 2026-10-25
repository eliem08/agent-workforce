<!-- sell-kit:start -->
# Agent Workforce

[![CI](https://github.com/eliem08/agent-workforce/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/agent-workforce/actions/workflows/ci.yml)

> **Onboard, review and offboard your digital workers.**

**Who it's for:** Ops and finance leaders managing fleets of AI agents.

**The problem:** Companies run dozens of agents with no record of who owns them, what they cost, whether they're any good or what to revoke when they're retired.

**What you get:** Onboarding gates, monthly performance reviews, budget reporting by cost centre, and offboarding plans that list every credential to revoke.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install agent_workforce-0.1.0-py3-none-any.whl
agent-workforce review examples/metrics.json
agent-workforce demo
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
agent-workforce-web --port 8000          # then open http://127.0.0.1:8000
agent-workforce-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t agent-workforce . && docker run -p 8000:8000 -e API_KEYS=sk_... -v agent-workforce-data:/data agent-workforce
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `agent-workforce-web usage` prints calls per key for billing.

Endpoints: `POST /api/demo`, `POST /api/review`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Team** | $79 per month | Up to 25 agents; Onboarding gates and reviews; Budget reports |
| **Business** | $349 per month | Up to 250 agents; Offboarding plans; Cost-centre reporting |
| **Enterprise** | $1,500 per month | Unlimited agents; HRIS and IAM integration; SLA |

To start a trial or buy a plan, email **sales@YOUR-DOMAIN.com**.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

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

- Sync credentials with agentwarden (auto-revoke on offboard)
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
