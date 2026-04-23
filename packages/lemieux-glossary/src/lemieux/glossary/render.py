"""Render glossary entries into various output formats."""
from __future__ import annotations

from typing import Literal

from .loader import Term, get_term

Lang = Literal["en", "fr"]


def render_for_markdown(term_id: str, lang: Lang = "en") -> str:
    """Return a markdown block suitable for embedding in a draft post."""
    t: Term = get_term(term_id, lang)
    tl = t.for_lang(lang)
    lines = [f"**{tl.short}** — {tl.long}"]
    if t.formula:
        lines.append("")
        lines.append(f"Formula: `{t.formula}`")
    if t.caveats:
        lines.append("")
        lines.append("Caveats:" if lang == "en" else "Mises en garde :")
        for c in t.caveats:
            lines.append(f"- {c}")
    return "\n".join(lines)


def render_for_docx_callout(term_id: str, lang: Lang = "en") -> dict:
    """Return a structured dict a docx builder can turn into a shaded callout box."""
    t: Term = get_term(term_id, lang)
    tl = t.for_lang(lang)
    return {
        "title": tl.short,
        "body": tl.long,
        "formula": t.formula,
        "caveats": list(t.caveats),
        "sources": list(t.sources),
    }


def render_mcp_resource(term_id: str, lang: Lang = "en") -> dict:
    """Return a JSON-serializable payload suitable as an MCP resource."""
    t: Term = get_term(term_id, lang)
    tl = t.for_lang(lang)
    return {
        "id": t.id,
        "lang": lang,
        "short": tl.short,
        "long": tl.long,
        "formula": t.formula,
        "caveats": list(t.caveats),
        "sources": list(t.sources),
    }
