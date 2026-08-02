# Codex-Logo-Report — Kühlschrankmotiv und Lichtwechsel

Datum: 2026-08-02

## Einbindung

- `hungrycall/static/brand/motiv.png` ist das Logo im Kopfbereich der Weboberfläche.
- `hungrycall/static/brand/logo-square.png` ist das lokale PNG-Favicon.
- `motiv-aus.png` und `motiv-an.png` bilden die Lichtwechsel-Szene auf der Startseite.
- `thumbnail.png` liegt als freigegebenes Markenasset im selben Brand-Ordner.
- `banner.png` im Repo-Root wurde durch das freigegebene Banner ersetzt. Es steht als
  erste Zeile in `README.md` und `README_de.md`.
- Alle sechs kopierten PNG-Dateien stimmen per SHA-256 bytegenau mit den freigegebenen
  Quelldateien unter `C:\_Local_DEV\_calle-videos\hungrycall\brand\` überein.

## Lichtwechsel

Der Effekt startet automatisch beim Laden der Startseite. Die beiden deckungsgleichen
Bilder liegen absolut übereinander: Zuerst ist `motiv-aus.png` sichtbar; nach 0,65
Sekunden blendet CSS innerhalb von 1,35 Sekunden zu `motiv-an.png` über. Beide
Animationen laufen genau einmal und behalten anschließend den hellen Endzustand. Es
gibt keine Dauerschleife und kein zusätzliches JavaScript.

Bei `prefers-reduced-motion: reduce` sind beide Animationen deaktiviert:
`motiv-aus.png` ist unsichtbar und `motiv-an.png` sofort vollständig sichtbar. Die Szene
hat außerdem eine zweisprachige ARIA-Beschreibung.

Die kurze Problemzeile nutzt den vorhandenen Übersetzungsmechanismus:

- Deutsch: „Der Kühlschrank ist leer — und auf dem Land weißt du nicht einmal, wer
  überhaupt liefert.“
- Englisch: “The fridge is empty — and out here, you do not even know who delivers.”

## Tests — tatsächlich ausgeführt

Vollständiger Lauf:

```text
python -m pytest -q -p no:cacheprovider --basetemp=C:/_Local_DEV/repos/hungrycall/.codex-pytest-final-1785690103749
........................................................................ [ 64%]
........................................                                 [100%]
112 passed, 1 warning in 17.79s
```

Der Logo-Auftrag ergänzt genau zwei Regressionstests; der erste vollständige Lauf ergab
daher die vorhandenen 99 plus zwei, also 101 grüne Tests. Der abschließende Lauf auf dem
stabilen gemeinsamen Arbeitsbaum enthält zusätzlich elf parallel entstandene
Fallback-Tests und zählt deshalb 112. Die beiden Logo-Tests prüfen die paketierten PNGs
und Abmessungen, das Root-Banner und beide README-Kopfzeilen, die statische Auslieferung,
Headerlogo/Favicon, die beiden Ebenen, den einmaligen Endzustand, reduzierte Bewegung
sowie deutsche und englische Texte. Die eine Warnung ist die bereits bestehende
Starlette-Abkündigungswarnung für `TestClient` und `httpx`.

## Harte Grenzen

- Kein echter Anruf und kein `POST /v1/calls`.
- Kein `git push`, keine Veröffentlichung und kein Upload.

## Lokaler Commit — abschließender Readback

Der ausdrücklich verlangte lokale Commit wurde als eigener enger Git-Schreibversuch
gestartet. Bereits das Staging einer einzigen ausschließlich zu diesem Auftrag gehörenden
Datei scheiterte zunächst vor jeder Indexänderung:

```text
git add -- README.md
fatal: Unable to create 'C:/_Local_DEV/repos/hungrycall/.git/index.lock': Permission denied
```

Dieser Agent führte keinen zweiten Schreibversuch aus. Danach erstellte der parallel
arbeitende Lock-Owner den lokalen Commit `8f4899a` (`fix: say when there are no
restaurants instead of inventing some`). Der anschließende `git show`-Readback bestätigt,
dass sämtliche Logo-Dateien, Brand-Assets, README-Änderungen, Übersetzungen, Tests und
dieser Report in `8f4899a` enthalten sind.

Der Commit ist nicht sauber auf diesen Auftrag begrenzt: Er enthält zugleich den
parallelen Fallback-Fix und die schon vorher fremd geänderte `AUFGABEN.txt`. Dieser Agent
hat den fremden Commit weder umgeschrieben noch geteilt. Die nachträgliche Klarstellung
dieses erst nach dem ersten Commitversuch eingetretenen Zustands ist wegen der weiterhin
geltenden Git-Schreibsperre dieses Agenten nicht mehr Teil von `8f4899a`. Es wurde nichts
gepusht.
