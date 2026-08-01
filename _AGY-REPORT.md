# _AGY-REPORT.md — Summary of Work (Antigravity Agent)

## 1. Was gebaut wurde

Das Python-Werkzeug **HungryCall** (`hungrycall`) wurde im Verzeichnis `C:\_Local_DEV\repos\hungrycall` als automatisierte Sprach-Agenten-Kaskade für den CALL-E Hackathon umgesetzt:

- **Drei Betriebsmodi**:
  - `delivery`: Prünft Lieferfähigkeit zur Adresse, exakten Haustür-Endpreis (inkl. Liefergebühr & Mindestbestellwert), ETA und platziert die Bestellung.
  - `reservation`: Prüft Tischverfügbarkeit für Datum, Uhrzeit und Personenanzahl, bestätigt Reservierung auf den Namen des Anrufers und liefert Rückrufnummer für Stornierungen.
  - `pickup`: Prüft Abholbarkeit, exakten Gesamtpreis, Zubereitungszeit und platziert Abholbestellung.
- **Priorisierungs-Ranking (`hungrycall/ranking.py`)**:
  - Der **aktuelle Essenswunsch schlägt das Lieblingsrestaurant** (z. B. Wunsch „Burger" priorisiert Burger-Laden vor dem Lieblings-Italiener).
  - Öffnungszeiten und Modus-Support filtern geschlossene/ungeeignete Restaurants vorab aus.
- **Höchstbetrag (Max Budget Limit Rule) & Unklare Preisauskunft**:
  - `max_budget_eur` wird vorab definiert und prüft den Haustür-Endpreis.
  - `price_known: False` (z. B. „so ungefähr 30 Euro") führt zur sofortigen höflichen Ablehnung ohne Schätzung.
  - Nach Zusage wird stets die Rückrufnummer ausgegeben.
- **Schema-Entwurf (`hungrycall/schemas.py`)**:
  - Strikte CALL-E `result_schema` Definitionen je Modus (`delivers_to_address`, `price_known`, `total_price_eur`, `eta_minutes`, `order_placed`, `callback_number`, `rejection_reason`).
- **Safety & Compliance (`hungrycall/safety.py`, `hungrycall/phone_utils.py`)**:
  - Standardmäßig 100 % Trockenlauf (`DryRunCallClient`) gegen Szenario-Fixtures (`hungrycall/fixtures.py`).
  - E.164-Rufnummernvalidierung vor Anruf.
  - Rufnummernmaskierung in allen Ausgaben, Reports und Logs (`+49 ••• ••••123`).
  - Inhaltliche Guardrails gegen unzulässige Themen (Notfall, Medizin, Recht).
  - Generierung von Idempotenz-Schlüsseln (`hungrycall-<mode>-<restaurant_id>-<hash>`).
  - Offenlegung des Datenflusses zum AiRudder-Server in Singapur (`https://seleven-mcp-sg.airudder.com`).

---

## 2. Welche Tests mit welcher echten Ausgabe liefen

Die Pytest-Suite in `tests/` umfasst **25 Tests**, die alle 100 % grün liefen:

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
tests/test_phone_utils.py::test_mask_phone PASSED                        [ 64%]
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

Getestete Kernszenarien:
1. `test_budget_limit_exceeded_rejection`: Ablehnung bei Preisüberschreitung (42.00 € > 35.00 € Limit). Kaskade schaltet auf Kandidat #2 um und schließt bei 31.50 € erfolgreich ab.
2. `test_vague_price_quote_rejection`: Ablehnung bei unklarer Preisauskunft (`price_known: False`, „so ungefähr 30 Euro"). Kaskade schaltet auf Kandidat #2 mit exaktem Preisangebot um.
3. `test_cascade_stops_immediately_on_first_success`: Kaskade bricht sofort nach dem ersten erfolgreichen Kandidaten ab und ruft KEINE weiteren Restaurants an.

---

## 3. Welche Annahmen nötig waren

1. **Recherche-Quellen im Trockenlauf**: Restaurant-Recherche (Google Places / lokale Liste) erfolgt lokal über Fixtures (`hungrycall/fixtures.py`), um die Unabhängigkeit von externen APIs ohne Konto zu garantieren.
2. **Kaskaden-Concurrency**: Die Kaskade ruft Kandidaten rein sequentiell nacheinander an, um Mehrfachanrufe oder unbeabsichtigte Doppelbestellungen strikt zu vermeiden.
3. **Mündlicher Vertrag & Transkript**: Das Transkript wird im `CallResult` als rechtsverbindlicher Nachweis der Bestellung mitgeführt.

---

## 4. Was offen blieb

1. **Echte Anrufe / Live-Konto**: Es existiert bewusst kein CALL-E-Konto. Der Live-Modus (`LiveCallClient`) setzt eine echte CALL-E-API-Authentifizierung voraus und verlangt das `--live` sowie `--confirm-live` Flag.
2. **Video / PR**: Veröffentlichung, Pull Request und Video-Erstellung verbleiben vereinbarungsgemäß beim Operator/Nutzer.
