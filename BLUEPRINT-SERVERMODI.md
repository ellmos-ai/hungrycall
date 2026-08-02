# Blueprint: Servermodi

> Architekturidee des Nutzers vom 2026-08-02. Sie löst den Befund aus `DATA-FLOW.md`:
> Heute teilen sich alle Besucher einen Prozesszustand, eine SQLite-Datei und einen
> API-Schlüssel — gehostet wäre das ein Datenschutzvorfall mit Ansage.
> **Noch nicht gebaut.** Dies ist der Schaltplan.

## Der Kerngedanke

**Der Nutzer speichert alles in seinem Browser. Der Host speichert nichts.**

Damit entfällt die Nutzerverwaltung nicht, weil sie schwer wäre — sie wird
**gegenstandslos**. Wo keine fremden Daten liegen, braucht es keine Konten, keine
Zugriffsprüfung, keine Löschfristen und keine Trennung zwischen Besuchern.

---

## Die drei Modi

| Modus | Kürzel | API-Schlüssel | Daten | Nutzerverwaltung |
|---|---|---|---|---|
| **huckepack-gift** | A1 | vom **Hoster**, im Backend | Browser des Nutzers | keine |
| **huckepack-only-host** | A2 | vom **Nutzer**, im Browser | Browser des Nutzers | keine |
| **pay-membership** | B | Hoster, abgerechnet | Server | **erforderlich** |

### A1 — huckepack-gift

Der Hoster stellt seinen Schlüssel zur Verfügung; die Anrufe laufen auf seine Rechnung.
Der Nutzer trägt nichts ein und legt sofort los.

Alles, was er eingibt und erhält — Bestellketten, Ergebnisse, Verlauf, Vorlagen, Tags —
liegt in **seinem Browser**. Der Host hält nur den Schlüssel und führt den Anruf aus.

*Der Hoster verschenkt Anrufe. Das ist die Einladung: ausprobieren ohne Hürde.*

### A2 — huckepack-only-host

Kein Schlüssel im Backend. Der Nutzer hinterlegt **seinen eigenen**, gespeichert in
seinem Browser, und ruft auf eigene Rechnung an.

Der Host stellt nur die Oberfläche und die Ausführung bereit — er zahlt nichts und
speichert nichts.

*Für alle, die die Anwendung nutzen wollen, ohne dass jemand anders ihre Anrufe bezahlt.*

### B — pay-membership (nur als Stub)

**Wird nicht gebaut.** Nur als Platzhalter angelegt, damit die Modusumschaltung ihn kennt
und die Stelle sichtbar bleibt.

**Grund:** Ab hier braucht es Nutzerverwaltung — Konten, Anmeldung, Abrechnung,
serverseitige Speicherung, und damit alles, was A1 und A2 gerade vermeiden. Das ist ein
eigenes Vorhaben, kein Schalter.

---

## Was der Modus jeweils festlegt

| Frage | A1 | A2 | B (Stub) |
|---|---|---|---|
| Woher kommt der Schlüssel? | Backend | Browser des Nutzers | Backend, abgerechnet |
| Wer zahlt den Anruf? | Hoster | Nutzer | Nutzer per Mitgliedschaft |
| Wo liegen Bestellungen und Verlauf? | Browser | Browser | Server |
| Sieht ein Besucher fremde Daten? | nein | nein | nein, aber nur per Zugriffsprüfung |
| Braucht es Konten? | nein | nein | ja |
| Braucht der Hoster eine Datenschutzerklärung? | für den Anrufvorgang | für den Anrufvorgang | vollumfänglich |

**Wichtig auch in A1 und A2:** Angerufen werden **Dritte** — deren Daten werden
verarbeitet, unabhängig davon, wo die Bestellung gespeichert ist. Eine Datenschutz-
erklärung des Hosters wird dadurch nicht überflüssig, aber sie wird kurz: Sie muss den
Anrufvorgang und die Weitergabe an CALL-E beschreiben, nicht eine Nutzerdatenbank.

---

## Modus-Erkennung und -Einstellung

**Eingestellt** wird der Modus beim Start des Servers — Umgebungsvariable oder Config,
nicht zur Laufzeit umschaltbar. Er ist eine Eigenschaft der Installation.

```
HUNGRYCALL_SERVER_MODE = local | huckepack-gift | huckepack-only-host | pay-membership
```

**Erkannt** wird er von der Oberfläche beim Laden, damit sie sich richtig verhält:

| Modus | Was die Oberfläche zeigt |
|---|---|
| `local` | wie heute — Daten lokal, Schlüssel aus Umgebung |
| `huckepack-gift` | Hinweis „Anrufe werden vom Betreiber gestellt", kein Schlüsselfeld |
| `huckepack-only-host` | Schlüsselfeld, Hinweis „Ihr Schlüssel bleibt in Ihrem Browser" |
| `pay-membership` | Hinweis „nicht verfügbar" — der Stub |

**Ohne Einstellung gilt `local`.** Wer nichts konfiguriert, bekommt das heutige Verhalten.

---

## Was im Browser liegt (A1 und A2)

| Was | Wo | Bemerkung |
|---|---|---|
| Bestellketten, Vorlagen, Tags | `localStorage` | überlebt das Schließen des Browsers |
| Verlauf und Ergebnisse | `localStorage` | inklusive Transkripten |
| API-Schlüssel (nur A2) | `localStorage`, maskiert angezeigt | wird nur zum Anruf mitgesendet |
| Sprache, Farbschema | wie heute | unverändert |

### Die Grenzen, ehrlich benannt

- **Browserdaten gelöscht = alles weg.** Es gibt keine Kopie beim Host. Deshalb braucht
  es einen **Export** (Datei herunterladen) und einen **Import** — sonst ist der Verlust
  endgültig und der Nutzer hat keine Handhabe.
- **Kein Gerätewechsel.** Was am Rechner liegt, ist am Telefon nicht da. Export und
  Import sind auch dafür der Weg.
- **Der Schlüssel im Browser (A2)** ist weniger geschützt als auf einem Server. Er gehört
  aber dem Nutzer selbst, und die Alternative wäre, ihn dem Hoster anzuvertrauen — das
  ist nicht offensichtlich besser.
- **Der Anruf läuft weiterhin über den Server.** Der Browser spricht nicht direkt mit
  CALL-E; die Anfrage geht durch den Host. In A2 reicht er den Schlüssel des Nutzers
  durch, ohne ihn zu speichern — das gehört ausdrücklich geprüft und dokumentiert.

---

## Was zu bauen ist

| Schritt | Umfang |
|---|---|
| Modus-Einstellung und -Erkennung, Vorgabe `local` | klein |
| Speicherschicht austauschbar: SQLite **oder** Browser | mittel — das ist der Kern |
| Schlüsselfeld für A2, maskiert, nie im Log | klein |
| Durchreichen des Nutzerschlüssels ohne Speicherung | klein, aber sorgfältig |
| Export und Import der Browserdaten | klein — und unverzichtbar |
| Stub für B | winzig |

**Der eigentliche Aufwand** steckt darin, die Speicherung austauschbar zu machen. Heute
schreibt die Anwendung direkt in SQLite; sie braucht eine Schicht dazwischen, die je nach
Modus entweder dorthin oder in den Browser schreibt.

---

## Nachtrag: Die Datenbank kann beim Nutzer liegen [U 2026-08-02]

**Frage des Nutzers:** *„Kann die App, die gehostet wird, die Speicherbank lokal einfach
beim Nutzer bauen lassen?"* — **Ja.**

**SQLite läuft im Browser.** Über `sql.js` bzw. das offizielle SQLite-WASM-Paket wird
dieselbe Datenbank im Browser ausgeführt; die dauerhafte Ablage übernimmt das **Origin
Private File System (OPFS)**. Für den Nutzer entsteht eine echte Datenbankdatei auf
seinem Rechner — nur im Browser-Bereich statt im Serververzeichnis.

**Damit schrumpft der Layer erheblich:** dasselbe Schema, dieselben Abfragen, anderer
Ausführungsort. Es sind nicht zwei Speicherwelten, sondern eine Datenbank an zwei Orten.

**Der Preis:** Die Abfragen laufen dann im Browser, nicht im Python-Backend. Für
Bestellketten, Verlauf, Vorlagen und Tags ist das unproblematisch — es sind kleine
Datenmengen ohne Serverlogik.

**Rangfolge der Browser-Speicher**, falls WASM zu schwer wirkt:
1. **SQLite-WASM + OPFS** — echte Datenbank, dasselbe Schema, größte Kapazität
2. **IndexedDB** — strukturiert, viel Platz, aber eigenes Abfragemodell
3. **localStorage** — nur für Kleinigkeiten wie Sprache und Farbschema

---

## Nachtrag: Quittung per E-Mail [U 2026-08-02]

**Ursprüngliche Idee für die Bestell-Apps:** Der Nutzer hinterlegt eine E-Mail-Adresse.
Nach einem **erfolgreichen** Vorgang bekommt er Gesprächsverlauf und Bestelldaten
zugesandt — als **Beleg und Quittung**, wahlweise als Text oder PDF.

### Was das verlangt

| Baustein | Ort | Bemerkung |
|---|---|---|
| E-Mail-Adresse | Browser des Nutzers (wie alle Daten) | optional, leer = kein Versand |
| Mailversand | **Server** | der Browser kann nicht versenden |
| PDF-Erzeugung | Server oder Browser | Textfassung ist die einfachere Vorgabe |

**Der Host muss also eine Mail-Anbindung bereitstellen** — das ist der einzige Punkt, an
dem der Server im Huckepack-Modus mehr tut als anrufen. Ohne konfigurierten Mailversand
bleibt die Funktion abgeschaltet und das Feld ausgeblendet.

### Datenschutzfolge — gehört in die Vorlagen

Die Adresse ist ein **personenbezogenes Datum**, und der Versand transportiert
Gesprächsverlauf und Bestelldaten nach außen. Das berührt auch den **angerufenen
Dritten**, dessen Äußerungen im Transkript stehen.

Für `PRIVACY-TEMPLATE.md` heißt das ein eigener, klar markierter Abschnitt:
- welche Adresse wozu verarbeitet wird
- **welcher Mailanbieter** eingesetzt wird (Auftragsverarbeiter, vom Hoster einzutragen)
- ob die Adresse gespeichert oder nur für den Versand benutzt wird
- dass das Transkript Äußerungen des Angerufenen enthält
- Aufbewahrungsdauer beim Mailanbieter — eine Tatsache des Hosters, keine der Anwendung

**Und in `DATA-FLOW.md`:** eine Zeile für die Adresse und eine für den Versand, mit dem
ehrlichen Vermerk, dass hier Daten den Rechner des Hosters verlassen.

### Alternative: Versand über das eigene Konto des Nutzers [U 2026-08-02]

**Idee des Nutzers:** *„Konto verknüpfen, Gmail oder anderes Konto: Mailversand läuft über
das eigene Mailkonto, man schickt eine Mail an sich selbst."*

Das ist konsequenter als Server-Versand — **der Host braucht dann gar keine
Mail-Anbindung**, und es bleibt dabei, dass er nichts verarbeitet. Zwei Abstufungen:

#### Weg 1 — `mailto:` (fast umsonst zu haben)

Die Anwendung baut einen `mailto:`-Link mit vorausgefülltem Betreff und Text; der Browser
öffnet das Mailprogramm des Nutzers, er klickt auf Senden.

- **Kein OAuth, keine Token, keine Konfiguration.** Funktioniert überall sofort.
- **Kein Anhang möglich** — die Quittung muss als Text im Nachrichtenkörper stehen.
- Bei sehr langen Transkripten stößt die Länge an Grenzen (URL-Limits); dann kürzen oder
  auf Weg 2 ausweichen.
- Der Nutzer sieht vor dem Senden, was rausgeht — das ist ein Vorzug, kein Mangel.

#### Weg 2 — Konto verknüpfen (Gmail API, OAuth)

Der Nutzer verknüpft sein Konto; die Anwendung versendet in seinem Namen an ihn selbst.

- **PDF-Anhang möglich**, beliebige Länge, automatischer Versand ohne Klick.
- Braucht OAuth-Zugangsdaten des Betreibers und eine Google-Freigabe — der Aufwand ist
  erheblich und trifft den Hoster, nicht den Nutzer.
- Das Zugriffstoken müsste im Browser liegen, wie der API-Schlüssel in A2.

#### Empfehlung

**`mailto:` als Vorgabe, Kontoverknüpfung später.** Der einfache Weg löst den Zweck
— eine Quittung im eigenen Postfach — ohne dass irgendwo ein Konto, ein Token oder ein
Mailserver dazukommt. Ein PDF ist nur dann nötig, wenn die Quittung als Beleg gegenüber
Dritten dienen soll; für den Eigengebrauch genügt Text.

#### Datenschutzfolge

**Sie entfällt weitgehend.** Verschickt der Nutzer aus seinem eigenen Programm an sich
selbst, verarbeitet der Hoster nichts — kein Auftragsverarbeiter, kein Mailanbieter in
der Erklärung. Es bleibt der Hinweis, dass das Transkript Äußerungen des Angerufenen
enthält und der Nutzer entscheidet, wohin es geht.

**Das macht diesen Weg auch rechtlich zur saubersten Lösung**, nicht nur zur einfachsten.

### Entschieden: Beleg herunterladen statt versenden [U 2026-08-02]

**Korrektur der beiden Wege oben.** Der Nutzer verwirft `mailto:` — es wäre ein Umweg über
ein Mailprogramm für etwas, das eine Datei ist. Und die Kontoverknüpfung lohnt den
OAuth-Aufwand nicht.

**Stattdessen: Der Beleg wird heruntergeladen, und der Nutzer stellt ein, wo die Belege
landen.**

#### Warum das besser ist

Ein Beleg ist eine **Datei**, kein Brief. Wer ihn braucht, will ihn ablegen — nicht ihn
sich selbst zumailen und dann aus dem Postfach heraussuchen. Der Umweg über eine Mail
erzeugt eine zweite Kopie an einem Ort, den man nicht gewählt hat.

Dazu entfällt alles, was am Mailweg hing: kein Mailserver beim Host, kein OAuth, kein
Token, kein Auftragsverarbeiter in der Datenschutzerklärung, keine Adresse als
personenbezogenes Datum. **Der Host bleibt vollständig unbeteiligt.**

#### Wie der Zielordner einstellbar wird

Die **File System Access API** (`showDirectoryPicker`) lässt den Nutzer einmal einen
Ordner wählen; die Erlaubnis bleibt bestehen, und die Anwendung legt Belege künftig
direkt dort ab.

| Fall | Verhalten |
|---|---|
| Ordner gewählt | Beleg landet ohne Nachfrage dort |
| kein Ordner gewählt | normaler Download in den Download-Ordner des Browsers |
| Browser ohne Unterstützung | wie oben — normaler Download, kein Funktionsverlust |

Die Ordnerwahl ist also **Komfort, keine Bedingung**. Ohne sie funktioniert alles, nur
landen die Dateien im Standardordner.

#### Format und Benennung

- **Text** als Vorgabe — lesbar, klein, ohne Abhängigkeiten
- **PDF** optional, im Browser erzeugt (der Host bleibt außen vor)
- Dateiname mit Datum, Zeit und Anbieter, damit die Ablage von selbst sortiert:
  `2026-08-02_1930_Surf-Grill-Express_beleg.txt`

#### Was im Beleg steht

Bestelldaten, Ergebnis, Preis, Zeitpunkt, angerufener Betrieb, Gesprächsverlauf — dazu
der Hinweis, dass das Transkript Äußerungen des Angerufenen enthält. **Rufnummern
maskiert**, wie überall sonst.
