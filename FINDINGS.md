# FINDINGS — gemessen am echten Dienst, 2026-08-01

> Ergänzt `AGENTS.md`. **Diese Befunde stammen aus einem echten Anruf und echten
> API-Aufrufen**, nicht aus der Doku. Wo sie der Doku widersprechen, gilt die Messung.
> Belegt in `.HACKATHONS/2026-call-e/_evidence/EVIDENCE-001` und `-002` (Operator).

## 1. Man KANN live mitlesen — über `activity`, nicht über `transcript`

Während des Gesprächs bleibt `transcript` **`null`**. Aber `activity` enthält den
Gesprächsverlauf in Echtzeit, beide Sprecher, mit Millisekunden-Zeitstempeln:

```
17:37:45.146 | Call is ringing.
17:37:49.509 | Call connected.
17:37:50.769 | Bot is speaking: Dies ist ein automatisierter Testanruf im Auftrag von Alex.
17:37:51.577 | Callee said: hallo
17:37:52.245 | Callee said: Hallo.
17:38:15.892 | Callee said: 2. Ja, unzufrieden.
17:38:21.375 | Call ended; syncing final Calling result.
```

**Achtung Dubletten:** „Callee said" kommt teils zweimal — erst eine Rohfassung
(`hallo`), Sekundenbruchteile später die korrigierte (`Hallo.`). Die Spracherkennung
liefert streamend und bessert nach. Wer mitliest, muss zusammenführen.

## 2. `status` ist als Fortschrittsanzeige unbrauchbar ⚠️

Der Status blieb auf **`PREPARING`**, während bereits gesprochen wurde — und sprang erst
nach Gesprächsende auf `COMPLETED`:

```
17:37:53Z | status=PREPARING | activity=12 | last: Callee said: Hallo.
17:38:09Z | status=PREPARING | activity=15 | last: Bot is speaking: Bitte antworten Sie mit…
17:38:45Z | status=COMPLETED | activity=21 | last: Call ended from realtime events.
```

**Wer auf `status` wartet, verpasst das Gespräch.** Fortschritt kommt aus `activity`.

## 3. Das Transkript liegt in `result.transcript` ⚠️

`structuredContent.transcript` ist `null` — auch nach Abschluss.
Das Transkript steht in **`structuredContent.result.transcript`**, als **String**
(nicht als Liste), Format `[mm:ss] SPRECHER: Text`, Sprecher `BOT` / `USER`.

## 4. Wörtliche Vorgaben halten bis ins gesprochene Wort ✅

Ein in **Anführungszeichen** gesetzter Fragetext wurde zeichengenau gesprochen —
einschließlich eines absichtlichen Tippfehlers („oeffentlichen"). Ein umformulierender
Agent hätte ihn korrigiert.

**Regel:** Was in Anführungszeichen steht, wird zitiert. Was außerhalb steht, wird
umformuliert **und ergänzt** — der Planer fügt eigenständig Verhaltensregeln hinzu
(z. B. Voicemail-Verhalten), die nicht in der Eingabe standen.

## 5. Kein Ergebnis-Schema über MCP/CLI ⚠️ betrifft die Architektur

`plan_call` kennt: `plan_id`, `to_phones`, `region`, `language`, `goal`, `scheduled_at`,
`retry_confirmation_action`, `user_input`, `ttl_seconds`.
**Kein `result_schema`, kein `recipient_result_schema`.**

Schema-validierte Ergebnisse gibt es nur über die **REST-API**
(`POST /v1/calls`, Header `Authorization: Bearer $CALLE_API_KEY`).

**Und beide Wege sind getrennte Welten:** Ein über MCP gestarteter Anruf ist über
`GET /v1/calls/{run_id}` **nicht** abrufbar (geprüft: HTTP 404 bei gültigem Key).
Wer Schemas will, muss den Anruf **über REST starten**, nicht nur dort abfragen.

→ Für Werkzeuge, die strukturierte Antworten brauchen, ist **REST der Hauptweg**;
MCP/CLI taugt für interaktive Einzelanrufe.

## 6. Zeitverhalten

| Ereignis | Abstand zum `run_call` |
|---|---|
| Bot wird erzeugt | +2 s |
| Anruf klingelt | **+39 s** |
| verbunden | +43 s |
| Gespräch beendet (32 s Gesprächszeit) | +75 s |
| `status` = COMPLETED | +99 s |

**Rund 40 Sekunden Vorlauf pro Anruf**, unabhängig von der Gesprächslänge. Seriell
gerechnet also ~1,5 Minuten pro Anruf, auch bei kurzen Gesprächen.

## 7. Der Agent interpretiert freie Antworten

„2. Ja, unzufrieden." wurde eigenständig als *unzufrieden* kategorisiert;
`completion_confidence` 0.92 („high"), dazu drei Belegsätze in `evidence`.

**Folge: Rohantwort immer mitführen, nicht nur die Deutung** — sonst ist nicht mehr
prüfbar, ob richtig kategorisiert wurde.

## 8. Kleinigkeiten

- API-Keys beginnen **nicht** mit `calle_live_` (so die Doku), sondern mit `iams_live_`.
  Nicht auf das Präfix prüfen.
- Es gibt ein viertes, undokumentiertes MCP-Werkzeug `track_ui_events` (UI-Telemetrie,
  für uns irrelevant).
- Ohne Rufnummer liefert `plan_call` `ready_to_run: false` und `confirm_token: null` —
  ein Anruf ist dann nicht auslösbar. Sauberer Schutz, auf den man sich verlassen kann.
- Pläne haben eine TTL von 24 Stunden.

## Weiterhin ungeprüft

- **Parallelität.** Ob mehrere Anrufe gleichzeitig laufen, ist offen. „concurrency
  controls" sind dokumentiert, die Grenze nicht. **Im Code beide Fälle offenhalten.**
- Verhalten bei Voicemail, Besetzt, Nicht-Abheben — bisher nur `COMPLETED` gesehen.
- Ob REST- und MCP-Weg dasselbe Kontingent teilen.

## 9. Live-measured status matrix and transport findings (2026-08-11)

> **Privacy-safe evidence boundary:** The findings below came from supervised live
> cascades to one consenting test line. No raw transcript, call/order identifier,
> personal name, exact timestamp or phone-number fragment is published. Dialogue
> examples are synthetic reproductions, not quotations. Facts marked
> **operator-observed** could not be independently reconstructed from a durable public
> artifact.

1. **Mailbox pickup could look completed — operator-observed.** A mailbox interaction
   returned a completed result rather than a distinct voicemail state. Status alone
   therefore cannot prove that a person was reached.
2. **Decline details and apparent provider retries — operator-observed.** The useful
   decline reason appeared in a failure message, while multiple provider dial attempts
   could still collapse into one application-level attempt.
3. **Recipient transcript turns are the usable transcript source.** The real top-level
   transcript was empty; `LiveCallClient._transcript_from_turns()` reconstructs the
   result from recipient attempt turns.
4. **The sparse top-level structured result shadowed the populated recipient result.**
   This caused three false-negative cascades and was fixed in `ff7f5ce` by preferring
   recipient data.
5. **A timed-out create request can still produce a call.** Commit `1b9883f` retries
   with the same idempotency key, preventing a second dial while re-attaching to the
   first request.
6. **Failed-call billing behaviour was operator-observed.** The repository cannot
   independently reconstruct provider balance changes, so it makes no general pricing
   claim from that observation.
7. **Prompt coverage did not guarantee quantity compliance.** The configured fallback
   quantity was two; the spoken closeout placed one, and the old result schema did not
   expose that mismatch. The following is a synthetic representation of the measured
   defect:

```text
[SYNTHETIC REPRODUCTION]
PLAN: Order two units of the accepted fallback item.
AGENT CLOSEOUT: Please confirm one unit.
LOCAL AUDIT BEFORE FIX: Accepted because ordered quantity was not represented.
LOCAL AUDIT AFTER FIX: Reject because the confirmed quantity differs from the plan.
```

The quantity field and evaluator check added after the trial close this specific gap.
The broader lesson remains: a correct prompt is not evidence that the result honoured
it; every material outcome needs an independently checkable result field.
