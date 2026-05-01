"""Lemieux glossary — bilingual hockey analytics terms."""
from __future__ import annotations

from .loader import Term, get_term, list_terms, load_terms
from .render import render_for_docx_callout, render_for_markdown, render_mcp_resource

__all__ = [
    "Term",
    "get_term",
    "list_terms",
    "load_terms",
    "render_for_markdown",
    "render_for_docx_callout",
    "render_mcp_resource",
]

__version__ = "0.1.0"
