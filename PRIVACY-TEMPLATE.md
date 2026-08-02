# Privacy notice template — HungryCall

> **Template only — adaptation required.** This is not a deployable privacy notice and is not legal advice. The operator must replace every `[REPLACE: ...]` marker, remove inapplicable options, verify all service-provider facts and obtain a case-specific legal review before processing real data.

Last updated: `[REPLACE: date]`

## 1. Controller

`[REPLACE: legal name of the party deciding why and how HungryCall is used]`<br>
`[REPLACE: postal address]`<br>
Email: `[REPLACE: privacy contact]`<br>
Data protection officer, if applicable: `[REPLACE or remove]`

Infrastructure hosting provider: `[REPLACE: provider, address and role; do not describe the infrastructure host as controller unless the role analysis supports that]`

## 2. Scope and people affected

This notice covers `[REPLACE: deployment URL and version]`. It may concern:

- registered or visiting users who create an order or reservation request;
- the individual named in that request;
- restaurant or venue contacts and people who answer a call; and
- `[REPLACE: administrators/support staff or remove]`.

## 3. Processing purposes and legal bases

| Purpose | Data used | Legal basis | Required or optional / consequence |
| --- | --- | --- | --- |
| Create and manage a request | Name, food/reservation request, address/location, time, party size, constraints and budget | `[REPLACE: exact Article 6 basis and reasoning]` | `[REPLACE]` |
| Find nearby venues | Postcode/city/country, coordinates, radius and returned venue data | `[REPLACE]` | `[REPLACE]` |
| Place an automated call, if enabled | Destination number, call task and the request details needed for the chosen mode | `[REPLACE]` | `[REPLACE]` |
| Return and optionally retain a result | Call status, venue, price/ETA, callback number, summary, transcript and structured result | `[REPLACE]` | `[REPLACE]` |
| Secure and operate the service | `[REPLACE: verified server, security and audit log fields]` | `[REPLACE]` | `[REPLACE]` |

Do not use consent as a generic fallback. If consent is selected, document how it is informed, specific, voluntary, evidenced and withdrawn. Assess separately whether the call and any transcription are lawful.

## 4. Local, connected and live modes

`[KEEP AND COMPLETE THE APPLICABLE VERSION]`

- **Fixture/test mode:** restaurant and call results use local fixtures, but the candidate map still requests OpenStreetMap tiles unless the deployment disables/replaces that layer. `[REPLACE: confirm map behavior, infrastructure logs and backups]`.
- **Connected restaurant search:** the app sends the entered area to Nominatim and sends coordinates/radius to an Overpass endpoint. The browser requests OpenStreetMap tiles.
- **Live calling:** the app sends the selected destination number and call task to the configured CALL-E endpoint and receives call results, activity and transcript data.

## 5. Recipients, processors and transfers

| Recipient/category | Data and purpose | Role and location | Safeguard/contract |
| --- | --- | --- | --- |
| `[REPLACE: infrastructure host]` | `[REPLACE]` | `[REPLACE]` | `[REPLACE: Article 28 agreement if applicable]` |
| `[REPLACE: CALL-E contracting entity and subprocessors, or remove live mode]` | Destination number, call task, metadata and returned call material | `[REPLACE: verified role and processing countries]` | `[REPLACE: DPA and, if needed, Chapter V mechanism]` |
| `[REPLACE: Nominatim operator/endpoint]` | Search area and ordinary connection data | `[REPLACE]` | `[REPLACE]` |
| `[REPLACE: Overpass operator/endpoint]` | Coordinates, radius and ordinary connection data | `[REPLACE]` | `[REPLACE]` |
| `[REPLACE: OpenStreetMap tile operator]` | Tile request, ordinary connection data and requested tile coordinates | `[REPLACE]` | `[REPLACE]` |
| Selected restaurant/venue | Request details spoken during the call | Independent recipient; `[REPLACE: role analysis]` | `[REPLACE]` |

The source code's endpoint names do not prove corporate identity, retention, subprocessors or international-transfer safeguards. Verify these from current contracts before launch.

## 6. Storage and deletion

The current application can store requests, callback numbers, results and transcripts in one SQLite database. It does not implement automatic expiry for those records.

Operator schedule:

| Record | Period or deletion criterion |
| --- | --- |
| Unsaved active request | `[REPLACE; implement it in code]` |
| Orders/reservations | `[REPLACE; implement it in code]` |
| Saved results and transcripts | `[REPLACE; implement it in code]` |
| Server/security logs | `[REPLACE after checking infrastructure]` |
| Backups | `[REPLACE: cycle and irreversible deletion point]` |
| Provider-side call/search data | `[REPLACE from verified contracts]` |

## 7. Browser storage

| Name | Purpose | Lifetime |
| --- | --- | --- |
| HungryCall language cookie `[REPLACE: deployed cookie name if changed]` | Remembers the interface language | One year in the current code |
| `hc-theme` in browser local storage | Remembers light/dark theme | Until removed by the user/browser |

`[REPLACE: add reverse-proxy, consent-tool, analytics or authentication cookies; otherwise state that none are used after verification]`

## 8. Source of contact data and information during calls

Venue contact data may come from OpenStreetMap/Overpass or `[REPLACE: other source]`. Where the GDPR applies and data were not obtained from the person, the controller must complete the Article 14 information and timing analysis. Data collected directly from the person during a call require the Article 13 analysis. Provide a concise, understandable first layer during the call and an accessible full notice at `[REPLACE: URL/non-digital channel]`, as confirmed by legal review.

## 9. Automated decisions

HungryCall ranks candidates and applies configured acceptance criteria. `[REPLACE: explain the logic, significance and effects, and state whether any decision within Article 22 is made. Do not claim that Article 22 is inapplicable without review.]`

## 10. Rights and complaints

Subject to the legal conditions, individuals may have rights of access, rectification, erasure, restriction, objection and data portability, and may withdraw consent without affecting prior processing. Requests: `[REPLACE: channel and identity-verification process]`.

Complaint authority: `[REPLACE: competent supervisory authority, address and URL]`.

## 11. Changes

We will update this notice when purposes, data, providers, retention or deployment architecture change. Previous versions: `[REPLACE: location]`.

## Annex A — Server modes (piggyback)

> **Still a template.** Pick the one block that matches `HUNGRYCALL_SERVER_MODE` on the deployed installation, delete the others, and keep replacing every marker. Choosing a mode changes what has to be written here; it does not remove the need to write it.

**Which mode is deployed:** `[REPLACE: local | huckepack-gift | huckepack-only-host]` — verifiable at `[REPLACE: deployment URL]/huckepack/mode`.

### A.1 If the mode is `local`

Sections 1–11 above apply unchanged. The database is a file on the host; the operator is the controller for everything in it.

### A.2 If the mode is `huckepack-gift` or `huckepack-only-host`

**Replace section 6 (Storage and deletion) with:**

> This installation keeps no database of your requests. Orders, results, transcripts, templates and tags are stored by your browser on your device. While you are using the service, a copy is held in this server's working memory so that the same queries can run; it is discarded at the latest `[REPLACE: confirm the value of SESSION_TTL_SECONDS in hungrycall/huckepack_storage.py]` after your last request, when you press "delete data", and whenever the server process restarts. Nothing is written to a file on the server.
>
> Because of that, deleting your browser data deletes everything, and we cannot restore it. Use "back up data" to keep a copy; that file is the plain database and is not encrypted — store it where you would store an unlocked address book.
>
> `[REPLACE: this says nothing about server, proxy and infrastructure logs — those exist regardless of where the database is, and must be described here after verification]`

**Replace section 7 (Browser storage) with:**

| Name | Purpose | Lifetime |
| --- | --- | --- |
| Language cookie `[REPLACE: name]` | Interface language | One year |
| `hc-theme` (local storage) | Light/dark theme | Until removed |
| `huckepack.session` (local storage) | Identifies your working copy on the server while you use it | Until you delete your data |
| `huckepack` database (IndexedDB) | **Your data**: orders, results, transcripts, plus the receipt folder you chose | Until you delete it |
| `huckepack.calle-key` (local storage) | *Only in `huckepack-only-host`:* your own CALL-E key | Until you press "forget" |

Under `[REPLACE: applicable national implementation of Article 5(3) ePrivacy Directive — in Germany § 25 TDDDG]`, storage on the user's device needs consent unless it is strictly necessary for a service the user explicitly requested. `[REPLACE: assess each row. The working position that these entries carry the user's own data for the function the user asked for, and that no entry is used for analytics or advertising, must be reviewed — it is an argument, not a finding.]`

**Add to section 5 (Recipients):** nothing is added by the mode. The call still goes to CALL-E, the search still goes to Nominatim/Overpass, and the tile requests still leave the browser.

**Keep in full:** sections 8 (contact data and information during the call), 9 (automated decisions) and 10 (rights). They concern the **called party**, whose data are processed no matter where the caller's records are stored. This is the point most easily lost: storing nothing does not make the operator a bystander to the call.

### A.3 Only in `huckepack-only-host` — the visitor's own key

> You enter your own CALL-E key. It is stored by your browser, shown only by its last four characters, and sent to this server with a call request so the call can be placed in your name. This server does not store it, does not write it to a log and does not keep it after the request. Calls you place are billed to your own account with `[REPLACE: CALL-E contracting entity]`, under the contract between you and them.

`[REPLACE: state who is controller for those calls under the deployed setup. Passing a key through does not by itself settle the role question, and the operator still decides how the call is composed.]`

### A.4 Receipts

> After a call you can save a receipt as a file. It is written by your browser, into a folder you chose or your download folder. It contains the business, the time, the outcome, the price and the conversation — with phone numbers masked — and it notes that the conversation contains statements by the person who was called. It is not sent anywhere.

`[REPLACE: if the deployment disables the receipt, remove this section]`

### A.5 What the modes do not change

- The call reaches a real person at the other end.
- The transcript contains that person's words.
- The operator chose to run this service and to compose the call.
- Server, reverse-proxy and infrastructure logs are a fact of the deployment, not of the mode.

## Pre-publication checklist

- [ ] Every placeholder is replaced or removed.
- [ ] Controller, processor and joint-controller roles are documented.
- [ ] Legal basis exists for user data, venue contact data, calls and transcription.
- [ ] Provider identity, location, retention, subprocessors, DPA and transfer safeguards are verified.
- [ ] Retention and deletion are implemented and tested, including backups.
- [ ] The deployed routes require authentication and tenant authorization.
- [ ] Call-layer Articles 13/14 information and withdrawal/objection handling are tested.
- [ ] A qualified lawyer has reviewed the completed deployment-specific notice and call workflow.
- [ ] The deployed `HUNGRYCALL_SERVER_MODE` is stated, and only the matching block of Annex A remains.
- [ ] In a piggyback mode: it has been checked on the running installation that no database file appears (the promise, not the intention).
- [ ] In `huckepack-only-host`: the key is nowhere in logs, in the database or in a response.
- [ ] Device-storage consent has been assessed for each browser entry in Annex A.2.
