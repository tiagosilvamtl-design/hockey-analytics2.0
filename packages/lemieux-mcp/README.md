# lemieux-mcp

FastMCP server that exposes Lemieux's analytics primitives and data access to any MCP client (Claude Code, Claude Desktop, Cursor, etc.).

## Run

```bash
pip install lemieux-mcp
lemieux-mcp --store ~/.lemieux/store.sqlite
```

Then add to your Claude Desktop `mcp.json`:

```json
{
  "mcpServers": {
    "lemieux": {
      "command": "lemieux-mcp",
      "args": ["--store", "/Users/<you>/.lemieux/store.sqlite"],
      "env": {
        "NST_ACCESS_KEY": "your-key-here"
      }
    }
  }
}
```

## Tools (what Claude can DO)

| Tool | Purpose |
|---|---|
| `query_skater_stats` | Fetch MTL roster or any team's skaters at any strength state, with pooled baseline |
| `query_team_stats` | Team totals by (season, stype, sit) |
| `project_swap` | The swap scenario engine — 80% CI bands, honest about sample size |
| `fetch_game_detail` | Shift-chart + play-by-play joined for one game |
| `rank_players` | Positive / negative contributors by iso net impact |
| `player_period_slice` | Slafkovský-style analysis: bucket shifts by (game, period) |

## Resources (what Claude reads for context)

| Resource | What |
|---|---|
| `lemieux://glossary` | List of all glossary term IDs |
| `lemieux://glossary/{term_id}?lang=en|fr` | One term's full definition |
| `lemieux://sources` | Data-source registry with license terms |
| `lemieux://methodology` | How CIs are constructed, pooling strategy, limits |

## Design principles

Every tool response includes **sample-size metadata** (TOI, GP, pooled-window spec) so Claude can't quietly hide uncertainty. Every numeric output is paired with an 80% CI where applicable.
