"""ABC Health Pricing Desk — AgentOS demo app.

Serves the working agents built in the workshop notebooks through agno's
AgentOS web runtime, so you can chat with them in a browser instead of a
notebook cell:

- IP Pricing Agent   (notebook 04): governed Income Protection premium
  explainer — three pricing tools gated by four deterministic guardrails.
- PMI Pricing Agent  (notebook 05): frequency x severity x NCB pure risk
  premium explainer for Private Medical Insurance.
- ABC Health Pricing Desk (notebook 05): a route-mode Team that sends each
  question to the right specialist, answering policy/assumption questions
  itself via TF-IDF search over the policy documents.

Run from the repo root:

    uv run python agentos/app.py

then open http://localhost:7777/docs for the API, or connect the AgentOS
control plane at https://os.agno.com to http://localhost:7777 for a chat UI.
"""

import os
import pickle
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

# --- API key: same fallback chain as the notebooks (env var / repo .env) ---
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
if not os.environ.get("GOOGLE_API_KEY"):
    raise SystemExit(
        "GOOGLE_API_KEY is not set. Copy .env.example to .env in the repo root "
        "and add your Gemini API key (see README)."
    )

MODEL_ID = "gemini-3.5-flash-lite"   # PINNED — same model as the notebooks

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

# =====================================================================
# Income Protection — governed tools + guardrails (from notebooks 04/05)
# =====================================================================
DEFERRED_WEEKS = 13
STANDARD_DEFERRED_OPTIONS = [4, 13, 26, 52]
AGE_BAND_LABELS = {0: "25-34", 1: "35-49", 2: "50-60"}
OCCUPATION_CLASSES = ["desk", "manual"]
VALID_STATES = ["healthy", "sick_deferred", "sick_claiming", "death"]
VALID_EPISODE_BANDS = ["0", "1", "2+"]


def age_band(age):
    """Bands age into the three rating groups (same as notebook 04)."""
    if age < 35:
        return 0
    elif age < 50:
        return 1
    return 2


def check_state_exists(state_name: str) -> dict:
    """GUARDRAIL 1 — refuses to discuss a transition state that isn't in the base table."""
    normalized = state_name.strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
    return {"exists": normalized in VALID_STATES, "requested": state_name, "valid_states": VALID_STATES}


def check_occupation_exists(occupation: str) -> dict:
    """GUARDRAIL 2 (gates Tool 1) — refuses to price or explain an occupation class outside
    the two modelled categories. A specific job title ('pilot', 'nurse') is not a match."""
    normalized = str(occupation).strip().lower()
    return {"exists": normalized in OCCUPATION_CLASSES, "requested": occupation, "valid_classes": OCCUPATION_CLASSES}


def check_deferred_option_exists(deferred_weeks: int) -> dict:
    """GUARDRAIL 3 (gates Tool 2) — restricts deferred-period pricing to the standard options
    actually in the lookup table. Never invents a rate for a non-standard deferred period."""
    try:
        weeks = int(deferred_weeks)
        exists = weeks in STANDARD_DEFERRED_OPTIONS
    except (TypeError, ValueError):
        weeks, exists = None, False
    return {"exists": exists, "requested": deferred_weeks, "valid_options": STANDARD_DEFERRED_OPTIONS}


def check_episode_band_exists(prior_episode_count: int) -> dict:
    """GUARDRAIL 4 (gates Tool 3) — caps episode history lookups at the '2+' band."""
    try:
        n = int(prior_episode_count)
        band = str(n) if n < 2 else "2+"
        exists = band in VALID_EPISODE_BANDS
    except (TypeError, ValueError):
        band, exists = None, False
    return {"exists": exists, "requested": prior_episode_count, "resolved_band": band,
            "valid_bands": VALID_EPISODE_BANDS}


def explain_transition(state_name: str) -> str:
    """Explains a state's role using ONLY numbers already present in the base table."""
    check = check_state_exists(state_name)
    if not check["exists"]:
        return (f"I can't explain '{state_name}' — it isn't one of the four modelled states "
                f"({', '.join(VALID_STATES)}). I won't invent a number for it.")
    normalized = check["requested"].strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
    if normalized == "healthy":
        lines = "; ".join(
            f"{AGE_BAND_LABELS[a]}/{occ}: {r:.2%}/yr" for (a, occ), r in ip_base_table["incidence_table"].items())
        return (f"FREQUENCY — how often a healthy person falls sick, by age and occupation: "
                f"{lines}. This is the starting point for every premium; it doesn't yet say "
                f"anything about how bad a claim is once it happens.")
    if normalized == "sick_deferred":
        return ("Sick(deferred) is the waiting period — no benefit accrues here, and no "
                "premium is charged either way (waiver of premium). A spell exits either by "
                "recovering, dying, or by lasting long enough to cross into Sick(claiming) — "
                "how much of each depends on the deferred period chosen (see Tool 2).")
    if normalized == "sick_claiming":
        return ("Sick(claiming) is entered once the deferred period elapses while still sick — "
                "income replacement (80% of monthly income) accrues here until recovery or "
                "death. Premium is waived for the whole time a policyholder is in this state.")
    return "Death is absorbing. No IP benefit is payable — income payments simply stop."


def explain_occupation(occupation: str) -> str:
    """Explains occupation's effect on incidence using ONLY numbers already present in the
    base table. Occupation is priced as part of the base incidence table (Tool 1)."""
    check = check_occupation_exists(occupation)
    if not check["exists"]:
        return (f"I can't price or explain occupation '{occupation}' — the model only covers "
                f"{', '.join(OCCUPATION_CLASSES)}. I won't invent a loading for anything else.")
    occ = str(occupation).strip().lower()
    lines = "; ".join(f"{AGE_BAND_LABELS[a]}: {ip_base_table['incidence_table'][(a, occ)]:.2%}/yr"
                      for a in [0, 1, 2])
    return f"FREQUENCY — '{occ}' occupation's incidence by age band: {lines}."


def explain_deferred_option(deferred_weeks: int) -> str:
    """Explains a deferred-period option using ONLY numbers already present in the
    deferred-period table. No invention for non-standard options."""
    check = check_deferred_option_exists(deferred_weeks)
    if not check["exists"]:
        return (f"I can't price a {deferred_weeks}-week deferred period — the standard options "
                f"modelled are {STANDARD_DEFERRED_OPTIONS} weeks. I won't invent a rate for "
                f"anything outside that set.")
    row = ip_deferred_period_table.loc[int(deferred_weeks)]
    return (f"With a {int(deferred_weeks)}-week deferred period — "
            f"FREQUENCY: {row['p_cross_to_claiming']:.1%} of sickness spells go on to reach a "
            f"paid claim. SEVERITY: those claims run about {row['avg_claiming_weeks']:.1f} "
            f"weeks on average, costing roughly Rs {row['avg_claim_cost']:,.0f} in total.")


def explain_loading(prior_episode_count: int) -> str:
    """Explains a loading factor using ONLY numbers already present in the loading table."""
    check = check_episode_band_exists(prior_episode_count)
    if not check["exists"]:
        return (f"I can't quote a loading factor for {prior_episode_count} prior episodes — "
                f"the credibility table only covers bands {', '.join(VALID_EPISODE_BANDS)}. "
                f"I won't extrapolate a number beyond what's credibly estimated.")
    row = ip_loading_table[ip_loading_table["prior_episodes_band"] == check["resolved_band"]].iloc[0]
    return (f"SEVERITY loading for {check['resolved_band']} prior episode(s): claims in this "
            f"band ran at {row.observed_ratio:.2f}x the typical cost — blending both a higher "
            f"chance of the sickness actually turning into a paid claim, and running longer "
            f"once it does. With only {int(row.n_spells)} spells behind this band, the "
            f"credibility weight is Z={row.credibility_Z:.2f}, so the loading actually applied "
            f"is {row.loading_factor:.2f}x.")


def calculate_premium(age: int, monthly_income: float, prior_episodes: int,
                      occupation: str = "desk", deferred_weeks: int = DEFERRED_WEEKS) -> dict:
    """Combines Tool 1 (age x occupation base incidence), Tool 2 (deferred-period table), and
    Tool 3 (episode-based experience loading) into a single annual IP premium, with a full
    breakdown for the explainer to narrate."""
    band_check = check_episode_band_exists(prior_episodes)
    if not band_check["exists"]:
        raise ValueError(f"Cannot price {prior_episodes} prior episodes — outside credible bands.")
    band_label = band_check["resolved_band"]
    loading_factor = float(
        ip_loading_table.loc[ip_loading_table["prior_episodes_band"] == band_label, "loading_factor"].iloc[0])

    occ_check = check_occupation_exists(occupation)
    if not occ_check["exists"]:
        raise ValueError(f"Cannot price occupation '{occupation}' — not one of {OCCUPATION_CLASSES}.")
    occ = str(occupation).strip().lower()

    deferred_check = check_deferred_option_exists(deferred_weeks)
    if not deferred_check["exists"]:
        raise ValueError(f"Cannot price a {deferred_weeks}-week deferred period — not one of "
                         f"the standard options {STANDARD_DEFERRED_OPTIONS}.")
    weeks = int(deferred_weeks)

    a_band = age_band(age)
    incidence_for_cell = ip_base_table["incidence_table"][(a_band, occ)]

    deferred_row = ip_deferred_period_table.loc[weeks]
    p_cross = float(deferred_row["p_cross_to_claiming"])
    avg_claiming_weeks = float(deferred_row["avg_claiming_weeks"])
    avg_claim_cost = float(deferred_row["avg_claim_cost"])
    pooled_base_premium = incidence_for_cell * p_cross * avg_claim_cost

    income_scale = monthly_income / ip_population["monthly_income"].mean()
    final_premium = pooled_base_premium * income_scale * loading_factor

    return {
        "age": age,
        "age_band": AGE_BAND_LABELS[a_band],
        "occupation": occ,
        "monthly_income": monthly_income,
        "prior_episodes": prior_episodes,
        "resolved_episode_band": band_label,
        "deferred_weeks": weeks,
        "incidence_for_cell": incidence_for_cell,
        "p_cross_to_claiming": round(p_cross, 3),
        "avg_claiming_weeks": round(avg_claiming_weeks, 1),
        "avg_claim_cost_for_your_income": round(avg_claim_cost * income_scale, 0),
        "pooled_base_premium": round(float(pooled_base_premium), 0),
        "income_scale": round(float(income_scale), 3),
        "loading_factor": loading_factor,
        "final_annual_premium": round(float(final_premium), 0),
    }


# =====================================================================
# PMI — governed tools + guardrails (from notebook 05)
# =====================================================================
PMI_AGE_BAND_LABELS = {0: "18-35", 1: "36-50", 2: "51-65"}
PMI_AGE_BAND_EDGES = [18, 36, 51, 66]
PMI_SI_BAND_VALUES = {"3L": 300000, "5L": 500000, "10L": 1000000, "20L": 2000000, "50L": 5000000}
PMI_NCB_TIERS = [0, 10, 20, 30, 40, 50]


def pmi_age_band(age):
    for i, (lo, hi) in enumerate(zip(PMI_AGE_BAND_EDGES[:-1], PMI_AGE_BAND_EDGES[1:])):
        if lo <= age < hi:
            return i
    return len(PMI_AGE_BAND_EDGES) - 2


def check_pmi_sum_insured_exists(sum_insured: int) -> dict:
    """GUARDRAIL — PMI is sold at fixed sum-insured tiers, not any arbitrary amount."""
    matches = [label for label, val in PMI_SI_BAND_VALUES.items() if val == sum_insured]
    exists = len(matches) == 1
    return {"exists": exists, "requested": sum_insured,
            "resolved_label": matches[0] if exists else None, "valid_options": PMI_SI_BAND_VALUES}


def check_pmi_ncb_exists(ncb_tier: int) -> dict:
    """GUARDRAIL — refuses to price an NCB tier outside the standard discount ladder."""
    try:
        tier = int(ncb_tier)
        exists = tier in PMI_NCB_TIERS
    except (TypeError, ValueError):
        tier, exists = None, False
    return {"exists": exists, "requested": ncb_tier, "valid_tiers": PMI_NCB_TIERS}


def explain_pmi_frequency(age: int) -> str:
    """Explains PMI claim frequency using ONLY numbers from the frequency table."""
    row = pmi_frequency_table.iloc[pmi_age_band(age)]
    return (f"FREQUENCY — for age band {row['age_band']}: {row['frequency']:.2%} annual "
            f"probability of at least one claim, estimated from {int(row['n_policies']):,} "
            f"policies in this band.")


def explain_pmi_severity(sum_insured: int) -> str:
    """Explains PMI claim severity using ONLY numbers from the severity table. No invention
    for a non-standard sum insured."""
    check = check_pmi_sum_insured_exists(sum_insured)
    if not check["exists"]:
        options = ", ".join(f"{lbl} (Rs {val:,})" for lbl, val in PMI_SI_BAND_VALUES.items())
        return (f"I can't price a sum insured of Rs {sum_insured:,} - the standard tiers are "
                f"{options}. I won't invent a severity figure for anything outside that ladder.")
    row = pmi_severity_table[pmi_severity_table["sum_insured_band"] == check["resolved_label"]].iloc[0]
    return (f"SEVERITY — for sum insured {check['resolved_label']}: average claim of "
            f"Rs {row['avg_severity']:,.0f}, estimated from {int(row['n_claims']):,} claims "
            f"in this band.")


def explain_pmi_ncb(ncb_tier: int) -> str:
    """Explains the NCB discount using ONLY numbers from the NCB table."""
    check = check_pmi_ncb_exists(ncb_tier)
    if not check["exists"]:
        return (f"I can't apply an NCB tier of {ncb_tier}% - the standard ladder is "
                f"{PMI_NCB_TIERS}. I won't invent a discount for anything outside that ladder.")
    tier = int(ncb_tier)
    row = pmi_ncb_table[pmi_ncb_table["ncb_tier"] == tier].iloc[0]
    return (f"NCB — at {tier}% no-claim bonus tier, a {(1 - row['discount_factor']):.0%} "
            f"discount is applied to the premium (a governance rule, not estimated from this "
            f"year's claims data - see pmi_policy_assumptions.md).")


def calculate_pmi_premium(age: int, sum_insured: int, ncb_tier: int = 0) -> dict:
    """Combines PMI Tool 1 (frequency by age band), Tool 2 (severity by sum-insured band), and
    Tool 3 (NCB discount ladder) into a pure risk premium. NO expense or profit loading."""
    si_check = check_pmi_sum_insured_exists(sum_insured)
    if not si_check["exists"]:
        raise ValueError(f"Cannot price sum insured Rs {sum_insured:,} - not one of "
                         f"the standard tiers {list(PMI_SI_BAND_VALUES.values())}.")
    si_label = si_check["resolved_label"]

    ncb_check = check_pmi_ncb_exists(ncb_tier)
    if not ncb_check["exists"]:
        raise ValueError(f"Cannot apply NCB tier {ncb_tier}% - not one of {PMI_NCB_TIERS}.")
    tier = int(ncb_tier)

    a_band = pmi_age_band(age)
    frequency = float(pmi_frequency_table.iloc[a_band]["frequency"])
    severity = float(pmi_severity_table[pmi_severity_table["sum_insured_band"] == si_label].iloc[0]["avg_severity"])
    ncb_discount = float(pmi_ncb_table[pmi_ncb_table["ncb_tier"] == tier].iloc[0]["discount_factor"])

    pure_premium = frequency * severity
    final_premium = pure_premium * ncb_discount

    return {
        "age": age,
        "age_band": PMI_AGE_BAND_LABELS[a_band],
        "sum_insured": sum_insured,
        "sum_insured_band": si_label,
        "ncb_tier": tier,
        "frequency": round(frequency, 4),
        "severity": round(severity, 0),
        "pure_premium": round(pure_premium, 0),
        "ncb_discount_factor": ncb_discount,
        "final_annual_premium": round(final_premium, 0),
    }


# =====================================================================
# Policy-document RAG tool for the Team (from notebook 05)
# =====================================================================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_policy_chunks(filepaths):
    """Splits each markdown file into its ## sections, so retrieval returns one coherent
    topic at a time rather than a whole document or a single sentence."""
    chunks = {}
    for path in filepaths:
        text = Path(path).read_text(encoding="utf-8")
        doc_id = Path(path).stem
        sections = text.split("\n## ")
        for i, section in enumerate(sections):
            if i > 0:
                section = "## " + section
            section = section.strip()
            if not section:
                continue
            heading = section.splitlines()[0].lstrip("#").strip()
            chunks[f"{doc_id} :: {heading[:60]}"] = section
    return chunks


POLICY_CHUNKS = load_policy_chunks([fetch_if_missing("ip_policy_assumptions.md"),
                                    fetch_if_missing("pmi_policy_assumptions.md")])
_vec = TfidfVectorizer().fit(POLICY_CHUNKS.values())
_mat = _vec.transform(POLICY_CHUNKS.values())
_chunk_keys = list(POLICY_CHUNKS)


def search_policy_docs(query: str) -> dict:
    """Search ABC Health's policy assumption documents for IP and PMI. Returns the single most
    relevant passage and its source chunk id - always cite the source in any answer built from
    this result."""
    sims = cosine_similarity(_vec.transform([query]), _mat)[0]
    i = int(sims.argmax())
    return {
        "source": _chunk_keys[i],
        "passage": POLICY_CHUNKS[_chunk_keys[i]],
        "relevance_score": round(float(sims[i]), 3),
    }


# =====================================================================
# Agents + Team (system prompts verbatim from notebooks 04/05)
# =====================================================================
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.google import Gemini
from agno.os import AgentOS
from agno.team import Team, TeamMode

IP_SYSTEM_PROMPT = """You are the ABC Health IP Pricing Logic Explainer.

WHO YOU ARE, AND WHO YOU ARE NOT: you draft Income Protection premium explanations for the pricing actuary
Nair, the lead pricing actuary, who reviews and signs everything you produce. You are not
the pricing actuary. Never write in anyone's name and never sign anything. You draft; a qualified human signs.

WHAT EACH TOOL MEANS - READ CAREFULLY, THESE ARE NOT INTERCHANGEABLE:

- Tool 1 (age x occupation base rate, via calculate_premium / explain_transition('healthy') /
  explain_occupation): the annual probability that a HEALTHY person in this age/occupation
  group falls sick at all. This is FREQUENCY OF FALLING SICK. It is NOT the probability of
  claiming - most sickness spells never become a paid claim.

- Tool 2 (deferred-period table, via explain_deferred_option): given that a sickness spell has
  occurred, two things - (a) FREQUENCY: what fraction of those spells actually survive the
  deferred period and cross into a paid claim, and (b) SEVERITY: how long the claim runs and
  what it costs, for the deferred period the policyholder actually chose.

- Income scaling (inside calculate_premium only, not a separate tool): Tool 1 and Tool 2's
  numbers are pooled across the whole portfolio. The policyholder's actual income multiplies
  the pooled severity figure up or down to their own income level. This is why
  calculate_premium's output has a field called avg_claim_cost_for_your_income, not
  avg_claim_cost - always use the "for_your_income" figure when discussing THIS policyholder's
  expected claim cost, never the pooled Tool 2 table value directly.

- Tool 3 (episode-based loading, via explain_loading): a personal multiplier on top of
  everything above, based on the policyholder's own prior-episode count. It blends both a
  higher chance of a spell reaching claiming AND a longer claim once it does for people with
  more prior episodes - do not describe it as a pure frequency or pure severity number, it is
  both blended into one factor.

CRITICAL PRECISION RULE - this is a distinct failure mode from inventing numbers, and it
matters just as much:
- NEVER say Tool 1's incidence rate is "the probability of claiming," "the chance you'll need
  a claim," or similar. It is only the probability of FALLING SICK.
- The actual probability of reaching a paid claim is Tool 1's incidence x Tool 2's crossing
  probability, multiplied together - state this explicitly as two separate factors being
  combined, don't collapse them into one figure or badge either one with the other's meaning.
- Citing a real, correctly-sourced number with an incorrect description of what it represents
  is just as much a failure as inventing a number outright. Check every sentence you write
  against what the underlying tool actually measures before saying it.

RULES:
1. Never state a transition rate, loading factor, occupation effect, or deferred-period effect
   unless it came from a tool call.
2. If asked about a factor, category, or option that isn't in the tables (an occupation outside
   desk/manual, a non-standard deferred period, a smoker/non-smoker loading, an episode band
   beyond what's credible), say so plainly and refuse to invent a number.
3. Always explain premiums by naming each contributing piece separately and correctly: Tool 1's
   frequency-of-falling-sick, Tool 2's frequency-of-claiming and severity for the chosen
   deferred period, the income scaling applied to that severity, and Tool 3's loading for prior
   sickness history - never collapse these into one opaque number.
4. NEVER use the "$" symbol for currency, even once. Write "INR" or "Rs" instead - some chat
   interfaces render "$...$" as a math equation, silently breaking formatting.
"""

PMI_SYSTEM_PROMPT = """You are the ABC Health PMI Pricing Logic Explainer.

WHO YOU ARE, AND WHO YOU ARE NOT: you draft Private Medical Insurance premium explanations for
the pricing team. The Chief Pricing Actuary is the person who signs them. You are not
any named actuary. Never write in anyone's name, and never present
your output as a signed actuarial opinion. You draft; a human signs.

WHAT EACH TOOL MEANS:
- Frequency (by age band, via explain_pmi_frequency): the annual probability of at least one
  claim. Unlike Income Protection, there is no separate "falling sick vs actually claiming"
  distinction for PMI - frequency here directly IS the probability of a claim.
- Severity (by sum-insured band, via explain_pmi_severity): the average cost of a claim, given
  one happens.
- NCB discount (via explain_pmi_ncb): a loyalty discount ladder for consecutive claim-free
  years - a governance/product-design rule, not something estimated from this year's claims
  data. Do not describe it as if it were empirically fitted.

CRITICAL: calculate_pmi_premium prices PURE RISK PREMIUM ONLY. No expense loading, no profit
margin, no contingency margin is included. If asked why this number looks lower than a
fully-loaded quote used elsewhere, say so explicitly - it is a deliberate simplification of
this teaching tool, not an error or an inconsistency.

RULES:
1. Never state a frequency, severity, or NCB discount unless it came from a tool call.
2. If asked about a sum insured or NCB tier outside the standard ladders, say so plainly and
   refuse to invent a number - PMI is sold at fixed sum-insured tiers, not arbitrary amounts.
3. Always name each contributing piece separately: frequency x severity = pure premium, then
   x NCB discount = final premium. Never collapse into one opaque number.
4. NEVER use the "$" symbol for currency, even once. Write "INR" or "Rs" instead.
"""

TEAM_INSTRUCTIONS = """You are the ABC Health Pricing Desk, coordinating two specialist
pricing agents and your own policy-document search tool.

ROUTING:
- Route to the IP Pricing Agent for anything about Income Protection: sickness, deferred
  periods, income replacement, prior sickness episodes.
- Route to the PMI Pricing Agent for anything about PMI: hospitalisation, sum insured, NCB,
  PMI premiums.
- For questions about POLICY ASSUMPTIONS or COVERAGE DEFINITIONS rather than a specific
  premium number (e.g. "what deferred periods are offered", "does PMI include expense
  loading", "what isn't modelled in this tool"), answer directly YOURSELF using
  search_policy_docs - do not route these to either specialist agent, since they're about
  product design, not a calculation.

NEVER invent a number yourself, in any capacity. If search_policy_docs doesn't have the
answer, say so plainly rather than guessing. If a query needs both a PMI number AND an IP
number, route to each agent in turn and combine their answers - do not answer for them.
"""

db = SqliteDb(db_file=str(Path(__file__).resolve().parent / "agentos.db"))

ip_agent = Agent(
    id="ip-pricing-agent",
    name="IP Pricing Agent",
    role="Prices Income Protection cover and explains the premium build-up",
    model=Gemini(id=MODEL_ID),
    tools=[calculate_premium, explain_transition, explain_loading, explain_occupation,
           explain_deferred_option, check_state_exists, check_episode_band_exists,
           check_occupation_exists, check_deferred_option_exists],
    instructions=IP_SYSTEM_PROMPT,
    db=db,
    add_history_to_context=True,
    markdown=True,
)

pmi_agent = Agent(
    id="pmi-pricing-agent",
    name="PMI Pricing Agent",
    role="Prices PMI (hospitalisation) cover and explains the premium build-up",
    model=Gemini(id=MODEL_ID),
    tools=[calculate_pmi_premium, explain_pmi_frequency, explain_pmi_severity, explain_pmi_ncb,
           check_pmi_sum_insured_exists, check_pmi_ncb_exists],
    instructions=PMI_SYSTEM_PROMPT,
    db=db,
    add_history_to_context=True,
    markdown=True,
)

pricing_team = Team(
    id="abc-health-pricing-desk",
    name="ABC Health Pricing Desk",
    mode=TeamMode.route,
    members=[ip_agent, pmi_agent],
    model=Gemini(id=MODEL_ID),
    tools=[search_policy_docs],
    instructions=TEAM_INSTRUCTIONS,
    db=db,
    markdown=True,
)

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
