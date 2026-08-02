![HungryCall](banner.png)

# HungryCall 🍕📞

**English · [Deutsch](README_de.md)**

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

4. **Structured Schema Work**:
   - Uses strict CALL-E `result_schema` definitions per mode (`delivers_to_address`, `price_known`, `total_price_eur`, `eta_minutes`, `order_placed`, `callback_number`, `rejection_reason`).

5. **Dynamic Fixture Input Reflection**:
   - In dry-run mode, actual user parameters (`delivery_address`, `food_prompt`, `customer_name`, `max_budget_eur`) are dynamically interpolated into verification transcripts, activity logs, and summaries to ensure dry-run output matches input exactness.

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
   - API keys must be loaded strictly from environment variables (`CALLE_API_KEY` or `IAM_API_KEY`), never hardcoded in code, logs, or commits.

6. **Serial Execution Safety**:
   - Concurrency limits remain unverified; HungryCall strictly uses serial cascade ordering (stopping immediately on first success) to avoid duplicate food orders or extra call costs.

---

## Data Flow & Privacy Disclosure

> ⚠️ **DATA TRANSFER NOTICE**:
> The CALL-E voice agent engine operates via AiRudder infrastructure located in **Singapore** (`https://seleven-mcp-sg.airudder.com`).
> 
> When a call is placed, prompt parameters (customer name, delivery address, food request) are transmitted to the Singapore endpoint. HungryCall follows strict **data minimization**:
> - Only the minimum information required for the single call is transmitted.
> - No user history or persistent profile data is shared.
> - Phone numbers are masked in all local outputs, logs, and summaries (`+49 ••• ••••123`).

---

## Safety & Compliance Standards

HungryCall adheres strictly to the CALL-E repository safety guidelines:

- **Dry-Run by Default**: Unless `--live` and `--confirm-live` flags are explicitly supplied, HungryCall runs 100% locally against dry-run fixtures. No CALL-E account or network access is required.
- **Explicit User Intent**: Calls are only initiated upon direct user action.
- **E.164 Validation**: All target phone numbers are validated against standard E.164 format (`+441632960090`) prior to dialing.
- **Phone Number Masking**: All phone numbers in console logs, JSON reports, and summaries are masked (e.g. `+49 ••• ••••123`).
- **No Hardcoded Credentials**: API tokens or secrets are never committed to code or logs; environment variables are used exclusively.
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

### The two branches

| | **Order food** (`/order`) | **Book a table** (`/reserve`) |
|---|---|---|
| Decides on | price, delivery, time | clock, party size, seating |
| Hard gate | the doorstep total | a free table at that hour |
| Switchable | delivery ⇄ pickup | indoor / outdoor / either |
| Concessions | — | tiered, and authorised by you |

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

* You grant concessions explicitly (`indoor_ok`, `time_flex`, `deposit_ok`).
* They are handed over **in tier order**, with an instruction never to offer a
  later step before an earlier one has failed.
* The result reports which step was played, in `tier_applied`.
* **A result that used a concession you did not grant is rejected**, exactly
  the way an over-budget quote is. An agent that bought the table with money
  you never offered has exceeded its mandate, and the yes it brought back does
  not count. See `CascadeEngine.check_concession_authority`.

### What the screen does

1. **Landing** — two tiles; hovering (or tabbing to) one reveals what that
   branch actually does. A CSS/SVG animation walks a call down four numbers:
   two declines, one connection, and the fourth never dialled.
2. **Location and criteria** — the branch's own questions. No budget field
   exists in the table branch at all.
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
   masked callback number, the transcript, and which concession (if any) was
   spent.

### German and English

Both complete. The interface uses the author's existing `TranslationSystem`
(vendored unchanged in `hungrycall/translator.py`) with
`hungrycall/locales/translations.json`. Language comes from an explicit choice,
then a cookie, then `Accept-Language`, then German.
`tests/test_i18n.py` fails the build if a key used in the code has no entry, if
either language has a gap, or if a `{placeholder}` is lost in translation.

### Honest about what it cannot do

The interface states these where you are working, rather than hiding them:

* **Real calls are locked.** There is no CALL-E account and the balance is
  −0.05 USD. `LiveCallClient` raises rather than pretend. There is deliberately
  no "go live" switch that does nothing.
* **The live OpenStreetMap search is unverified.** The code exists; the dry run
  never enters it.
* **Map tiles come from OpenStreetMap.** The application logic runs with no
  network; without one the map stays grey and everything else keeps working.
  No fonts, scripts or styles are fetched from anywhere.

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
git clone https://github.com/user/hungrycall.git
cd hungrycall

# Install in editable mode
pip install -e .
```

---

## Usage

### 0. 30-Second Core Jury Demo (No Account Required)
```bash
hungrycall demo
```
*Executes the complete core cascade in 30 seconds: Candidate 1 rejected (over budget), Candidate 2 rejected (vague quote), Candidate 3 succeeds, early exit halts Candidate 4, and prints formatted order proof transcript.*

### 1. Delivery Mode (Dry-Run Scenario with Custom Address & Prompt)
```bash
hungrycall delivery --food "2x Döner Kebab" --address "Dorfstrasse 1, 16321 Bernau" --budget 30.0 --scenario success_direct
```

### 2. Table Reservation Mode
```bash
hungrycall reservation --food "Italian" --date "2026-08-05" --time "19:00" --party 4 --scenario reservation_cascade
```

### 2a. A table outside — and what you would settle for
```bash
# Without the grant, the agent's indoor table is refused: it spent authority it did not have.
hungrycall reservation --food "Italian" --date "2026-08-07" --time "19:00" --party 4   --seating outdoor --scenario table_concession_cascade

# With it granted, the same call goes through, and the result says which step was used.
hungrycall reservation --food "Italian" --date "2026-08-07" --time "19:00" --party 4   --seating outdoor --concession indoor_ok --scenario table_concession_cascade
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

---

## Running Tests

85 tests, all in the dry run, no account and no network required:

```bash
pytest -v
```

They cover ranking and its per-mode distance weighting, opening hours across
midnight, the schemas, phone masking, the safety gates, budget and vague-price
rejection, concession authority in both directions, both branches end to end
over the event stream, the candidate order the user arranged, the goal preview,
cancellation, saving with the mode that actually happened, HTML escaping of
free-text input, and the completeness of both languages.

---

## License

MIT License.

