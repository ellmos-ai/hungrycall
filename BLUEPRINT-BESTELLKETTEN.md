# Blueprint: Bestellwunschketten

> Formalisierung der Nutzer-Beschreibung vom 2026-08-02 in Felder, Schalter und Regeln.
> Nach dem Verfahren aus `software-in-worten`: Ein Klick ist eine Entscheidung, eine
> Einstellung ist Config, und was nach dem Klick passiert, ist ein Skill.
> **Noch nicht gebaut.** Dies ist der Schaltplan, aus dem gebaut wird.

## Der Kern in einem Satz

Eine Bestellung ist keine Liste von Wünschen, sondern eine **Kette von Bedingungen mit
Rückfallpositionen** — und jede Bedingung ist entweder hart (Abbruch) oder weich
(weitermachen).

---

## 1. Die Bestellzeile

Jede Zeile ist ein Posten. Erste Zelle = Wunsch, folgende Zellen = Ersatzwünsche in
absteigender Präferenz.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  POSTEN 1                                                     [Tag: Lukas ▾] │
│                                                                              │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐            │
│   │ (1) Burger      │ → │ (1) Burger      │ → │ (3) Toast       │  [ + ]     │
│   │        ⚙        │   │        ⚙        │   │        ⚙        │            │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘            │
│      Wunsch                1. Ersatz             2. Ersatz      weitere       │
│                                                                              │
│   Wenn keiner davon verfügbar:  [ Posten weglassen ▾ ]                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                                                    [ + Posten ]
```

**Gelesen als:** *Wenn es das nicht gibt, dann das. Wenn es das nicht gibt, dann das.
Und wenn gar nichts davon — dann diese Regel.*

### Felder je Zelle

| Feld | Typ | Vorgabe | Bemerkung |
|---|---|---|---|
| `menge` | Zahl ≥ 1 | 1 | der Zähler vor dem Produkt |
| `produkt` | Text | — | Pflicht in der ersten Zelle |
| `art` | Auswahl | `essen` | `essen` \| `getraenk` — Getränke sind gleichwertige Posten |

### Felder je Zeile

| Feld | Typ | Vorgabe | Bemerkung |
|---|---|---|---|
| `tag` | Auswahl (mehrfach) | leer | frei anlegbare Tags, siehe Abschnitt 4 |
| `wenn_nichts_verfuegbar` | Auswahl | `posten_weglassen` | siehe unten |

### Die Regel am Zeilenende

| Wert | Bedeutung | Härte |
|---|---|---|
| `posten_weglassen` | Dieser Posten entfällt, der Anruf läuft weiter | **weich** |
| `bestellung_abbrechen` | Der gesamte Anruf endet ohne Bestellung | **hart** |

---

## 2. Zusatzkriterien je Zelle (das ⚙-Symbol / Rechtsklick)

Pro Zelle beliebig viele. **Jedes einzelne ist hart oder weich.**

```
┌─ Zusatzkriterien für „(1) Burger" ───────────────────────────┐
│                                                              │
│  ☑ Höchstpreis         [ 12,00 ] €      ( ) hart  (•) weich  │
│  ☑ Sonderwunsch        [ ohne Gurken ]  ( ) hart  (•) weich  │
│  ☑ Rückfrage           [ Haben Sie den Burger glutenfrei? ]  │
│         └─ bei JA:     (•) annehmen   ( ) ablehnen           │
│         └─ bei NEIN:   ( ) annehmen   (•) nächster Ersatz    │
│                                                              │
│                                        [ Abbrechen ] [ OK ]  │
└──────────────────────────────────────────────────────────────┘
```

### Die drei Kriterienarten

| Art | Eingabe | Was der Agent am Telefon tut |
|---|---|---|
| `hoechstpreis` | Betrag | fragt den Einzelpreis und vergleicht |
| `sonderwunsch` | Freitext | bittet darum und wartet auf Bestätigung |
| `rueckfrage` | Frage + zwei Reaktionen | stellt die Ja-Nein-Frage, reagiert je nach Antwort |

### Die drei möglichen Reaktionen

| Reaktion | Wirkung |
|---|---|
| `annehmen` | Kriterium gilt als erfüllt, weiter im Ablauf |
| `naechster_ersatz` | diese Zelle scheitert, die nächste Zelle wird versucht |
| `ablehnen` (hart) | der ganze Posten scheitert → Zeilenregel greift |

**Vorgabe bei Sonderwunsch:** bestätigt → `annehmen`. Nicht bestätigt → einstellbar,
Vorgabe `naechster_ersatz`.

---

## 3. Die Übersetzung ins Gespräch

Derselbe Schaltplan, gelesen als Gesprächsablauf — **das ist der Skill-Text, den der
Agent ausführt:**

```
Für jeden Posten, in Reihenfolge:
  Für jede Zelle, in Reihenfolge:
    Frage: „Haben Sie <menge>× <produkt>?"
      NEIN            → nächste Zelle
      JA              → prüfe die Zusatzkriterien dieser Zelle:
          Höchstpreis   → „Was kostet das?"  über Grenze → je nach Härte
          Sonderwunsch  → „Ginge das <wunsch>?"  abgelehnt → je nach Härte
          Rückfrage     → „<frage>"  Antwort → hinterlegte Reaktion
      alle Kriterien erfüllt → Posten übernommen, nächster Posten
  keine Zelle hat getragen → Zeilenregel:
      posten_weglassen      → merken, weiter
      bestellung_abbrechen  → Gespräch höflich beenden
```

**Damit ist bewiesen, was das Projekt behauptet:** Eine Definition, drei Zugänge — die
Zelle in der Oberfläche, die Frage im Gespräch, der Eintrag in der Config.

---

## 4. Tags

Frei anlegbar, kein festes Schema. Beispiel des Nutzers: eine Familie mit `Lukas`,
`Simon`, `Claud`, `Renate`.

- Jeder Posten (Essen wie Getränk) kann beliebig viele Tags tragen
- Tags werden im Profil gespeichert und stehen bei der nächsten Bestellung zur Auswahl
- **Beim Bestellabschluss: Übersicht nach Tags gruppiert** — wer bekommt was

```
┌─ Bestellübersicht ───────────────────────────────┐
│  Lukas      1× Burger, 1× Cola                   │
│  Simon      1× Pizza Margherita                  │
│  Renate     1× Salat (ohne Zwiebeln)             │
│  ohne Tag   3× Toast                             │
│                                    Summe 42,50 € │
└──────────────────────────────────────────────────┘
```

---

## 5. Profil und Vorlagen

Ersetzt die ursprünglich geplante Kontaktseite — der Nutzer hält Vorlagen für sinnvoller.

| Was | Wird gespeichert | Wozu |
|---|---|---|
| **Bestellvorlagen** | vollständige Bestellketten samt Kriterien | „Freitagabend wie immer" |
| **Tag-Vorlagen** | die angelegten Tags | einmal die Familie erfassen |
| **Verlauf** | jede abgeschickte Bestellung | wiederverwendbar und anpassbar |

Eine Bestellung aus dem Verlauf lässt sich laden, ändern und erneut abschicken.

---

## 6. Was daraus zu bauen ist

| Schritt | Umfang |
|---|---|
| Datenmodell für Posten, Zellen, Kriterien, Tags | klein — es sind vier verschachtelte Strukturen |
| Oberfläche: Zeilen mit Zellen, ⚙-Dialog, Tag-Auswahl | mittel |
| Übersetzer Kette → Gesprächsanweisung | klein, siehe Abschnitt 3 |
| Auswertung der Agentenantwort gegen die Kriterien | mittel — das ist die eigentliche Logik |
| Profil, Vorlagen, Verlauf | klein |
| Abschlussübersicht nach Tags | klein |

**Einschätzung des Nutzers, die sich hier bestätigt:** *„hört sich größer an, als es ist —
man muss es einmal formalisieren in Wort und Schalterregeln, also einen Schaltplan, und
dann kann man es gut umsetzen."* Der Kern sind drei Schachtelungen (Posten → Zelle →
Kriterium) und zwei Härtegrade. Alles andere ist Darstellung.
