# HungryCall Strukturreparatur — 2026-08-03

## Umfang und Sicherheitsgrenzen

- Ausgangszustand: sauberer Arbeitsbaum, Branch `main`, 12 lokale Commits vor `origin/main`.
- Baseline vor der Änderung: `163 passed, 1 warning`.
- Es wurde kein echter Anruf ausgeführt, kein CALL-E-POST gesendet und nichts gepusht.
- Der laufende Server auf Port 8000 wurde nur gelesen. Für die Abschlussprüfung lief ein frischer Server auf Port 8013 und wurde danach im selben Prozess sauber beendet.
- Ein echter Browser stand der Chrome-Steuerung in dieser Sitzung nicht zur Verfügung (`browsers.list()` ergab keine Browserinstanz). Deshalb gibt es keinen erfundenen Browser-Konsolenbefund. Stattdessen wurden Asset-HTTP-Antworten, JavaScript-Syntax und die Leaflet-Initialisierung in einem DOM-Laufzeittest geprüft.

## 1. Karte wird nicht angezeigt

### Echte Ursache

Leaflet selbst war nicht verschwunden:

- `/static/leaflet.js` und `/static/leaflet.css` antworteten auf dem laufenden Server mit HTTP 200.
- `#map` war im HTML vorhanden und hatte weiterhin eine Höhe von 460 px.
- `app.js` wurde vor dem verzögert geladenen Leaflet-Skript eingebunden, rief die Karte aber erst später über `HC.initCandidates()` auf; diese Reihenfolge verursachte keinen direkten Fehler.

Der strukturelle Defekt lag in der Erfolgskopplung: `HC.initMap()` beziehungsweise `HC.initCandidates()` wurde nur im Kandidatenfragment einer erfolgreichen Restaurantsuche ausgegeben. Bei einem Overpass-Fehler oder wenn alle gefundenen Restaurants durch Öffnungszeit beziehungsweise Bedingungen herausfielen, kam das Fragment ohne Karteninitialisierung zurück. Genau der gleichzeitig defekte Restaurantdienst ließ die Karte deshalb ebenfalls verschwinden.

### Reparatur

- Nach erfolgreicher Geokodierung wird die Karte auch bei einem Restaurantdienstfehler mit Mittelpunkt und gewähltem Radius initialisiert.
- Auch bei null derzeit geeigneten Kandidaten bleiben Radius-Karte, echte Restaurantquelle und die aufklappbaren Ausschlussgründe sichtbar.
- Der bestehende hell-weiß/blau/lila/pinke Stil mit grasgrünem Akzent blieb unverändert; hinzu kamen nur funktionale Zustände.
- Ein neuer JavaScript-Laufzeittest lädt `app.js` in einem kontrollierten DOM, erzeugt Leaflet-Karte, OSM-Layer, Mittelpunkt und einen Kreis mit 4.500 m Radius.

### Beleg

- Python: `59 passed, 1 warning` in den fokussierten Web-/Suchtests.
- JavaScript: `12 passed`, darunter die neue Leaflet-Initialisierung ohne JavaScript-Ausnahme.
- Frischer HTTP-Smoke-Test: `/order` HTTP 200, `id="map"` vorhanden; die Fixture-Suche liefert `HC.initCandidates(...)`.
- Der Regressionstest für einen vollständig herausgefilterten Pool erhält `HC.initMap(52.52, 13.405, 3.0, [])` und die Ausschlussgründe.

## 2. Restaurantdienst funktioniert nicht

### Empirischer Befund mit echter deutscher Adresse

Verwendete Suche: `16321 Bernau bei Berlin Deutschland`, Radius 3 km.

Nominatim antwortete am 2026-08-03 wirklich:

```text
HTTP 200 in 777 ms
Content-Type: application/json; charset=utf-8
lat: 52.6908773
lon: 13.5823608
display_name: 16321, Ladeburg, Bernau, Barnim, Brandenburg, Deutschland
type: postal_code
```

Nominatim war damit weder die Ursache noch war der Radius falsch.

Der bisherige Overpass-POST ohne identifizierenden Header antwortete wirklich:

```text
HTTP 406 Not Acceptable in 288 ms
Content-Type: text/html; charset=iso-8859-1
An appropriate representation of the requested resource could not be found on this server.
```

Derselbe Query mit einem identifizierenden HungryCall-`User-Agent` und `Accept: application/json` antwortete bei der ersten Gegenprobe wirklich mit HTTP 200 in 3.396 s. Die JSON-Antwort nannte `Overpass API 0.7.62.11` als Generator und enthielt reale OSM-Elemente, darunter einen anrufbaren Betrieb; seine Rufnummer wurde hier absichtlich maskiert. Eine spätere Wiederholung lieferte außerdem ehrlich HTTP 504 mit:

```text
runtime error: ... Dispatcher_Client::request_read_and_idx::timeout.
The server is probably too busy to handle your request.
```

Die reproduzierbare interne Ursache war also der fehlende Request-Identifier, der HTTP 406 auslöste. HTTP 504 bleibt ein möglicher externer Überlastungszustand und wird nicht als „behoben“ ausgegeben.

### Reparatur

- Nominatim und Overpass verwenden nun gemeinsam:
  - `User-Agent: HungryCall/0.1.0 (+https://github.com/lukisch/hungrycall)`
  - `Accept: application/json`
- Es gibt weiterhin keinen stillen Rückfall auf Beispieldaten. 406, 504, Timeout, ungültiges JSON und null anrufbare Ergebnisse bleiben unterscheidbare Fehler.
- OSM-Rufnummern werden aus üblichen Schreibweisen wie Leerzeichen, Schrägstrichen, Klammern, nationalem Präfix oder mehreren Nummern auf eine geprüfte E.164-Nummer normalisiert. Unbrauchbare Metadaten werden nicht als anrufbarer Kandidat ausgegeben.
- Unmittelbar vor einem möglichen Live-Payload wird die Nummer erneut normalisiert und geprüft; getestet wurde ausschließlich mit einem gemockten Transport, ohne Anruf.

### Beleg

- Der Header-Regressionstest erfasst URL, `User-Agent`, `Accept` und den Overpass-Query.
- Ein OSM-Fixture mit `03338 / 60 49 63` wird zu `+493338604963` normalisiert.
- Der gemockte CALL-E-Payload erhält aus `+49 170 1234567` ausschließlich `+491701234567`.
- Der frische reale App-Pfad für Bernau antwortete nach der Reparatur in 6.907 s ohne Restaurantdienstfehler. Er fand einen Pool, filterte dessen Kandidaten zur aktuellen Uhrzeit aber als nicht geeignet; dieser Zustand zeigt jetzt Karte und Ausschlussgründe statt einer scheinbar toten Suche.

## 3. Testmodi an die richtige Stelle

### Echte Ursache

Der Restaurant-Testmodus war ein dauerhaft sichtbares Kontrollkästchen mitten im Bestellformular. `test_mode=yes` wurde wie ein Bestellwert durch Folgeformulare getragen. Dadurch war der Modus weder ein klarer Arbeitsbereich noch installationsweit abschaltbar; ein direkter Formular-POST konnte ihn zudem ohne den vorgesehenen UI-Schritt aktivieren.

Beim echten Smoke-Test zeigte sich eine zweite Ursache: Selbst der Fixture-Modus verwendete die reale Uhrzeit. Nachts wurden deshalb sämtliche Beispiele als geschlossen herausgefiltert und der ausdrücklich aktivierte Testmodus blieb funktionslos.

### Reparatur

Nach dem funktionierenden ResearchCall-Muster ist der Testmodus jetzt ein separater Seitenmodus:

- sichtbarer Banner oberhalb der Arbeitsfläche;
- eigener POST-Schalter „Testmodus einschalten“;
- im aktiven Zustand eigener Knopf „Testmodus verlassen“;
- HttpOnly-Cookie mit `SameSite=Lax`, kein Bestellfeld;
- abgesicherter Rücksprung nur zu `/`, `/order` oder `/reserve`;
- `HUNGRYCALL_RESTAURANT_TEST_MODE=off` entfernt Banner und Umschalter vollständig und ignoriert alte Cookies;
- `on` schaltet das Feature ausdrücklich frei; ohne Variable bleibt es für diesen Evaluations-Build verfügbar;
- Fixture-Modus verwendet kohärent Freitag 19:00, damit die Demonstration nicht von der realen Uhrzeit abhängt;
- echte Anrufe bleiben mit Restaurant-Fixtures weiterhin hart gesperrt.

### Beleg

Der frische HTTP-Smoke-Test auf Port 8013 ergab:

```text
/order: HTTP 200
Kartencontainer: vorhanden
Bestellfeld name="test_mode": nicht vorhanden
Banner zunächst: off
Toggle: HTTP 303
Cookie: HttpOnly
Banner danach: active
Fixture-Suche: HTTP 200
Kandidatenreihenfolge: vorhanden
Karteninitialisierung: vorhanden
```

Zusätzliche Tests beweisen Ausschalten, erneutes Einschalten, installationsweites Entfernen, Ignorieren alter Cookies, Netzwerkfreiheit und die Sperre der Kombination Fixture-Restaurants plus Live-Anruf.

## 4. Allgemeine Bugsuche und Codeverbesserung

### Bugsweep-Messung

- Produktiver Umfang: 8.405 Zeilen in den Python-Modulen sowie den eigenen `app.js`-/`huckepack.js`-Dateien.
- Sweep-Faktor: `ceil(8405 / 1500) = 6`.
- Geforderte Ground-Rate: 18 eindeutig benannte fehlerfreie Prüfflächen nach den bekannten Reparaturen.

Geprüfte Flächen:

1. CLI-Trockenlauf und doppelte Live-Bestätigung
2. CALL-E-Preflight ohne POST
3. REST-Payload, Idempotency-Key und Polling-Endzustände
4. Schlüsselmaskierung und request-lokale Schlüsselbindung
5. Inhalts-, Rufnummern- und Live-Safety
6. Delivery-, Pickup- und Reservierungs-Ergebnisschemata
7. lokale SQLite-Speicherung und parametrisierte Zugriffe
8. browsergebundene Huckepack-Snapshots
9. Huckepack-Session- und Eigentumsgrenzen
10. Kaskadenabbruch, Ablehnung und Erfolgsauswertung
11. Bestellketten-Parsing und Reaktionslogik
12. Öffnungszeiten, Modusfilter, Distanz und Ranking
13. FastAPI-Routen gegen alle Template- und JavaScript-Requests
14. Template-`HC.*`-Aufrufe gegen vorhandene JavaScript-Funktionen
15. Leaflet-Karte, Radius und Kandidatenpins
16. deutsche/englische Übersetzungsschlüssel und Mojibake-Suche
17. Fixture-Isolation und Modellvalidierung
18. Servermodus-Schalter und bewusst nicht implementierter Mitgliedschaftsmodus

### Suche nach Attrappen und Stubs

Die systematische Suche nach `TODO`, `FIXME`, `NotImplemented`, `placeholder`, `stub`, leeren `pass`-Blöcken und scheinbaren Frontend-Aktionen ergab keine weitere vorgetäuschte Produktfunktion:

- `CallClient.execute_candidate_call()` ist die abstrakte Transportgrenze; beide verwendeten Implementierungen sind vorhanden.
- `pay-membership` ist bewusst nicht gebaut und wird vom Middleware-Gate sichtbar abgelehnt. Es erscheint nicht als funktionierender Modus.
- Alle gefundenen Template-Aktionen haben eine vorhandene JavaScript-Funktion.
- Alle geprüften Frontend-Requests haben eine vorhandene Serverroute.

Zusätzlich zu den vier Nutzerbefunden wurden drei reale Randdefekte beseitigt: unnormalisierte OSM-Rufnummern, uhrzeitabhängig unbrauchbarer Fixture-Modus und verschwundene Karte bei vollständig herausgefilterten Kandidaten.

## Abschlussbelege

```text
python -X utf8 -m pytest -q -p no:cacheprovider ...
169 passed, 1 warning in 16.43s

node --test tests/app_js.test.js tests/huckepack_js.test.js
12 passed, 0 failed

python -X utf8 -m compileall -q hungrycall
Exit 0

node --check hungrycall/static/app.js
Exit 0

node --check hungrycall/static/huckepack.js
Exit 0

git diff --check
Exit 0 (nur erwartete LF/CRLF-Hinweise)
```

Die verbleibende Testwarnung stammt aus der vorhandenen FastAPI-TestClient-Abhängigkeit: Starlette meldet die Nutzung von `httpx` zugunsten von `httpx2` als veraltet. Sie ist kein fehlgeschlagener Test.

## Git-Status und Blocker

Der geforderte regelmäßige lokale Commit wurde direkt nach der ersten Kartenreparatur versucht. Git antwortete wörtlich:

```text
fatal: Unable to create 'C:/_Local_DEV/repos/hungrycall/.git/index.lock': Permission denied
```

Die `.git`-Metadaten sind in dieser Sitzung nur lesbar. Deshalb konnte kein lokaler Commit erzeugt werden; ein erneutes blindes Staging wurde nicht versucht. Es gab keinen Push. Der Arbeitsbaum enthält ausschließlich die hier beschriebenen Repo-Änderungen; temporäre Testdaten und der Arbeits-Lock wurden entfernt.
