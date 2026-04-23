"""Smoke tests: the server module imports and registers tools/resources."""
from __future__ import annotations


def test_server_imports():
    from lemieux.mcp import server
    assert server.mcp is not None


def test_tools_registered():
    from lemieux.mcp import server
    # FastMCP stores tools as an internal registry; the exact API differs by SDK version.
    # We just verify the decorated functions are importable and callable objects.
    for name in ["query_skater_stats", "query_team_stats", "project_swap_scenario",
                 "rank_players", "fetch_game_detail"]:
        assert hasattr(server, name), f"tool {name} missing from server module"


def test_resources_registered():
    from lemieux.mcp import server
    for name in ["list_glossary", "get_glossary_term", "list_sources", "get_methodology"]:
        assert hasattr(server, name), f"resource {name} missing"


def test_methodology_mentions_ci():
    from lemieux.mcp import server
    m = server.get_methodology()
    assert "80%" in m and "CI" in m
