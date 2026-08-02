# HungryCall — Farben und CALL-E-Anbindung

Stand: 2026-08-02

## Ergebnis

HungryCall startet jetzt in einem hellen, lebendigen Farbschema. Das dunkle
Switchboard-Design bleibt als zweiter Modus erhalten. Trockenlauf bleibt bei CLI
und Web die Voreinstellung. Ein echter Anruf wurde nicht ausgeführt.

Die Gestaltung folgt einer „elektrischen Routenkarte“: Weiß bildet die Fläche,
Kobaltblau führt durch den Ablauf, Lila strukturiert, Pink markiert Aktionen und
Absagen. Grasneongrün erscheint nur punktuell an Live- und Erfolgszuständen. Damit
bleibt HungryCall deutlich lebendiger als die ruhige Papier-Optik von ResearchCall.

## Gewählte Farbwerte

### Heller Standardmodus

| Rolle | Wert | Verwendung |
|---|---:|---|
| Grundfläche | `#F7F9FF` | heller Seitenhintergrund |
| Karten und Panels | `#FFFFFF` | weiße Hauptflächen |
| Kobaltblau | `#2563EB` | Routen, Hauptaktionen, Fokus |
| Lila | `#7C3AED` | Struktur, Umschalter, Verlauf |
| Pink | `#EC4899` | Live-Warnung, Absagen, Aktionsmarken |
| Grasneongrün | `#82F21B` | nur Live-/Erfolgsakzente |
| Haupttext | `#18203B` | gut lesbarer Dunkelblau-Ton |
| Trennlinien | `#C7D2FE` | leichte blau-lila Konturen |

### Dunkler Zweitmodus

| Rolle | Wert |
|---|---:|
| Grundfläche | `#111327` |
| Panels | `#191B35` |
| zweite Panelstufe | `#25284D` |
| Blau | `#6EA8FF` |
| Lila | `#A78BFA` |
| Pink | `#FF5CA8` |
| Grasneongrün | `#8CFF32` |
| Haupttext | `#F8FAFF` |

## Umschaltung

Im Kopf jeder Seite befindet sich der Schalter „Hell/Dunkel“. Ohne gespeicherte
Auswahl gilt immer Hell. Der Browser speichert ausschließlich die Auswahl unter
`hc-theme` in `localStorage`; es werden dabei keine Personen- oder Auftragsdaten
gespeichert. Ein früher Scriptblock setzt den gespeicherten Modus vor dem Rendern,
damit kein störender Farbblitz entsteht.

Die Browserprüfung der hellen Startseite ergab:

```text
theme: light
body: rgb(247, 249, 255)
tile surface: rgb(255, 255, 255)
text: rgb(24, 32, 59)
theme button action: Dunkel
console errors: 0
```

## CALL-E-Key-Anbindung

Die Anbindung liest Zugangsdaten in dieser Reihenfolge:

1. Prozessvariablen `CALLE_API_KEY` oder `IAM_API_KEY`;
2. externe `.env` über `CALLE_ENV_FILE` beziehungsweise `--env-file`;
3. auf diesem Rechner der vorhandene Standardpfad
   `C:\_Local_DEV\CREDENTIALS\call-e\call-e.env`.

`CALLE_BASE_URL` wird auf dieselbe Weise aufgelöst. Fehlt der Schlüssel, nennt die
Fehlermeldung die erlaubten Variablen und den geprüften Pfad; der Trockenlauf bleibt
weiter nutzbar. Der Schlüsselwert wird weder geloggt noch in `repr`, Code, Doku,
Bericht oder Commit aufgenommen.

Der Live-Adapter baut den REST-Auftrag mit `recipient_result_schema`, prüft E.164
vor dem Transport, setzt einen `Idempotency-Key`, ruft Kandidaten nur seriell auf,
pollt bis zu einem differenzierten Endstatus und liest das Transkript aus
`result.transcript`. Rufnummern in Aktivität und Transkript werden vor der Ausgabe
maskiert.

### Sichtbare Live-Gatter

* CLI: Sowohl `--live` als auch `--confirm-live` sind nötig.
* Web: Live muss ausgewählt und über ein separates Häkchen bestätigt werden; danach
  wird die Kandidatenliste nochmals mit der Warnung gezeigt.
* Sichtbarer Warntext: **„Echte Anrufe — kostet Geld“**.
* Trockenlauf ist weiterhin vorausgewählt.

## Read-only Dienstprüfung

Ausgeführt wurde ausschließlich:

```powershell
python -X utf8 -m hungrycall.cli preflight
```

Ergebnis: CALL-E antwortete auf
`GET /v1/calls/probe-does-not-exist` mit HTTP 404. Das belegt, dass der Dienst
erreichbar war und den Schlüssel akzeptiert hat; die absichtlich nicht vorhandene
Ressource wurde erwartungsgemäß abgelehnt. Der Preflight hat keine Rufnummer und
sendet niemals `POST /v1/calls`.

Bei einem Guthaben von derzeit −0,05 USD gehen echte Anrufe aktuell nicht durch.
Deshalb wurde kein echter Anruf gestartet und keine kostenpflichtige Ablehnung
provoziert.

## Tests

Echter Gesamtlauf nach der Umsetzung:

```text
99 passed, 1 warning in 14.17s
```

Die Warnung ist die bereits vorhandene Starlette-Abkündigungswarnung zu
`TestClient`/`httpx`. Die neuen Tests prüfen unter anderem Farbtokens und hellen
Standard, Dunkel-Umschaltung, sichtbare Live-Warnung, doppelte Web-Bestätigung,
Umgebungs-/`.env`-Priorität, fehlenden Schlüssel, read-only GET-Preflight,
REST-Payload, Polling, Idempotenz und Rufnummernmaskierung. Sämtliche
Netz-/Live-Pfade der Tests sind gemockt; kein Test telefoniert.

## Harte Grenzen eingehalten

* kein echter Anruf;
* kein `git push`;
* keine Veröffentlichung;
* kein Schlüsselwert in Repo oder Bericht.

## Lokaler Commit

Der verlangte lokale Commit wurde versucht, aber bereits `git add` konnte
`.git/index.lock` nicht anlegen:

```text
fatal: Unable to create 'C:/_Local_DEV/repos/hungrycall/.git/index.lock': Permission denied
```

Damit wurden keine Dateien gestaged und kein Commit erzeugt. `AUFGABEN.txt` enthält
eine während dieses Laufs fremd entstandene Änderung zum Video-Feedback; sie wurde
bewusst weder verändert noch in den Stage-Versuch aufgenommen. Ohne wiederhergestellten
Git-Schreibzugriff wurde kein zweiter Versuch unternommen.
