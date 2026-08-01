# HungryCall 🍕📞

> **Hackathon Submission for CALL-E ("Your Code Is Calling")**
>
> Automated voice agent cascade for food delivery, table reservations, and pickup.

HungryCall solves a real-world problem in rural and suburban areas: local restaurants often lack integration with central delivery platforms (e.g. Lieferando/DoorDash). Finding out who delivers, table availability, or total cost requires calling restaurants one by one. HungryCall automates this via CALL-E by executing a **sequential calling cascade with immediate early exit upon success**.

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
- **E.164 Validation**: All target phone numbers are validated against standard E.164 format (`+491701234567`) prior to dialing.
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

HungryCall includes a lightweight, zero-build Web UI based on **FastAPI, HTMX, SQLite, and Leaflet**:

### Key Web Features:
- **1. Location & Address**: International PLZ, Ort, and Country geocoding with radius search.
- **2. Search State**: Smooth search animation with *"Wir suchen für Sie die besten Essenspunkte..."*.
- **3. Always-Visible Map**: OpenStreetMap Leaflet map displaying the user's location as a glowing pulse marker surrounded by candidate restaurants.
- **4. Restaurant Selection & Drag-and-Drop Prioritization**: Includes UI-SPEC guidance text, checkable cards, closed restaurant toggle, and priority ordering.
- **5. Mode & Food Request**: Delivery, Pickup, and Table Reservation with free-text food prompt and maximum doorstep budget input.
- **6. Prompt Transparency Preview**: Displays the exact CALL-E goal prompt text before starting calls.
- **7. Live SSE Cascade**: Stationary restaurant list with moving 📞 telephone handset icon (gray preparing, green connected, red rejected, green checkmark success).
- **8. Result Card**: Prominent summary sentence, total price, ETA, **prominently highlighted restaurant callback phone number**, expandable transcript, and SQLite persistence.
- **9. 100% Offline Showcase**: Bundled local HTMX & Leaflet assets allow full offline demonstrations without internet or CALL-E accounts.

### Launching the Web UI
```bash
# Option 1: Using the runner script
python run_web.py

# Option 2: Using the CLI entry point
hungrycall-web
```
Access the interface in your browser at `http://127.0.0.1:8000`.

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

### 1. Delivery Mode (Dry-Run Scenario with Custom Address & Prompt)
```bash
hungrycall delivery --food "2x Döner Kebab" --address "Dorfstrasse 1, 16321 Bernau" --budget 30.0 --scenario success_direct
```

### 2. Table Reservation Mode
```bash
hungrycall reservation --food "Italian" --date "2026-08-05" --time "19:00" --party 4 --scenario reservation_cascade
```

### 3. Pickup Mode
```bash
hungrycall pickup --food "Pizza" --budget 25.0 --scenario pickup_cascade
```

### 4. Simulating Budget Exceeded Rejection
```bash
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario budget_exceeded_cascade
```
*Output excerpt:*
```text
Attempt History & Activity Stream:
  Attempt #1: Burger House Dorfstadt (+491 ••• ••••111) -> ❌ REJECTED
    Reason: Total price 42.00 EUR exceeds maximum budget limit of 35.00 EUR
    Live Activity Progress:
      • 17:37:05.100 | Bot initialized.
      • 17:37:44.200 | Call is ringing (~40s setup latency).
      • 17:37:49.500 | Call connected.
      • 17:37:50.700 | Bot is speaking: Hello, calling on behalf of Lukas...
      • 17:37:52.200 | Callee said: 42 Euro.
      • 17:38:00.100 | Call ended; syncing final Calling result.
  Attempt #2: Trattoria Bella Luigi (+491 ••• ••••222) -> ✅ PASSED

RESULT: SUCCESS
SUMMARY: Ordered from Trattoria Bella Luigi: delivers in 40 minutes, items 'Burger', total 31.50 EUR. Callback at +491 ••• ••••222.
```

### 5. Simulating Vague Price Rejection
```bash
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario vague_price_cascade
```

---

## Running Tests

Run the full pytest suite (29 tests covering ranking, schemas, phone masking, safety, budget rejection, vague price rejection, dynamic fixture rendering, STT deduplication, and CLI execution):

```bash
pytest -v
```

---

## License

MIT License.
