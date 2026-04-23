# Connector template

Copy this directory to `packages/lemieux-connectors/src/lemieux/connectors/<your_source>` to start a new connector.

## Files

- `__init__.py` — exports your client + metadata
- `client.py` — subclass of `Connector`, implements `refresh()`
- `schemas.py` — pandera schemas for canonical DataFrames

## Checklist before opening a PR

- [ ] `refresh()` returns a DataFrame matching the declared schema
- [ ] `ConnectorMetadata` filled in (license note, rate limit, key_required)
- [ ] Tests: `test_schema.py`, `test_refresh_happy.py`, `test_refresh_error.py`
- [ ] Fixture captured via VCR or saved HTML/JSON
- [ ] Entry added to `packages/lemieux-connectors/REGISTRY.yaml`
- [ ] Note in `SOURCES.md` at the repo root
- [ ] FR + EN description in both files
