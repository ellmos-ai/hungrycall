![I am hungry](banner.png)

## Demo video

[![Watch the demo video](youtube-play-thumb.png)](https://youtu.be/5RIq7lpKv4w)

**Live demo (dry-run, no calls possible):** https://yr5xa7sodp76bt6uvivprlvz5i0wbfcd.lambda-url.eu-central-1.on.aws/

The public deployment runs with `DEMO_MODE=1` and without any `CALLE_*`
credential, so `LiveCallClient` refuses every live call before it even reaches
its own confirmation gate — including the E41 correction call, which goes
through the same seam. Restaurant lookup defaults to the app's own fixture
mode, so nothing leaves the sandbox. See [`infra/README.md`](infra/README.md).


# HungryCall 🍕📞

**English · [Deutsch](README_de.md)**

[![Ecosystem: ellmos-ai](https://img.shields.io/badge/ecosystem-ellmos--ai-blue.svg)](https://github.com/ellmos-ai)
[![Umbrella: open-bricks](https://img.shields.io/badge/umbrella-open--bricks-indigo.svg)](https://github.com/open-bricks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-407%20passed-brightgreen.svg)](tests/)
[![llms.txt](https://img.shields.io/badge/llms.txt-standardized-green.svg)](llms.txt)

> [!TIP]
> **LLM Context & AI Agent Integration**: See [`llms.txt`](llms.txt) for machine-readable architecture and documentation optimized for LLMs and AI coding assistants.

> **Hackathon Submission for CALL-E ("Your Code Is Calling")**
>
> Automated voice agent cascade for food delivery, table reservations, and pickup based on the **Generalized Calling Cascade Pattern** (`MUSTER.md`).

HungryCall solves a real-world problem in rural and suburban areas: local restaurants often lack integration with central delivery platforms (e.g. Lieferando/DoorDash). Finding out who delivers, table availability, or total cost requires calling restaurants one by one. HungryCall automates this via CALL-E by executing a **sequential calling cascade with immediate early exit upon success**.

---

## 💡 The Generalized Calling Cascade Pattern (Core Contribution)

While food ordering is our primary demonstration, **the true contribution to the developer community is the Generalized Calling Cascade Pattern (`MUSTER.md`)**.

```
User Intent & Boundaries  ──>  Rank Candidates  ──>  Sequential Calling Cascade with Judgment
                                                                │
                                            ┌───────────────────┴───────────────────┐
                                            ▼                                       ▼
                                     Gate Violated                             All Met
                               (e.g., Over budget / Vague quote)       (Place order / Reserve)
                                            │                                       │
                                     Polite exit, call                       Halt remaining
                                     next candidate                          calls immediately
```

### Why This Pattern Matters
In many everyday situations, a person needs a service from **one out of several candidate providers**, but cannot determine availability, cost, or terms without calling them sequentially. 

Examples beyond food delivery:
* **Dentist Appointments**: Finding an urgent appointment within 30 km, trying regular insurance first, stepping down to private fee concessions (up to €30) only if necessary.
* **Auto Repair / Mechanics**: Finding an open emergency slot for brake repair before the weekend.
* **Spare Parts & Hardware**: Locating a specific plumbing component in stock at local supply shops.
* **Care & Nursing Services**: Securing temporary respite care slots across local providers.

### The Four Types of Evaluation Criteria
Unlike simple dialing scripts, HungryCall evaluates four distinct condition tiers during every call turn:

| Criterion Type | Definition | Example in HungryCall | Example in Healthcare / Services |
|---|---|---|---|
| **Must (Pflicht)** | Non-negotiable prerequisite; without it, call fails | "Must deliver to address X" | "Must be within 30 km radius" |
| **Hard Boundary (Grenze)** | Absolute limit; agent politely declines if exceeded | "Doorstep end price ≤ €35.00" | "Maximum co-pay ≤ €50.00" |
| **Tiered Concession (Zugeständnis)** | Conditional flexibility; **played only when primary path fails** | "Accept 15 min longer ETA if price is lower" | "Pay private deposit only if regular slot full" |
| **Wish (Wunsch)** | Optimizes priority ranking beforehand; doesn't block | "Prefer wood-fired pizza" | "Prefer 4+ star rated practice" |

---

## 🧩 The Cascade Blueprint

The section above names the pattern; this one spells it out as five steps that any call-based inquiry-and-booking pipeline can reuse, independent of what is being ordered, reserved, or arranged:

1. **Build a ranked candidate list.** Turn the user's intent into search criteria (cuisine, radius, opening hours, a rating threshold — whatever the domain needs), find candidates, and rank them. Nothing is dialled yet.
2. **Call one candidate at a time, with a fixed shape:** hard gates first (non-negotiable prerequisites that end the call immediately if unmet), then negotiable conditions, then a set of criteria the agent checks turn by turn. Each criterion carries an explicit reaction — what happens on a yes, what happens on a no. A configured replacement *substitutes* a failed position; it never runs alongside a satisfied one, and only fires once the original genuinely failed.
3. **On failure, move on — with a reason.** A call that hits a hard gate or exhausts its concessions ends politely, and the cascade advances to the next candidate with the failure reason attached to the record, not silently.
4. **Stop the instant one candidate succeeds.** No further candidate is dialled once an order, reservation, or appointment is confirmed — calling the remaining candidates after that would waste money and risk a duplicate commitment for no reason.
5. **Every attempt is audited and kept as evidence**, successful or not: the structured result, the full transcript, and — where the domain supports it — a result card the user can save. An oral agreement over the phone has no paper trail of its own; this record is what stands in for one.

### A hard lesson from the live measurements: the audit protects the data, not the real world

Steps 3 and 5 describe what the cascade's own bookkeeping does: it validates a structured result and decides, from that result alone, whether a call counted as a success. Measuring against the live service made clear that this is not the same as protecting what actually happened on the other end of the line:

- A call can end ambiguously — the callee's words leave real doubt about whether something was agreed — and the cascade's audit correctly flags the result as unusable data, but the underlying decision (stop here, ask the user, or dial the next candidate anyway) still has to be made explicitly. Advancing automatically past an ambiguous outcome risks the exact duplicate commitment that step 4 exists to prevent.
- An agent can read a firm order or booking back to the callee, hang up without ever hearing an explicit yes, and have the cascade's audit correctly reject the missing confirmation as bad data — while the person on the other end of the phone still believes the call ended in an agreement, because nobody told them otherwise before the line closed.

The general rule this leaves for anyone building on this pattern: **a retraction or a cancellation belongs in the conversation itself, spoken before the call ends — not only in the audit that runs afterwards.** A structured-result check can refuse to *record* a bad outcome; only the agent's own words during the call can undo it in the other person's mind. The same goes for any consequence the caller needs to hear about in the moment — an audit step alone is never a substitute for saying it out loud.

### Reuse beyond this repository

Nothing about the five steps above is specific to food, restaurants, or even to CALL-E. The gate/condition/criterion shape, the ranked-candidate search, and the stop-on-success rule apply equally to a dentist-appointment search, a repair-shop capacity check, or a spare-parts stock inquiry (see [`MUSTER.md`](MUSTER.md) for the pattern's origin story and worked non-food examples). The engine implementation in this repository is deliberately kept close to the food-ordering domain for this submission; a purpose-neutral extraction of the cascade engine itself — usable for any candidate-and-criteria phone search, independent of any single use case — is a planned next step, kept out of this repository for now.

---

## ❓ Why Not Just Use the CALL-E App?

The official CALL-E chat / app is designed to solve **a single phone call to a single pre-known target for a single goal**.

HungryCall addresses an entirely different class of problem — **a multi-candidate autonomous search & negotiation process**:

1. **Multi-Candidate Search & Pre-Filtering**: HungryCall automatically geocodes locations, checks opening hours, and ranks candidate providers *before* picking up the phone.
2. **Serial Execution & Cost Minimization**: Calling all providers simultaneously creates duplicate orders and wastes API credits. HungryCall executes sequentially and **halts all remaining calls the microsecond a candidate succeeds**.
3. **Financial Authority Limits**: Extending CALL-E's `goal.commitment` design from time windows to monetary amounts (`max_budget_eur`), preventing unexpected doorstep charges.
4. **Strict Quote Validation**: Rejects vague price quotes (`price_known: false`, e.g. *"about 30 Euros depending on driver"*) to eliminate guesswork.
5. **Tiered Concessions**: Manages negotiation steps over the call duration, withholding concessions until necessary.
6. **Oral Contract Evidence**: Captures full timestamped transcript logs (`[mm:ss] BOT: ...`) as binding verification proof alongside masked callback numbers.

---

## Key Features

1. **Three Operating Modes**:
   - `delivery`: Verifies delivery address, exact doorstep total price (food + delivery fee + minimum order), estimated ETA, and places the order.
   - `reservation`: Checks table availability for date, time, and party size; confirms reservation under caller's name; provides direct callback number for cancellation.
   - `pickup`: Verifies pickup order capability, exact total price, prep time, and places pickup order.

2. **Smart Priority Ranking**:
   - Current food craving **always beats** a favorite restaurant if the favorite does not serve the requested cuisine (e.g. a craving for "Burger" ranks a local burger joint higher than a favorite Italian pizzeria).
   - Opening hours pre-filter closed restaurants before making any call attempt.

3. **Maximum Total Budget Limit (Höchstbetrag — Crucial Guardrail)**:
   - **Doorstep End Price**: The budget limit applies to the final total amount at the doorstep (including delivery fees, service surcharges, and minimum order values).
   - **Vague Price Rejection**: If a restaurant gives a vague or unconfirmed price quote (`price_known: false`, e.g., "about 30 Euros depending on the driver"), the agent politely declines and moves to the next candidate. Guessing prices is strictly forbidden.
   - **No Return After Commitment**: Once an order is confirmed, it is binding. HungryCall always outputs the restaurant's direct callback number for caller modifications.

4. **Order Wish Chains**:
   - An order is modeled as `position -> replacement cell -> criterion`, not as an unstructured wish list.
   - Each cell carries quantity, product, food/drink type and any number of maximum-price, special-request or yes/no criteria. A failed criterion either accepts, advances to the next replacement, or rejects the position; the position rule then skips it or aborts the whole order.
   - The same JSON definition renders the editor, generates the call instruction and evaluates `order_chain_results`. The result screen groups the selected products by free-form tags.
   - Complete chains can be saved as templates. Every submitted order remains loadable, editable and reusable from history.

5. **Structured Schema Work**:
   - Uses strict CALL-E `result_schema` definitions per mode (`delivers_to_address`, `price_known`, `total_price_eur`, `eta_minutes`, `order_placed`, `callback_number`, `rejection_reason`).

6. **Dynamic Fixture Input Reflection**:
   - In dry-run mode, actual user parameters (`delivery_address`, `food_prompt`, `customer_name`, `max_budget_eur`) are dynamically interpolated into verification transcripts, activity logs, and summaries to ensure dry-run output matches input exactness.

7. **Human Confirmation Contact**:
   - The web form collects first name, last name and a required E.164 requester callback number. The number is carried only in transient request state, is included in each live call goal for restaurant questions or human confirmation, and is repeated at the end of that goal. It is not written to orders, saved results, history exports or fixture transcripts.

8. **Closing Routine with Binding Confirmation**:
   - Every call that places an order or reservation ends with a mandatory closing routine: read back the complete order or booking, state clearly that it is hereby placed, and obtain the other side's confirmation. A condition that surfaces only after that summary — a fee, a changed price, a changed time — is re-checked against the caller's authority; if it exceeds it, the agent retracts aloud instead of leaving the restaurant believing something stands that was never actually authorised.

9. **Call Language, Independent of the Interface Language**:
   - `HUNGRYCALL_CALL_LOCALE` (`de` by default, `en` optional) selects the language CALL-E is asked to conduct the phone call in, and with it the language of every verbatim-quoted sentence in the goal text (`hungrycall/call_language.py`). This is separate from the web interface's own German/English switch below, which only affects what the browser shows.

10. **Order Receipt via Call Attempts**:
    - Every dialled attempt — accepted or rejected — is stored with its provider run id, status, rejection reason and masked transcript as soon as the cascade evaluates it, not only the final outcome. `GET /api/order-attempts?order_id=...` serves the list under the same session rule as the live event stream.

11. **Correction-Call Queue for Ambiguous Failures**:
    - Every failed attempt shown in history's "Rejected/failed orders" section is classified by severity from its own stored status and rejection reason: a clean, explicit decline is low severity, but a call that expired mid-conversation or was only rejected by this app's own post-hoc validation is critical — the restaurant may still believe an order was agreed, even though HungryCall discarded it (the field-trial case behind this feature: a restaurant believed an order stood while the app had already thrown it away).
    - Moderate and critical attempts that have not already been corrected get a manual **Trigger correction call** button — nothing dials automatically. The correction call reaches the same restaurant, states up front (before anything else) that it is a follow-up to an earlier call on the requester's behalf, explicitly declares it is *not* a new order or reservation, and asks only whether anything still stands — cancelling it on the spot if so. Its goal text never reads `food_prompt`, `delivery_address`, price, or order-chain data, only the mode and the requester's own name.
    - Correction calls get their own idempotency key (a `"correction-{mode}"` prefix that never reuses the original attempt's key) and are linked back to the attempt they correct via `corrects_attempt_id`, so a corrected attempt is visibly marked in history and cannot itself be corrected a second time.

**[`CONVERSATION-TREE.md`](CONVERSATION-TREE.md)** documents every branch the goal text above can
take, node by node, tagged with the exact builder function that produces it — plus a settings
coverage table answering, for every configurable field, whether it actually reaches the prompt.

---

## Real CALL-E Service Dynamics (Measured Findings)

HungryCall incorporates empirical findings measured against the live CALL-E service (`FINDINGS.md`):

1. **`status` vs. `activity` Progress Tracking**:
   - `status` remains on `PREPARING` throughout active conversation and only updates to `COMPLETED` when the call ends.
   - HungryCall relies exclusively on `activity` events to monitor real-time progress and display active conversation turns.

2. **Live Speech & STT Deduplication**:
   - `activity` emits real-time events (`Bot is speaking: ...` and `Callee said: ...`).
   - The STT engine streams an initial raw draft followed immediately by a refined/corrected version. HungryCall automatically deduplicates streaming STT drafts.

3. **Transcript as Order Proof**:
   - Transcripts reside in `result.transcript` as a single formatted string (`[mm:ss] BOT: ...` / `[mm:ss] USER: ...`). Because phone orders form an oral contract, HungryCall displays the full formatted transcript as verification proof.

4. **Call Setup Overhead**:
   - Each call incurs a ~40-second setup latency (bot initialization + ringing + connection) prior to conversation start. HungryCall displays this latency notice in the live activity stream.

5. **REST API vs. MCP Architecture**:
   - Schema-validated call results (`result_schema`) are supported **only via the REST API** (`POST /v1/calls`, Header `Authorization: Bearer $CALLE_API_KEY`). MCP (`plan_call`) does not support result schemas and operates in a separate ID space.
   - API keys are loaded from `CALLE_API_KEY` / `IAM_API_KEY`, or from an external `.env` file. Environment variables win. Values are never hardcoded, logged, documented, or committed.

6. **Serial Execution Safety**:
   - Concurrency limits remain unverified; HungryCall strictly uses serial cascade ordering (stopping immediately on first success) to avoid duplicate food orders or extra call costs.

7. **Poll Resilience and Create-Retry**:
   - A single transient network or 5xx failure no longer aborts a running cascade: status polling tolerates up to 3 consecutive failures before giving up. A `POST /v1/calls` that times out on the client side is retried up to 3 times with the SAME `Idempotency-Key`, so a retry re-attaches to a call the provider may already have placed ("ghost call") instead of dialling a second time. Full write-up: `FINDINGS.md` §9.

8. **Payload Diagnostics (Opt-In)**:
   - Setting `HUNGRYCALL_DEBUG_PAYLOAD_DIR` writes the masked terminal API payload of each live call to that local directory — used to diagnose exactly what the API returned when a live result looked wrong. Off by default; local files only, phone numbers masked before they are written.

---

## How We Tested

HungryCall was tested against the real CALL-E service in two live sessions, both routed exclusively through one explicitly consenting test phone line (`HUNGRYCALL_FIELD_TRIAL_PHONE`, `field_trial.py`) — every dialled number was rewritten to that line before a call ever went out, regardless of what number the candidate data carried. The author played every counterpart role (restaurant staff, reservation desk) in real time, unscripted beyond knowing which scenario was under test. No restaurant outside that one line was ever dialled.

**2026-08-11 — first live calls.** The first-ever live `POST /v1/calls` traffic against the real API, run against deterministic fixture restaurant data (the day's public restaurant search was rate-limited). Four cascades produced local, gitignored diagnostic receipts: a delivery chain that substituted an unavailable item, a pickup call that rejected a vague price until an exact one was given, a reservation whose new fee was rejected by the app's independent authority audit, and one complete delivery cascade. The public `EVIDENCE.md` §16 intentionally contains only aggregate findings and clearly labelled synthetic reproductions—not raw transcripts, call/order IDs, personal names, exact timestamps or phone-number fragments.

**2026-08-22 — full walkthrough, then a same-day retest.** All three call modes were run live end to end in one session, each as its own cascade across multiple restaurants until one succeeded: three calls for the delivery chain (two rejected on price, the third completed the order), four calls for pickup (one over the single-item price limit, one with an ambiguous outcome, one not reached, the fourth completed the order), and two calls for the reservation (the first rejected on time, the second completed it). Fixes for what had gone wrong were written the same day and re-verified with fresh live calls before the session ended — a retest cascade re-ran the delivery-chain scenario (2 calls) and the reservation fee-pushback scenario (1 call); when that retest surfaced a new variant of a problem thought already fixed, a further fix landed and was itself re-checked with two more live calls, the same day.

**What went wrong, and what became of it:**

1. **A mandate breach at the phone level.** A criterion that had actually failed (both prices over the configured limit) still got spoken out loud as a binding order — the app's own audit correctly discarded the result afterwards, but the restaurant would have delivered the food regardless. The same class of problem had already surfaced once, in a reservation's booking fee, on the first test day, and was fixed there specifically — that fix did not generalize to order-chain criteria, which is where it resurfaced. Fixed properly this time: every criterion's consequence now has to be applied *out loud, in the moment*, in every call mode, not just recorded for later.
2. **A self-correction that made things worse.** An earlier fix had the voice agent calculate the order total itself from the unit prices it had gathered; live, that arithmetic was itself wrong and triggered an unnecessary budget abort on an order that was well within limits. Reverted by design decision: the agent now asks the restaurant to state the total and only plausibility-checks a wildly implausible figure — the arithmetic is left to the human running the call, not the voice agent.
3. **A missing confirmation window.** A call ended, or the agent said an order was placed "bindingly", without the other side ever having given an actual, explicit yes. Fixed: the closing routine now has to hear that yes before anything counts as placed, and has to say so out loud — a cancellation, not silence — if that yes never comes.
4. **Order-before-price sequencing.** The agent asked a restaurant for a total price before it had ever spoken the order itself out loud — something a restaurant cannot compute from unit prices alone. Found three times in the first full walkthrough, weakened again by a later same-day fix written for an unrelated problem, and found live a second time in that same day's retest even though the instruction to speak the order first already stood in the right place in the text. Hardened into an explicit, critical ordering rule rather than one instruction among several.
5. **A first-call-in-a-cascade FAILED pattern.** Three cascades in a row, across both test sessions, misclassified the whole call's first attempt as "not reached" — once discarding a complete, gracefully-declined conversation this way. Still open; the retrievable transcript evidence points at the platform's own structured-result reporting for that specific case, not at this repository's own logic.
6. **A redaction gap.** A callback number read aloud as digit words once bypassed the generic number masker. Fixed: the purpose-bound requester callback is now redacted recursively in numeric, formatted and known digit-word form before any result, receipt or diagnostic payload can retain it.

The working pattern across both days was the same: **find it live, fix it locally, re-run the exact scenario that broke, and only then call it done** — the same discipline `AUFGABEN.txt` and `FINDINGS.md` track for every entry in this repository's history, not a one-off for the submission deadline.

---

## Data Flow & Privacy Disclosure

> ⚠️ **DATA TRANSFER NOTICE**:
> The CALL-E voice agent engine operates via AiRudder infrastructure located in **Singapore** (`https://seleven-mcp-sg.airudder.com`).
> 
> When a live call is placed, prompt parameters (customer name, requester callback number, delivery address or reservation details, and the request) are transmitted to the configured CALL-E endpoint and spoken to the selected restaurant as needed. HungryCall follows strict **data minimization**:
> - Only the minimum information required for the single call is transmitted.
> - No user history or persistent profile data is shared.
> - The requester callback number is E.164-validated and transient; HungryCall does not write it to SQLite, saved history, receipts or fixture output.
> - Phone numbers are masked in all local outputs, logs, and summaries (`+49 ••• ••••123`).

---

## Safety & Compliance Standards

HungryCall adheres strictly to the CALL-E repository safety guidelines:

- **Call Dry-Run by Default**: Unless `--live` and `--confirm-live` are explicitly supplied, the call cascade uses local fixtures and needs no CALL-E account. Restaurant discovery is a separate boundary: normal web searches use OpenStreetMap, while an explicit, clearly labelled restaurant test mode is fully local.
- **Field-Trial Mode**: `HUNGRYCALL_FIELD_TRIAL_PHONE` reroutes every live candidate's phone number to one explicitly consenting test number before a cascade starts; restaurant names and ranking stay real, only the dialled wire is redirected. Fail-closed: a set-but-invalid number refuses the live run instead of silently falling back to real numbers. Only under this override may a restaurant sourced from the fixture/test-mode scenarios go out on a live wire — never with a real restaurant's own number.
- **Explicit User Intent**: Calls are only initiated upon direct user action.
- **E.164 Validation**: All target phone numbers are validated against standard E.164 format (`+441632960090`) prior to dialing.
- **Phone Number Masking**: All phone numbers in console logs, JSON reports, and summaries are masked (e.g. `+49 ••• ••••123`).
- **Public German Example Numbers**: Every German diallable-looking number committed as fixture or documentation data comes from the permanently unassigned “Drama Numbers” in Bundesnetzagentur Mitteilung 148/2021.
- **No Hardcoded Credentials**: API tokens or secrets are never committed to code or logs. HungryCall reads the process environment or a machine-local `.env` file outside the repository.
- **No Hidden Recurring Background Schedules**: HungryCall operates as a single execution CLI. No background daemons or infinite loops exist.
- **Idempotency Safeguards**: Every call generates a unique idempotency key (`hungrycall-<mode>-<restaurant_id>-<hash>`) to prevent duplicate accidental calls.
- **Domain Guardrails**: Prompts containing medical, legal, financial, or emergency terms are automatically rejected prior to call planning.
- **Graceful Interruption**: Pressing `Ctrl+C` cleanly aborts execution while preserving execution state.

---

## Alignment with CALL-E Design

In the official CALL-E repository, `apps/typescript/call-on-behalf` constrains agent authority using time windows (`goal.commitment`). HungryCall extends this architectural principle from **time windows to monetary amounts** (`max_budget_eur`). The agent operates within strict budget authority delegating decision power safely without risking unexpected charges.

---

## Web Interface (FastAPI + HTMX + SQLite + Leaflet)

Zero build step, no bundler, no CDN. Two branches start from the landing page,
and both end in the same cascade engine on different criteria.

### Appearance: light first, dark on request

The default theme is deliberately bright and energetic: white surfaces, cobalt
blue routes, violet structure and pink refusal/action marks. Grass-neon green is
reserved for a genuinely live connection or a successful candidate; it is never
used as a large fill. The header's **Light / Dark** control switches to the retained
dark scheme and stores only that preference in `localStorage`. With no saved choice,
every page starts light. This electric route-map identity is intentionally distinct
from ResearchCall's quiet paper-like surface.

### The two branches

| | **Order food** (`/order`) | **Book a table** (`/reserve`) |
|---|---|---|
| Decides on | price, delivery, time | clock, party size, seating and permitted fallback bounds |
| Hard gate | the doorstep total | a free table at that hour |
| Switchable | delivery ⇄ pickup | indoor / outdoor / either / custom table request |
| Concessions | — | earlier/later time and booking-fee limits, authorised by you |

The switch between **delivery and pickup is not cosmetic**. It changes the
ranking (distance is weighted 12× higher when you are the one driving), it
changes the gate (the budget is the doorstep total with delivery, the plain
price without), it changes the shortlist (a pub that does not deliver is still
a fine place to collect from), and it changes the goal text handed to the
agent. `hungrycall/ranking.py` holds the weights; `tests/test_ranking.py`
pins the behaviour.

### Concessions: authority, not a hint

The table branch implements the third kind of criterion from
[`MUSTER.md`](MUSTER.md) — *something you are willing to give, but not yet*:

* You select a named seating preference or enter your own table request and an
  additional note for the restaurant.
* You grant concrete fallback bounds: up to three hours plus additional minutes
  earlier and/or later, and an explicit maximum booking fee.
* The agent must try the requested time without a fee first, then move through
  those bounds in order. The structured result reports the steps actually used.
* **A result outside the granted time window or fee cap is rejected**, exactly
  the way an over-budget quote is. See
  `CascadeEngine.check_reservation_authority`.

### What the screen does

1. **Landing** — two tiles; hovering (or tabbing to) one reveals what that
   branch actually does. A CSS/SVG animation walks a call down four numbers:
   two declines, one connection, and the fourth never dialled.
2. **Location and criteria** — the branch's own questions, split name fields,
   required callback number and visible authority limits. The food editor starts
   with one usable item row; its Add control appends and focuses another row.
3. **Candidates** — ranked, with distance, and reorderable. **The visible order
   is the call order**: the arrows write a hidden `candidate_order` field and
   the server calls exactly that sequence.
4. **Goal text** — the complete text that will leave the building, produced by
   the same `build_call_goal()` used for the real call, fetched from
   `/api/preview-goal`. Not a copy maintained in JavaScript.
5. **Cascade** — server-sent events carrying *data*, not markup: `dialing`,
   `connected`, `activity`, `rejected`, `accepted`, `outcome`. The conversation
   streams into a live log; each decline shows its reason on the candidate.
6. **Result** — the sentence in your language, the binding commitment, the
   restaurant's masked callback number, the transcript, and which authority
   step (if any) was spent.

### German and English

Both complete. The interface uses the author's existing `TranslationSystem`
(vendored unchanged in `hungrycall/translator.py`) with
`hungrycall/locales/translations.json`. Language comes from an explicit choice,
then a cookie, then `Accept-Language`, then German.
`tests/test_i18n.py` fails the build if a key used in the code has no entry, if
either language has a gap, or if a `{placeholder}` is lost in translation.

### Honest about what it cannot do

The interface states these where you are working, rather than hiding them:

* **Real calls are gated.** The REST transport exists, but the safe local path is
  the default. Web users must opt into Live and tick a second confirmation; CLI
  users need `--live`, `--confirm-live` and a requester callback number. The UI
  states **“Real calls — cost money”**. This change was verified without placing
  a real call; service readiness and account balance remain external facts.
* **Restaurant sources are explicit.** Normal mode geocodes through Nominatim and
  searches OpenStreetMap via Overpass. The candidate page names that source and
  reports the number of results within the selected radius. An unavailable service,
  an unresolved address, and zero usable results are separate visible errors; none
  of them substitutes example restaurants.
* **Restaurant examples require a separate test mode.** The page banner starts
  with test mode off and provides explicit **Enable test mode** and **Leave test
  mode** actions; it is the only visible test label. The fixture-scenario selector
  appears only while Test mode is active, and the Live control is then absent.
  The result panel says **“Test mode — example data, no real restaurants”** and
  performs no restaurant-network request. Set `HUNGRYCALL_RESTAURANT_TEST_MODE=off` to remove the switch for the
  whole installation and ignore any previously stored browser choice; set it to
  `on` to expose the switch explicitly. If unset, it remains available for the
  evaluation build.
* **Map tiles come from OpenStreetMap.** Without a connection the map stays grey
  and a normal restaurant search reports the network failure; explicit test mode
  remains available. No fonts, scripts or styles are fetched from anywhere.

* **No field trial with real restaurants has taken place.** A supervised field trial
  did take place on 2026-08-11, but under `HUNGRYCALL_FIELD_TRIAL_PHONE`: every
  candidate's dialled number was replaced with one consenting test line, never with a
  real restaurant's own number. Findings from those calls are in `FINDINGS.md` §9 and
  the hardening they led to is listed under Key Features and Real CALL-E Service
  Dynamics above.

### Launching the Web UI
```bash
python run_web.py          # or: hungrycall-web
```
Then open `http://127.0.0.1:8000`.

---

## Setup & Installation

### Requirements
- Python 3.11+
- `pytest` (for test suite)

### Installation
```bash
# Clone the repository
git clone https://github.com/ellmos-ai/hungrycall.git
cd hungrycall

# Install in editable mode
pip install -e .
```

### CALL-E credentials (optional; live mode only)

Dry-run needs no account and reads no credential. For a live-capable setup, use
`CALLE_API_KEY` (or `IAM_API_KEY`) and optionally `CALLE_BASE_URL`. HungryCall can
also read an external file selected with `CALLE_ENV_FILE` / `--env-file`. On this
operator machine the existing file is:

```text
C:\_Local_DEV\CREDENTIALS\call-e\call-e.env
```

Only this path may be named. Never copy the value into the repository, command
history, documentation, screenshots, reports, or commits.

---

## Usage

### 0. 30-Second Core Jury Demo (No Account Required)
```bash
hungrycall demo
```
*Executes the complete core cascade in 30 seconds: Candidate 1 rejected (over budget), Candidate 2 rejected (vague quote), Candidate 3 succeeds, early exit halts Candidate 4, and prints formatted order proof transcript.*

### 1. Delivery Mode (Dry-Run Scenario with Custom Address & Prompt)
```bash
hungrycall delivery --food "2x Döner Kebab" --address "Dorfstrasse 1, 12345 Dorfstadt" --budget 30.0 --scenario success_direct
```

### 2. Table Reservation Mode
```bash
hungrycall reservation --food "Italian" --date "2026-08-05" --time "19:00" --party 4 --scenario reservation_cascade
```

### 2a. A specific table — and bounded fallbacks
```bash
hungrycall reservation --food "Italian" --date "2026-08-07" --time "19:00" --party 4 \
  --seating custom --seating-custom "our usual table under the palm" \
  --earlier-hours 1 --earlier-minutes 30 --later-hours 2 --later-minutes 15 \
  --max-booking-fee-eur 3 --note "birthday dinner" --scenario reservation_cascade
```

### 3. Pickup Mode
```bash
hungrycall pickup --food "Pizza" --budget 25.0 --scenario pickup_cascade
```

### 4. Simulating Budget Exceeded Rejection
```bash
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario budget_exceeded_cascade
```

### 5. Simulating Vague Price Rejection
```bash
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario vague_price_cascade
```

### 6. Read-only credential preflight (no phone call)

```bash
hungrycall preflight
```

This sends one authenticated `GET /v1/calls/probe-does-not-exist`. It has no phone
number input and never sends `POST /v1/calls`; an authenticated `404` is the expected
success result. A real cascade additionally requires both live gates:

```bash
# WARNING: real calls cost money. This is syntax documentation, not an instruction to call.
hungrycall delivery ... --requester-callback-number +441632960090 --live --confirm-live
```

---

## Running Tests

The product tests use fixtures and mocked transports; no test places a real call:

```bash
pytest -v
```

They cover ranking and its per-mode distance weighting, opening hours across
midnight, the schemas, phone masking, the safety gates, budget and vague-price
rejection, reservation time/fee authority in both directions, both branches end to end
over the event stream, the candidate order the user arranged, the goal preview,
cancellation, saving with the mode that actually happened, HTML escaping of
free-text input, the light/dark theme, external credential loading, read-only
preflight semantics, live REST payload/polling behavior, and the completeness of
both languages.

---

## License

MIT License.
