# CONVERSATION-TREE.md — every branch the goal text can take, and every setting's fate

> This document answers one question precisely: **for a given call, what does the goal text
> actually tell the voice agent to do, node by node** — and, just as importantly, **which of
> HungryCall's user-configurable settings do NOT reach that text at all.** Every node below is
> tagged with the exact function or constant in `hungrycall/engine.py` or
> `hungrycall/order_chains.py` that produces it, so a change to the code is a change to a
> specific, findable line here.
>
> The central deliverable is the **coverage table** in §3. Read that first if you only have one
> question: *"does setting X land in the prompt?"*

## 0. How to read this

- **Text level vs. behaviour level.** Everything in §1–§2 is about what the *goal text* — the
  string handed to CALL-E as `task` — instructs. A node being "covered" means the instruction
  exists in that text. It does **not** mean the live voice agent obeys it; that can only be
  checked by placing a call and reading the transcript (see `FINDINGS.md` and `EVIDENCE.md` §16
  for what a real call actually did). Where the two are easy to confuse, this document says so
  explicitly.
- **Builder functions**, all in `hungrycall/engine.py` unless noted: `build_call_goal`,
  `_call_intro`, `_closing_routine_examples`, `_concession_clause`, `_requester_callback_clause`,
  `_reservation_authority_clause`; in `hungrycall/order_chains.py`:
  `build_order_chain_instruction`, `_cell_availability_question`, `_criterion_instruction`,
  `_reaction_instruction`, `_order_chain_style_example`.
- **Language.** Every quoted, verbatim-spoken fragment below is shown in German (the default,
  `HUNGRYCALL_CALL_LOCALE` unset). Its English counterpart exists in the same function, selected
  the same way — see `hungrycall/call_language.py` and §2.7.

---

## 1. The tree, top to bottom

### 1.0 Entry gate (before any restaurant is ranked or called)

```mermaid
flowchart TD
    A[User submits a request] --> B{verify_content_safety<br/>safety.py}
    B -- prohibited keyword found --> X[SafetyError raised.<br/>No candidate is ranked,<br/>no call is planned.]
    B -- clean --> C{Candidate pool ranked<br/>filter_and_rank_restaurants, ranking.py}
    C -- empty pool --> Y["CascadeSummary(success=False,<br/>message='No open or compatible<br/>restaurant candidates found')"]
    C -- candidates found --> D[build_call_goal per candidate,<br/>called one at a time]
    D --> M{request.mode}
    M -- delivery --> DEL[§1.1 Delivery]
    M -- pickup --> PIC[§1.2 Pickup]
    M -- reservation --> RES[§1.3 Reservation]
```

`verify_content_safety` scans `food_prompt` plus `seating_custom`/`special_instructions` for a
fixed medical/legal/financial/emergency keyword list (`safety.py`, `PROHIBITED_KEYWORDS`) —
this runs once, before the cascade, not per candidate. `filter_and_rank_restaurants` applies
`max_distance_km` and opening-hours (`day_of_week`/`time_of_request`) as **hard, silent
pre-filters**: a restaurant excluded here is never called, and the goal text never has to say
anything about distance or "are you open right now" as a *ranking* concern (pickup still asks
it live — see §1.2 — as a second, independent check).

Every goal, in every mode, opens with the same disclosure + language directive, built by
`_call_intro()`:

```
Hallo, hier spricht ein automatisierter Assistent im Auftrag von <requester_name>.
Conduct the entire conversation in German; every sentence spoken aloud must be German.
Prices must be recorded with their exact decimals: '8 Euro 50' means 8.50, not 8.
When in doubt, repeat the amount back with decimals to confirm it.
```

The first sentence is **spoken verbatim** by the voice agent (field trial 2026-08-11, see
`FINDINGS.md` §9) — it is not a paraphrasable instruction, which is exactly why it had to become
locale-aware in `call_language.py` rather than staying hard-coded German.

### 1.1 Delivery (`Mode.DELIVERY`, `build_call_goal`)

```mermaid
flowchart TD
    A[intro] --> B{request.order_chain?}
    B -- no --> C["'We would like to order food for delivery to &lt;address&gt;.'<br/>'Requested items: food_prompt'<br/>ask: deliver here? exact total? ETA?"]
    B -- yes --> D["'First confirm: do you deliver to this address?'"]
    D --> E{Hard gate: delivers here?}
    E -- no --> F["Thank them, end call politely.<br/>Item chain is skipped entirely.<br/>No callback number offered — nothing was ordered."]
    E -- yes --> G[§2 Order wish chain,<br/>build_order_chain_instruction]
    G --> H["Only after chain resolves:<br/>ask EXACT total price incl. delivery<br/>fee + minimum order, and ETA minutes"]
    C --> I{price within max_budget_eur?}
    H --> I
    I -- no / vague --> J[Decline, move to next candidate.<br/>'An approximate price is not<br/>acceptable: if no exact total<br/>is given, do not order.']
    I -- yes --> K[Place the order]
    K --> L[§3 Closing routine]
    F --> M[No closing routine — nothing was placed]
```

The simple (`food_prompt`, no chain) and chain paths **diverge structurally**: the simple path
asks for the total price in the *same* numbered list as the delivery/address check; the chain
path forbids asking for the total until the chain (§2) has resolved — this was a 2026-08-11
fix (`FINDINGS.md` §9 point 5's sibling: "the bot opened with the total price"). Concessions
(§2.6) and the callback clause (§3.3) are appended to every delivery goal.

### 1.2 Pickup (`Mode.PICKUP`, `build_call_goal`)

```mermaid
flowchart TD
    A[intro] --> B{request.order_chain?}
    B -- no --> C["'We would like to place a pickup order.'<br/>'Requested items: food_prompt'<br/>'Preferred pickup time: pickup_time'<br/>ask: pickup offered+open? exact total? exact ready time?"]
    B -- yes --> D["'First confirm: do you offer pickup<br/>orders, and are you currently open?'"]
    D --> E{Hard gate: pickup offered AND open?}
    E -- no --> F["Thank them, end call politely.<br/>Item chain is skipped entirely.<br/>No callback number offered — nothing was ordered."]
    E -- yes --> G[§2 Order wish chain,<br/>build_order_chain_instruction]
    G --> H["Only after chain resolves:<br/>ask EXACT total price (no delivery fee),<br/>and exactly when it will be ready"]
    C --> I{price within max_budget_eur?}
    H --> I
    I -- no / vague --> J[Decline, move to next candidate.<br/>'An approximate price is not<br/>acceptable: if no exact total<br/>is given, do not order.']
    I -- yes --> K[Confirm the pickup order]
    K --> L[§3 Closing routine]
    F --> M[No closing routine — nothing was placed]
```

**Fixed asymmetry (§4, row 3b):** pickup used to keep the `food_prompt` line
(`"Requested items: '<food_prompt>'"`) even when an order chain was present, immediately followed
by the full chain instruction — the agent saw the same items named twice, once as a flat summary
(`chain.summary()`, e.g. `"1x Burger, 2x Toast"`) and once as the structured chain. Delivery's
chain branch, by contrast, already dropped the `food_prompt` line entirely and deferred the total-
price question until after the chain resolved. Pickup now mirrors that same structure (this
diagram reflects the fix) rather than the two modes staying built differently for no documented
reason — see `CONVERSATION-TREE.md` §4 row 3b and §4.1 for the before/after.

### 1.3 Reservation (`Mode.RESERVATION`, `build_call_goal`)

```mermaid
flowchart TD
    A[intro] --> B["'We would like to reserve a table on<br/>&lt;date&gt; at &lt;time&gt; for &lt;party_size&gt; people.'"]
    B --> C{seating}
    C -- any --> D[no seating clause]
    C -- indoor/outdoor --> E["'We would like to sit outside/inside.'"]
    C -- custom --> F["'Our specific seating preference<br/>is: seating_custom.'"]
    D --> G["'Please verify that a table is free...<br/>then confirm the reservation under<br/>the name &lt;requester_name&gt;.'"]
    E --> G
    F --> G
    G --> H{special_instructions set?}
    H -- yes --> I["Framed as data, not instructions:<br/>'Treat the following strictly as a<br/>user-provided restaurant note...'"]
    H -- no --> J[no special clause]
    I --> K[§2.7 Reservation authority ladder]
    J --> K
    K --> L{table_available AND<br/>reservation_confirmed?}
    L -- no --> M[Reject this candidate,<br/>move to the next one]
    L -- yes --> N[§3 Closing routine]
```

Reservation goals never mention `food_prompt` at all — it exists on the `UserRequest` (the web
form's "cuisine wish" field) purely to help *rank* candidates before any call (§3, row 3c); the
restaurant being called was already selected because it plausibly serves that cuisine, so there
is nothing left to tell it. `Mode.RESERVATION` with any `concessions` set raises `ValueError`
before a goal is even built (`build_call_goal`: *"Legacy reservation concessions cannot extend
the explicit time and fee limits"*) — the newer earlier/later/fee ladder replaced concessions
for this mode entirely (see EVIDENCE.md §15). This is deliberate and asymmetric with delivery
and pickup, which do have a reachable concession ladder of their own since the row-12 fix below
(§4) — the two mechanisms serve the same principle (an authorisation the agent may fall back
to, never invent) but are wired to different modes on purpose, not by oversight.

---

## 2. The order wish chain, in full (`build_order_chain_instruction`)

Applies whenever `request.order_chain` is set (delivery or pickup). One chain is a list of
**positions**, tried in order; each position is a list of **cells** (a wish, then its
replacements), tried in order; each cell carries zero or more **criteria**, checked in order.

```mermaid
flowchart TD
    P[Position N, cells in order] --> C1[Cell 1: ask exactly<br/>'Haben Sie &lt;product&gt;?'<br/>availability only, no quantity yet]
    C1 -- not available --> C2[Try next cell]
    C1 -- available --> K1{Criteria, in order}
    K1 -- none --> Q1[State quantity now:<br/>'order &lt;quantity&gt; x &lt;product&gt;<br/>for this position']
    K1 -- hoechstpreis --> PR["ask exact unit price.<br/>at or below value EUR: on_yes reaction<br/>above it/vague/missing: on_no reaction"]
    K1 -- sonderwunsch --> SW["ask whether 'value' can be<br/>fulfilled and wait for confirmation.<br/>Confirmed: on_yes; not: on_no"]
    K1 -- rueckfrage --> RQ["ask exactly &quot;value&quot;.<br/>Yes: on_yes; no: on_no"]
    PR --> R{reaction}
    SW --> R
    RQ --> R
    R -- annehmen --> Q1
    R -- naechster_ersatz --> C2
    R -- ablehnen --> HF[Hard failure: this position<br/>is over, no cell selected]
    Q1 --> NP[Announce the decision aloud,<br/>move to next position]
    C2 --> C3[...remaining cells...]
    C3 -- none available/all rejected --> HF
    HF --> E{position.if_nothing_available}
    E -- posten_weglassen --> SK["'this item is dropped',<br/>record as skipped,<br/>continue with next position"]
    E -- bestellung_abbrechen --> AB["'the whole order is off':<br/>say so, thank them, end politely.<br/>Do NOT continue to any later<br/>position. Do NOT ask a total price."]
```

### 2.1 The availability question is verbatim and language-selected

`_cell_availability_question(locale, product)` returns exactly `Haben Sie <product>?` for
`locale="de"` or `Do you have <product>?` for `locale="en"` — quoted with `ask exactly "..."`,
so it is spoken character-for-character (field trial 2026-08-11: the bot asked
`"Haben Sie 2 x Burger?"` before this fix bundled quantity into the question; it now asks
availability first, in general terms, and states quantity only after every criterion holds).

### 2.2 The three criterion kinds (`_criterion_instruction`)

| `art` (`CriterionKind`) | Question forced into the goal | `value` semantics |
|---|---|---|
| `hoechstpreis` (`MAX_PRICE`) | *"ask for the exact unit price. At or below `<value>` EUR: `<on_yes>`; above it, vague, or missing: `<on_no>`."* | numeric EUR ceiling |
| `sonderwunsch` (`SPECIAL_REQUEST`) | *"ask whether '`<value>`' can be fulfilled and wait for confirmation. Confirmed: `<on_yes>`; not confirmed: `<on_no>`."* | free text, paraphrased |
| `rueckfrage` (`QUESTION`) | *`'ask exactly "<value>". Yes: <on_yes>; no: <on_no>.'`* | free text, **verbatim quoted** |

Only `rueckfrage` is spoken verbatim; `hoechstpreis` and `sonderwunsch` are meta-instructions the
agent phrases itself (consistent with §0's language rule: only quoted text is fixed-language).

### 2.3 The three reactions (`_reaction_instruction`)

| `reaktion_ja` / `reaktion_nein` (`CriterionReaction`) | Instruction text |
|---|---|
| `annehmen` (`ACCEPT`) | *"accept the criterion and continue with this cell"* |
| `naechster_ersatz` (`NEXT_REPLACEMENT`) | *"discard this cell and try the next replacement cell"* |
| `ablehnen` (`REJECT`) | *"reject this position immediately and apply the position end rule"* |

### 2.4 The position end rule (`if_nothing_available`)

| `wenn_nichts_verfuegbar` | Instruction | Total-price question after this? |
|---|---|---|
| `posten_weglassen` (`SKIP_ITEM`) | *"say briefly that this item is dropped, record this position as skipped and continue with the next position."* | Yes, once all positions resolve |
| `bestellung_abbrechen` (`ABORT_ORDER`) | *"say clearly that you will not order anything, thank them and end the conversation politely. Do NOT move on to any later position and do NOT ask for any total price."* | **Never** — the call ends here |

This is the exact rule the 2026-08-11 field trial found violated (`FINDINGS.md`; second live
cascade: the bot asked for a total of an empty basket after an abort-rule position failed) —
fixed by adding the explicit "Do NOT ask for any total price" sentence and the mandatory
decision-announcement rule below.

### 2.5 Announcing decisions aloud, and the worked example

Every chain instruction ends with a fixed instruction to narrate decisions
(`"Announce every decision aloud as you go..."`) followed by `_order_chain_style_example(locale)`
— a literal, verbatim-quoted worked dialogue (take/drop, and the budget-abort announcement),
in German or English depending on `call_language()`. Positions carry a free-text `tags` list
purely for the *result screen's* grouping (`selections_by_tag`, `templates.py`); it is
nonetheless printed into the goal as `"Position N (tags: <tags>):"` — the agent sees it, but no
instruction anywhere tells it to do anything with it (§3, row 20).

### 2.6 Concessions (delivery/pickup only — `_concession_clause`)

| `concessions` | Instruction |
|---|---|
| empty | *"Do not offer anything beyond what is stated above. If the request cannot be met as stated, thank them politely and end the call."* |
| one or more, ordered by `tier` | A numbered fallback ladder: *"Step 1: only if the previous attempt failed, `<label>`"*, ... *"Never offer a later step before an earlier one has failed... Report which step you used in the field 'tier_applied'..."* |

The evaluator (`CascadeEngine.check_concession_authority`) independently rejects any result
whose `tier_applied` is not in `granted_concession_keys()` — an agent cannot manufacture
authority the clause never granted, even if it hallucinates a concession offer.

### 2.7 Reservation authority ladder (reservation only — `_reservation_authority_clause`)

Always step 1: *"first request the exact stated time, the stated seating preference, and no
booking fee."* Then, only for the tolerances actually granted:

| Condition | Added step |
|---|---|
| `earlier_tolerance_minutes() > 0` | *"only if the exact time is unavailable, you may accept a time up to `<N>` minutes earlier, but nothing earlier than that."* |
| `later_tolerance_minutes() > 0` | *"only if every earlier authorised option failed, you may accept a time up to `<N>` minutes later, but nothing later than that."* |
| `max_booking_fee_eur > 0` | *"only after all fee-free authorised times failed, you may accept a booking fee up to `<X>` EUR; never accept a higher fee."* |
| `max_booking_fee_eur == 0` | fixed: *"Do not accept any booking fee or deposit."* |

`CascadeEngine.check_reservation_authority` recomputes the delta and fee independently of what
the agent *reports* — the 2026-08-11 field trial's third live cascade is the standing proof this
works: the agent verbally accepted a 5 EUR fee against an authorised maximum of 0 EUR, and the
authority audit rejected the result deterministically regardless (`EVIDENCE.md` §16.3).

### 2.8 Quantity verification (`menge_bestellt`, AUFTRAG F fix, 2026-08-11)

The §2.1 quantity commitment (*"order `<quantity>` x `<product>` for this position"*) is a
correct prompt fragment that a live call still violated: a chain requiring 2 x Pasta Napoli was
placed as 1 x, and `evaluate_order_chain` accepted it, because nothing in `order_chain_results`
carried the quantity actually ordered — only which cell was taken. Two changes closed the gap,
neither of which existed before this finding (§4 row 13 tracks both the finding and the fix):

1. **Reinforcement, at the point of commitment.** Immediately after the existing quantity
   sentence, `build_order_chain_instruction` now adds: *"When you later place and summarize the
   order, place and confirm exactly `<quantity>` x `<product>` for this position — never a
   smaller or different amount, even if the conversation drifted."* The evidence-reporting
   instruction at the end of the chain block was extended the same way, telling the agent to
   report the placed quantity in a new `menge_bestellt` field for every cell it took, and to omit
   the field entirely for a cell it did not take.
2. **Verification, independent of the transcript.** `ORDER_CHAIN_RESULT_SCHEMA` gained an
   optional `menge_bestellt` integer property per cell — optional because its *absence* is how
   an untaken cell (unavailable, or rejected by a criterion) is represented; a schema-level
   `required` entry would force every cell, taken or not, to report a quantity, which the
   position it was never asked to fill is not owed. `evaluate_order_chain` now checks, for every
   cell it is about to accept as a position's winner, that `menge_bestellt` is present and equal
   to `cell.quantity`; a missing or mismatched value rejects the whole evaluation with
   `"Ordered quantity <N> does not match the configured <M> x <product>"` (or, if the field is
   simply absent, `"...is missing the ordered quantity (menge_bestellt)"`).

Tested in `tests/test_order_chains.py`: the exact match case, the exact live mismatch (configured
2, reported 1), a taken cell missing the field entirely, and — the negative case that must *not*
raise — an untaken cell that correctly reports no quantity at all.

---

## 3. Closing routine, retract-aloud, and the human callback

Shared by every mode, appended after the mode-specific body (`confirmation` in
`build_call_goal`, examples via `_closing_routine_examples(locale)`):

```mermaid
flowchart TD
    A[Order/reservation criteria satisfied] --> B[1. Summarize aloud: items+quantities,<br/>total price, name, address/time]
    B --> C[2. Place it bindingly:<br/>state clearly it is hereby placed]
    C --> D["3. Obtain confirmation, e.g.:<br/>'Bestätigen Sie mir bitte kurz die<br/>Bestellung: Was wird geliefert,<br/>und an wen?'"]
    D --> E{Other side repeats the order back?}
    E -- yes --> F["Check the read-back against what<br/>was agreed; correct/complete it, e.g.:<br/>restaurant: 'Sie bestellen also 2<br/>Pasta Napoli?' — you: 'Ja, und ein<br/>Tiramisu.'"]
    E -- no --> G[Confirmation still required before hangup]
    F --> H{NEW condition surfaces after<br/>the summary? fee/price/time change}
    G --> H
    H -- no --> I[Give restaurant callback<br/>number, only now — §3.3]
    H -- yes --> J[Re-check against limits]
    J --> K{Within authority?}
    K -- yes --> I
    K -- no --> L[RETRACT ALOUD: say it exceeds<br/>the mandate, cancel the order/<br/>reservation. End the call with<br/>nothing placed. No callback number.]
```

### 3.1 What this is a text-level guarantee of, and what it is not

The goal text **instructs** the retract-aloud behaviour; it cannot *guarantee* the voice agent
executes it faithfully on a real call (behaviour level, not text level — §0). What §2.7 makes
independently certain, regardless of what the agent said or did, is that `CascadeEngine`
**rejects** a result whose reported authority does not match its own audit of the confirmed
time/fee — that check runs on structured data after the call, not on the transcript.

### 3.2 The retract-aloud clause is meta, not verbatim

Unlike the read-back examples above (which are quoted and therefore language-selected, see §0),
the instruction to retract — *"say that this goes beyond your mandate and that you must
therefore cancel the order or reservation"* — carries no quotation marks. It is a meta-
instruction the agent rephrases in the call's own language on its own; nothing in
`call_language.py` needs to special-case it (matches the team's own framing of this clause as
*"Meta (bleibt englisch)"*).

### 3.3 Human callback number (`_requester_callback_clause`, every mode)

*"If and only if an order or reservation was actually placed, give the restaurant this human
callback number at the end of the call: `<number>`... When nothing was ordered or reserved, do
not mention any callback number."* This is why §1.1/§1.2's hard-gate failure paths end without a
closing routine or a callback mention at all — the clause is conditioned on something having
actually been placed, and a call that never got past a hard gate placed nothing.

---

## 4. Coverage table — does every setting land in the prompt?

Legend: **Covered** = the setting drives a distinct, findable fragment of the goal text.
**App-side only** = deliberately never sent to the agent; enforced elsewhere (ranking filter or
a post-hoc structured-result audit), with the reasoning stated. **Finding** = the setting is
user-configurable (or intended to be) but does **not** currently reach the prompt where a user
would reasonably expect it to — listed here as discovered, not silently fixed, per this
document's own mandate.

**Prompt coverage is not result coverage** (AUFTRAG F, live-measured 2026-08-11 — see
`FINDINGS.md`). A setting can drive perfectly correct goal text and still be silently violated:
the delivery-chain goal told the agent, verbatim, to *"order 2 x Pasta Napoli for this
position"* — genuinely **Covered** by every measure in this table's original sense — and the
voice agent still placed and confirmed only one, and `evaluate_order_chain` accepted the result,
because `order_chain_results` had no field to compare the ordered quantity against the
configured one. The **Result verification** column below is therefore a second, independent
question for every row: even where the setting reaches the prompt, does anything on the
*receiving* end check that the outcome actually matched it, or does correctness rest entirely on
trusting the transcript? Most rows have no such check and are marked `—`; that is not itself a
finding (asking CALL-E to prove every single instruction was followed is not tractable), but it
is the reason row 13 below needed a fix rather than only a prompt fragment.

| # | Setting | Configured via | Prompt fragment / builder | Status | Result verification |
|---|---|---|---|---|---|
| 1 | `mode` | web form / CLI subcommand | Dispatches all of §1 (`build_call_goal`) | **Covered** | — |
| 2 | `first_name` / `last_name` (→ `requester_name()`) | web form / `--customer-name` | Intro, "place the order under that name", "confirm the reservation under the name" | **Covered** | — |
| 3a | `food_prompt` (simple, no chain) | web form / `--food` | `"Requested items: '<food_prompt>'."` (delivery-simple, pickup) | **Covered** | — |
| 3b | `food_prompt` (= `chain.summary()` in chain mode) | derived from chain | Delivery and pickup: dropped entirely once a chain exists, chain is authoritative. Reservation: never used. | **Before the fix: Finding** — pickup kept the `food_prompt` line alongside the chain (redundant, agent saw the same items named twice); delivery already dropped it. **After the fix: Covered, consistently** — pickup's chain branch was restructured to match delivery's (no `Requested items` line, the exact-total-price question deferred until after the chain resolves); documented in §1.2 | — |
| 3c | `food_prompt` (reservation's cuisine wish) | web form (`table.wish` field) | never in the goal — used only by `ranking.py` to pick which restaurants get called | **App-side only** — by design: the restaurant was already selected for matching that cuisine before it was dialled | — |
| 4 | `max_budget_eur` | web form / `--budget` | `"within our maximum budget limit of <X> EUR"` / `"within our limit of <X> EUR"` | **Covered** (delivery/pickup; correctly absent for reservation) | `CascadeEngine.check_price_and_order` rejects `total_price_eur > max_budget_eur` independently of what the agent reports |
| 5 | `delivery_address` | web form / `--address` | `"delivery to <address>"`, `"do you deliver to this address?"` | **Covered** (delivery only) | — (relies on `delivers_to_address` as reported) |
| 6 | `reservation_date` / `reservation_time` / `party_size` | web form / `--date --time --party` | `"reserve a table on <date> at <time> for <party_size> people"` | **Covered** (reservation only) | date/time re-derived and bounds-checked, see row 23-25 |
| 7 | `seating` / `seating_custom` | web form / `--seating --seating-custom` | seating_clause (§1.3) | **Covered** (reservation only) | `CascadeEngine.evaluate_result` rejects `seating_confirmed` that does not match the requested indoor/outdoor value |
| 8 | `pickup_time` | web form / `--pickup-time` | `"Preferred pickup time: <X>"` | **Covered** (pickup only) | — |
| 9 | `max_distance_km` | web form | `ranking.py` hard cutoff, before any call | **App-side only** — the restaurant does not need to know the caller's distance limit; it decides *which* candidates are dialled, not what is said | n/a (never in the prompt to begin with) |
| 10 | `day_of_week` / `time_of_request` | derived (reservation date, or system clock) | `ranking.py` opening-hours pre-filter | **App-side only** — pickup independently re-asks *"are you currently open?"* live (§1.2), so this is not the only check, just the earliest one | n/a |
| 11 | `favorite_restaurant_ids` | — (no web field, no CLI flag) | `ranking.py` `is_fav` ranking boost | **Finding** — modelled and used by ranking, but there is currently no way for a user to actually populate it | n/a |
| 12 | `concessions` (`FOOD_CONCESSIONS`: `wait_longer_ok`, `higher_price_ok`, `substitute_ok`) | web form checkboxes (delivery/pickup) | `_concession_clause()` — tier-ordered fallback ladder, independently audited (§2.6) | **Before the fix: Finding** — the mechanism was complete and correct, but no checkbox anywhere emitted `name="concessions"`; `templates.py` only ever wrote a hidden pass-through field for a value nothing could set. `request.concessions` was always empty in practice. **After the fix: Covered** — three real checkboxes on the delivery/pickup form now emit `name="concessions"`, read by the existing `form.getlist("concessions")` in `web.py`. The content also changed, not just the wiring: the checkboxes used to be named `TABLE_CONCESSIONS` and carried reservation-only labels (an indoor table, a €15 deposit) that would have made no sense on a food order and were already superseded there by the earlier/later/fee fields (row 23-25) — see the comment above `FOOD_CONCESSIONS` in `templates.py`. Reservation still has no checkbox and still raises `ValueError` if `concessions` is set (unchanged, and correct — see §1.3) | `CascadeEngine.check_concession_authority` rejects a reported `tier_applied` that is not in `granted_concession_keys()` |
| 13 | order chain: `cells[].quantity` | web chain builder | `"order <quantity> x <product> for this position"`, reinforced at the binding-placement step (§2.5) | **Before the AUFTRAG F fix (live-measured 2026-08-11): Prompt coverage yes, result/verification coverage no** — the goal text correctly said *"order 2 x Pasta Napoli"*, the live agent placed 1 x, and `evaluate_order_chain` accepted it, because nothing compared the two. **After the fix, same day: Covered AND result-verified** — `evaluate_order_chain` now compares the reported `menge_bestellt` against `cell.quantity` for every taken cell and rejects a mismatch with `"Ordered quantity <N> does not match the configured <M> x <product>"` | `evaluate_order_chain` (see Status column — this row's own fix) |
| 14 | order chain: `cells[].product` | web chain builder | Availability question + every criterion/quantity sentence for that cell | **Covered** | Implicitly, via `zelle_index`/position matching — a wrong product cannot be reported under the right cell index without the evidence shape itself being invalid |
| 15 | order chain: `cells[].art` (`ProductKind`: `essen`/`getraenk`) | — (no longer a UI selector, see Status) | — | **Before the fix: Finding** — a dropdown in the chain builder let a user mark a cell as food or drink; nothing in `build_order_chain_instruction` or `_cell_availability_question` ever read `cell.kind`. **After the fix: removed, not wired up** — the selector is gone from `app.js`'s `renderCell`; the honest read is that the field never changed a question or a sentence a restaurant employee already answers from their own menu (e.g. "Do you have Cola?" needs no "...as a drink?" qualifier), so there was nothing to wire it *to*, unlike row 22's `special_instructions` which has a real, if currently unreachable, place to go. `OrderCell.kind` still exists in the data model, always `ProductKind.FOOD`, for `order_chain_json` shape stability (round-tripping an older saved template must not break) | n/a (field no longer settable) |
| 16 | order chain: `criteria[].art` (`hoechstpreis`/`sonderwunsch`/`rueckfrage`) | web chain builder | `_criterion_instruction()`, three distinct question forms (§2.2) | **Covered** | `evaluate_order_chain` recomputes the reaction from raw evidence (`preis_eur`, `bestaetigt`, `antwort_ja`) itself; a reported outcome label is never trusted (module docstring) |
| 17 | order chain: `criteria[].wert` | web chain builder | Interpolated into the criterion's question | **Covered** | For `hoechstpreis`, the reported `preis_eur` is compared against this value directly in `_criterion_reaction` |
| 18 | order chain: `criteria[].reaktion_ja` / `reaktion_nein` | web chain builder | `_reaction_instruction()`, three distinct reactions (§2.3) | **Covered** | Same re-derivation as row 16 — the configured reaction, not a reported one, decides accept/replace/reject |
| 19 | order chain: `posten[].wenn_nichts_verfuegbar` (`posten_weglassen`/`bestellung_abbrechen`) | web chain builder | Position end rule, two structurally different instructions incl. the total-price prohibition (§2.4) | **Covered** | `_apply_position_end_rule` applies the configured rule directly; there is nothing for the agent to misreport here since the app decides the outcome from `verfuegbar`/criteria evidence alone |
| 20 | order chain: `posten[].tags` | web chain builder | — (no longer printed, see Status) | **Before the fix: Finding (minor)** — printed as `"Position N (tags: <tags>):"`, but no instruction anywhere told the agent what to do with it; it exists solely for the result screen's grouping and leaked into the agent's view by accident. **After the fix: removed, not instructed** — `build_order_chain_instruction` prints `"Position N:"` with no tag mention at all. The tags feature itself is unchanged: the web UI's tag input, `position.tags`, and `render_tag_summary`'s result-screen grouping all still work exactly as before, because that grouping reads `OrderSelection.tags` (from `evaluate_order_chain`, itself reading `position.tags` directly) and never depended on the prompt text in the first place | n/a (field still real, just no longer sent to the voice agent) |
| 21 | `requester_callback_number` | web form (required) / `--requester-callback-number` | `_requester_callback_clause()` (§3.3) | **Covered** | — (no check that it was actually spoken; it is redacted from stored output, not verified for delivery) |
| 22 | `special_instructions` | web form (**reservation branch only**) | `special_clause`, built **only** inside the `Mode.RESERVATION` branch of `build_call_goal` | **Before the fix: Finding (latent)** — there was no delivery/pickup UI for this, but `build_user_request` did not gate the field by mode either, so a hand-crafted request carrying it for delivery/pickup was accepted and the note silently dropped, never surfaced as an error. **After the fix: rejected, not silently dropped** — `build_user_request` now raises `ValueError` if `special_instructions` is set for any mode other than `RESERVATION`, the same way `seating_custom` is rejected outside custom seating. Support for delivery/pickup notes was **not** added — only the trap was closed; adding real support is a separate, larger decision (a new form field, plus deciding what "leave it with the neighbour" even means for a phone order) that nobody asked for here | n/a |
| 23 | `earlier_hours` / `earlier_minutes` | web form / `--earlier-hours --earlier-minutes` | `_reservation_authority_clause()` step 2 (§2.7) | **Covered** (reservation only) | `CascadeEngine.check_reservation_authority` recomputes the confirmed-vs-requested delta itself and rejects anything outside the granted window |
| 24 | `later_hours` / `later_minutes` | web form / `--later-hours --later-minutes` | `_reservation_authority_clause()` step 3 (§2.7) | **Covered** (reservation only) | Same audit as row 23 |
| 25 | `max_booking_fee_eur` | web form / `--max-booking-fee-eur` | `_reservation_authority_clause()` fee step or fixed refusal (§2.7) | **Covered** (reservation only) | `check_reservation_authority` rejects a reported fee above this value regardless of what the agent verbally accepted — the live proof is `EVIDENCE.md` §16.3 |
| 26 | `HUNGRYCALL_CALL_LOCALE` (env, not a `UserRequest` field) | operator environment | `call_language()` → intro, closing-routine examples, chain availability question, chain worked example, and `call_client.py`'s recipient `region`/`locale` | **Covered** (2026-08-11, `call_language.py`) | — |

### 4.1 Findings, gathered

Six items above were not simple "covered" when this table was first built: **#3b** (inconsistent
chain/food_prompt handling between delivery and pickup), **#11** (`favorite_restaurant_ids` has no
way to be set), **#12** (the whole concessions ladder was unreachable in practice), **#15**
(`cell.kind` never reaches the prompt — a real gap between what the UI lets you configure and what
the agent is told), **#20** (`tags` leaks into the prompt without instructing anything), and **#22**
(`special_instructions` would silently vanish if ever wired up for delivery/pickup). None of these
were fixed while this document was first built, in keeping with the instruction that a gap is a
finding first and a fix second, in its own reviewable commit. **#13 (order-chain quantity) was a
seventh finding of the same shape, discovered live on 2026-08-11 rather than while building this
table, and has since been fixed** (`evaluate_order_chain`, AUFTRAG F) — its row above documents
both the original gap and the fix, rather than being silently updated to just say "Covered".

**#12 has since been fixed** the same way: real checkboxes now exist for a rewritten,
food-appropriate `FOOD_CONCESSIONS` set (row 12 above documents both the original gap — including
why the *original* three labels could not simply have been wired up as-is — and the fix).

**#15 has since been fixed the other way round from #12: by removal, not wiring.** Row 15 above
lays out why — `cell.kind` had no sentence to be wired *to*; the plain removal was the honest fix
rather than inventing prompt text nobody needed just to make the setting "reach" somewhere.

**#20 turned out to be the same shape as #15, not the same shape as #12 or #22** (this table's own
first pass at describing it undersold that — corrected here): `tags` had no more of a genuine
sentence to be wired to than `cell.kind` did. Row 20 above documents the fix: the `(tags: ...)`
label is gone from `build_order_chain_instruction`, and the tags feature itself — the web UI's
input, `position.tags`, `render_tag_summary`'s result-screen grouping — is completely unaffected,
because none of it ever depended on the prompt text.

**#22 has since been fixed a third, genuinely different way: by rejection, not wiring or
removal.** Unlike `cell.kind` and `tags`, `special_instructions` *does* have somewhere to go
(reservation's `special_clause`) — the gap was that delivery/pickup could carry the field without
either reaching the goal or being told they could not. Row 22 above documents the fix:
`build_user_request` now raises rather than silently dropping it, closing the trap without
inventing delivery/pickup support nobody asked for.

**#3b has since been fixed a fourth way: by unifying two builders, not by wiring, removing or
rejecting a setting.** This one was never about a setting failing to reach the prompt — `food_prompt`
reached it in both modes — it was about the *same* situation (a chain present) producing
differently-shaped goals for delivery and pickup with no documented reason. Row 3b and §1.2 above
document the fix: pickup's chain branch was restructured to match delivery's (drop the
`Requested items` line, defer the exact-total-price question until after the chain resolves)
rather than the reverse, because delivery's structure was already the one without the redundancy.
Status of the remaining finding as of this writing: **#11 — open**, tracked for the same
priority-ordered fix pass as #12, #15, #20, #22 and #3b.

---

## 5. Where the scenario tests live

`tests/test_scenario_goals.py` turns every row of §4 that is **Covered** into at least one
assertion that the documented fragment actually appears (and, for the branching rows —
`if_nothing_available`, `reaktion_ja`/`reaktion_nein`, `de`/`en`, per-mode openings — a flip test
proving the *other* branch produces different, and only different, text). `tests/goldens/`
holds one full expected goal text per scenario in the matrix; see that test file's module
docstring for the regeneration procedure.
