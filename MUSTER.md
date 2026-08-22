# Das Muster hinter „I am hungry"

> Erkannt vom Nutzer am 2026-08-02: Essen bestellen ist nur **ein Fall** eines allgemeinen
> Musters. Das ist der eigentliche Beitrag für die Gemeinschaft — nicht die App.

## Das Muster in drei Sätzen

**Ich lege fest, was ich will** — als Kriterien, Prioritäten und Grenzen, nicht als Auftrag
an einen bestimmten Anbieter.
**Das Werkzeug sucht, wer dazu passt** und bringt die Kandidaten in eine Reihenfolge.
**Dann wird der Reihe nach telefoniert, bis einer alle Bedingungen erfüllt** — und ab da
niemand mehr.

```
Kriterien + Grenzen   →   Kandidaten finden + ranken   →   Kaskade mit Urteil
                                                              ↓
                                            Gate verletzt → höflich raus, nächster
                                            alle erfüllt  → abschließen, Rest stoppen
```

## Warum das mehr ist als Essen

Der Nutzer hat es an einem zweiten Fall durchgespielt — **Zahnarzttermin**:

> „Ich brauche einen Zahnarzttermin, nicht weiter als 30 Kilometer entfernt. Ich bin
> bereit zu zahlen, auch privat, bis 30 Euro — hauptsächlich will ich den Termin. **Aber
> biete das nicht zuerst an, sondern versuch erst, einen regulären Termin zu bekommen.**
> Zeiten, an denen ich kann: Dienstag, Mittwoch, Donnerstag vormittags. Im Notfall nehme
> ich jeden Termin, **aber erst verhandeln**. Und such vorher Bewertungen — möglichst
> besser als vier Sterne."

Derselbe Ablauf, anderer Gegenstand. Weitere Fälle liegen auf der Hand: Handwerker mit
freiem Termin, Ersatzteil auf Lager, Werkstatt mit Kapazität, Kursplatz, Pflegedienst.

## Was der Zahnarztfall dem Muster hinzufügt: **gestufte Zugeständnisse**

Bei „I am hungry" ist der Höchstbetrag eine harte Grenze — erreicht oder nicht.
Beim Zahnarzttermin ist es feiner: Es gibt **Dinge, die man zu geben bereit ist, aber
nicht sofort.**

> „Auch privat, bis 30 Euro — **aber biete das nicht zuerst an.**"

Das ist eine **Verhandlungsstufe**: eine Karte, die im Ärmel bleibt, bis der reguläre Weg
gescheitert ist. Ein Agent, der sie sofort ausspielt, verschenkt Geld — und verhält sich
anders, als ein Mensch es täte.

Daraus folgt eine dritte Art von Bedingung:

| Art | Bedeutung | Beispiel |
|---|---|---|
| **Muss** | ohne das kein Abschluss | „nicht weiter als 30 km" |
| **Grenze** | bis hierhin, nicht weiter | „höchstens 30 Euro Endbetrag" |
| **Zugeständnis** | vorhanden, aber gestuft — erst wenn nötig | „privat zahlen, aber erst nach dem regulären Versuch" |
| **Wunsch** | verbessert die Rangfolge, blockiert nichts | „möglichst über vier Sterne" |

**Zugeständnisse haben eine Reihenfolge.** Der Agent arbeitet sie ab, statt sie zu bündeln:
erst der reguläre Termin, dann der ungünstige Zeitpunkt, dann die Privatleistung. Jede
Stufe ist ein eigener Versuch im selben Gespräch.

## Was das für den Wettbewerb bedeutet

Die Bewertung honoriert ausdrücklich, was **„reusable by the community"** ist. Eine App zum
Essenbestellen ist es nicht. **Ein Kaskadenmuster mit Urteil, Grenzen und gestuften
Zugeständnissen schon** — es lässt sich auf jede Suche übertragen, bei der man mehrere
Stellen abtelefonieren muss, bis eine passt.

Deshalb gehört das Muster ins README und ins Video, nicht nur die Pizza.

## Woran sich das Muster von der Anbieter-App unterscheidet

Der CALL-E-Chat erledigt **einen** Anruf mit **einem** Ziel. Hier geht es um:

- **mehrere Kandidaten**, die erst gefunden und geordnet werden müssen
- **Kriterien, die im Gespräch geprüft werden**, nicht vorher feststehen
- **eine Abbruchentscheidung je Anruf** und den Übergang zum nächsten
- **einen Zustand über die Kaskade hinweg** — wer wurde gefragt, woran ist es gescheitert
- **gestufte Zugeständnisse**, die über Gespräche hinweg verwaltet werden

Das ist der Unterschied zwischen einem Anruf und einer Suche.

## Stand: das Muster ist jetzt im Code, nicht nur im Text [2026-08-02]

Bis hierhin war dieses Dokument eine Beschreibung. Der zweite Zweig der App —
**Tisch reservieren** — ist der Beleg, dass die Kaskade über Essen hinausträgt:
dieselbe Mechanik, kein einziges gemeinsames Kriterium. Statt Preis, Lieferung
und Zeitfenster entscheidet dort die Uhrzeit, die Personenzahl und drinnen
gegen draußen.

**Zugeständnisse sind eine Vollmacht, kein Hinweis.** Das ist der Punkt, an dem
sich die Umsetzung von der bloßen Idee unterscheidet:

- Der Nutzer erteilt sie ausdrücklich. Für die Essens-Zweige (Lieferung/Abholung)
  sind das die `FOOD_CONCESSIONS`-Stufen (`wait_longer_ok`, `higher_price_ok` —
  beide mit einem eigenen Eingabefeld statt fester Werte seit dem
  Endabnahme-Befund E2 2026-08-22; die dritte, `substitute_ok`, wurde als
  Duplikat der genaueren posten-eigenen Ersatzlogik entfernt, siehe E1);
  der Tisch-Zweig regelt dasselbe Prinzip seit der
  Auslagerung der Zeit-/Gebührenfelder über die numerischen Felder
  `earlier_hours`/`later_hours`/`max_booking_fee_eur` statt über einzelne
  Zugeständnis-Schlüssel — Legacy-Zugeständnisse sind ihm ausdrücklich
  verboten (siehe die `ValueError` in `engine.build_call_goal`).
- Sie gehen **in Stufenreihenfolge** in den Auftragstext, mit der Anweisung,
  keine spätere Stufe vor einer gescheiterten früheren anzubieten.
- Das Ergebnis muss melden, welche Stufe gezogen wurde (`tier_applied`).
- **Ein Ergebnis, das eine nicht erteilte Stufe verwendet hat, wird
  zurückgewiesen** — genau wie ein Angebot über dem Höchstbetrag. Ein Agent,
  der den Tisch mit Geld gekauft hat, das ihm niemand angeboten hat, hat sein
  Mandat überschritten; sein Ja zählt nicht.

Damit ist die Zugeständnisstufe symmetrisch zur Preisgrenze: beides sind
Vollmachten des Nutzers, und beide werden nach dem Gespräch geprüft, nicht
vorher geglaubt. Code: `CascadeEngine.check_concession_authority`,
`engine._concession_clause`. Belege in beide Richtungen:
`tests/test_cascade.py::test_unauthorised_concession_is_rejected` und
`tests/test_cli.py::test_cli_reservation_accepts_seating_and_concessions`.

## Offene Frage

Der Zahnarztfall braucht **Bewertungsrecherche vor dem Anruf** („besser als vier Sterne").
Das ist derselbe Rechercheschritt wie die Restaurantsuche — aber mit einer Qualitätshürde
davor. Ob das ein eigener Schritt im Muster ist („Kandidaten filtern") oder Teil des
Rankings, ist noch nicht entschieden.
