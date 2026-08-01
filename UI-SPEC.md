# „I am hungry" — Produktkonzept der Oberfläche

> Diktiert vom Nutzer am 2026-08-01, aufgenommen vom Operator. **Seine Vorstellung,
> nicht meine Ableitung** — Ergänzungen und Bedenken sind als solche markiert.
> Projektname: der Sprachbefehl **„I am hungry"** ist der Name der Sache; `hungrycall`
> bleibt der Repo-Arbeitsname.

## Grundhaltung

**Schnell offen, clean, leicht.** Man ist direkt da. Im Wesentlichen: durchklicken,
absenden, los. Keine Einarbeitung, keine Konfigurationsorgie.

---

## Der Lieferweg (der Hauptweg)

### 1. Ort — alles wird um den Ort herum gebaut

Erster Schritt: **Ortserkennung oder Eingabe** — Postleitzahl, Ort, Land.
Zusätzlich **Adresse**, denn die braucht man ohnehin für die Bestellung.
Dann **Umkreis** einstellen.

> **Nutzer-Anmerkung:** Wo sitzt die Jury? Der Sitz von CALL-E sollte berücksichtigt
> werden, damit die Jury die App **selbst benutzen** kann — nicht nur ein deutsches
> Dorf im Blick haben.

Braucht: Anbindung an einen Dienst, der Orte auflöst.

### 2. Suche — die Datenbank baut sich selbst auf

Ein LLM oder eine Suche sammelt live Restaurants in der Umgebung und **scrapet die Daten**:

- Telefonnummer *(bleibt im Hintergrund — der Nutzer braucht sie nicht)*
- Adresse / GPS-Koordinate
- Typ des Restaurants
- **Öffnungszeiten**
- soweit möglich: **Speisekarte oder Gerichte**, die es dort gibt bzw. die im Zusammenhang
  gefunden wurden

**Prinzip:** Man startet **clean**. Die Datenbank entsteht durch die eigenen Suchanfragen
und das Profil. Vorbild aus dem Bestand: **MediaBrain**.

**Wo das Modell läuft:** Hat der Nutzer ein eigenes LLM im Hintergrund, läuft Suche und
Auswertung darüber. Läuft es auf einem Server, übernimmt das dortige Modell.

**Währenddessen:** eine schöne Animation — *„Wir suchen für Sie die besten Essenspunkte."*

### 3. Karte — der Nutzer ist der leuchtende Punkt

Braucht einen **Kartendienst**.

Der Nutzer sitzt als **leuchtender Punkt im Zentrum** (aus seiner Adresse), um ihn herum
gruppieren sich die gefundenen Stellen — mit Namen und, je nach Typ, **eigenen Symbolen**
(Italiener, Inder, …), die per KI generiert werden.

- Standardmäßig sind **alle aktiviert**, der Nutzer kann einzeln an- und abwählen —
  mit visuellem Leuchteffekt.
- **Vermutlich geschlossene werden nicht angezeigt**, mit Hinweis darunter und einem
  Schalter zum Einblenden. Wer es besser weiß („die haben doch offen"), lässt sie drin.
- **Die Karte bleibt die ganze Zeit sichtbar.**

### 4. Modus

*Wie möchtest du an dein Essen kommen?* → **Lieferung · Abholen · Tisch reservieren**

### 5. Personen und Profile

*Für wie viele Personen möchtest du bestellen?*

**Profile für Freunde und Familie** werden gespeichert und wiederverwendet:

- **Spitzname statt Klarname** — „dann ist der Datenschutz auch kein Problem"
- Lieblingsessen, Standardessen, eigene **Prioritätenliste**
- **Alter/Stufe:** Kleinkind, Kind, Jugendlicher, …
- **Besonderheiten je Gericht:** „mag keine Oliven — immer ohne Oliven"
  → **muss beim Telefonat mitgesprochen werden.** Geht es nicht, springt die Bestellung
  zum nächsten Gericht der Liste.

Vorhandene Profile klickt man an, neue legt man direkt an.

> **Vereinfachung des Nutzers:** Die Personenzahl kann man auch weglassen — sie ergibt
> sich aus den hinzugefügten Personen.

### 6. Essenswahl

Drei Wege, frei kombinierbar:
- **Freitext** eingeben
- **anklicken** aus dem Profil (Lieblingsessen als Bilder, „AG kann dazu schöne Bilder
  generieren, mehr symbolisch")
- **„wie immer"** — die Prioritätenliste wird abgearbeitet

Dazu **„heute aber nicht"**: Ein Eintrag wird für diesen Lauf übersprungen.

**Mehrere Gerichte** sind hinzufügbar. Tags statt starrer Gänge:
**Hauptspeise · Vorspeise · Nachspeise · Getränke**, dazu Kategorien wie
**Fleisch · Fisch · Gemüse**.

**Regeln:**
- Ein bereits gewähltes Hauptgericht wird beim zweiten Gericht **übersprungen** —
  „mir kommt nicht dasselbe".
- Dafür gibt es einen **Zähler**: zweimal dasselbe, dreimal dasselbe.
- Damit kann man theoretisch **über ein Profil alles bestellen**, ohne für jede Person
  einzeln anzugeben.

### 7. Restaurantauswahl

> *„Wir rufen alle an und prüfen zuerst, ob sie liefern können. Bitte wählen Sie
> diejenigen ab, die nicht angerufen werden sollen."*

Die **erste Frage im Gespräch ist immer: Liefern Sie überhaupt hierhin?**

### 8. Priorisierung

Die ausgewählten Restaurants untereinander, durchnummeriert, **per Drag & Drop
umsortierbar**. Bestätigen.

### 9. Preisprognose und Höchstbetrag

Aus Bestellung und (falls vorhanden) Speisekarten wird eine **Hochrechnung** erstellt —
und **ausdrücklich als Schätzung gekennzeichnet**.

> *„Geschätzt kostet es 50 €. Geben Sie einen Höchstbetrag an, den Sie zahlen möchten.
> Wir fragen ihn vor der Bestellung ab und schließen nur ab, wenn er eingehalten wird.
> Andernfalls legen wir Ihnen einen Rückruf beim Restaurant nahe."*

- **Speisekarten** kommen aus dem Scraping **oder** werden vom Nutzer hochgeladen; ein
  Modell wertet sie aus (lokal oder auf dem Server).
- **Lieber etwas höher schätzen**, damit der Nutzer nicht enttäuscht wird.
- Ist es zu teuer: zurück, Sachen abwählen, **neue Prognose**.
- Danach die Warnung, dass ohne Einhaltung nicht bestellt wird → **„Bestellen"**.

### 10. Die Anrufe — Fortschritt sichtbar

Die Restaurantliste steht ohnehin schon da. Daran wandert ein **Telefonhörer-Symbol**:

- **grau** = wird gerade gewählt
- **grün** = Gespräch steht
- **Klick darauf** → das Gesprächsprotokoll dieses Anrufs
- **Abbruch** → Restaurant wird **durchgestrichen**, der Hörer wandert weiter
- **Erfolg** → ein Symbol erscheint, ein **heller Ton**, alle übrigen werden ausgegraut

### 11. Nach der Bestellung

- Das Transkript des erfolgreichen Anrufs geht **als Beleg per E-Mail** an den Nutzer
  (wenn eine Adresse hinterlegt ist).
- Sind **Konnektoren** hinterlegt (z. B. WhatsApp), kommt die Nachricht auch dort an.
- Wurde im Gespräch eine **Lieferzeit** genannt: **Countdown**, wann das Essen ungefähr da ist.
- Wurde ein **genauer Betrag** genannt: der steht dort, nicht die Schätzung.
- Dazu die **benutzte Telefonnummer** und der Kontakt zum Restaurant.
- Läuft der Countdown ab: Animation — **„Guten Appetit"**.

---

## Der Abholweg

„Die Abweichungen sind nicht sonderlich groß" — im Wesentlichen wie Lieferung, ohne
Lieferadresse, mit Abholzeit statt Lieferzeit. Details zeigen sich im Gespräch selbst.

---

## Tisch reservieren

Der **einfachste Modus** — das ganze Essensthema entfällt.

Nötig sind nur:
- **Personenzahl**
- **Besonderheiten:** drinnen oder draußen, hinten in der Ecke, Schattenplatz, …
- **Kinder:** wie viele, Babystühle, Kleinkindstühle
- ein **Freifeld** für alles, woran man nicht denkt: *„Gibt es ein besonderes Anliegen,
  das wir dort erfragen sollen?"*

Restaurantauswahl und Prioritätenliste wie gehabt.

> **Schöner Nebeneffekt, den der Nutzer benennt:** Man muss gar nicht wissen, ob offen ist
> — man nimmt einfach alle, die man haben möchte. *„Jemand anderes testet das jetzt für
> einen durch."*

Bei Erfolg: **Reservierungsbestätigung** auf dem Bildschirm, Protokoll per E-Mail, sonst
am Bildschirm.

---

## Wiederverwendung aus dem Bestand (Nutzer-Idee)

Genannt: **MediaBrain** (selbstaufbauende Datenbank), **Kontaktbuch**, **Mail-Connector /
IMAP-Modul** — „wie es ja auch ursprünglich gedacht ist von unserem ellmos: einen Stack
bauen".

### Ist das im Wettbewerb erlaubt? — **Ja.** (geprüft in den Regeln)

Die Regeln verlangen, dass die Einreichung *„your original work product"* und
*„solely owned by you"* ist — **eigene Module erfüllen das per Definition**.

Zum Alter der Bausteine sagt die Regel:

> „Projects must be either newly created by the Entrant or, if the Entrant's Project
> existed prior to the Hackathon Submission Period, **must have been significantly
> updated after the start of the Hackathon Submission Period**."

→ **Bestandsmodule dürfen einfließen**, solange der Beitrag selbst nach dem 23.07.2026
wesentlich entstanden ist — und die wesentlichen Änderungen sind zu **erläutern**.
Das ist bei uns ohnehin der Fall: Der CALL-E-Teil ist komplett neu.

Open Source ist ausdrücklich erlaubt, wenn Lizenzen eingehalten werden und die
Einreichung das zugrundeliegende Produkt *„enhances and builds upon"*.

---

## Bedenken des Operators (nicht vom Nutzer)

**1. Der Umfang ist die eigentliche Gefahr.**
Das hier ist eine vollwertige Produkt-App. Dazu kommen zwei weitere Werkzeuge und
44 Tage bis zur Frist. Ohne Schnitt wird nichts davon fertig. Vorschlag weiter unten.

**2. Restaurantsuche: Quelle klären, bevor gebaut wird.**
Google Places kostet und hat Nutzungsbedingungen; Scraping von Portalen ist rechtlich
heikel. **OpenStreetMap / Overpass** liefert Name, Typ, Adresse, Telefon und
Öffnungszeiten frei und legal — das ist vermutlich die richtige Basis. Karte dann
Leaflet + OSM-Kacheln, ebenfalls frei.

**3. Speisekarten und Preisprognose sind der wackeligste Teil.**
Speisekarten liegen meist als PDF oder Bild vor, oft gar nicht online. Eine Schätzung,
die danebenliegt, beschädigt das Vertrauen mehr, als sie nützt. Der Höchstbetrag
funktioniert auch **ohne** Prognose — er ist ohnehin die harte Grenze.

**4. Der Jury-Standort.** Berechtigter Punkt des Nutzers. Zu bedenken: CALL-E ruft nur in
17 Ländern an; Singapur ist dabei, ebenso Deutschland. Für die Demo heißt das: Die
Ortssuche muss international funktionieren — mit OSM tut sie das.

## Vorschlag für den Schnitt

**Kern (muss fertig werden, trägt das Video):**
Ort + Umkreis → Suche (OSM) → Karte mit an-/abwählbaren Punkten → Modus →
Essenswunsch als Freitext → Restaurantauswahl + Drag-&-Drop-Priorität → **Höchstbetrag** →
Kaskade mit wanderndem Telefonhörer und Protokoll je Anruf → Ergebniskarte mit Betrag,
Lieferzeit, Rückrufnummer und Transkript.

**Kür (wenn Zeit bleibt, in dieser Reihenfolge):**
Personenprofile mit Besonderheiten („keine Oliven") · Countdown + „Guten Appetit" ·
E-Mail-Beleg · Tisch-Reservierung als eigener Modus · KI-Symbole je Küchentyp ·
Speisekarten-Auswertung und Preisprognose · WhatsApp-Konnektor

**Begründung des Schnitts:** Der Kern zeigt im Video alles, was die Bewertung honoriert —
ein echtes Problem, sichtbare nicht-triviale Logik, ein vollständiger Ablauf. Die Kür ist
das, was das Produkt später gut macht, aber im Wettbewerb keine zusätzlichen Punkte holt.
