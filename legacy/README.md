# legacy/ — prototype that seeded Lemieux

This directory contains the original `claudehockey` prototype that was refactored into the `lemieux` monorepo structure (`packages/`, `.claude/`, etc.).

It is kept for two reasons:

1. **Working Streamlit app.** `legacy/app.py` still runs and provides the validation UI described in the architectural plan. It will be migrated into `packages/lemieux-app` in a follow-up.
2. **Habs Round 1 2026 example orchestrator.** `legacy/analytics/habs_round1.py` is the script that produced `examples/habs_round1_2026/habs_round1_2026.docx`. Until it's ported to use the new MCP tools, this is the canonical "from numbers to published artifact" reference.

## Running the legacy app

```bash
# From repo root, after pip install -e packages/lemieux-connectors etc.
cd legacy
python -m venv .venv && source .venv/bin/activate
pip install -r ../packages/lemieux-connectors/pyproject.toml  # or: pip install pandas streamlit plotly requests
python app.py
```

## Migration status

| Legacy path | New home | Migrated? |
|---|---|---|
| `legacy/data/nst_client.py` | `packages/lemieux-connectors/src/lemieux/connectors/nst/client.py` | ✅ |
| `legacy/data/nst_parsers.py` | `packages/lemieux-connectors/src/lemieux/connectors/nst/parsers.py` | ✅ |
| `legacy/analytics/swap_engine.py` | `packages/lemieux-core/src/lemieux/core/swap_engine.py` | ✅ |
| `legacy/ui/` (Streamlit) | `packages/lemieux-app/` | ⏳ pending |
| `legacy/analytics/habs_round1.py` | `examples/habs_round1_2026/` + MCP tool calls | ⏳ pending |
| `legacy/reports/build_habs_round1_2026.js` | `examples/habs_round1_2026/` | ⏳ pending |

Contributions welcome to complete the migration.
