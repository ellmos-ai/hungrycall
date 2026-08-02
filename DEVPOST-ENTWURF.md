# DEVPOST DRAFT: HungryCall 🍕📞

> **Hackathon**: CALL-E ("Your Code Is Calling")
> **Track / Category**: Open Agent Application / Voice Agent Showcase
> **Project Name**: HungryCall — The Autonomous Calling Cascade & Negotiation Engine
> **Tagline**: Stop dialing one by one: HungryCall runs a smart, budget-capped calling cascade across local service providers until your request is fulfilled.

---

## Elevator Pitch (2 Sätze)

In rural and suburban areas lacking delivery apps like DoorDash or UberEats, finding food delivery, table availability, or service slots requires calling local businesses one by one. HungryCall automates this by executing a sequential voice-agent cascade via CALL-E that calls candidates, enforces strict doorstep budget limits and exact price validation, and halts immediately upon success—turning 20 minutes of telephone friction into a single click.

---

## The Problem: Telephone Friction & Unserved Communities

Centralized delivery platforms and online booking systems dominate major cities. But in rural and suburban towns:
* Local restaurants and service providers are not listed on digital platforms.
* Determining who delivers, has an open table, or has capacity requires calling place after place.
* For people who dread phone calls, have speech or hearing impairments, or worry about surprise delivery charges, this friction means settling for the same single spot over and over.

Calling businesses one by one is slow, repetitive, and stressful.

---

## What It Does: Sequential Calling Cascade with Real-Time Early Exit

HungryCall introduces an autonomous voice agent search cascade operating across three distinct modes:

* **Delivery Mode**: Verifies delivery capability to the user's address, obtains an exact doorstep end-price quote (including delivery fees and minimum order requirements), checks ETA, enforces a maximum budget limit, places the order, and captures direct callback details.
* **Table Reservation Mode**: Checks table availability for date, time, and party size, confirms the reservation under the user's name, and provides callback information.
* **Pickup Mode**: Checks pickup availability, total price, and preparation time, placing orders for collection.

### Crucial Safety Guardrail: Doorstep End-Price Budget Cap
HungryCall extends CALL-E's agent authority design (`goal.commitment`) from time windows to monetary limits (`max_budget_eur`):
* The agent evaluates total cost at the doorstep before placing an order.
* If a quote exceeds the user's budget, the agent politely declines and cascades to the next candidate.
* If a business gives a vague quote (e.g., "about 30 Euros depending on the driver"), HungryCall rejects it (`price_known: false`), because guessing prices is strictly prohibited.

---

## 💡 The Core Contribution: The Generalized Calling Cascade Pattern (`MUSTER.md`)

HungryCall is more than just a food app—it introduces a **reusable architectural pattern** for multi-candidate telephone searches.

### The Four Evaluation Criteria Tiers:

1. **Must Criteria (Pflicht)**: Non-negotiable conditions required to proceed (e.g., "Must deliver to address X" or "Must be within 30 km").
2. **Hard Boundaries (Grenzen)**: Strict limits where exceeding the threshold forces polite rejection (e.g., "Doorstep total price ≤ €35.00").
3. **Tiered Concessions (Zugeständnisse)**: Conditional flexibility held back by the agent and only offered when primary attempts fail (e.g., paying a deposit fee for a private dining room only when regular tables are full).
4. **Wishes / Preferences (Wünsche)**: Pre-call ranking criteria that optimize candidate order without blocking execution (e.g., preferring wood-fired pizza or 4+ star rated providers).

### Beyond Food: Real-World Applications
The Calling Cascade Pattern applies directly to any multi-candidate phone search:
* **Urgent Dental / Medical Appointments**: Finding an open slot within 30 km, trying regular coverage first, stepping down to private fee concessions only if necessary.
* **Emergency Auto Repairs**: Locating a garage with immediate brake repair capacity before the weekend.
* **Hardware & Spare Parts**: Checking local supply stores for specific plumbing or electrical components in stock.
* **Respite Care Slots**: Securing temporary nursing care availability across local providers.

---

## ❓ Why Not Just Use the CALL-E App?

The official CALL-E chat/app handles **a single call to a single pre-known target for a single goal**.

HungryCall handles **a multi-candidate autonomous search process**:
* **Pre-Call Intelligence**: Geocodes locations, filters closed businesses by opening hours, and ranks candidates based on craving and proximity.
* **Cost-Minimizing Early Exit**: Halts all remaining call attempts the exact second a candidate meets all criteria, saving API costs and preventing duplicate orders.
* **Financial Authority Caps**: Guarantees the agent cannot spend beyond the user's specified budget limit.
* **Exact Quote Enforcement**: Prevents commitments based on vague or unconfirmed price statements.
* **Oral Contract Proof**: Captures timestamped transcript logs (`[mm:ss] BOT: ...`) as binding verification evidence alongside masked callback numbers.

---

## How We Built It (Technical Architecture)

HungryCall is built with Python 3.11+, FastAPI, HTMX, SQLite, and Leaflet:

* **Core Engine (`hungrycall/engine.py`)**: Executes sequential cascades, evaluates REST API `result_schema` responses, and manages state transitions.
* **Web UI (`hungrycall/web.py`, `templates.py`)**: Zero-build dashboard using HTMX and Server-Sent Events (SSE) for real-time handset (📞) cascade tracking.
* **Interactive Map (`hungrycall/location.py`)**: OpenStreetMap Leaflet integration with user pulse markers and candidate pins.
* **Safety & Privacy (`hungrycall/safety.py`, `phone_utils.py`)**: Enforces E.164 phone validation, full phone number masking (`+49 ••• ••••123`), idempotency keys (`hungrycall-<mode>-<rest_id>-<hash>`), and prohibited content filters.
* **Dry-Run Engine (`hungrycall/fixtures.py`)**: 100% offline fixture framework with dynamic user input interpolation into transcripts, activity logs, and summaries. Allows complete evaluation without an API account.

---

## Empirical Findings & Measured CALL-E Service Dynamics

During integration testing against the live CALL-E service (`FINDINGS.md`), we uncovered key runtime behaviors:

1. **`status` vs. `activity` Progress Tracking**: The `status` field remains on `PREPARING` during live conversation, only changing to `COMPLETED` when the call ends. HungryCall parses real-time `activity` events to display live speech turns.
2. **STT Streaming Draft Deduplication**: The speech-to-text engine streams initial raw text followed by refined corrections. HungryCall automatically deduplicates intermediate STT drafts.
3. **Setup Latency**: Calls incur a ~40-second setup latency (bot initialization + ringing) prior to conversation start, which HungryCall explicitly displays in logs.
4. **REST API vs. MCP Architecture**: Schema-validated call results (`result_schema`) are exclusive to the REST API (`POST /v1/calls`), while MCP operates in a separate ID space.

---

## Accomplishments We're Proud Of

* **34 Unit Tests 100% Green**: Full test suite covering ranking, safety, budget caps, vague quote rejections, tiered concessions, CLI commands, and web routes.
* **30-Second Core Jury Demo (`hungrycall demo`)**: Single CLI command demonstrating Budget Rejection -> Vague Quote Rejection -> Success -> Early Exit -> Verification Transcript Proof in 30 seconds.
* **Zero-Build Web UI**: Lightweight FastAPI + HTMX interface running 100% offline with bundled local static assets.
* **Strict Privacy Compliance**: E.164 phone masking across all outputs, data minimization disclosures, and explicit dry-run defaults.

---

## What We Learned

* Extending agent authority using monetary limits (`max_budget_eur`) provides effective financial safety when delegating real-world phone tasks.
* Real-time STT streaming requires deduplication logic to prevent cluttering live progress logs.

---

## What's Next for HungryCall

* **Multi-Domain Expansion**: Packaging the core cascade engine into a standalone library for medical appointments, mechanic slots, and hardware availability searches.
* **Multi-Language Negotiation**: Expanding prompt templates for multilingual negotiation across international service providers.

---

## Links & Repository Info

* **GitHub Repository**: (Private Hackathon Repository)
* **Demo Command**: `hungrycall demo`
* **Video Demo**: (Included in submission)
