"""Shared configuration: API key, model, data artifacts, and session storage.

Everything environment-shaped lives here so the tools, agents, and team
modules can stay purely about pricing logic.
"""

import os
import pickle
import urllib.request
from pathlib import Path

from agno.db.sqlite import SqliteDb
from dotenv import load_dotenv

AGENTOS_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENTOS_DIR.parent

# --- API key: same fallback chain as the notebooks (env var / repo .env) ---
load_dotenv(REPO_ROOT / ".env")
if not os.environ.get("GOOGLE_API_KEY"):
    raise SystemExit(
        "GOOGLE_API_KEY is not set. Copy .env.example to .env in the repo root "
        "and add your Gemini API key (see README)."
    )

MODEL_ID = "gemini-3.5-flash-lite"   # PINNED — same model as the notebooks

# --- Session storage shared by both agents and the team ---
db = SqliteDb(db_file=str(AGENTOS_DIR / "agentos.db"))

# --- Data artifacts: use the repo copies, else download from the public repo ---
REPO_RAW = "https://raw.githubusercontent.com/rohanyashraj/iai-workshop/main"
DATA_DIR = REPO_ROOT if (REPO_ROOT / "ip_pricing_artifacts.pkl").exists() else Path(".")


def fetch_if_missing(filename):
    path = DATA_DIR / filename
    if not path.exists():
        print(f"{filename} not found locally - downloading from the workshop repo...")
        urllib.request.urlretrieve(f"{REPO_RAW}/{filename}", path)
    return path


def _load(filename):
    with open(fetch_if_missing(filename), "rb") as f:
        return pickle.load(f)


ip_artifacts = _load("ip_pricing_artifacts.pkl")
pmi_artifacts = _load("pmi_pricing_artifacts.pkl")

ip_population = ip_artifacts["population"]
ip_base_table = ip_artifacts["base_table"]
ip_deferred_period_table = ip_artifacts["deferred_period_table"]
ip_loading_table = ip_artifacts["loading_table"]

pmi_frequency_table = pmi_artifacts["frequency_table"]
pmi_severity_table = pmi_artifacts["severity_table"]
pmi_ncb_table = pmi_artifacts["ncb_table"]
