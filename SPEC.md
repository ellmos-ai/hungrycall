# SPEC — HungryCall *(Arbeitsname)*

> **Lies zuerst `AGENTS.md`.** Dort stehen die nicht verhandelbaren Regeln
> (Trockenlauf, Safety, Datensparsamkeit, was CALL-E kann).
> Der Sprachbefehl des Werkzeugs heißt **„I am hungry"** — der Projektname ist offen,
> der Nutzer entscheidet ihn final. `hungrycall` ist auf npm und GitHub frei.

## Das Problem

Auf dem Land gibt es viele Restaurants, aber keines ist bei einem Lieferdienst-Portal
dabei. Um überhaupt herauszufinden, **ob** jemand liefert, muss man anrufen. Und dann
nochmal. Und nochmal. Wer ungern telefoniert, isst deshalb, was das eine Restaurant
anbietet, dessen Nummer er auswendig kann.

## Warum das eine echte Lücke ist

Im offiziellen Ziel-Repo gibt es **keinen** Beitrag zu Restaurants, Bestellungen oder
Reservierungen. Alle vorhandenen Apps rufen genau eine Person zu genau einem Zweck an.
Eine **Kaskade mit Abbruch bei Erfolg** existiert dort nicht.

## Die drei Modi

### 1. Lieferung
Fragt: *Liefern Sie nach `<Adresse>`? Wie lange dauert es? Was kostet es?*
Bei Erfüllung aller Kriterien: **Bestellung aufgeben** innerhalb des Höchstbetrags.

### 2. Tisch reservieren
Fragt: *Freier Tisch am `<Datum>` um `<Uhrzeit>` für `<n>` Personen?*
Bei Erfolg: Bestätigung **mit Rückrufnummer zum Abbestellen**.

### 3. Abholung
Wie Lieferung, ohne Lieferadresse — fragt nach Abholzeit statt Lieferzeit.

## Ablauf

1. **Profil / Wunsch**
   - dauerhaftes Profil (Lieblingsessen, Unverträglichkeiten) **oder** spontan
     „die drei Dinge, die ich jetzt am liebsten essen würde"
   - Ort + Umkreis, Lieferadresse, Favoriten-Restaurants

2. **Recherche** *(Eigenleistung, nicht CALL-E)*
   - passende Restaurants im Umkreis, Öffnungszeiten, Lieferhinweise, Telefonnummer
   - Fallback: E-Mail-Adresse, falls vorhanden
   - Quelle offenlassen (Websuche/Places/lokale Liste) — aber **im Trockenlauf müssen
     Fixtures reichen**

3. **Rangfolge**
   - Präferenz des aktuellen Wunsches + Favoriten höher gewichtet
   - **Wichtig:** Der aktuelle Essenswunsch **schlägt** das Lieblingsrestaurant.
     Wer Burger will, bekommt nicht den Lieblings-Italiener vorgeschlagen.
   - Öffnungszeiten schließen Kandidaten vorab aus (kein Anruf bei geschlossenem Laden)

4. **Kaskade**
   - anrufen → Antwort gegen die Abbruchkriterien prüfen
   - **Kriterium verletzt** → höflich verabschieden, nächster Kandidat
   - **alle Kriterien erfüllt** → abschließen (bestellen/reservieren) und
     **keine weiteren anrufen**
   - Liste erschöpft → ehrlich melden, was fehlgeschlagen ist und warum

5. **Erfolgsmeldung**
   > „Bestellt bei *Trattoria Bella*: liefert in 40 Minuten, zwei Burger und zwei
   > Getränke, 30 €. Rückruf unter +49 ••• ••••123."

## Der Höchstbetrag — die entscheidende Sicherung

Der Agent bekommt das Limit **vorab** mit, erfragt den Preis und lehnt bei Überschreitung
ab. Drei harte Regeln:

1. **Das Limit ist der Endbetrag an der Haustür** — inklusive Liefergebühr,
   Mindestbestellwert, allem. Nicht der Speisenpreis.
2. **Unklare Preisauskunft = Ablehnung, nicht Schätzung.** „So ungefähr dreißig" oder
   „kommt auf die Beilagen an" ist keine prüfbare Zahl → höflich verabschieden,
   nächster Kandidat. Lieber ein Anruf mehr als eine Überraschung.
3. **Nach der Zusage gibt es kein Zurück.** Deshalb **immer** die Rückrufnummer ausgeben.

**Vorbild im Ziel-Repo:** `apps/typescript/call-on-behalf` begrenzt die Autorität des
Agenten über `goal.commitment` (`none` bzw. „darf nur innerhalb dieser Zeitfenster
zusagen"). Wir übertragen dasselbe Prinzip von Zeitfenstern auf **Geldbeträge**. Das ist
die Fortsetzung ihres Designs, kein Bruch damit — und gehört so ins README.

## Schema-Arbeit (Kern)

`result_schema` je Modus, z. B. Lieferung:

```json
{
  "type": "object",
  "required": ["delivers_to_address", "price_known"],
  "properties": {
    "delivers_to_address": {"type": "boolean"},
    "price_known":         {"type": "boolean"},
    "total_price_eur":     {"type": "number"},
    "eta_minutes":         {"type": "integer"},
    "order_placed":        {"type": "boolean"},
    "callback_number":     {"type": "string"},
    "rejection_reason":    {"type": "string"}
  }
}
```

`price_known: false` **muss** zur Ablehnung führen — auch wenn `total_price_eur` gesetzt
ist. Der Agent darf nicht raten, und der Code darf ihm nicht glauben, wenn er es doch tut.

## Fallstricke

- Restaurants sind Geschäfte mit veröffentlichter Nummer, die Bestellanrufe erwarten —
  **der Anruf selbst ist unkritisch**. Das ist die risikoärmste der drei Ideen.
- Die **Bestellung ist ein mündlicher Vertrag** ohne Papier. Das **Transkript ist der
  einzige Beleg** und gehört ins Ergebnis, nicht nur ins Log.
- Der Anruf muss offenlegen, dass eine Maschine im Auftrag von `<Name>` anruft.
- Keine Anrufe außerhalb der Öffnungszeiten. Kein zweiter Anruf beim selben Restaurant
  in derselben Runde.

## Was Erfolg bedeutet

Ein Trockenlauf, der aus einem Wunsch („ich will Burger, maximal 35 €, Lieferung nach X")
eine gerankte Kandidatenliste erzeugt, die Kaskade mit simulierten Antworten durchspielt
— darunter mindestens eine Ablehnung wegen Preisüberschreitung und eine wegen unklarer
Preisauskunft — und mit einer Erfolgsmeldung endet, die man vorlesen könnte.
