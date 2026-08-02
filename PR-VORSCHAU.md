# PR-VORSCHAU: Formal Requirements & Draft Entry for `CALLE-AI/awesome-phone-call-agents`

> 🛑 **GATE NOTICE**: 
> In accordance with `AGENTS.md` and user safety rules, **NO Pull Request has been opened, NO git push executed, and NO repository made public**.
> This document serves exclusively as a formal preparation audit and PR entry preview for the operator/user to review.

---

## 1. Formal Pull Request Checklist for `CALLE-AI/awesome-phone-call-agents`

To ensure immediate acceptance by the maintainers of `CALLE-AI/awesome-phone-call-agents` when the user decides to submit, HungryCall has been verified against all target repository submission rules:

### Technical & Dry-Run Requirements
* [x] **100% Dry-Run Default**: Running `hungrycall` CLI or `python run_web.py` operates 100% locally against dry-run fixtures without requiring an API key or CALL-E account.
* [x] **Python 3.11+ Compatibility**: Clean execution on Python 3.11+ (`pyproject.toml` specified).
* [x] **No Private Service Dependency**: Full fixture framework (`hungrycall/fixtures.py`) provides zero-network offline evaluation.

### Safety & Compliance Requirements
* [x] **Explicit User Action**: Calls are triggered solely by direct user invocation (CLI flag or Web UI button).
* [x] **E.164 Phone Validation**: All target phone numbers are strictly validated against standard E.164 format (`+491701234567`) prior to execution.
* [x] **Phone Number Masking**: All output channels (CLI stdout, Web UI, JSON reports, logs) mask phone numbers (`+49 ••• ••••123`).
* [x] **No Hardcoded Credentials**: API tokens are read strictly from environment variables (`CALLE_API_KEY` / `IAM_API_KEY`). Zero secrets in code or git history.
* [x] **No Hidden Background Daemons**: Single-execution architecture without background cron jobs, daemons, or polling loops.
* [x] **Idempotency Safeguards**: Header `Idempotency-Key` sent with every API attempt (`hungrycall-<mode>-<rest_id>-<hash>`).
* [x] **Graceful Abort**: Handles `Ctrl+C` cleanly without corrupting local state or SQLite records.
* [x] **Domain Guardrails**: Automatically rejects prompts containing prohibited keywords (medical, legal, financial, emergency).

### Documentation & Privacy Disclosures
* [x] **English Language**: Repository `README.md`, code comments, and documentation are written strictly in English.
* [x] **Singapore Server Data Flow Disclosure**: `README.md` prominently discloses data transfer to AiRudder servers in Singapore (`https://seleven-mcp-sg.airudder.com`) and data minimization protocols.
* [x] **Architectural Alignment**: Explicitly documents alignment with CALL-E's `goal.commitment` design, extending time windows to monetary authority caps (`max_budget_eur`).

---

## 2. Draft PR Entry for `awesome-phone-call-agents/README.md`

When submitting a PR to `CALLE-AI/awesome-phone-call-agents`, the maintainers require adding a formatted entry under the Community Applications section of their `README.md`. Here is the exact markdown snippet to insert:

```markdown
### 🍕 [HungryCall](https://github.com/<user>/hungrycall)
> Automated voice agent cascade for food delivery, table reservations, and pickup.

* **Description**: HungryCall solves telephone friction in rural/suburban areas where central delivery apps do not operate. It executes a sequential calling cascade across local restaurants with immediate early exit upon success, enforcing strict doorstep budget caps (`max_budget_eur`), exact price quote validation (`price_known: true`), and full verification transcript proofs.
* **Core Architectural Pattern**: Introduces the **Generalized Calling Cascade Pattern** (`MUSTER.md`) featuring 4 evaluation tiers (Must, Hard Boundaries, Tiered Concessions, Wishes), applicable to medical appointments, mechanic slots, and hardware availability searches.
* **Tech Stack**: Python 3.11+, FastAPI, HTMX, SQLite, Leaflet, CALL-E REST API.
* **Safety Highlights**: 100% dry-run by default, E.164 phone validation, full phone number masking (`+49 ••• ••••123`), idempotency keys, Singapore data flow disclosure, zero hardcoded credentials.
* **Quick Demo**: `hungrycall demo` (30-second offline dry-run cascade).
```

---

## 3. Recommended PR Title & Description Template

### Proposed PR Title
`feat(apps): add HungryCall - Sequential calling cascade & budget cap engine`

### Proposed PR Description Template
```markdown
## Application Overview
HungryCall is an autonomous voice agent application built on top of CALL-E. It addresses a real-world gap for communities where central delivery platforms (Lieferando/DoorDash) are unavailable.

Instead of placing a single call, HungryCall executes a **sequential calling cascade across ranked candidates** with immediate early exit upon success to minimize call costs and prevent duplicate orders.

## Key Features & Contributions
1. **Generalized Calling Cascade Pattern (`MUSTER.md`)**: A reusable multi-candidate search pattern evaluating Must conditions, Hard Budget Limits, Tiered Negotiation Concessions, and Ranking Preferences.
2. **Doorstep End-Price Budget Cap**: Extends CALL-E's `goal.commitment` authority model to monetary limits (`max_budget_eur`), politely declining quotes that exceed budget caps.
3. **Exact Quote Enforcement**: Rejects vague quotes (`price_known: false`) to prevent unauthorized commitments.
4. **Zero-Account Dry-Run Engine**: 100% offline evaluation mode out of the box (`hungrycall demo`).
5. **FastAPI + HTMX Web UI**: Lightweight dashboard with live Server-Sent Events (SSE) handset progress tracking.

## Safety Compliance Checklist
- [x] Dry-run default execution (runs out of the box without API keys)
- [x] E.164 phone validation & masking (`+49 ••• ••••123`)
- [x] No committed secrets or credentials
- [x] Unique `Idempotency-Key` header on every call
- [x] Prohibited domain guardrails (medical/legal/financial/emergency prompt rejection)
- [x] Data flow & privacy disclosures included in README.md
```
