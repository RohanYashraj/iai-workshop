"""Income Protection — governed tools + guardrails (from notebooks 04/05)."""

from config import ip_base_table, ip_deferred_period_table, ip_loading_table, ip_population

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
