# Security model

ESL Manager is a local operations tool. Its default runtime is a demo/simulation mode and must remain useful without access to a physical ESL controller.

## Trust boundaries

1. Browser ↔ local backend: the browser uses only the application's same-origin REST API.
2. Backend ↔ SQLite: all SQL values are parameterized; migrations/schema are static application code.
3. Backend ↔ ESL controller: credentials and session cookies come only from process environment/runtime memory.

## Live-write controls

A physical display update is denied unless all conditions are true:

- process environment contains `ESL_LIVE_WRITES=1`;
- the caller has a valid write session created with the deployment's high-entropy API token;
- the request includes the exact explicit confirmation expected by the backend;
- the pre-write state is known and post-write read-back observes a relevant state transition.

The default is deny. Every API mutation requires authentication when an API token is configured. Session cookies are `HttpOnly` and `SameSite=Strict`, expire after an absolute eight hours, and browser-origin mutations must match the request host. The in-memory session store is capped at 128 entries. Read-only sync and simulated job processing are separate operations. Physical delete endpoints are not exposed.

## Deployment assumptions

- Bind to `127.0.0.1` unless the operator explicitly chooses LAN exposure.
- The live launcher enables built-in token-to-session authentication, but it does not provide TLS. Use only on a trusted, firewalled LAN or place it behind an HTTPS reverse proxy; the login token otherwise travels over plain HTTP.
- Do not expose the application to the public Internet.
- Rotate legacy ESL credentials before enabling integration because historical research files contain test credentials/session material.

## Data handling

Products, pricing, device inventory, jobs and audit events are stored in local SQLite. Runtime databases are ignored by Git. CSV export can contain commercial pricing data and should be handled accordingly.
