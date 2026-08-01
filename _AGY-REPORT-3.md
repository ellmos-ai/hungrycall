# HungryCall Web UI Implementation Report — Antigravity Agent (_AGY-REPORT-3.md)

**Datum**: 2026-08-01  
**Repository**: `C:\_Local_DEV\repos\hungrycall`  
**Framework**: FastAPI + HTMX + SQLite + Leaflet (OpenStreetMap)  
**Status**: 100% Erfolgreich abgeschlossen, alle 32 Tests grün, lokal committet.

---

## 1. Was gebaut wurde (Implementierte Komponenten)

Aufbauend auf der bestehenden CLI, Engine und Safety-Architektur wurde eine vollständige, leichtgewichtige Weboberfläche ohne Build-Schritt, ohne Frontend-Framework und ohne npm umgesetzt:

1. **Ort & Adresse (Internationale Ortssuche)**:
   - Eingabe von PLZ, Ort, Land, Lieferadresse und Umkreis (km) in `hungrycall/location.py`.
   - Unterstützt deutsche und internationale Standorte (z. B. Singapore für den CALL-E Hub, London, New York) mit Geocoding (`geocode_location`) und Overpass-API der OpenStreetMap.
   - 100% offline-fähig durch integrierte Fixture-Pools für Vorführungen ohne Internet.

2. **Suche mit Wartezustand**:
   - Animierter Pulsier-Indikator mit Hinweistext *"Wir suchen für Sie die besten Essenspunkte..."* während der Suche.

3. **Dauerhaft sichtbare Karte (Leaflet + OpenStreetMap)**:
   - Der Nutzer sitzt als leuchtender blauer Puls-Punkt im Zentrum (aus der Zieladresse).
   - Gefundene Restaurants ordnen sich auf der Karte an.
   - Bündelung lokaler Statik-Dateien (`htmx.min.js`, `htmx-sse.js`, `leaflet.js`, `leaflet.css` in `hungrycall/static/`), um 100% offline-fähig zu sein.

4. **Restaurantauswahl & Priorisierung**:
   - Hinweistext gemäß `UI-SPEC.md` (*"Wir rufen alle an und prüfen zuerst, ob sie liefern können..."*).
   - Sichtbarer Umschalter für geschlossene Restaurants mit Zähler (*"X vermutlich geschlossene Restaurants ausgeblendet"*).
   - Reordering-Steuerung (Priorisierung per Drag-&-Drop / Up-Down-Tasten).

5. **Modus & Essenswunsch**:
   - Auswahl zwischen **Lieferung**, **Abholung** und **Tisch reservieren**.
   - Freitextfeld für Essenswünsche (z. B. *"2x Cheeseburger, 1x Große Pommes, 1x Cola Zero"*).
   - Eingabe des Höchstbetrags (€ an der Haustür als harte Obergrenze).

6. **Prompt-Vorschau (Transparenz vor Absenden)**:
   - Vorschau-Box zeigt den exakten `goal`-Text für CALL-E vor dem Auslösen der Kaskade.

7. **Die Kaskade Live (SSE Server-Sent Events)**:
   - Stationäre Restaurantliste mit wanderndem Telefonhörer-Symbol 📞.
   - **Grau (mit Pulsing-Animation)**: Vorbereitung / ~40s Vorlaufzeit (sichtbare Wartezeit, kein hängendes Programm).
   - **Grün**: Gespräch steht, Live-Activity-Stream mit STT-Entwürfen.
   - **Rot / Durchgestrichen**: Abbruch / Kriterium nicht erfüllt / abgelehnt; Hörer wandert weiter.
   - **Erfolg**: Grüne Bestätigungs-Badge, übrige Kandidaten ausgegraut.
   - **Jederzeit erreichbarer Abbrechen-Knopf** (`/api/cancel-cascade`).

8. **Ergebniskarte & SQLite-Speicherung**:
   - Vorlesbarer großer Satz: *"Erfolgreich bestellt bei Burger House Dorfstadt! Das Essen kommt in ca. 35 Minuten."*
   - Betrag, Lieferzeit (ETA) und **prominente Rückrufnummer des Restaurants** (`+49 ... ..1111`).
   - Aufklappbares vollständiges Gesprächsprotokoll (Transkript).
   - **Speichern-Knopf**: Speichert die erfolgreiche Bestellung dauerhaft in der SQLite-Datenbank (`hungrycall.db`).

9. **Safety & Design-Vorgaben**:
   - Trockenlauf als Normalfall (`dry_run=true`).
   - Echter Anruf optisch anders markiert (mit Kostenhinweis `$0.05 / Anruf` und Anrufzähler).
   - Rufnummern in der Oberflaeche durchgehend maskiert (`+49 ... ..123`).
   - Keine Zugangsdaten in der Oberflaeche; Schlüssel nur aus Umgebungsvariable.

---

## 2. Welche Tests mit welcher echten Ausgabe ausgeführt wurden

Die Pytest-Suite wurde erweitert (`tests/test_web.py`) und deckt die SQLite-Datenbank, Geocoding, Overpass-Fixtures und FastAPI-Routen ab.

### Befehl:
```powershell
python -m pytest -v
```

### Echte Testausgabe:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.0, pluggy-1.6.0
rootdir: C:\_Local_DEV\repos\hungrycall
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0, asyncio-1.4.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False
collected 32 items

tests\test_budget_and_price_rejection.py ...                             [  9%]
tests\test_cascade.py ...                                                [ 18%]
tests\test_cli.py ......                                                 [ 37%]
tests\test_findings_and_dynamic_fixtures.py ....                         [ 50%]
tests\test_phone_utils.py ....                                           [ 62%]
tests\test_ranking.py ...                                                [ 71%]
tests\test_safety.py .....                                               [ 87%]
tests\test_schemas.py .                                                  [ 90%]
tests\test_web.py ...                                                    [100%]

======================== 32 passed, 1 warning in 1.95s ========================
```

---

## 3. Was offen blieb (Bewusst zurückgestellt laut SPEC)

Wie in der `UI-SPEC.md` und Aufgabenstellung vorgeschrieben, wurden folgende Punkte bewusst zurückgestellt, jedoch so strukturiert, dass sie später aufgenommen werden können:
- Personenprofile mit Vorlieben/Allergien ("keine Oliven")
- Countdown mit "Guten Appetit"-Endanimation
- Automatische E-Mail-Belegversendung via IMAP/SMTP
- KI-generierte Speisekartenauswertung & PDF-Scraping
- KI-generierte Küchensymbole (Custom SVG markers)
- WhatsApp / IM-Connector integration

---

## 4. Starten der Oberflaeche

Die Oberflaeche kann lokal mit einem einzigen Befehl gestartet werden:
```bash
python run_web.py
# oder
hungrycall-web
```
URL im Browser: `http://127.0.0.1:8000`
