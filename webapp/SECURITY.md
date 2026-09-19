# Security model

ESL Manager is a local operations tool. Its default runtime is a demo/simulation mode and must remain useful without access to a physical ESL controller.

## Trust boundaries

1. Browser ↔ local backend: the browser uses only the application's same-origin REST API.
2. Backend ↔ SQLite: all SQL values are parameterized; migrations/schema are static application code.
3. Backend ↔ ESL controller: credentials and session cookies come only from process environment/runtime memory.

## Live-write controls

A physical display update is denied unless both conditions are true:

- process environment contains `ESL_LIVE_WRITES=1`;
- the request includes the exact explicit confirmation expected by the backend.

The default is deny. Read-only sync and simulated job processing are separate operations. Physical delete endpoints are not exposed.

## Deployment assumptions

- Bind to `127.0.0.1` unless the operator explicitly chooses LAN exposure.
- LAN exposure requires an authenticated reverse proxy and network firewall; the built-in server does not provide user authentication or TLS.
- Do not expose the application to the public Internet.
- Rotate legacy ESL credentials before enabling integration because historical research files contain test credentials/session material.

## Data handling

Products, pricing, device inventory, jobs and audit events are stored in local SQLite. Runtime databases are ignored by Git. CSV export can contain commercial pricing data and should be handled accordingly.
