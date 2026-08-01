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

### 1. Delivery Mode (Dry-Run Scenario)
```bash
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario success_direct
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
Attempt History:
  Attempt #1: Burger House Dorfstadt (+49 ••• ••••111) -> ❌ REJECTED
    Reason: Total price 42.00 EUR exceeds maximum budget limit of 35.00 EUR
  Attempt #2: Trattoria Bella Luigi (+49 ••• ••••222) -> ✅ PASSED

RESULT: SUCCESS
SUMMARY: Ordered from Trattoria Bella Luigi: delivers in 40 minutes, items 'Burger', total 31.50 EUR. Callback at +49 ••• ••••222.
```

### 5. Simulating Vague Price Rejection
```bash
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario vague_price_cascade
```

---

## Running Tests

Run the full pytest suite (25 tests covering ranking, schemas, phone masking, safety, budget rejection, vague price rejection, and CLI execution):

```bash
pytest -v
```

---

## License

MIT License.
