# HungryCall host-readiness finding

## Verdict

**Not ready for untrusted multi-user hosting.** The current application is a local, single-operator tool. Exposing it to multiple visitors would give them a shared state and shared CALL-E credential without user or record isolation.

## Evidence

| Question | Current implementation | Consequence | Evidence |
| --- | --- | --- | --- |
| Accounts or authenticated sessions? | None in the FastAPI application. The only cookie is a language preference. | A visitor has no authenticated owner identity. | `hungrycall/web.py:51-94` and route set in `hungrycall/web.py` |
| Per-user state? | No. `ACTIVE_ORDERS` and `CANCELED_ORDERS` are module-level process-wide collections. | Active order state is shared by every visitor to the process. | `hungrycall/web.py:62-64, 421-453` |
| Per-user database? | No. One path from `HUNGRYCALL_DB_PATH`, otherwise `hungrycall.db`, holds all orders and saved results. | History and results share one namespace. | `hungrycall/db.py:9-25, 37-73` |
| Object-level authorization? | No. History returns all saved results; order operations use only an order ID. | Anyone reaching the routes can view shared history and can act on a known order ID. | `hungrycall/web.py:125-131, 445-640` |
| Can each user provide their own API key? | No. `LiveCallClient.from_environment()` resolves one process credential from environment/external file. | One credential and its quota/billing apply to all visitors. | `hungrycall/call_client.py:64-116, 281-289`; `hungrycall/web.py:395` |
| Safe retention controls? | No automatic expiry/delete workflow for orders or saved results was found. | A host cannot enforce a declared schedule through the current app. | `hungrycall/db.py:27-205`; route set in `hungrycall/web.py` |
| Network exposure? | The built-in runner binds to `127.0.0.1` by default. | This reduces accidental exposure, but a reverse proxy or changed binding can still publish an unauthenticated app. | `hungrycall/web.py:643-649`; `run_web.py` |

## Required work before multi-user hosting

1. Add accounts, secure authenticated sessions, logout and account recovery; define administrator roles separately.
2. Introduce a tenant/user owner on every order and saved result. Enforce object-level authorization in every read, stream, save and cancel route. Migrate existing rows deliberately.
3. Replace process-wide active state with a tenant-aware persistent job model; use unguessable identifiers as references, not as authorization.
4. Store each user's CALL-E credential in a real secret store with encryption, access controls, rotation and deletion, or make calls an operator-only service. Never expose or log the credential. Enforce per-user quotas and billing boundaries.
5. Add a tested retention schedule and deletion/export workflow covering SQLite rows, transcripts, active jobs, logs and backups.
6. Add CSRF protection for state-changing browser actions, secure cookie settings, TLS at the edge, rate limits, request-size limits, audit events and monitoring. Perform a separate security review.
7. Make connected services configurable and visible. Document Nominatim, Overpass, tile service and CALL-E roles, contracts, regions, subprocessors and retention from verified provider material.
8. Complete the controller/processor allocation, legal bases, Article 13/14 call-layer information, processor agreements and any Chapter V transfer mechanism before launch.

The privacy notice template is only one launch artifact. Filling it in does not repair these technical gaps or establish a legal basis.
