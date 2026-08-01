# VIDEO-ENTWURF: Demo-Video Konzept & Storyboard für HungryCall 🍕📞

> **Hackathon-Beitrag**: CALL-E ("Your Code Is Calling")  
> **Projekt**: HungryCall (`hungrycall`) — Web UI: *„I am hungry"*  
> **Ziel-Länge**: ~2:30 Minuten (strikte Vorgabe: **unter 3 Minuten**)  
> **Sprache**: Englisch (Voiceover) + Englische Untertitel  
> **Prinzip**: 100% ehrlich und vorführbar auf Basis der existierenden Codebase (`hungrycall/web.py`, CLI, Leaflet-Karten, SSE-Stream, SQLite). Keine gefakten Animationen oder erfundenen Features.

---

## 1. Storyline (Prosa: 6 Sätze)

In rural and suburban communities, central delivery platforms like Lieferando or DoorDash simply don't exist, forcing hungry residents to manually call restaurant after restaurant just to ask if they deliver. For people who dread phone calls or just want a quick dinner without endless dialing, this friction means eating from the same single spot over and over again. HungryCall solves this by launching an automated, sequential voice-agent cascade that calls local restaurants one by one on your behalf. You set your location, your craving, and a strict doorstep budget cap—then sit back as HungryCall's live map and handset cascade monitor every call in real time. Rather than blindly placing orders, the agent intelligently evaluates each response: if a restaurant doesn't deliver, exceeds your budget, or gives a vague price quote like "around 30 euros depending on the driver," HungryCall politely declines and cascades to the next candidate. The moment a restaurant meets all criteria, HungryCall completes the order, halts all further calls to save costs, and presents a complete verification card with exact total price, delivery ETA, full transcript proof, and a callback number. What used to take 20 minutes of tedious phone calls is reduced to a single click with complete financial safety.

---

## 2. Storyboard (Tabelle)

| Timecode | Visuals on Screen (Bildschirmaufnahme) | Voiceover Script (Wortgenauer englischer Text) | Rationale & Bedientes Kriterium |
|---|---|---|---|
| **0:00 – 0:20** | **Problem-Intro**: Screen recording of standard delivery portal (e.g. Lieferando) returning *"No delivery available in your area"* for a rural postcode. Smooth transition to the clean, dark-mode landing page of HungryCall Web UI (`http://127.0.0.1:8000`). | *"If you live outside a major city, delivery apps don't work for you. Finding out who delivers means calling restaurant after restaurant yourself. If you hate phone calls or worry about surprise costs, you end up ordering from the exact same spot every time. Meet HungryCall."* | **Real World Impact**: Crosses the digital gap for unserved rural areas and addresses authentic telephone friction. |
| **0:20 – 0:45** | **Setup & Budget Guardrails**: User types location (`12345 Dorfstadt`). Interactive Leaflet map loads with glowing center pulse marker and local restaurant pins. User enters craving (*"2x Cheeseburger, 1x Große Pommes, 1x Cola Zero"*) and sets `Max Budget: 35.00 EUR`. Prompt transparency preview box expands. | *"HungryCall geocodes your location and places nearby restaurants on an interactive map. Enter what you're craving and set a hard doorstep budget cap—here, 35 Euros. HungryCall extends agent authority with financial guardrails: it will never overspend your budget."* | **Quality of Idea** & **Product Experience**: Financial safety guardrail architecture; clean zero-build web interface. |
| **0:45 – 1:25** | **Live Cascade & Smart Rejections (Hero Scene)**: User clicks *"Anrufkaskade starten"*. Stationary cards show handset icons (📞).<br>1. Restaurant #1 (*Burger House*) handset turns gray (dialing/setup) -> speech log appears -> **❌ REJECTED** (*Exceeds budget limit 35.00 EUR*).<br>2. Handset moves to Restaurant #2 (*Trattoria Bella Luigi*) -> speech log appears: *"Callee said: about 30 Euros depending on driver"* -> **❌ REJECTED** (*Vague price quote: price_known=false*).<br>3. Handset moves to Restaurant #3 (*Dorf-Grill Express*). | *"Watch the live cascade in action. Restaurant number one quotes 42 Euros. HungryCall detects this exceeds our 35 Euro limit, declines, and moves to the next. Restaurant number two says 'about 30 Euros depending on the driver'. Because guessing prices is strictly forbidden, HungryCall enforces safety and rejects vague price quotes instantly."* | **Technical Implementation** & **Quality of Idea**: Real-time SSE `activity` event parsing, STT draft deduplication, and intelligent decision-making logic. |
| **1:25 – 1:55** | **Success, Early Exit & Proof Card**: Restaurant #3 connects. Speech log confirms delivery for 31.50 EUR in 40 mins. Handset turns green checkmark (✅). Gold-highlighted Result Card pops up. User highlights total price, 40 min ETA, masked callback number (`+49 170 •••• 123`), and clicks *"Protokoll & Transkript anzeigen"* to expand full formatted transcript proof. | *"Candidate number three confirms delivery for 31.50 Euros in 40 minutes. HungryCall completes the order, immediately halts all remaining calls to save costs, and renders a complete result card with exact price, ETA, direct callback number, and full transcript proof."* | **Product Experience and Demo** & **Technical Implementation**: End-to-end user journey, early exit cost optimization, REST result schema validation, and SQLite persistence. |
| **1:55 – 2:25** | **CLI & Technical Architecture**: Cut to terminal. Running `pytest -v` (29 passed in green). Executing CLI command: `hungrycall delivery --food "Burger" --budget 35.0 --scenario vague_price_cascade`. Console displays masked phone numbers, idempotency key generation, and dry-run output. | *"Under the hood, HungryCall is built with Python 3.11, FastAPI, HTMX, and SQLite. It enforces E.164 phone number masking, idempotency safeguards, domain safety filters, and dynamic fixture interpolation. The entire suite runs 100% offline in dry-run mode without requiring API accounts."* | **Technical Implementation**: Robustness, code quality, 29 passing unit tests, CLI entry points, and strict safety compliance. |
| **2:25 – 2:45** | **Outro & Call to Action**: Return to Web UI with *"Guten Appetit!"* toast banner. Final screen with HungryCall logo, tagline *"Your Code Is Calling"*, and GitHub repo link. | *"HungryCall turns telephone friction into effortless, safe, and autonomous food delivery for underserved communities. Thank you for watching!"* | **Product Experience and Demo**: High-impact closing statement. |

---

## 3. Die stärkste Einzelszene (Herzensszene)

* **Benennung**: Szene 3 (Timecode **0:45 – 1:25**) — **Die Ablehnung wegen unklarer Preisauskunft ("Vague Price Rejection") & Budgetüberschreitung in der Live-Kaskade**.
* **Begründung**:
  1. **Zeigt echte Beurteilung statt stumpfes Wählen**: Ein trivialer Dialer würde einfach die Nummer anrufen und auflegen oder unkontrolliert bestellen. HungryCall zeigt in dieser Szene seine **eigentliche KI-Logik und Härtung**: Das System hört zu, parst den Preis und prüft die Verbindlichkeit.
  2. **Perfekte Kombination der Bewertungskriterien**:
     * **Technical Implementation**: Der Zuschauer sieht live im SSE-Stream, wie `activity`-Events verarbeitet, STT-Rohfassungen dedupliziert und gegen Pydantic/Result-Schemas geprüft werden.
     * **Quality of Idea**: Relevante Innovation gegenüber Standard-Agenten (Erweiterung der Agenten-Autorität von Zeitfenstern auf Geldbeträge). Wenn das Restaurant *"ca. 30 Euro je nach Fahrer"* sagt, bewertet HungryCall `price_known: false` und lehnt höflich ab.
     * **Visualisierung**: Das rote ❌-Symbol auf der Karte, das Durchstreichen der Restaurantkarte und das nahtlose Weiterwandern des Telefonhörer-Icons (📞) machen die Kaskaden-Logik sofort greifbar.

---

## 4. Drei Thumbnail-Ideen

1. **Thumbnail 1: "The Cascade in Action"**  
   *Beschreibung*: Dunkles Web-UI Dashboard mit der Leaflet-Karte von Dorfstadt und drei gestapelten Restaurant-Karten: Die erste rot durchgestrichen (❌ Exceeds 35€), die zweite mit gelbem Telefonhörer-Icon (📞 Calling...), im Vordergrund die fette Headline *"Auto-Calling Delivery Cascade"*.

2. **Thumbnail 2: "Financial Guardrail"**  
   *Beschreibung*: Split-Screen-Motiv: Links ein genervter Smartphone-Nutzer mit Telefon am Ohr (*"How much is delivery?"*), rechts das HungryCall Dashboard mit einem prominent schimmernden Badge *"Max Budget: 35.00 € — Guardrail Active"*, grünem Häkchen und Pizzaschachtel-Icon.

3. **Thumbnail 3: "Transcript Verification Proof"**  
   *Beschreibung*: Nahaufnahme der HungryCall Result Card mit gold hervorgehobener Rückrufnummer (`+49 170 •••• 123`) und dem ausgeklappten Transkript-Beleg (*"[00:12] BOT: Delivers to Dorfstraße 10? [00:18] RESTAURANT: Yes, 31.50 EUR"*), flankiert vom CALL-E Logo und dem Slogan *"Your Code Is Calling"*.

---

## 5. Was im Video NICHT gezeigt wird und warum (Ehrlichkeit über Grenzen)

Aus Gründen der Transparenz und Hackathon-Konformität werden folgende Aspekte im Video **ausdrücklich nicht gezeigt** bzw. als bewusste Systemgrenzen benannt:

1. **Kein Eingriff ins laufende Gespräch**: CALL-E bietet keine Live-Interventions-Schnittstelle während eines aktiven Anrufs (kein Mitsprechen oder Live-Inject). Das Video behauptet daher an keiner Stelle, dass der Nutzer in das Telefonat eingreifen kann.
2. **Keine magische Preisprognose vor dem Anruf**: Im ursprünglichen Oberflächen-Konzept (`UI-SPEC.md`) war eine Vorab-Preisschätzung per Menu-Scraping angedacht. Da Speisekarten auf dem Land selten digital vorliegen, ist diese Funktion im gebauten System nicht enthalten. Das Video zeigt ehrlich, dass der Preis erst *während* des Anrufs erfragt und validiert wird.
3. **Keine versteckten Daemons oder Hintergrund-Loops**: HungryCall arbeitet als punktuelle Session. Es gibt keine Daemons, Cronjobs oder versteckten Hintergrundschleifen.
4. **Keine unvermuteten Live-Kosten / Kein gefakter Live-Netzwerk-Anruf**: Der komplette Ablauf ist im Trockenlauf (Dry-Run) vorführbar. Wenn Trockenlauf-Szenen verwendet werden, wird am unteren Bildschirmrand transparent ein Hinweis eingeblendet: *"Demonstrated via offline dry-run engine (100% reproducible fixture)"*.

---

## 6. Aufnahmeliste (Recording Checklist)

### Software & Setup
* **Environment**: Python 3.11+ mit installierter `hungrycall`-Suite (`pip install -e .`).
* **Browser**: Chrome/Firefox im Fullscreen-Modus (1920x1080 resolution).
* **Terminal**: Windows Terminal / bash mit dark theme.
* **Recording Tool**: OBS Studio (1080p, 60fps, crisp typography).

### Vorbereitung im Werkzeug (Prerequisites)
1. Webserver starten via `python run_web.py`.
2. Browser unter `http://127.0.0.1:8000` öffnen.
3. SQLite-Datenbank gegebenenfalls bereinigen (`rm hungrycall.db`), um eine frische Session zu garantieren.
4. Trockenlauf-Schalter in der Header-Leiste aktiviert lassen (Dry-Run Modus = Active).

### Clips & Reihenfolge der Aufnahmen

1. **Clip 1: Problem-Intro (15s)**
   * *Inhalt*: Browser ruft `lieferando.de` auf -> Postleitzahl eingeben -> "Kein Lieferdienst verfügbar".
   * *Zweck*: Zeigt das reale Problem auf dem Land.

2. **Clip 2: Web UI Landing & Suche (25s)**
   * *Inhalt*: Aufruf `http://127.0.0.1:8000`. Formular befüllen: PLZ `12345`, Ort `Dorfstadt`, Land `Deutschland`, Adresse `Dorfstraße 10, 12345 Dorfstadt`, Radius `3.0 km`. Klick auf *"Restaurants suchen"*. Ladeanimation *"Wir suchen für Sie..."*.
   * *Zweck*: Zeigt Geocoding & interaktive Leaflet-Karte mit Puls-Marker.

3. **Clip 3: Konfiguration & Budget-Limit (25s)**
   * *Inhalt*: Modus `delivery` auswählen, Essen: *"2x Cheeseburger, 1x Große Pommes, 1x Cola Zero"*, Max Budget: `35.00 €`. Klick auf *"Anrufkaskade starten"*.
   * *Zweck*: Zeigt die Parametrisierung und die finale Ziel-Prompt-Vorschau.

4. **Clip 4: SSE-Kaskade & Vague Price Rejection (40s)**
   * *Inhalt*: Monitor-Container mit den 3 Restaurant-Karten.
     * Restaurant #1 (*Burger House*): Hörer grau -> rot ❌ (*Exceeds budget limit*).
     * Restaurant #2 (*Trattoria Bella Luigi*): Hörer grau -> rot ❌ (*Vague price quote*).
     * Restaurant #3 (*Dorf-Grill Express*): Hörer grau -> grün ✅.
   * *Zweck*: Die Kernszene (Hero Scene) der Kaskade.

5. **Clip 5: Result Card & Transkript (30s)**
   * *Inhalt*: Einblendung der Result Card. Hover/Cursor-Fokus auf Betrag (31.50 €), ETA (40 Min), hervorgehobene Rückrufnummer (`+49 170 •••• 123`). Klick auf *"Protokoll & Transkript anzeigen"*, Scrollen durch das formatierte Gesprächsprotokoll. Klick auf *"In SQLite speichern"*.
   * *Zweck*: Nachweis des vollständigen Ablaufs und der SQLite-Persistenz.

6. **Clip 6: Terminal CLI & Unit Tests (20s)**
   * *Inhalt*: Wechsel ins Terminal. Ausführen von `pytest -v` (29 passed in grün). Ausführen des CLI-Befehls `hungrycall delivery --food "Burger" --budget 35.0 --scenario vague_price_cascade`.
   * *Zweck*: Nachweis der technischen Korrektheit, Testabdeckung und CLI-Bedienbarkeit.

7. **Clip 7: Outro & Toast (10s)**
   * *Inhalt*: Web UI Endbildschirm mit *"Guten Appetit!"* Toast-Notification. Fade to Black.

---

## 7. Abgrenzung: Trockenlauf (Dry-Run) vs. Echter Anruf

| Clip Nr. | Inhalt | Modus | Transparenz-Kennzeichnung im Video |
|---|---|---|---|
| **Clip 1** | Portal-Vergleich | Realer Browseraufruf | Keine Kennzeichnung nötig |
| **Clip 2** | Suche & Karte | Dry-Run (Offline OSM Fixtures) | Live UI |
| **Clip 3** | Formular & Budget | Dry-Run UI | Live UI |
| **Clip 4** | Kaskade & Rejections | Dry-Run Engine (`vague_price_cascade`) | **Einblendung**: *"Demonstrated via offline dry-run engine (100% reproducible fixture)"* |
| **Clip 5** | Result Card & Transkript | Dry-Run Engine & SQLite | Live UI & DB-Persistenz |
| **Clip 6** | CLI & Pytest | Dry-Run CLI & Pytest | Live Terminal |
| **Clip 7** | Outro | Dry-Run UI | Live UI |

> **Hinweis zur Durchführung**: Das gesamte Video kann **ohne CALL-E-Konto und ohne Kosten** gedreht werden, da die Dry-Run-Engine (`hungrycall/fixtures.py`) alle Szenarien (Budgetüberschreitung, unklare Preisauskunft, Erfolg) dynamisch mit den Nutzereingaben durchspielt. Sollten vor dem Hackathon-Submit echte Anrufe mit einem Live-API-Key getätigt werden, kann Clip 4 durch eine echte Gesprächsaufzeichnung ausgetauscht werden, wobei die E.164-Rufnummernmaskierung unverändert beibehalten wird.
