# EVIDENCE.md — HungryCall Execution Log

> **Note on Evidence**: This document records literally what was actually executed during development and testing, without invention or smoothing. What was not executed is explicitly listed as "NOT EXECUTED".

---

## 1. Local Environment Details

- **Date & Time**: 2026-08-01T19:22:45+02:00
- **Operating System**: Windows 10 / 11 (PowerShell)
- **Python Version**: Python 3.12.10
- **Pytest Version**: pytest 9.1.0
- **Working Directory**: `C:\_Local_DEV\repos\hungrycall`
- **Git Branch**: `main`

---

## 2. Actual Commands Executed & Outputs

### Command 1: Pytest Suite Run
```powershell
python -m pytest -v
```

**Literal Output**:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.0, pluggy-1.6.0 -- C:\Program Files\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\_Local_DEV\repos\hungrycall
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0, asyncio-1.4.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 25 items

tests/test_budget_and_price_rejection.py::test_budget_limit_exceeded_rejection PASSED [  4%]
tests/test_budget_and_price_rejection.py::test_vague_price_quote_rejection PASSED [  8%]
tests/test_budget_and_price_rejection.py::test_strict_all_budget_exceeded_fails PASSED [ 12%]
tests/test_cascade.py::test_cascade_stops_immediately_on_first_success PASSED [ 16%]
tests/test_cascade.py::test_reservation_cascade PASSED                   [ 20%]
tests/test_cascade.py::test_pickup_cascade PASSED                        [ 24%]
tests/test_cli.py::test_cli_delivery_dry_run PASSED                      [ 28%]
tests/test_cli.py::test_cli_delivery_json_output PASSED                  [ 32%]
tests/test_cli.py::test_cli_budget_exceeded_scenario PASSED              [ 36%]
tests/test_cli.py::test_cli_reservation PASSED                           [ 40%]
tests/test_cli.py::test_cli_pickup PASSED                                [ 44%]
tests/test_cli.py::test_cli_live_without_confirm_fails PASSED            [ 48%]
tests/test_phone_utils.py::test_validate_e164_valid PASSED               [ 52%]
tests/test_phone_utils.py::test_validate_e164_invalid PASSED             [ 56%]
tests/test_phone_utils.py::test_normalize_e164 PASSED                    [ 60%]
tests/test_mask_phone PASSED                        [ 64%]
tests/test_ranking.py::test_food_prompt_beats_favorite PASSED            [ 68%]
tests/test_ranking.py::test_favorite_wins_when_cuisine_matches PASSED    [ 72%]
tests/test_ranking.py::test_closed_restaurant_filtered_out PASSED        [ 76%]
tests/test_safety.py::test_verify_content_safety_valid PASSED            [ 80%]
tests/test_safety.py::test_verify_content_safety_prohibited_keywords PASSED [ 84%]
tests/test_safety.py::test_verify_phone_safety PASSED                    [ 88%]
tests/test_safety.py::test_verify_live_safety PASSED                     [ 92%]
tests/test_safety.py::test_generate_idempotency_key PASSED               [ 96%]
tests/test_schemas.py::test_get_result_schema_types PASSED               [100%]

============================= 25 passed in 0.11s ==============================
```

---

### Command 2: CLI Dry-Run Execution (Delivery Mode - Budget Exceeded Scenario)
```powershell
python -m hungrycall.cli delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario budget_exceeded_cascade
```

**Literal Output**:
```text
============================================================
HUNGRYCALL — Cascade Agent Execution
Mode: DELIVERY | Prompt: 'Burger'
Maximum Total Budget: 35.00 EUR (doorstep end price limit)
Execution Mode: DRY-RUN (Fixtures)
============================================================
NOTICE: CALL-E voice agent operates via AiRudder servers located in Singapore (https://seleven-mcp-sg.airudder.com). Only minimal data required for food ordering/reservation is transmitted.
------------------------------------------------------------

Attempt History:
  Attempt #1: Burger House Dorfstadt (+491 ••• ••••111) -> ❌ REJECTED
    Reason: Total price 42.00 EUR exceeds maximum budget limit of 35.00 EUR
  Attempt #2: Trattoria Bella Luigi (+491 ••• ••••222) -> ✅ PASSED

============================================================
RESULT: SUCCESS
SUMMARY: Ordered from Trattoria Bella Luigi: delivers in 40 minutes, items 'Burger', total 31.50 EUR. Callback at +491 ••• ••••222.

Verification Transcript:
  [00:00:05] Agent: Hello, calling on behalf of Lukas. Can you deliver for 31.50 EUR total?
  [00:00:12] Restaurant: Yes, total is 31.50 Euros. Order placed!
============================================================
```

---

### Command 3: CLI Dry-Run Execution (Vague Price Quote Rejection Scenario)
```powershell
python -m hungrycall.cli delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" --budget 35.0 --scenario vague_price_cascade
```

**Literal Output**:
```text
============================================================
HUNGRYCALL — Cascade Agent Execution
Mode: DELIVERY | Prompt: 'Burger'
Maximum Total Budget: 35.00 EUR (doorstep end price limit)
Execution Mode: DRY-RUN (Fixtures)
============================================================
NOTICE: CALL-E voice agent operates via AiRudder servers located in Singapore (https://seleven-mcp-sg.airudder.com). Only minimal data required for food ordering/reservation is transmitted.
------------------------------------------------------------

Attempt History:
  Attempt #1: Burger House Dorfstadt (+491 ••• ••••111) -> ❌ REJECTED
    Reason: Unclear price statement: Restaurant said 'about 30 Euro depending on driver'
  Attempt #2: Trattoria Bella Luigi (+491 ••• ••••222) -> ✅ PASSED

============================================================
RESULT: SUCCESS
SUMMARY: Ordered from Trattoria Bella Luigi: delivers in 45 minutes, items 'Burger', total 29.00 EUR. Callback at +491 ••• ••••222.

Verification Transcript:
  [00:00:05] Agent: Hello, calling on behalf of Lukas. Can you deliver to Hauptstraße 12?
  [00:00:10] Restaurant: Yes, we deliver there. The total price is exactly 29.00 Euros.
  [00:00:18] Agent: 29.00 EUR is within the 35 EUR limit. Please place the order.
  [00:00:25] Restaurant: Order received! Delivery in 45 minutes.
============================================================
```

---

## 3. What Was NOT Executed (Explicit Exclusions)

Per `AGENTS.md` boundaries:

1. **Real Phone Calls**: NOT EXECUTED. No phone numbers were dialed. All runs executed via `DryRunCallClient` against local scenario fixtures.
2. **CALL-E Account Registration / Login**: NOT EXECUTED. Development was completed entirely without a CALL-E account or live access tokens.
3. **Remote Git Push / Pull Request**: NOT EXECUTED. The repository remains local and private.
4. **Video Recording**: NOT EXECUTED.
5. **Background Daemons / Cron Jobs**: NOT EXECUTED.
