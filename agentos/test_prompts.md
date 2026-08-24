# Test Prompts — ABC Health Pricing Desk

One prompt per component, for testing the AgentOS demo (chat UI or REST API).
Each prompt is designed to exercise the component's tools end-to-end, and the
"What to look for" notes tell you how to judge the response.

## 1. IP Pricing Agent

> I'm 45 years old with a desk job, earning Rs 80,000 a month, and this is my
> 2nd sickness episode. My deferred period is 4 weeks instead of the usual 13.
> What's my annual premium, and how does each factor contribute to it?

**What to look for:**
- The agent calls `calculate_premium(age=45, monthly_income=80000, prior_episodes=2, occupation='desk', deferred_weeks=4)` — check the tool-call trace.
- The build-up is explained factor by factor: base incidence (frequency of *falling sick*, not of claiming), the 4-week deferred-period crossing probability and severity, income scaling, and the 2+ episode loading — never collapsed into one opaque number.
- The 4-week premium is noticeably higher than the 13-week equivalent (shorter waiting period → more spells reach a paid claim).
- All amounts in Rs / INR, never "$".

## 2. PMI Pricing Agent

> I'm 52, I want a sum insured of Rs 20,00,000, and I've earned a 40% no-claim
> bonus. What's my PMI premium? And while you're at it, what would it cost for
> a sum insured of Rs 12,00,000?

**What to look for:**
- The first part prices cleanly: frequency (51–65 age band) × severity (20L tier) = pure premium, then × the 40% NCB discount factor — each named separately.
- The second part is **refused**: Rs 12,00,000 is not one of the standard tiers (3L/5L/10L/20L/50L), so the guardrail rejects it and the agent says so instead of interpolating a number.
- The agent notes this is a *pure risk premium* (no expense or profit loading) if the number is questioned.

## 3. ABC Health Pricing Desk (Team)

> Three questions: (1) What deferred periods does the IP product offer, and
> does it pay anything if the policyholder dies? (2) What's the IP premium for
> a 30-year-old manual worker earning Rs 50,000 a month with no prior
> episodes, on the standard deferred period? (3) What's the PMI premium for
> that same person at age 30 with a 5 lakh sum insured and no NCB?

**What to look for:**
- Question 1 is answered by the **team itself** via `search_policy_docs`, with the source chunk cited — it should *not* be routed to a specialist (it's about product design, not a calculation).
- Question 2 is routed to the **IP Pricing Agent** (13-week default, manual occupation loading visible in the build-up).
- Question 3 is routed to the **PMI Pricing Agent** (18–35 band frequency × 5L severity, NCB factor 1.0).
- The team combines all three answers without inventing any number of its own.
