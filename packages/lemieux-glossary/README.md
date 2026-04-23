# lemieux-glossary

Bilingual (EN/FR) canonical definitions of hockey analytics terms. Every metric cited by any Lemieux output links back to an entry here.

```python
from lemieux.glossary import get_term, list_terms, render_for_markdown

term = get_term("iso_xgf60", lang="fr")
print(term.short)  # "xGF/60 isolé"
```

Add a term by editing `src/lemieux/glossary/terms.yaml`. Tests enforce that every entry has both languages and at least one caveat.
