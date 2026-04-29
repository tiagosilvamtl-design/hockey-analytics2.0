# lemieux-connectors

Plugin-style data source adapters. Every connector is a self-contained sub-package with its own schema, tests, and license metadata.

## Shipping day-1

| Connector | Source | Key required | Status |
|---|---|---|---|
| `nhl_api` | api-web.nhle.com, api.nhle.com/stats | no | ✅ |
| `nst` | data.naturalstattrick.com | yes (user-level) | ✅ |
| `moneypuck` | moneypuck.com/data.htm | no | 🚧 roadmap |
| `pwhl` | thepwhl.com | no | 🚧 roadmap |

## Adding a connector

```bash
cp -r templates/connector-template packages/lemieux-connectors/src/lemieux/connectors/<your-source>
# implement refresh(), declare schema, record fixtures
```

## Global conventions

- Every connector reads its secrets (if any) from `os.environ`; no hardcoded keys.
- Every connector routes through the shared `HttpCache` in `_base/cache.py` (SQLite-backed).
- Every connector uses a `RateLimiter` from `_base/rate_limit.py` (defaults to 1 req/sec).
- `truststore.inject_into_ssl()` is called once at import so corporate SSL-intercepted machines work out of the box.
