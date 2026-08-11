![I am hungry](banner.png)

## Demovideo

[![Demovideo ansehen](youtube-play-thumb.png)](https://youtu.be/5RIq7lpKv4w)


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

## Abschlussroutine, Anrufsprache und Bestellbeleg

Jeder Anruf, der bestellt oder reserviert, endet mit einer verbindlichen **Abschlussroutine**:
die komplette Bestellung oder Buchung wird vorgelesen, ausdrücklich als verbindlich erklärt und
von der Gegenseite bestätigt. Taucht danach noch eine neue Bedingung auf — eine Gebühr, ein
geänderter Preis, eine geänderte Zeit —, prüft der Agent sie erneut gegen seine Vollmacht und
zieht die Bestellung hörbar zurück, statt die Gegenseite im Glauben zu lassen, es stünde etwas,
das nie erteilt wurde.

Die **Anrufsprache** ist von der Sprache der Weboberfläche getrennt: `HUNGRYCALL_CALL_LOCALE`
(Standard `de`, optional `en`) legt fest, in welcher Sprache CALL-E das Telefonat führt, und
damit auch die Sprache jedes wörtlich zitierten Satzes in der Gesprächsanweisung
(`hungrycall/call_language.py`). Der Sprachschalter im Kopf der Weboberfläche (siehe unten)
ändert nur, was im Browser angezeigt wird — nicht, in welcher Sprache tatsächlich telefoniert
wird.

Jeder gewählte Versuch — angenommen oder abgelehnt — wird mit Anbieter-Kennung (`run_id`),
Status, Ablehnungsgrund und maskiertem Transkript als **Bestellbeleg** gespeichert, sobald die
Kaskade ihn auswertet, nicht erst am Ende. `GET /api/order-attempts?order_id=...` liefert diese
Liste unter derselben Sitzungsregel wie der Live-Ereignisstrom.

**[`CONVERSATION-TREE.md`](CONVERSATION-TREE.md)** (Englisch) dokumentiert jeden Zweig, den der
obige Gesprächstext nehmen kann, Knoten für Knoten mit der erzeugenden Funktion — dazu eine
Abdeckungstabelle, die für jede Einstellung beantwortet, ob sie tatsächlich im Gesprächstext
ankommt.

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
git clone https://github.com/ellmos-ai/hungrycall.git
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
hungrycall delivery --food "2x Döner Kebab" --address "Dorfstrasse 1, 12345 Dorfstadt" \
  --budget 30.0 --scenario success_direct

# Tisch reservieren
hungrycall reservation --food "Italian" --date "2026-08-05" --time "19:00" --party 4 \
  --scenario reservation_cascade

# Eigener Tischwunsch mit präzisen Zeit- und Gebührenobergrenzen
hungrycall reservation --food "Italian" --date "2026-08-07" --time "19:00" --party 4 \
  --seating custom --seating-custom "unser Standardtisch unter der Palme" \
  --earlier-hours 1 --earlier-minutes 30 --later-hours 2 --later-minutes 15 \
  --max-booking-fee-eur 3 --note "Geburtstagsessen" --scenario reservation_cascade

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
Lauf würde zusätzlich `--requester-callback-number`, `--live` und `--confirm-live`
benötigen. Dienstbereitschaft und Guthaben müssen vor jedem echten Lauf aktuell geprüft
werden.

### Weboberfläche

```bash
python run_web.py          # oder: hungrycall-web
```

Danach `http://127.0.0.1:8000` öffnen. FastAPI, HTMX, SQLite und Leaflet — kein Bundler,
kein Build-Schritt, kein CDN. Zwei Zweige starten auf der Startseite und enden beide in
derselben Kaskade, nur mit anderen Kriterien. Oberfläche vollständig auf Deutsch und
Englisch; `tests/test_i18n.py` lässt den Build scheitern, wenn ein Schlüssel fehlt, eine
Sprache eine Lücke hat oder ein `{platzhalter}` bei der Übersetzung verloren geht.

Das Bestellformular startet mit einem sichtbaren, verwendbaren Essensposten; „Hinzufügen“
erzeugt und fokussiert den nächsten. Vorname, Nachname und die Rückrufnummer der anfragenden
Person stehen in einem eigenen Bereich, der Preisrahmen darunter. Bei Tischreservierungen
lassen sich eine vorgegebene oder eigene Tischpräferenz, ein zusätzlicher Hinweis, frühere
und spätere Zeiten in Stunden plus Minuten sowie eine maximale Buchungsgebühr festlegen.
Ergebnisse außerhalb dieser erteilten Vollmacht werden serverseitig abgewiesen.

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

Aus dem betreuten Feldversuch am 2026-08-11 (Einzelheiten in `FINDINGS.md` §9):

5. **Ein Netzwerkaussetzer beendet die Kaskade nicht mehr, und ein hängender POST
   verdoppelt keinen Anruf.** Das Status-Polling verträgt bis zu 3 aufeinanderfolgende
   Netzwerk-/5xx-Fehler, bevor es aufgibt. Ein `POST /v1/calls`, der clientseitig in den
   Timeout läuft, wird bis zu dreimal mit **demselben** `Idempotency-Key` wiederholt — ein
   Wiederholungsversuch hängt sich so an einen bereits laufenden „Geisteranruf" an, statt
   ein zweites Mal zu wählen.
6. **`HUNGRYCALL_DEBUG_PAYLOAD_DIR` schreibt das maskierte End-Payload jedes Live-Anrufs
   lokal mit.** Nur mit gesetzter Variable, nur lokal, Rufnummern vorher maskiert —
   entstanden, um zu klären, was die API bei einem unerwarteten Ergebnis wirklich
   zurückgegeben hatte.

---

## Datenfluss und Datenschutz

> ⚠️ **Hinweis zur Datenübermittlung**
> Der Sprachagent von CALL-E läuft auf AiRudder-Infrastruktur in **Singapur**
> (`https://seleven-mcp-sg.airudder.com`).
>
> Bei einem echten Anruf gehen die nötigen Auftragsparameter (Name, Rückrufnummer der
> anfragenden Person, Lieferadresse oder Reservierungsdaten und der Wunsch) an den
> konfigurierten CALL-E-Endpunkt und werden dem ausgewählten Restaurant zweckgebunden
> mitgeteilt. HungryCall hält Datensparsamkeit ein:
> * Nur das Nötigste für genau diesen einen Anruf wird übergeben.
> * Keine Vorgeschichte, kein dauerhaftes Profil.
> * Die Pflicht-Rückrufnummer wird als E.164 geprüft und nur flüchtig geführt; sie landet
>   nicht in SQLite, Verlauf, Belegen oder Fixture-Ausgaben.
> * Rufnummern sind in allen Ausgaben, Protokollen und Zusammenfassungen maskiert
>   (`+49 ••• ••••123`).

## Sicherheit

* **Der Anruf-Trockenlauf ist der Normalfall.** Ohne ausdrückliches `--live` und
  `--confirm-live` nutzt die Anrufkaskade lokale Fixtures und braucht kein CALL-E-Konto.
  Die Restaurantquelle ist davon getrennt: Im Web fragt der Normalbetrieb
  OpenStreetMap ab; nur ein ausdrücklich gewählter Restaurant-Testmodus ist vollständig lokal.
* **Feldversuchsmodus:** `HUNGRYCALL_FIELD_TRIAL_PHONE` leitet vor Kaskadenstart die
  Rufnummer jedes Live-Kandidaten auf eine einzige, ausdrücklich zustimmende Testnummer um;
  Restaurantnamen und Ranking bleiben echt, nur die gewählte Leitung wird umgeleitet.
  Fail-closed: Eine gesetzte, aber ungültige Nummer verweigert den Live-Lauf, statt
  stillschweigend auf echte Nummern zurückzufallen. Nur unter dieser Umleitung darf ein
  Restaurant aus den Fixture-/Testmodus-Szenarien überhaupt auf eine Live-Leitung gehen —
  nie mit der echten Nummer eines echten Betriebs.
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

* **Echte Anrufe sind mehrfach gegattert.** Der sichere lokale Pfad ist vorausgewählt.
  Im Web braucht Live zusätzlich ein Bestätigungshäkchen, im CLI `--live`,
  `--confirm-live` und eine Rückrufnummer der anfragenden Person. Die Warnung „Echte
  Anrufe — kostet Geld“ ist sichtbar. Diese Änderung wurde ohne echten Anruf geprüft;
  Dienstbereitschaft und Kontostand sind externe, jeweils neu zu prüfende Tatsachen.
* **Die Restaurantquelle ist sichtbar.** Im Normalbetrieb geocodiert Nominatim und
  OpenStreetMap via Overpass liefert die Kandidaten. Die Oberfläche nennt die Quelle und
  die Trefferzahl im gewählten Umkreis. Nicht erreichbarer Dienst, nicht gefundene Adresse
  und null nutzbare Treffer sind getrennte Fehlermeldungen; keine davon ersetzt das
  Ergebnis durch Beispieldaten.
* **Restaurant-Beispieldaten gibt es nur in einem getrennten Testmodus.** Der
  Seitenbanner startet im ausgeschalteten Zustand und bietet ausdrücklich
  **„Testmodus einschalten“** und **„Testmodus verlassen“**; der Modus ist kein Feld des
  Bestellformulars und ist die einzige sichtbare Testbezeichnung. Die Szenarioauswahl
  erscheint nur bei aktivem Testmodus; die Live-Auswahl ist dann ausgeblendet. Die
  Ergebnisfläche sagt deutlich: **„Testmodus — Beispieldaten, keine echten Restaurants“**.
  Dabei findet kein Netzwerkzugriff für die Restaurantsuche
  statt. `HUNGRYCALL_RESTAURANT_TEST_MODE=off` entfernt den Schalter installationsweit
  und ignoriert eine frühere Browserauswahl; `on` schaltet ihn ausdrücklich frei. Ohne
  gesetzte Variable bleibt er im Evaluations-Build verfügbar.
* **Kartenkacheln kommen von OpenStreetMap.** Ohne Verbindung bleibt die Karte grau und
  eine normale Restaurantsuche meldet den Netzwerkfehler; der ausdrückliche Testmodus
  bleibt verfügbar. Schriften, Skripte und Stile werden von nirgendwo nachgeladen.
* **Ein Feldversuch mit echten Betrieben hat nicht stattgefunden.** Ein betreuter
  Feldversuch fand am 2026-08-11 statt, aber unter `HUNGRYCALL_FIELD_TRIAL_PHONE`: Die
  gewählte Nummer jedes Kandidaten war durchgehend eine einzige zustimmende Testleitung,
  nie die echte Nummer eines echten Betriebs. Die Befunde aus diesen Anrufen stehen in
  `FINDINGS.md` §9, die daraus entstandene Härtung oben unter „Abschlussroutine,
  Anrufsprache und Bestellbeleg" sowie in „Am echten Dienst gemessen".

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
