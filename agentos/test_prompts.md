# Test Prompts — ABC Health Pricing Desk

One prompt per component, for testing the AgentOS demo (chat UI or REST API).
The prompts are written from the perspective of a **pricing actuary** using the
agents to interrogate the pricing basis — not a policyholder asking for a
quote. Each prompt exercises the component's tools end-to-end, and the
"What to look for" notes tell you how to judge the response.

## 1. IP Pricing Agent

> I'm reviewing a quote before sign-off: policy ABC-IP-204551, age 45, desk
> occupation, monthly income Rs 80,000, 2 prior sickness episodes, 4-week
> deferred period. Walk me through the premium derivation component by
> component — base incidence for the rating cell, the deferred-period
> frequency/severity split, the income scaling, and the credibility-weighted
> episode loading. Also confirm how the premium moves if this case were on the
> standard 13-week deferred period instead.

**What to look for:**
- The agent calls `calculate_premium(...)` for both the 4-week and 13-week variants — check the tool-call trace.
- Each component is named and sourced correctly: incidence quoted as frequency of *falling sick* (not of claiming), the crossing probability and severity attributed to the deferred-period table, the income scale factor stated explicitly, and the 2+ band loading reported with its credibility weight Z.
- The 4-week premium is materially higher than the 13-week one, and the agent attributes the difference to more spells crossing into paid claiming.
- All amounts in Rs / INR, never "$".

## 2. PMI Pricing Agent

> For the PMI basis review: give me the pure risk premium for the 51–65 age
> band at the 20L sum-insured tier with a 40% NCB, showing frequency, severity,
> and the discount factor separately with the data volumes behind each
> estimate. Also, a broker has asked us to quote a Rs 12,00,000 sum insured —
> what does the rating basis say about that?

**What to look for:**
- Frequency (51–65 band) × severity (20L tier) = pure premium, then × the 40% NCB factor — each stated separately, with the n_policies / n_claims behind the estimates (from the explain tools).
- The Rs 12,00,000 request is **refused**: it is not one of the standard tiers (3L/5L/10L/20L/50L), so the guardrail rejects it and the agent says the basis does not support it rather than interpolating.
- The agent flags that this is a *pure risk premium* — no expense, profit, or contingency loading — as a deliberate feature of the basis.

## 3. ABC Health Pricing Desk (Team)

> I'm preparing the peer-review pack. Three things: (1) From the product
> specification — what deferred-period options does the IP product actually
> offer, and what happens to the benefit on death of the policyholder?
> (2) From the IP basis — the premium build-up for a 30-year-old manual
> worker, Rs 50,000 monthly income, no prior episodes, standard deferred
> period. (3) From the PMI basis — the pure risk premium at age 30, 5 lakh
> sum insured, no NCB. Keep each answer attributable to its source.

**What to look for:**
- Item 1 is answered by the **team itself** via `search_policy_docs`, with the source chunk cited — it should *not* be routed to a specialist (it's a product-design question, not a calculation).
- Item 2 is routed to the **IP Pricing Agent** (13-week default applied, manual occupation loading visible in the build-up).
- Item 3 is routed to the **PMI Pricing Agent** (18–35 band frequency × 5L severity, NCB factor 1.0).
- The team combines all three answers without inventing any number of its own, and each figure remains traceable to the specialist or document that produced it.
