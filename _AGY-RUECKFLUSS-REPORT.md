# _AGY-RUECKFLUSS-REPORT.md — Rückfluss-Bericht Videoentwurf ➔ Software

> **Datum**: 2026-08-02
> **Operator**: Gemini (Antigravity Agent)
> **Projekt**: HungryCall (`C:\_Local_DEV\repos\hungrycall`)
> **Grundsatz**: *"Erfundene Dinge können auch Ideen sein, wenn sie gut sind."* (LEARNINGS.md). Bei Abweichungen zwischen Videoentwurf und Software gilt die 3-Optionen-Regel:
> 1. *Stimmt* ➔ Bleibt
> 2. *Stimmt nicht* ➔ Wird im Video korrigiert
> 3. **Stimmt nicht, ist aber besser ➔ Wird in die Software gebaut!**

---

## 1. Szene-für-Szene-Prüfung des Videoentwurfs

Die Analyse erfolgte auf Basis des gerenderten Videoentwurfs (`hungrycall_2026-08-02_03-07-56.mp4`, 88,7 s) über den Contact-Sheet- und Einzelbild-Scatterer von `ai-media-editor` (`python tools/frame_view.py --every 8 --label`):

| Zeitstempel | Szene / Bildinhalt | Videodarstellung | Bisherige Software | Bewertung & Regelentscheidung |
|---|---|---|---|---|
| **00:00.0** | Title Hook | "Beyond Single-Call Provider Apps" | Web-Titel & Header | (1) Stimmt überein. |
| **00:08.0** | Anfrage-Setup mit Karte | Gestrichelter Kandidaten-Suchradius um Benutzer-Pin auf Leaflet-Karte | Karte zeigte nur Stecknadeln ohne Radius | **(3) STIMMT NICHT, IST ABER BESSER ➔ GEBAUT.** Der Radius macht die geografische Suchgrenze (z. B. 3,0 km) sofort verständlich. |
| **00:16.0** | Restaurantauswahl & Priorität | Checkbox-Liste & Drag-and-Drop Sortierung | Liste mit Checkboxen & Mini-Buttons | (1) Stimmt überein. |
| **00:24.0** | Budget-Band & Vollmacht | Visuelles Shield-Banner mit Höchstbetrag & Concept-Badge | Budget-Eingabefeld im Formular | **(3) STIMMT NICHT, IST ABER BESSER ➔ GEBAUT.** Der permanente Banner hebt die finanzielle Leitplanke (*Financial Authority Cap*) während der Ausführung hervor. |
| **00:32.0** | Kaskade & Ablehnungen | Inline-Badge mit roter Begründung an der Karte (*42,00 € > 35,00 € Budget*) | Hörer-Icon schlug fehl, aber Grund stand nur im Log | **(3) STIMMT NICHT, IST ABER BESSER ➔ GEBAUT.** Transparenter Echtzeit-Grund direkt am Restaurant-Item. |
| **00:40.0** | Anruf verbunden | Grüner Hörer & Echtzeit-Sprachzüge-Stream | SSE-Stream mit Hörer-Icon | (1) Stimmt überein. |
| **00:48.0** | Ergebnis-Karte | Bestätigungsbox, ETA, Endbetrag & hervorgehobene Rückrufnummer | Result-Card mit Rückrufbox | (1) Stimmt überein. |
| **00:56.0** | Transkript-Ansicht | Hervorgehobener Endpreis-Verifizierungs-Banner über Transkriptzeilen | Plaintext pre-Tag ohne Preis-Highlight | **(3) STIMMT NICHT, IST ABER BESSER ➔ GEBAUT.** Hebt die verifizierte Preisaussage als visuellen Beleg hervor. |
| **01:04.0** | Allgemeines Muster | `MUSTER.md` Kriterien-Stufen (Must, Boundary, Concessions, Wishes) | `MUSTER.md` vorhanden | (1) Stimmt überein. |
| **01:12.0** | Erweitertes Use-Case-Set | Zahnarzttermine, Handwerker, Notfall-Reparaturen | Doku & CLI-Demomodi vorhanden | (1) Stimmt überein. |
| **01:20.0–01:28.0** | Outro & Safety-Notice | E.164 Maskierung, Datenfluss-Transparenz, Trockenlauf | Safety-Verifikation im Code & README | (1) Stimmt überein. |

---

## 2. Aus dem Video abgeleitete Software-Upgrades (Aufgabe 1 & 3)

Alle vier Kandidaten aus der Szene-für-Szene-Prüfung haben die Option-3-Bewertung bestanden und wurden **vollständig in die Software eingebaut**:

1. **Kandidatenradius auf der Karte**:
   - `initLeafletMap(lat, lon, zoom, radiusKm)` in `hungrycall/templates.py` zeichnet nun dynamisch `L.circle([lat, lon], radiusKm * 1000)` mit gestricheltem Rand und Amber-Fill (`fillOpacity: 0.08`).
2. **Ablehnungsgründe auf den Restaurant-Karten**:
   - `#rejection-{id}` Container in `render_restaurant_selection_step()` und SSE DOM-Update in `hungrycall/web.py` fügt bei Ablehnung sofort das Badge `<div style="color: #f87171;">🔴 Abgelehnt: <Grund></div>` ein.
3. **Active Budget Band Header**:
   - `render_cascade_monitor()` in `hungrycall/templates.py` rendert nun das Shield-Banner `🛡️ FINANCIAL AUTHORITY CAP (Harte Grenze) | Höchstbetrag: XX.XX €` im Header der Kaskadenausführung.
4. **Transkript-Preis-Highlighting**:
   - `render_result_card()` in `hungrycall/templates.py` bettet das Verifizierungsbanner `🏷️ Bestätigter Transkript-Endpreis: XX.XX € | ✓ In Budget` direkt über dem Transkript ein.

### Eingetragene Aufgaben
- In **`TODO.md`** und **`AUFGABEN.txt`** eingetragen und als `[x]` bzw. `[ERLEDIGT]` markiert.

---

## 3. Gehärtete EVIDENCE-Dokumentation (Aufgabe 2)

`EVIDENCE.md` wurde überarbeitet und ist nun für einen externen Juror ohne Zugangsdaten zu 100 % transparent und nachvollziehbar:

### Was WIRKLICH lokal ausgeführt wurde:
- **Pytest-Suite**: 35 Unit- und Integrationstests **100 % grün in 1.45 s** (`python -m pytest -v`).
- **CLI Demo**: 30-Sekunden-Kaskadenausführung (`python -m hungrycall.cli demo`) mit Budget-Ablehnung, Unklarer-Preis-Ablehnung, Erfolg und frühem Abbruch.
- **Web-Interface**: Geocoding, Radius-Kreis, HTMX-Kaskadenstart, SSE-Echtzeit-Stream und SQLite-Ergebnisspeicherung.
- **Video-Scatterer**: Frame-Extraktion und Contact-Sheet-Generierung via `ai-media-editor`.

### Ehrlich benannte Lücken & Grenzen (Unverified Boundaries):
- **Echter Anruf (CALL-E)**: **NICHT AUSGEFÜHRT**. Konto-Guthaben steht bei -0.05 USD. Sämtliche Läufe erfolgten im Offline-Trockenlauf (`DryRunCallClient`).
- **Parallelität / Concurrency**: **UNGEPRÜFT**. Die Kaskade läuft strikt sequenziell. Ob CALL-E parallele Anrufe unterstützt, ist serverseitig nicht verifiziert.
- **Akustische Wortlauttreue**: **UNVERIFIZIERT**. Transkripte wurden als Text-Payloads geprüft; Tonfall, Betonung und Sprachqualität der CALL-E-Voicebot-Engine wurden nicht akustisch abgehört.
- **Remote Operations**: `git push`, PR-Erstellung, DevPost-Formularübermittlung per User-Rule **NICHT AUSGEFÜHRT**.

---

## 4. Letzter Pytest-Lauf (Exakter Output)

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.0, pluggy-1.6.0 -- C:\Program Files\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\_Local_DEV\repos\hungrycall
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0, asyncio-1.4.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 35 items

tests/test_budget_and_price_rejection.py::test_budget_limit_exceeded_rejection PASSED [  2%]
tests/test_budget_and_price_rejection.py::test_vague_price_quote_rejection PASSED [  5%]
tests/test_budget_and_price_rejection.py::test_strict_all_budget_exceeded_fails PASSED [  8%]
tests/test_cascade.py::test_cascade_stops_immediately_on_first_success PASSED [ 11%]
tests/test_cascade.py::test_reservation_cascade PASSED                   [ 14%]
tests/test_cascade.py::test_pickup_cascade PASSED                        [ 17%]
tests/test_cascade.py::test_tiered_concessions_cascade PASSED            [ 20%]
tests/test_cli.py::test_cli_delivery_dry_run PASSED                      [ 22%]
tests/test_cli.py::test_cli_delivery_json_output PASSED                  [ 25%]
tests/test_cli.py::test_cli_budget_exceeded_scenario PASSED              [ 28%]
tests/test_cli.py::test_cli_reservation PASSED                           [ 31%]
tests/test_cli.py::test_cli_pickup PASSED                                [ 34%]
tests/test_cli.py::test_cli_live_without_confirm_fails PASSED            [ 37%]
tests/test_cli.py::test_cli_demo_subcommand PASSED                       [ 40%]
tests/test_findings_and_dynamic_fixtures.py::test_dynamic_user_input_reflection_in_transcript PASSED [ 42%]
tests/test_findings_and_dynamic_fixtures.py::test_cli_reflects_custom_user_address PASSED [ 45%]
tests/test_findings_and_dynamic_fixtures.py::test_activity_stt_deduplication PASSED [ 48%]
tests/test_findings_and_dynamic_fixtures.py::test_activity_log_contains_40s_setup_latency_notice PASSED [ 51%]
tests/test_phone_utils.py::test_validate_e164_valid PASSED               [ 54%]
tests/test_phone_utils.py::test_validate_e164_invalid PASSED             [ 57%]
tests/test_phone_utils.py::test_normalize_e164 PASSED                    [ 60%]
tests/test_phone_utils.py::test_mask_phone PASSED                        [ 62%]
tests/test_ranking.py::test_food_prompt_beats_favorite PASSED            [ 65%]
tests/test_ranking.py::test_favorite_wins_when_cuisine_matches PASSED    [ 68%]
tests/test_ranking.py::test_closed_restaurant_filtered_out PASSED        [ 71%]
tests/test_safety.py::test_verify_content_safety_valid PASSED            [ 74%]
tests/test_safety.py::test_verify_content_safety_prohibited_keywords PASSED [ 77%]
tests/test_safety.py::test_verify_phone_safety PASSED                    [ 80%]
tests/test_safety.py::test_verify_live_safety PASSED                     [ 82%]
tests/test_safety.py::test_generate_idempotency_key PASSED               [ 85%]
tests/test_schemas.py::test_get_result_schema_types PASSED               [ 88%]
tests/test_web.py::test_db_order_and_save_result PASSED                  [ 91%]
tests/test_web.py::test_location_geocoding_and_fixtures PASSED           [ 94%]
tests/test_web.py::test_fastapi_web_routes PASSED                        [ 97%]
tests/test_web.py::test_video_backflow_radius_and_budget_band PASSED     [100%]

======================== 35 passed, 1 warning in 1.45s ========================
```

---

## 5. Lokaler Git Commit

Die Änderungen wurden lokal im Repo gepusht-frei committet:
```text
Commit Hash: df69fb1
Message: feat(backflow): integrate video draft UI features into software & harden EVIDENCE audit
Files: EVIDENCE.md, hungrycall/templates.py, hungrycall/web.py, tests/test_web.py, AUFGABEN.txt, TODO.md
```
