"""ABC Health Pricing Desk — AgentOS demo app (entrypoint).

Serves the working agents built in the workshop notebooks through agno's
AgentOS web runtime, so you can chat with them in a browser instead of a
notebook cell:

- IP Pricing Agent   (agents/ip_agent.py, from notebook 04): governed Income
  Protection premium explainer — three pricing tools gated by four
  deterministic guardrails (tools/ip_pricing.py).
- PMI Pricing Agent  (agents/pmi_agent.py, from notebook 05): frequency x
  severity x NCB pure risk premium explainer (tools/pmi_pricing.py).
- ABC Health Pricing Desk (team/pricing_team.py, from notebook 05): a
  route-mode Team that sends each question to the right specialist, answering
  policy/assumption questions itself via TF-IDF search over the policy
  documents (tools/policy_docs.py).

Shared configuration — API key, model id, data artifacts, session db — lives
in config.py.

Run from the repo root:

    uv run python agentos/app.py

then open http://localhost:7777/docs for the API, or connect the AgentOS
control plane at https://os.agno.com to http://localhost:7777 for a chat UI.
"""

import sys
from pathlib import Path

# Make the sibling modules importable regardless of where this is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agno.os import AgentOS

from agents.ip_agent import ip_agent
from agents.pmi_agent import pmi_agent
from team.pricing_team import pricing_team

agent_os = AgentOS(
    id="iai-workshop-agentos",
    name="IAI Workshop — ABC Health Pricing Desk",
    description="Governed IP and PMI pricing agents (notebooks 04 & 05) served as a working app.",
    agents=[ip_agent, pmi_agent],
    teams=[pricing_team],
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app=app, host="localhost", port=7777, reload=False)
