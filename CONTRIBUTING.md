# Contributing to Lemieux / Contribuer à Lemieux

🇬🇧 English first, 🇫🇷 Français below.

---

## 🇬🇧 English

Thanks for considering a contribution. The project is deliberately small-scoped: a handful of well-tested components that let Claude (or any MCP client) do honest hockey analysis. Your PR should leave it boringly functional.

### Easiest first PR: a new connector

Most contributions are new data source connectors. The template-and-three-tests pattern:

1. **Copy the template**
   ```bash
   cp -r templates/connector-template packages/lemieux-connectors/src/lemieux/connectors/<your-source>
   ```
2. **Implement `refresh()`** — return a DataFrame matching your declared schema (pandera).
3. **Record HTTP fixtures** — use `vcrpy` (or save HTML snapshots) to capture a happy path and a failure.
4. **Write three tests**: schema shape, happy refresh, error handling.
5. **Update `REGISTRY.yaml`** — license, rate-limit, "safe to cache" flag.
6. **Open the PR** with a one-paragraph doc on what the source provides and any gotchas.

### Adding a skill

1. `cp -r templates/skill-template .claude/skills/<your-skill>`
2. Write both EN and FR `SKILL.md` instructions.
3. Skill must reference glossary terms (not inline definitions) and surface sample size in outputs.
4. Include an example invocation + expected output shape.

### Adding a glossary term

1. Open `packages/lemieux-glossary/src/lemieux/glossary/terms.yaml`
2. Add entry with `id`, `en.short`, `en.long`, `fr.short`, `fr.long`, `formula`, `caveats`, `sources`.
3. Run `pytest packages/lemieux-glossary/tests` — tests check every term has both languages and at least one caveat.

### Docs

- English under `docs/en/`, French under `docs/fr/`. Keep them in sync; a "translation pending" stub is acceptable for brand-new pages.
- Glossary content is source-of-truth for metric definitions — don't duplicate into docs.

### Test & CI expectations

- `pytest` must pass across all packages. Each package has its own `tests/` dir.
- Connectors use recorded fixtures; **no live network calls in CI**.
- `uv run ruff check` and `ruff format` before pushing.
- The `connector-health` workflow runs nightly against live APIs and opens issues on schema drift — if you own a connector, you're expected to triage drift within 2 weeks.

### Community norms

- **Be wrong out loud.** If your analysis turns out to overclaim, fix it publicly.
- **Cite sources.** Every factual claim in docs/examples needs a link.
- **No predictions.** This project does not produce "who will win" content.
- **No betting tooling.** We stay on the analytics side.
- **Code of conduct**: Contributor Covenant 2.1 applies.

### Maintainer cadence

One-two maintainers currently. PR reviews happen weekly in batches. Stale bot auto-closes inactive issues after 90 days. If you need something sooner, drop a note in the PR — real urgency is respected.

---

## 🇫🇷 Français

Merci d'envisager une contribution. La portée du projet est volontairement restreinte : quelques composantes bien testées qui permettent à Claude (ou à tout client MCP) de produire une analyse de hockey honnête. Votre PR devrait laisser le projet fonctionnel et sans surprises.

### Contribution la plus facile : un nouveau connecteur

La plupart des contributions sont des connecteurs de sources de données. Le modèle « gabarit + trois tests » :

1. **Copier le gabarit**
   ```bash
   cp -r templates/connector-template packages/lemieux-connectors/src/lemieux/connectors/<votre-source>
   ```
2. **Implémenter `refresh()`** — retourner un DataFrame conforme au schéma déclaré (pandera).
3. **Enregistrer des réponses HTTP** — `vcrpy` ou captures HTML, pour un chemin heureux et un échec.
4. **Écrire trois tests** : forme du schéma, rafraîchissement heureux, gestion d'erreurs.
5. **Mettre à jour `REGISTRY.yaml`** — licence, limites de débit, indicateur « sûr à mettre en cache ».
6. **Ouvrir la PR** avec un paragraphe expliquant ce qu'offre la source et les pièges connus.

### Ajouter une habileté (skill)

1. `cp -r templates/skill-template .claude/skills/<votre-skill>`
2. Rédiger les instructions `SKILL.md` en anglais ET en français.
3. L'habileté doit référencer les termes du lexique (pas de définitions incluses) et afficher la taille de l'échantillon dans ses sorties.
4. Inclure un exemple d'invocation + la forme attendue de la sortie.

### Ajouter un terme au lexique

1. Ouvrir `packages/lemieux-glossary/src/lemieux/glossary/terms.yaml`
2. Ajouter une entrée avec `id`, `en.short`, `en.long`, `fr.short`, `fr.long`, `formula`, `caveats`, `sources`.
3. Lancer `pytest packages/lemieux-glossary/tests` — les tests vérifient que chaque terme a les deux langues et au moins une mise en garde.

### Documentation

- Anglais sous `docs/en/`, français sous `docs/fr/`. Gardez-les synchronisés; un message « traduction en attente » est acceptable pour les toutes nouvelles pages.
- Le lexique est la source de vérité pour les définitions de métriques — ne pas dupliquer dans la doc.

### Attentes sur les tests et l'intégration continue

- `pytest` doit passer pour tous les paquets. Chaque paquet a son propre dossier `tests/`.
- Les connecteurs utilisent des réponses enregistrées; **pas d'appels réseau en direct dans l'IC**.
- `uv run ruff check` et `ruff format` avant de pousser.
- Le flux `connector-health` s'exécute toutes les nuits contre les API en direct et ouvre des tickets lorsqu'un schéma change — si vous maintenez un connecteur, vous êtes responsable de traiter les dérives dans les 2 semaines.

### Normes communautaires

- **Admettez vos erreurs publiquement.** Si une analyse s'avère exagérée, corrigez-la ouvertement.
- **Citez vos sources.** Chaque affirmation factuelle en doc/exemples doit avoir un lien.
- **Pas de prédictions.** Ce projet ne produit pas de contenu « qui va gagner ».
- **Pas d'outillage de paris sportifs.** On reste du côté analytique.
- **Code de conduite** : Contributor Covenant 2.1 s'applique.

### Rythme de maintenance

Un à deux mainteneurs actuellement. Les révisions de PR se font une fois par semaine, par lots. Le robot d'archivage ferme automatiquement les tickets inactifs après 90 jours. Si vous avez besoin de quelque chose plus tôt, mentionnez-le dans la PR — l'urgence réelle est respectée.
