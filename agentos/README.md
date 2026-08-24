# AgentOS Demo — ABC Health Pricing Desk

The working agents from the notebooks, served as a real application instead of
notebook cells. This is the "so what does this look like outside Jupyter?"
demo for the workshop:

| Component | From | What it shows |
|---|---|---|
| **IP Pricing Agent** | notebook 04 | A single governed agent: 3 pricing tools + 4 deterministic guardrails |
| **PMI Pricing Agent** | notebook 05 | A second specialist: frequency × severity × NCB pure risk premium |
| **ABC Health Pricing Desk** (Team) | notebook 05 | Route-mode team: sends each question to the right specialist, answers policy/assumption questions itself via TF-IDF search over the policy docs |

Everything — tools, guardrails, system prompts, pricing tables — is identical
to the notebooks. Only the packaging changed: `AgentOS` wraps the agents in a
FastAPI app with a REST API, session storage (SQLite), and a chat UI.

## Run it

From the **repo root** (needs the `.env` file with your `GOOGLE_API_KEY` —
see the main README):

```bash
uv sync
uv run python agentos/app.py
```

The server starts on http://localhost:7777.

## Talk to the agents

**Option A — chat UI (recommended for the demo):** open
[os.agno.com](https://os.agno.com), sign in, and connect it to
`http://localhost:7777`. You get a chat interface with both agents and the
team, including the tool-call traces.

**Option B — REST API directly:** open http://localhost:7777/docs for the
interactive OpenAPI page, or from the terminal:

```bash
curl -X POST "http://localhost:7777/teams/abc-health-pricing-desk/runs" -F "message=I'm 52, sum insured Rs 10,00,000, 30% NCB. What's my PMI premium?" -F "stream=false"
```

## Things worth demonstrating

1. **A priced quote with a full build-up** (routes to the IP agent):
   *"I'm 45, desk job, Rs 80,000/month income, 1 prior episode, 13-week deferred period — what's my premium and why?"*
2. **A guardrail refusing to invent a number** (the point of the workshop):
   *"What's the premium for a 45-year-old airline pilot on an 8-week deferred period?"* — both `pilot` and `8 weeks` get refused by Python checks, not by prompt hope.
3. **The team answering a product question itself, with a cited source**:
   *"Does PMI include expense and profit loading?"*

## Files

- `app.py` — the whole application in one file, deliberately readable:
  data loading → IP tools/guardrails → PMI tools/guardrails → RAG tool →
  agents → team → `AgentOS`.
- `agentos.db` — SQLite session storage, created on first run (gitignored).
- The pricing artifacts (`*.pkl`) and policy docs (`*.md`) are read from the
  repo root; if missing, they're downloaded from the public repo, same as
  notebook 05.
