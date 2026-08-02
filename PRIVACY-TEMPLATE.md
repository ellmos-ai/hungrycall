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

## Pre-publication checklist

- [ ] Every placeholder is replaced or removed.
- [ ] Controller, processor and joint-controller roles are documented.
- [ ] Legal basis exists for user data, venue contact data, calls and transcription.
- [ ] Provider identity, location, retention, subprocessors, DPA and transfer safeguards are verified.
- [ ] Retention and deletion are implemented and tested, including backups.
- [ ] The deployed routes require authentication and tenant authorization.
- [ ] Call-layer Articles 13/14 information and withdrawal/objection handling are tested.
- [ ] A qualified lawyer has reviewed the completed deployment-specific notice and call workflow.
