# Pull request

## What does this PR do?

<!-- One sentence. Link any related issue with "Fixes #123". -->

## Type

- [ ] New connector (copy of `templates/connector-template/`)
- [ ] New Claude skill (copy of `templates/skill-template/`)
- [ ] New glossary term(s)
- [ ] Bug fix
- [ ] Docs / translation
- [ ] Other: ___

## Checklist

- [ ] Tests added or updated under the relevant `packages/*/tests/`
- [ ] `pytest packages/` passes locally
- [ ] `ruff check packages/` passes
- [ ] If adding a connector: entry in `packages/lemieux-connectors/REGISTRY.yaml` + note in root `SOURCES.md`
- [ ] If adding a skill: both EN + FR instructions in `SKILL.md`
- [ ] If adding a glossary term: EN + FR + at least one caveat

## Non-goals honoured

- [ ] Does not predict series outcomes
- [ ] Does not introduce a single "player rating" scalar
- [ ] Does not republish raw third-party data (only derived analyses)
- [ ] Does not fabricate quotes or unverifiable narrative

## Data source terms (if applicable)

<!-- For connector PRs: paste or link the source's terms of use. Confirm redistribution posture. -->
