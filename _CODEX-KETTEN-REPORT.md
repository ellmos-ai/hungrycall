# Codex-Bericht: Bestellwunschketten

Datum: 2026-08-02

## Gebaut

- Das Datenmodell bildet den freigegebenen Schaltplan als drei Schachtelungen ab:
  `Posten -> Zelle -> Kriterium`.
  - Posten: frei anlegbare Tags und `posten_weglassen` oder
    `bestellung_abbrechen`.
  - Zelle: `menge`, `produkt`, `art` mit `essen` oder `getraenk`.
  - Kriterium: `hoechstpreis`, `sonderwunsch` oder `rueckfrage`; Reaktionen sind
    `annehmen`, `naechster_ersatz` und `ablehnen`.
- Eine einzige JSON-Definition ist die gemeinsame Währung für Config, Oberfläche,
  Gesprächsanweisung und Auswertung. Sie wird nicht in vier getrennten Varianten gepflegt.
- Der Übersetzer arbeitet Abschnitt 3 des Blueprints in der festgelegten Reihenfolge ab:
  Posten, Zellen, Verfügbarkeitsfrage, Kriterien, Ersatz und abschließende Zeilenregel.
- Die Auswertung berechnet das Ergebnis selbst aus den rohen strukturierten Antworten.
  Ein vom Agenten behauptetes Ergebnis kann dadurch keine harte Bedingung in eine weiche
  umdeuten. Fehlende Rückfrage-Antworten werden nicht geraten.
- Das dynamische CALL-E-Ergebnisschema verlangt `order_chain_results` mit Belegen für jeden
  versuchten Posten, jede Zelle und jedes Kriterium. Der lokale Trockenlauf erzeugt diese
  Struktur vollständig aus Fixtures und benötigt weder Konto noch Netz.
- Die Bestelloberfläche zeigt Postenzeilen mit Wunsch- und Ersatzzellen, `+` für weitere
  Ersatzwünsche, einen Zahnrad-Dialog für beliebig viele Zusatzkriterien, die Zeilenregel
  und eine freie Tag-Auswahl. Deutsch und Englisch laufen über die vorhandene
  `translations.json`-Schicht.
- Tags werden gespeichert und bei der nächsten Bestellung als Vorschläge angeboten. Die
  Abschlussansicht gruppiert die tatsächlich ausgewählten Produkte nach Tags; bestätigte
  Sonderwünsche erscheinen am Produkt.
- Vollständige Ketten lassen sich benennen und als Vorlage speichern, wieder laden und unter
  demselben Namen ändern. Jede abgeschickte Bestellung speichert ihre Kette im Verlauf und
  kann von dort in den Editor geladen, geändert und erneut abgeschickt werden.
- README und deutsche README beschreiben das neue Modell und seine Bedienung.

## Testabdeckung

Die neue Datei `tests/test_order_chains.py` prüft insbesondere:

1. Roundtrip der verbindlichen Config-Werte.
2. Reihenfolge der erzeugten Gesprächsanweisung.
3. Weiches Kriterium: Wechsel zum nächsten Ersatz.
4. Hartes Kriterium: Ersatzkette endet und die Zeilenregel greift.
5. Hartes Kriterium plus `bestellung_abbrechen`: gesamte Bestellung wird abgebrochen.
6. Unterschiedliche Ja-/Nein-Reaktionen einer Rückfrage.
7. Fehlende Antwortbelege werden nicht erfunden.
8. Dynamisches Ergebnisschema und Gesprächsanweisung stammen aus derselben Kette.
9. Vollständiger Offline-Fixture-Pfad mit Kriterienauswertung.
10. Speicherung und Roundtrip von Tags, Vorlagen und abgeschickten Bestellungen.
11. Zweisprachiger Editor und Wiederladen eines Verlaufseintrags.
12. End-to-end: Webformular -> gespeicherte Kette -> Fixture-Gespräch -> Auswertung ->
    nach Tags gruppierte Abschlussübersicht.

Ausgeführt am kombinierten aktuellen Repo-Stand:

- `python -m pytest -q -p no:cacheprovider` -> **160 passed**, eine vorhandene
  Starlette-Deprecation-Warnung.
- `node --check hungrycall/static/app.js` -> Exit 0, keine Ausgabe.
- `node --test tests/huckepack_js.test.js` -> **11 passed**, 0 failed.
- `python -m compileall -q hungrycall` -> Exit 0, keine Ausgabe.

## Offen geblieben

- Kein echter Anruf wurde ausgeführt. Deshalb ist die Annahme des dynamischen
  `order_chain_results`-Schemas durch den echten CALL-E-Dienst in dieser Sitzung nicht
  gemessen. Der Code hält diesen Punkt offen; der vollständige Fixture-Pfad ist geprüft.
- Keine manuelle visuelle Browserabnahme wurde behauptet. Server-HTML, zweisprachige
  Routen, JavaScript-Syntax und der vollständige HTTP-/SSE-Trockenlauf sind automatisiert
  geprüft.
- Kein Push und keine Veröffentlichung wurden ausgeführt.
- Der verlangte lokale Bestellketten-Commit konnte nicht angelegt werden: `git add`
  scheiterte mit `Unable to create '.git/index.lock': Permission denied`. Es wurde
  dadurch keine Bestellketten-Datei gestaged oder committet; die geprüften Änderungen
  liegen weiterhin im Arbeitsbaum.

## Grenzen eingehalten

- Anruf-Trockenlauf blieb Vorgabe; es wurde keine Nummer gewählt und kein Guthaben belastet.
- Keine Zugangsdaten wurden gelesen, geschrieben oder ausgegeben.
- Der parallel vorhandene weiche Huckepack-Lock schloss die Bestellketten ausdrücklich aus.
  Dessen eigener lokaler Commit und die fremden Änderungen an `EVIDENCE.md`,
  `_CODEX-LOGO-REPORT.md` sowie den beiden Blueprint-Dateien wurden nicht in diesen
  Bestellketten-Commit aufgenommen.
