# HungryCall — AGY Report 2 (Nacharbeit & Real-Service-Messungen)

> **Zeitstempel**: 2026-08-01T21:05:00+02:00  
> **Repository**: `C:\_Local_DEV\repos\hungrycall`  
> **Status**: Alle 29 Pytest-Tests grün, lokal committet (Branch `main`, Commit `81df59d`).

---

## 1. Was geändert wurde

1. **Dynamische Fixture-Eingabenübernahme (`render_fixture_data`)**:
   - Die Fixtures in `hungrycall/fixtures.py` spiegeln nun exakt die vom Nutzer übergebenen Daten (`delivery_address`, `food_prompt`, `customer_name`, `max_budget_eur`, `reservation_date`, `reservation_time`, `party_size`, `pickup_time`).
   - Bei Eingabe von `--address "Dorfstrasse 1, 16321 Bernau"` und `--food "2x Döner Kebab"` steht nun im Transkript und der Zusammenfassung wörtlich `Dorfstrasse 1, 16321 Bernau` und `2x Döner Kebab` anstelle von statischen Dummy-Adressen.

2. **Fortschrittsanzeige & Live-Mitlesen über `activity`**:
   - Da `status` während des laufenden Anrufs auf `PREPARING` verharrt, erfolgt die Fortschrittsmeldung nun ausschließlich über das `activity`-Event-Log.
   - Einbau einer Hinweiszeile für die gemessene **~40s Vorlaufzeit** (Bot-Initialisierung + Klingeln).
   - Implementierung von `deduplicate_activity()` zur Bereinigung von Doppelungseinträgen des strömenden Spracherkenners (Rohfassung vs. korrigierte Fassung).

3. **Transkript-Formatierung als Bestellbeleg**:
   - Bereitstellung des Transkripts im gemessenen String-Format `[mm:ss] SPRECHER: Text` (`BOT` / `USER`).
   - Ausgabe des formatierten Transkripts in der Konsole und im JSON-Output als Beleg für die mündliche Bestellung.

4. **REST-API vs. MCP Architektur & Key-Sicherheit**:
   - Dokumentierung des REST-Hauptwegs (`POST /v1/calls` mit `Bearer $CALLE_API_KEY` und `result_schema`), da MCP keine Ergebnis-Schemas unterstützt.
   - Striktes Auslesen des API-Keys aus `CALLE_API_KEY` oder `IAM_API_KEY`. Keine Keys im Code, in Logs oder Commits.

5. **Konsolen-Kompatibilität auf Windows**:
   - Vermeidung von Unicode-Encode-Fehlern auf Windows-Terminals mit Codepage `cp1252` durch Robuste Konsolenausgaben.

---

## 2. Welche Tests mit welcher echten Ausgabe gelaufen sind

### Pytest Testsuite (29 von 29 passed)

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.0, pluggy-1.6.0
rootdir: C:\_Local_DEV\repos\hungrycall
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0, asyncio-1.4.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False
collected 29 items

tests/test_budget_and_price_rejection.py::test_budget_limit_exceeded_rejection PASSED [  3%]
tests/test_budget_and_price_rejection.py::test_vague_price_quote_rejection PASSED [  6%]
tests/test_budget_and_price_rejection.py::test_strict_all_budget_exceeded_fails PASSED [ 10%]
tests/test_cascade.py::test_cascade_stops_immediately_on_first_success PASSED [ 13%]
tests/test_cascade.py::test_reservation_cascade PASSED                   [ 17%]
tests/test_cascade.py::test_pickup_cascade PASSED                        [ 20%]
tests/test_cli.py::test_cli_delivery_dry_run PASSED                      [ 24%]
tests/test_cli.py::test_cli_delivery_json_output PASSED                  [ 27%]
tests/test_cli.py::test_cli_budget_exceeded_scenario PASSED              [ 31%]
tests/test_cli.py::test_cli_reservation PASSED                           [ 34%]
tests/test_cli.py::test_cli_pickup PASSED                                [ 37%]
tests/test_cli.py::test_cli_live_without_confirm_fails PASSED            [ 41%]
tests/test_findings_and_dynamic_fixtures.py::test_dynamic_user_input_reflection_in_transcript PASSED [ 44%]
tests/test_findings_and_dynamic_fixtures.py::test_cli_reflects_custom_user_address PASSED [ 48%]
tests/test_findings_and_dynamic_fixtures.py::test_activity_stt_deduplication PASSED [ 51%]
tests/test_findings_and_dynamic_fixtures.py::test_activity_log_contains_40s_setup_latency_notice PASSED [ 55%]
tests/test_phone_utils.py::test_validate_e164_valid PASSED               [ 58%]
tests/test_phone_utils.py::test_validate_e164_invalid PASSED             [ 62%]
tests/test_phone_utils.py::test_normalize_e164 PASSED                    [ 65%]
tests/test_phone_utils.py::test_mask_phone PASSED                        [ 68%]
tests/test_ranking.py::test_food_prompt_beats_favorite PASSED            [ 72%]
tests/test_ranking.py::test_favorite_wins_when_cuisine_matches PASSED    [ 75%]
tests/test_ranking.py::test_closed_restaurant_filtered_out PASSED        [ 79%]
tests/test_safety.py::test_verify_content_safety_valid PASSED            [ 82%]
tests/test_safety.py::test_verify_content_safety_prohibited_keywords PASSED [ 86%]
tests/test_safety.py::test_verify_phone_safety PASSED                    [ 89%]
tests/test_safety.py::test_verify_live_safety PASSED                     [ 93%]
tests/test_safety.py::test_generate_idempotency_key PASSED               [ 96%]
tests/test_schemas.py::test_get_result_schema_types PASSED               [100%]

============================= 29 passed in 0.20s ==============================
```

### Echte CLI-Ausgabe für eigene Adresse (`Dorfstrasse 1, 16321 Bernau`)

```text
python -m hungrycall.cli delivery --food "2x Döner Kebab" --address "Dorfstrasse 1, 16321 Bernau" --budget 30.0 --customer-name "Alex" --scenario success_direct

============================================================
HUNGRYCALL — Cascade Agent Execution
Mode: DELIVERY | Prompt: '2x Döner Kebab'
Maximum Total Budget: 30.00 EUR (doorstep end price limit)
Execution Mode: DRY-RUN (Fixtures)
============================================================
NOTICE: CALL-E voice agent operates via AiRudder servers located in Singapore (https://seleven-mcp-sg.airudder.com). Only minimal data required for food ordering/reservation is transmitted.
------------------------------------------------------------

Attempt History & Activity Stream:

  Attempt #1: Trattoria Bella Luigi (+491 ••• ••••222) -> [REJECTED]
    Reason: Call failed with status 'FAILED'
    Live Activity Progress:
      * Call initiated
      * No response

  Attempt #2: Burger House Dorfstadt (+491 ••• ••••111) -> [PASSED]
    Live Activity Progress:
      * 17:37:05.100 | Bot initialized.
      * 17:37:44.200 | Call is ringing (~40s setup latency).
      * 17:37:49.500 | Call connected.
      * 17:37:50.700 | Bot is speaking: Hello, I am an automated assistant calling on behalf of Alex. Do you deliver to Dorfstrasse 1, 16321 Bernau?
      * 17:37:52.200 | Callee said: Ja, wir liefern nach Dorfstrasse 1, 16321 Bernau.
      * 17:38:15.800 | Bot is speaking: Great! What is the exact total price including delivery fee for 2x Döner Kebab?
      * 17:38:21.300 | Callee said: 28.50 Euro.
      * 17:38:40.100 | Call ended; syncing final Calling result.

============================================================
RESULT: SUCCESS
SUMMARY: Ordered from Burger House Dorfstadt: delivers in 35 minutes, items '2x Döner Kebab', total 28.50 EUR. Callback at +491 ••• ••••111.

Verification Transcript (Order Proof):
  [00:05] BOT: Hello, I am an automated assistant calling on behalf of Alex. Do you deliver to Dorfstrasse 1, 16321 Bernau?
  [00:10] USER: Yes, we deliver to Dorfstrasse 1, 16321 Bernau.
  [00:15] BOT: Great! What is the exact total price including delivery fee for 2x Döner Kebab?
  [00:22] USER: The total end price at your door is exactly 28 Euros and 50 Cents.
  [00:28] BOT: Perfect, that is within our 30.00 Euro limit. Please place the order. How long will it take?
  [00:35] USER: Order is confirmed! Delivery will take about 35 minutes.
  [00:40] BOT: Thank you very much. Goodbye!
============================================================
```

---

## 3. Was offen blieb

1. **Parallelität der Anrufe**:
   - Die Möglichkeit paralleler Anrufe bleibt ungeprüft. Die Kaskade arbeitet weiterhin seriell (Abbruch sofort bei Erfolg), was für Bestellungen und Kostenkontrolle zwingend erforderlich ist.
2. **Echte Netzwerkanrufe (`--live`)**:
   - Gemäß `AGENTS.md` wurden keine echten Anrufe getätigt. Der Live-Pfad ist durch Safety-Checks geschützt und erfordert ein valides Konto sowie `--confirm-live`.
3. **Erweiterte Endstatus im Echtbetrieb**:
   - Die Unterscheidung der Endstatus (`BUSY`, `NO_ANSWER`, `VOICEMAIL`, `DECLINED`) ist im Code implementiert, wurde bisher am echten Dienst aber nur mit `COMPLETED` verifiziert.
