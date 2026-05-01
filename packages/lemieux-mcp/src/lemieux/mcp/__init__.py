"""Lemieux MCP server — analytics tools + resources for any MCP client."""
from __future__ import annotations

from .server import build_server, main

__all__ = ["main", "build_server"]
__version__ = "0.1.0"
