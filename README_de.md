![I am hungry](banner.png)

# HungryCall 🍕📞

**[English](README.md) · Deutsch**

> **Einreichung zum CALL-E-Hackathon („Your Code Is Calling")**
>
> Automatisierte Sprachagenten-Kaskade für Lieferung, Tischreservierung und Abholung,
> aufgebaut auf dem **verallgemeinerten Kaskadenmuster** (`MUSTER.md`).

HungryCall löst ein Problem, das es auf dem Land und am Stadtrand wirklich gibt: Die
Gaststätten vor Ort stehen auf keiner Lieferplattform. Wer wissen will, wer liefert, wo ein
Tisch frei ist oder was es an der Haustür am Ende kostet, ruft einen nach dem anderen an.
HungryCall macht daraus **eine Kaskade, die abbricht, sobald ein Kandidat alle Bedingungen
erfüllt**.

---

## 💡 Das verallgemeinerte Kaskadenmuster (der eigentliche Beitrag)

Essen ist nur die Vorführung. Wiederverwendbar ist das Muster dahinter (`MUSTER.md`):

```
Absicht & Grenzen  ──>  Kandidaten ranken  ──>  Kaskade mit Urteilsvermögen
                                                       │
                                    ┌──────────────────┴──────────────────┐
                                    ▼                                     ▼
                             Grenze verletzt                        alles erfüllt
                    (über Budget / Preis nur geschätzt)        (bestellen / reservieren)
                                    │                                     │
                          höflich beenden,                       restliche Anrufe
                          nächster Kandidat                      sofort einstellen
```

### Warum das Muster trägt

In vielen Alltagslagen braucht jemand eine Leistung von **einem aus mehreren** Anbietern,
kann Verfügbarkeit, Preis und Bedingungen aber nur telefonisch klären — nacheinander.
Dieselbe Kaskade passt auf:

* **Zahnarzttermin, dringend** — freier Termin im Umkreis von 30 km, erst Kassenleistung,
  private Zuzahlung nur, wenn es anders nicht geht.
* **Werkstatt** — Bremsen noch vor dem Wochenende.
* **Ersatzteil** — wer hat das Teil im Regal?
* **Kurzzeitpflege** — freier Platz bei einem der Träger vor Ort.

### Die vier Arten von Kriterien

Anders als ein Wählskript unterscheidet HungryCall in jedem Gesprächsschritt vier Stufen:

* **Pflicht** — nicht verhandelbar; ohne das scheitert der Anruf.
  *Beispiel: „muss an Adresse X liefern"; im Gesundheitsfall: „höchstens 30 km".*
* **Grenze** — harte Obergrenze; wird sie überschritten, lehnt der Agent höflich ab.
  *Beispiel: „Endpreis an der Haustür ≤ 35,00 €"; sonst: „Zuzahlung ≤ 50,00 €".*
* **Zugeständnis** — bedingte Nachgiebigkeit, die der Agent **zurückhält** und erst
  ausspielt, wenn der Hauptweg scheitert.
  *Beispiel: „15 Minuten längere Lieferzeit, wenn es günstiger wird"; sonst:
  „Privatzuzahlung nur, wenn kein Kassentermin frei ist".*
* **Wunsch** — sortiert die Reihenfolge vorab, blockiert aber nichts.
  *Beispiel: „lieber Holzofen"; sonst: „lieber Praxis mit 4+ Sternen".*

Ein Zugeständnis, das nicht ausdrücklich erteilt wurde, darf der Agent nicht ausgeben. Tut
er es doch, wird das Ergebnis verworfen — er hat Vollmacht ausgegeben, die er nicht hatte.

---

## ❓ Warum nicht einfach die CALL-E-App?

Benutz sie. Für **einen** Anruf ist der CALL-E-Chat schneller als alles, was man hier bauen
könnte. HungryCall tritt nicht an seine Stelle.

Der Unterschied ist die Menge, nicht der Anruf:

* **Vorbereitung** — Adressen geokodieren, geschlossene Betriebe nach Öffnungszeiten
  aussortieren, Kandidaten nach Wunsch und Entfernung ranken.
* **Früher Ausstieg** — die Kaskade endet in der Sekunde, in der ein Kandidat alles
  erfüllt. Das spart Anrufe und verhindert Doppelbestellungen.
* **Finanzielle Vollmacht** — der Agent kann das Budget nicht überschreiten, weil die
  Grenze vor dem Anruf feststeht und nicht im Gespräch ausgehandelt wird.
* **Kein geschätzter Preis** — „ungefähr 30 Euro, kommt auf den Fahrer an" ist kein Preis.
  Solche Auskünfte werden als `price_known: false` verworfen.
* **Beleg** — Transkript mit Zeitmarken (`[mm:ss] BOT: …`) als Nachweis der mündlichen
  Abrede, dazu die maskierte Rückrufnummer.

## Bestellwunschketten

Eine Bestellung ist keine unstrukturierte Wunschliste. Sie besteht aus **Posten**, deren
Zellen von links nach rechts Wunsch und Ersatzwünsche bilden. Jede Zelle trägt Menge,
Produkt, die Art Essen/Getränk und beliebig viele Zusatzkriterien:

- `hoechstpreis`, `sonderwunsch` oder `rueckfrage`
- Reaktion `annehmen`, weich zum `naechster_ersatz` wechseln oder den Posten hart
  `ablehnen`
- Zeilenregel: den Posten weglassen oder die gesamte Bestellung abbrechen

Dieselbe JSON-Definition zeichnet den Editor, erzeugt die Gesprächsanweisung und prüft die
strukturierte Agentenantwort. Frei angelegte Tags gruppieren die Abschlussübersicht. Ganze
Ketten lassen sich als Vorlagen speichern; jede abgeschickte Bestellung kann aus dem Verlauf
geladen, geändert und erneut durch den Trockenlauf geschickt werden.

---

## Kernprobe für Juroren — 30 Sekunden, ohne Zugang

Ein Befehl, kein Konto, kein API-Schlüssel, kein Netz:

```bash
pip install -e .
hungrycall demo
```

Die Kaskade läuft komplett durch: Kandidat 1 abgelehnt (über Budget), Kandidat 2 abgelehnt
(Preis nur geschätzt), Kandidat 3 erfüllt alles, die restlichen Kandidaten werden **nicht**
mehr angerufen — und am Ende steht das Transkript als Bestellbeleg.

> `python -m hungrycall` funktioniert **nicht**; das Paket hat keinen `__main__`-Einstieg.
> Nach `pip install -e .` steht der Befehl `hungrycall` zur Verfügung.

---

## Installation

Voraussetzungen: Python 3.11+, für die Testsuite `pytest`.

```bash
git clone https://github.com/lukisch/hungrycall.git
cd hungrycall
pip install -e .
```

Für den Trockenlauf wird kein Zugang gelesen. Der Live-Adapter nimmt den Schlüssel
zuerst aus `CALLE_API_KEY` oder `IAM_API_KEY`, ersatzweise aus einer externen
`.env`-Datei (`CALLE_ENV_FILE` beziehungsweise `--env-file`). Auf diesem Rechner liegt
sie hier:

```text
C:\_Local_DEV\CREDENTIALS\call-e\call-e.env
```

Nur dieser Pfad darf genannt werden. Der Wert gehört nie in Repo, Doku, Bericht,
Kommandozeile oder Commit.

## Benutzung

```bash
# Lieferung, eigene Adresse, eigenes Budget
hungrycall delivery --food "2x Döner Kebab" --address "Dorfstrasse 1, 16321 Bernau" \
  --budget 30.0 --scenario success_direct

# Tisch reservieren
hungrycall reservation --food "Italian" --date "2026-08-05" --time "19:00" --party 4 \
  --scenario reservation_cascade

# Tisch draußen — und wozu man bereit wäre.
# Ohne erteiltes Zugeständnis wird der Innentisch des Agenten verworfen:
hungrycall reservation --food "Italian" --date "2026-08-07" --time "19:00" --party 4 \
  --seating outdoor --scenario table_concession_cascade
# Mit erteiltem Zugeständnis geht derselbe Anruf durch, und das Ergebnis nennt die Stufe:
hungrycall reservation --food "Italian" --date "2026-08-07" --time "19:00" --party 4 \
  --seating outdoor --concession indoor_ok --scenario table_concession_cascade

# Abholung
hungrycall pickup --food "Pizza" --budget 25.0 --scenario pickup_cascade

# Ablehnung wegen Budget bzw. wegen geschätztem Preis vorführen
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" \
  --budget 35.0 --scenario budget_exceeded_cascade
hungrycall delivery --food "Burger" --address "Hauptstraße 12, 12345 Dorfstadt" \
  --budget 35.0 --scenario vague_price_cascade

# Authentifizierung read-only prüfen; keine Rufnummer, kein POST, kein Anruf
hungrycall preflight
```

Der Preflight sendet ausschließlich ein authentifiziertes
`GET /v1/calls/probe-does-not-exist`; HTTP 404 ist der erwartete Erfolgsfall. Ein echter
Lauf würde zusätzlich `--live --confirm-live` benötigen. Bei negativem Guthaben nicht
ausführen.

### Weboberfläche

```bash
python run_web.py          # oder: hungrycall-web
```

Danach `http://127.0.0.1:8000` öffnen. FastAPI, HTMX, SQLite und Leaflet — kein Bundler,
kein Build-Schritt, kein CDN. Zwei Zweige starten auf der Startseite und enden beide in
derselben Kaskade, nur mit anderen Kriterien. Oberfläche vollständig auf Deutsch und
Englisch; `tests/test_i18n.py` lässt den Build scheitern, wenn ein Schlüssel fehlt, eine
Sprache eine Lücke hat oder ein `{platzhalter}` bei der Übersetzung verloren geht.

Das Farbschema startet **hell**: weiße Flächen, Kobaltblau, Lila und Pink. Grasneongrün
bleibt auf einzelne Live- und Erfolgsakzente beschränkt. Der Schalter im Kopf wechselt
zu einem dunklen Zweitmodus und speichert ausschließlich diese Auswahl in
`localStorage`. Ohne gespeicherte Wahl startet jede Seite hell. Die lebendige
Routen-Optik unterscheidet HungryCall bewusst von der ruhigen Papier-Optik von
ResearchCall.

---

## Am echten Dienst gemessen

Diese Punkte stammen aus einem echten Anruf am 2026-08-01, nicht aus der Doku — mehrere
widersprechen ihr:

1. **`status` taugt nicht als Fortschrittsanzeige.** Das Feld blieb während des laufenden
   Gesprächs auf `PREPARING` und wechselte erst nach Gesprächsende auf `COMPLETED`.
   HungryCall liest den Fortschritt deshalb aus `activity`.
2. **Die Spracherkennung streamt und korrigiert sich selbst.** Dieselbe Zeile kommt zweimal
   — grob, dann korrigiert. Zwischenstände werden entdoppelt.
3. **Rund 40 Sekunden Vorlauf je Anruf**, bevor überhaupt ein Wort fällt, unabhängig von
   der Gesprächsdauer. Die Kosten fallen pro Anruf an, nicht pro Minute.
4. **Schema-Ergebnisse gibt es nur über REST.** `plan_call` über MCP/CLI kennt kein
   `result_schema`, und ein über MCP gestarteter Anruf ist über REST gar nicht abrufbar —
   getrennte ID-Räume.

---

## Datenfluss und Datenschutz

> ⚠️ **Hinweis zur Datenübermittlung**
> Der Sprachagent von CALL-E läuft auf AiRudder-Infrastruktur in **Singapur**
> (`https://seleven-mcp-sg.airudder.com`).
>
> Bei einem echten Anruf gehen die Parameter des Auftrags (Name, Lieferadresse, Bestellung)
> dorthin. HungryCall hält Datensparsamkeit ein:
> * Nur das Nötigste für genau diesen einen Anruf wird übergeben.
> * Keine Vorgeschichte, kein dauerhaftes Profil.
> * Rufnummern sind in allen Ausgaben, Protokollen und Zusammenfassungen maskiert
>   (`+49 ••• ••••123`).

## Sicherheit

* **Der Anruf-Trockenlauf ist der Normalfall.** Ohne ausdrückliches `--live` und
  `--confirm-live` nutzt die Anrufkaskade lokale Fixtures und braucht kein CALL-E-Konto.
  Die Restaurantquelle ist davon getrennt: Im Web fragt der Normalbetrieb
  OpenStreetMap ab; nur ein ausdrücklich gewählter Restaurant-Testmodus ist vollständig lokal.
* **Nur auf ausdrückliche Handlung** wird gewählt.
* **E.164-Prüfung** jeder Zielnummer vor dem Wählen.
* **Rufnummern-Maskierung** in Konsole, JSON-Berichten und Zusammenfassungen.
* **Keine Zugangsdaten im Code oder Log** — Prozess-Umgebung oder eine externe
  `.env`-Datei außerhalb des Repos; die Umgebung hat Vorrang.
* **Keine versteckten wiederkehrenden Zeitpläne** — ein CLI-Lauf, kein Daemon, keine
  Endlosschleife.
* **Idempotenzschlüssel** je Anruf (`hungrycall-<modus>-<id>-<hash>`) gegen Doppelanrufe.
* **Inhaltsgrenzen** — Aufträge mit medizinischen, rechtlichen, finanziellen oder
  Notfallbezügen werden vor der Planung abgewiesen.
* **Sauberer Abbruch** — `Strg+C` beendet den Lauf und erhält den Stand.

---

## Grenzen — was das Werkzeug nicht kann

Die Oberfläche schreibt das dort hin, wo man arbeitet, statt es zu verstecken:

* **Echte Anrufe sind mehrfach gegattert und werden aktuell vom Dienst abgelehnt.**
  Trockenlauf ist vorausgewählt. Im Web braucht Live zusätzlich ein Bestätigungshäkchen,
  im CLI `--live` und `--confirm-live`. Die Warnung „Echte Anrufe — kostet Geld“ ist
  sichtbar. Bei derzeit −0,05 USD lehnt CALL-E echte Anrufe ab.
* **Die Restaurantquelle ist sichtbar.** Im Normalbetrieb geocodiert Nominatim und
  OpenStreetMap via Overpass liefert die Kandidaten. Die Oberfläche nennt die Quelle und
  die Trefferzahl im gewählten Umkreis. Nicht erreichbarer Dienst, nicht gefundene Adresse
  und null nutzbare Treffer sind getrennte Fehlermeldungen; keine davon ersetzt das
  Ergebnis durch Beispieldaten.
* **Restaurant-Beispieldaten gibt es nur in einem getrennten Testmodus.** Der
  Seitenbanner startet im ausgeschalteten Zustand und bietet ausdrücklich
  **„Testmodus einschalten“** und **„Testmodus verlassen“**; der Modus ist kein Feld des
  Bestellformulars. Die Ergebnisfläche sagt deutlich: **„Testmodus — Beispieldaten,
  keine echten Restaurants“**. Dabei findet kein Netzwerkzugriff für die Restaurantsuche
  statt. `HUNGRYCALL_RESTAURANT_TEST_MODE=off` entfernt den Schalter installationsweit
  und ignoriert eine frühere Browserauswahl; `on` schaltet ihn ausdrücklich frei. Ohne
  gesetzte Variable bleibt er im Evaluations-Build verfügbar.
* **Kartenkacheln kommen von OpenStreetMap.** Ohne Verbindung bleibt die Karte grau und
  eine normale Restaurantsuche meldet den Netzwerkfehler; der ausdrückliche Testmodus
  bleibt verfügbar. Schriften, Skripte und Stile werden von nirgendwo nachgeladen.
* **Ein Feldversuch mit echten Betrieben hat nicht stattgefunden.**

## Tests

Die Produktpfade laufen in der Testsuite mit Fixtures beziehungsweise gemocktem
Transport; kein Test führt einen echten Anruf aus:

```bash
pytest -v
```

Abgedeckt sind Ranking samt modusabhängiger Entfernungsgewichtung, Öffnungszeiten über
Mitternacht, die Schemata, Rufnummern-Maskierung, die Sicherheitsgatter, Ablehnung wegen
Budget und wegen geschätztem Preis, Zugeständnis-Vollmacht in beide Richtungen, beide
Zweige Ende zu Ende über den Ereignisstrom, die vom Nutzer festgelegte Kandidatenreihenfolge,
die Auftragsvorschau, der Abbruch, das Speichern mit dem tatsächlich gelaufenen Modus,
HTML-Maskierung freier Texteingaben, Hell-/Dunkelmodus, externes Laden der Zugangsdaten,
read-only Preflight, REST-Payload und Polling sowie die Vollständigkeit beider Sprachen.

## Lizenz

MIT.
