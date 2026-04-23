"""Load and query bilingual glossary terms."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

TERMS_YAML = Path(__file__).parent / "terms.yaml"
Lang = Literal["en", "fr"]


@dataclass(frozen=True)
class TermLang:
    short: str
    long: str


@dataclass(frozen=True)
class Term:
    id: str
    en: TermLang
    fr: TermLang
    formula: str | None
    caveats: tuple[str, ...]
    sources: tuple[str, ...]

    def for_lang(self, lang: Lang) -> TermLang:
        return self.fr if lang == "fr" else self.en


@lru_cache(maxsize=1)
def load_terms(path: Path | None = None) -> dict[str, Term]:
    p = path or TERMS_YAML
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    entries = raw.get("terms", [])
    out: dict[str, Term] = {}
    for e in entries:
        out[e["id"]] = Term(
            id=e["id"],
            en=TermLang(short=e["en"]["short"], long=e["en"]["long"]),
            fr=TermLang(short=e["fr"]["short"], long=e["fr"]["long"]),
            formula=e.get("formula"),
            caveats=tuple(e.get("caveats") or ()),
            sources=tuple(e.get("sources") or ()),
        )
    return out


def get_term(term_id: str, lang: Lang = "en") -> Term:
    terms = load_terms()
    if term_id not in terms:
        raise KeyError(f"Unknown glossary term: {term_id!r}. Known: {sorted(terms)}")
    return terms[term_id]


def list_terms() -> list[Term]:
    return list(load_terms().values())
