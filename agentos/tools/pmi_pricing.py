"""PMI — governed tools + guardrails (from notebook 05)."""

from config import pmi_frequency_table, pmi_ncb_table, pmi_severity_table

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
