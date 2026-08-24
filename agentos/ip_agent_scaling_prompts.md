# IP Pricing Agent — Scaling Demo: 1 → 5 → 10 → 200 Policies

The Friday-evening scenario: the Chief Pricing Actuary has forwarded **200
Income Protection cases**, starting with **ABC-IP-118420**. The distributor
and Underwriting want to know why each one is priced the way it is, every
explanation must reconcile to the premium actually charged, every one must be
signable, and **Board is Monday**.

These four prompts walk the participants up the scale. Run them in order
against the **IP Pricing Agent** — the point of the arc is that the same
governed tools answer one case and two hundred, and the guardrails refuse at
every scale.

Each scenario's case data is also provided as a CSV in [`scenarios/`](scenarios/):

| Scenario | File | Cases |
|---|---|---|
| 1 policy | [`scenarios/scenario_1_policy.csv`](scenarios/scenario_1_policy.csv) | ABC-IP-118420 |
| 5 policies | [`scenarios/scenario_5_policies.csv`](scenarios/scenario_5_policies.csv) | 118421–118425 |
| 10 policies | [`scenarios/scenario_10_policies.csv`](scenarios/scenario_10_policies.csv) | 118426–118435 (3 will be referred) |
| 200 policies | [`scenarios/scenario_200_policies.csv`](scenarios/scenario_200_policies.csv) | 118420–118619: the full book — the 16 cases above as its first rows, then 184 more (183 clean, 9 unmodelled occupations, 8 non-standard deferred periods) |

The 200-case file is what Scenario 4's industrialised loop consumes: one
`POST /agents/ip-pricing-agent/runs` per row, with the guardrails referring
the 17 unpriceable cases automatically.

**Attachments:** instead of pasting the tables from Scenarios 2 and 3 into the
chat, you can attach the corresponding CSV directly (paperclip button in the
os.agno.com UI, or `-F "files=@..."` on the API) and simply ask *"Price each
case in the attached file."* The IP agent knows the schema and returns a
PRICED table plus a REFERRED list with each guardrail's reason.

---

## Scenario 1 — One policy (the case the Chief forwarded first)

> The Chief Pricing Actuary has forwarded policy ABC-IP-118420 — the
> distributor is questioning the price. Profile: age 45, desk occupation,
> monthly income Rs 80,000, 2 prior sickness episodes, 4-week deferred period.
> Draft a plain-English explanation of why this policy is priced the way it
> is, reconciling exactly to the premium charged, component by component. It
> goes to the Chief for signature, so keep it precise about what each number
> does and does not measure.

**What this illustrates:** the core loop — every figure comes from a tool
call, the build-up reconciles multiplicatively to the final premium, and the
agent drafts for a human signatory rather than signing itself.

---

## Scenario 2 — Five policies (the first batch)

> The next five cases from the distributor's list. For each, give me the final
> annual premium and a two-line plain-English rationale naming the dominant
> rating drivers:
>
> | Policy | Age | Occupation | Monthly income | Prior episodes | Deferred |
> |---|---|---|---|---|---|
> | ABC-IP-118421 | 29 | desk | Rs 55,000 | 0 | 13 weeks |
> | ABC-IP-118422 | 52 | manual | Rs 65,000 | 1 | 13 weeks |
> | ABC-IP-118423 | 38 | desk | Rs 120,000 | 0 | 26 weeks |
> | ABC-IP-118424 | 45 | manual | Rs 40,000 | 2 | 4 weeks |
> | ABC-IP-118425 | 58 | desk | Rs 90,000 | 0 | 52 weeks |
>
> Then rank the five by premium and tell me, in one paragraph, which single
> rating factor drives the most spread across this batch.

**What this illustrates:** the agent iterates the same governed tool over a
batch — five `calculate_premium` calls in one conversation — and can then
reason *across* the results (ranking, attribution of spread) without inventing
any number.

---

## Scenario 3 — Ten policies (including the ones that should fail)

> Next ten cases. Same drill — premium plus a one-line rationale each — but
> this batch came straight from the distributor's spreadsheet, so validate
> each case against the rating basis before pricing it, and give me a clean
> two-part output: PRICED cases, then REFERRED cases with the exact reason
> each one cannot be priced on the current basis.
>
> | Policy | Age | Occupation | Monthly income | Prior episodes | Deferred |
> |---|---|---|---|---|---|
> | ABC-IP-118426 | 33 | desk | Rs 70,000 | 0 | 13 weeks |
> | ABC-IP-118427 | 47 | manual | Rs 85,000 | 1 | 26 weeks |
> | ABC-IP-118428 | 51 | airline pilot | Rs 250,000 | 0 | 13 weeks |
> | ABC-IP-118429 | 26 | desk | Rs 45,000 | 0 | 4 weeks |
> | ABC-IP-118430 | 44 | manual | Rs 60,000 | 3 | 13 weeks |
> | ABC-IP-118431 | 39 | desk | Rs 95,000 | 1 | 8 weeks |
> | ABC-IP-118432 | 55 | manual | Rs 50,000 | 2 | 52 weeks |
> | ABC-IP-118433 | 31 | desk | Rs 110,000 | 0 | 13 weeks |
> | ABC-IP-118434 | 49 | nurse | Rs 75,000 | 1 | 13 weeks |
> | ABC-IP-118435 | 42 | desk | Rs 80,000 | 2 | 26 weeks |
>
> For the referred cases, state what Underwriting would need to decide before
> we could quote.

**What this illustrates:** guardrails at scale. "Airline pilot" and "nurse"
are not modelled occupation classes, and 8 weeks is not a standard deferred
option — the agent must price seven cases and **refuse** the three bad ones
with the guardrail's reason, not a guess. (Case 118430 with 3 prior episodes
still prices: the basis caps episode history at the 2+ band.) The refusal
comes from Python checks inside the tools, so it happens on case 3 exactly as
it would on case 173.

---

## Scenario 4 — The full 200-case book (industrialising the answer)

> The full file is 200 cases and Board is Monday, so pasting them into a chat
> one batch at a time is not the process. Help me industrialise this instead:
>
> 1. Define the exact input fields you need per case, and the validation you
>    will apply to each (valid occupations, deferred options, episode bands),
>    so I can pre-screen the spreadsheet.
> 2. Produce the standard explanation template you would emit per policy —
>    with every figure slot naming the tool it comes from — so all 200
>    explanations are structurally identical and each reconciles to the
>    premium charged.
> 3. Estimate, from the validation rules, which kinds of cases in a typical
>    distributor file will end up REFERRED rather than priced, and draft the
>    one-paragraph covering note to the Chief Pricing Actuary describing the
>    process and its controls, so the whole pack is signable.
>
> Then demonstrate the template once, on ABC-IP-118420 (age 45, desk,
> Rs 80,000, 2 prior episodes, 4-week deferred).

**What this illustrates:** the jump from chat to system. The same agent and
tools run behind the AgentOS REST API, so the 200-case run is a loop over
`POST /agents/ip-pricing-agent/runs` — one request per case, identical
template out, guardrails referring the unpriceable cases automatically. The
chat prompt produces the *design* (inputs, validations, template, covering
note) and proves it on the known case; the API does the volume. That is the
difference between a chatbot and a governed pricing tool: the 200th
explanation is as auditable as the 1st, and the Chief signs a process, not
200 improvisations.
