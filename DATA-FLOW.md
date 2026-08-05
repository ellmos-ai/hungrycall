# HungryCall data flow

Status: code and regression-test review on 2026-08-05. No live call was placed. This document describes the current implementation, not a planned deployment.

For server-side rows, “leaves the computer” means leaving the machine that runs the Python process. The OpenStreetMap tile row is different: that request leaves the user's browser device directly. If the app is remotely hosted, browser-to-host form submissions already disclose data to the app operator and its infrastructure, including when restaurant/call fixtures are used.

## Operating modes

- `test_mode=True` uses local fixtures for restaurant discovery and the dry-run call client. It does **not** by itself make the browser offline: rendering the candidate map still requests OpenStreetMap tiles.
- The ordinary non-test search sends location data to Nominatim and coordinates plus radius to Overpass even when the later call cascade is a dry run.
- Live calling is a separate, explicitly gated path. It sends data to CALL-E. The web server binds to loopback by default, but loopback is not an access-control system if the application is exposed through another service.

## Data switchboard

| Data | Collection and use | Storage | Retention implemented in code | Who can see it | Leaves the computer? | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| First and last name, food request, budget, delivery address, reservation date/time, party size, seating request, additional note, time/fee bounds, pickup time, location text and mode | Entered in the web form and used to search, rank and build the restaurant call task | One process-wide `ACTIVE_ORDERS` dictionary and the `orders` table in the configured SQLite file (`hungrycall.db` by default) | Memory remains until process exit; no automatic SQLite expiry or deletion routine was found | The current process; any visitor able to use the unauthenticated history/result routes can reach shared records | Form submission stays on the app host; some values leave during live calling as described below | `hungrycall/web.py`; `hungrycall/models.py`; `hungrycall/db.py` |
| Requester callback number | Required by the web form, normalized and validated as E.164, then carried in transient request/form state so a restaurant can ask questions or obtain human confirmation; repeated at the end of every live call goal | **Not written** to the `orders` or `saved_results` SQLite tables, result JSON, history export, receipt or fixture transcript | Active request/process state only | App process, CALL-E and the selected restaurant in live mode | **Yes, live mode only:** inside the purpose-bound call instruction | `hungrycall/web.py`; `hungrycall/models.py`; `hungrycall/engine.py`; `tests/test_requester_callback_and_reservation_authority.py` |
| Postcode, city and country | Geocoded for restaurant search | The query postcode/country are not separately written to SQLite; the order's `location_info` receives the city text | No separate retention mechanism beyond the order's city text | App process and the Nominatim service | **Yes in non-test search:** sent as the `q` request parameter to Nominatim | `hungrycall/location.py:124-166`; `hungrycall/web.py:228-337, 409-418`; `hungrycall/db.py:37-54` |
| Latitude, longitude and search radius | Used to discover restaurants and render the candidate map | The search centre/radius are used for the response/browser view; the `orders` schema does not persist them. Selected restaurant objects remain in active process memory | Active process lifetime; no SQLite retention for search centre/radius | App process, browser and Overpass service | **Yes in non-test search:** sent in an Overpass query | `hungrycall/location.py:169-210`; `hungrycall/web.py:228-337, 421-438` |
| OpenStreetMap tile requests | Renders the map in the browser | Browser/network caches are controlled by the browser and tile service, not by HungryCall | Not controlled by HungryCall | OpenStreetMap tile endpoint receives the request | **Yes:** the browser requests tiles, exposing ordinary connection data and requested tile coordinates | `hungrycall/static/app.js:69-81` |
| Restaurant/venue data: OSM identifier, name, cuisine, address, coordinates and public contact number | Returned by Overpass, ranked, displayed and used as call candidate data | Candidate objects are held in active process memory. A saved result writes restaurant ID/name/phone and call-result fields, not the complete cuisine/address/coordinate object | Active process lifetime; saved result fields have no automatic deletion | App visitors through shared screens/routes; CALL-E receives the selected destination number in live mode | Overpass supplies it; selected destination data then leave for CALL-E in live mode | `hungrycall/location.py:169-241`; `hungrycall/web.py:340-582, 597-635`; `hungrycall/db.py:57-73` |
| Live call task: selected restaurant number, customer name and transient requester callback number, request, address or reservation details, budget/constraints, language and metadata | Builds and starts a live CALL-E call; the goal permits the restaurant to use the requester number for questions or human confirmation and repeats it at the end | Sent to CALL-E; returned structured result, activity and transcript are held in memory, and can be saved to SQLite without the requester callback number | CALL-E-side retention is not specified in this repository; local saved records have no automatic expiry | Restaurant recipient, CALL-E, app process, and visitors able to access the shared result/history endpoints | **Yes, live mode only:** HTTPS requests to the configured CALL-E base URL (default `https://api.heycall-e.com`) | `hungrycall/engine.py`; `hungrycall/call_client.py`; `hungrycall/web.py` |
| Saved result: restaurant name/ID, masked number, unmasked callback number, price, ETA, summary, phone-masked transcript text and result JSON | Saved after a cascade result | `saved_results` in the shared SQLite file | No automatic expiry or delete endpoint found | `/history` and `/api/saved-results` expose the shared collection without account or ownership checks | No new transfer at save time; the data may already have come from CALL-E | `hungrycall/call_client.py:430-471`; `hungrycall/db.py:57-73, 127-205`; `hungrycall/web.py:125-131, 597-640` |
| Language preference | Selects interface language | Cookie | One year | Browser and app host | Sent with requests to the app host | `hungrycall/web.py:83-94` |
| Theme preference | Selects light/dark theme | Browser `localStorage` key `hc-theme` | Until the user/browser removes it | The user's browser | No transfer by this code | `hungrycall/static/app.js:31-37`; `hungrycall/templates.py:610` |
| CALL-E API key | Authenticates live API requests | Process environment or an external credential file; loaded once for the process | Controlled outside the data database | Server process and CALL-E authentication endpoint; the UI must never receive it | **Yes, live mode only:** sent as an authorization credential | `hungrycall/call_client.py:23-26, 64-116, 281-329` |

## Important boundaries

- A masked display value is not deletion: `saved_results.callback_number` stores the unmasked number. The saved transcript has phone-like strings masked by the live adapter, but its conversation content can still be personal data.
- The restaurant callback number in saved results is distinct from `requester_callback_number`. Regression tests inspect the SQLite schema, database rows, JSON, receipts and history to ensure the requester number is not persisted.
- An opaque order ID is not authorization. All visitors share the same process state and SQLite history.
- The repository specifies neither CALL-E-side retention nor the legal entity, hosting location or transfer safeguards for the configured endpoint. A deployer must obtain those facts contractually; this review does not infer them.
- Browser, reverse-proxy, operating-system and infrastructure logs are deployment facts and cannot be derived from this repository. They must be added to the final privacy notice and retention schedule.

See `HOST-READINESS.md` for the multi-user gap and `PRIVACY-TEMPLATE.md` for an operator-owned notice template.

## Server modes (added 2026-08-02)

> **On the name.** In English this hosting pattern is called *piggyback*:
> the application rides on infrastructure it does not own. The literal mode
> values are still spelled `huckepack-gift` and `huckepack-only-host` — that is
> the German working title the code was built under, and it is what an operator
> actually types. Prose says piggyback; configuration says huckepack.

The table above describes `local`, which is what an unconfigured installation is. `HUNGRYCALL_SERVER_MODE` selects one of four modes (`hungrycall/server_mode.py:25-76`); an unknown value is refused by name rather than silently ignored (`hungrycall/server_mode.py:78-90`), and the resolved mode is held for the process, so no request can switch it (`hungrycall/server_mode.py:98-113`).

| Mode | Where the database is | Whose key pays | Accounts |
| --- | --- | --- | --- |
| `local` (default) | SQLite file on the host, as before | host environment or credential file | none |
| `huckepack-gift` | the visitor's browser | the host's | none |
| `huckepack-only-host` | the visitor's browser | the visitor's, per request | none |
| `pay-membership` | — | — | would be required; **not built**, every page answers 503 (`hungrycall/huckepack_web.py:47-50, 145-155`) |

### What changes in a piggyback mode

| Data | Collection and use | Storage | Retention implemented in code | Who can see it | Leaves the computer? | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Orders, saved results, templates, tags — the whole database | Unchanged in purpose; the same schema and the same SQL | **Not on the host.** The durable copy is a SQLite file in the visitor's browser (IndexedDB); the host holds a copy in memory for the length of a browser session | Memory only: dropped after two hours without use, on session delete, and on process exit; no file is created | The one browser session that supplied the session token | The database bytes travel between browser and host on load and after each change; they are never written to the host's disk | `hungrycall/huckepack_storage.py:58-72, 74-163, 191-202`; `hungrycall/db.py:25-40`; test `tests/test_huckepack.py::test_a_huckepack_mode_never_creates_the_database_file` |
| Session token | Addresses the in-memory database of one browser | Browser `localStorage`, sent as `X-Huckepack-Session` | Until the visitor deletes the data | Browser and host process | Sent with every request | `hungrycall/huckepack_web.py:27-40`; `hungrycall/static/huckepack.js` (`sessionToken`, `headers`) |
| Visitor's CALL-E key (`huckepack-only-host` only) | Authenticates that visitor's own live calls | **Browser `localStorage`**, displayed masked to the last four characters | Until the visitor presses "forget"; on the host only for the duration of one request (`ContextVar`) | The visitor's browser; the host process while the call runs; CALL-E | Sent as the `X-Calle-Key` request header, never as a query parameter, and on to CALL-E | `hungrycall/calle_key.py:30-38, 43-70, 90-116`; `hungrycall/web.py:476-486`; tests `test_the_visitors_key_reaches_no_store_and_no_log`, `test_only_host_never_falls_back_to_the_hosts_key` |
| Receipt file | Written after a saved result: business, time, price, outcome, transcript | The visitor's file system — a folder chosen once via `showDirectoryPicker`, otherwise the ordinary download folder | The visitor's own file; nothing on the host | Whoever can read that folder | No transfer: the file is built in the browser from a payload the host already sent | `hungrycall/web.py:686-731`; `hungrycall/static/huckepack.js` (`saveReceipt`, `writeFile`, `receiptText`) |
| Chosen receipt folder | Lets later receipts be written without a dialog | A directory handle in the browser's IndexedDB | Until the visitor deletes the data or revokes the permission | The visitor's browser | No transfer | `hungrycall/static/huckepack.js` (`chooseFolder`, `FOLDER_RECORD`) |
| Export / import file | The visitor's own backup and their way to another device | A `.sqlite` file wherever the visitor puts it | The visitor decides | Whoever can read that file — **it is the unmasked database** | Leaves only on the visitor's own instruction | `hungrycall/static/huckepack.js` (`exportData`, `importData`) |

### Boundaries that remain

- **A piggyback mode does not make the call private.** The destination number and the call task still go to CALL-E, and a third party is still called. Where the data are *stored* changes; what is *transmitted* does not. The live-call row in the table above stays valid word for word.
- **The host still sees the data in transit.** Form submissions, the in-memory database and the call payload pass through the host's process. "The host stores nothing" is a statement about persistence, and is meant as one.
- **A cleared browser is a total loss.** There is no copy at the host to fall back on. Export is therefore a condition of the pattern, not a convenience — and the interface says so on the bar.
- **The exported file is unprotected.** It is the plain database, including the callback number. That is deliberate — a passphrase the visitor forgets would destroy the backup — but it belongs in the privacy notice.
- **`local` is unchanged.** No new storage, no new transfer, one additional script tag in the page (`hungrycall/templates.py:647`) that fetches `/huckepack/mode` and then, in `local`, does nothing but offer the receipt download.
