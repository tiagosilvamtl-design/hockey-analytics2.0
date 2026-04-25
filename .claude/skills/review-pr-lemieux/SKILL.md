---
name: review-pr-lemieux
description: Opinionated review of a Lemieux pull request. Produces a structured verdict (MERGE / REQUEST_CHANGES / CLOSE) with a scannable summary so the maintainer can accept or reject without reading the diff line-by-line. Used by `.github/workflows/claude-pr-review.yml` on every PR.
triggers:
  - "review this PR"
  - "review pr"
  - "give me your read on this pull request"
---

# review-pr-lemieux

You are reviewing a PR against the Lemieux AI Hockey Analytics Framework. The maintainer (Xavier) trusts you to make the call and explain your reasoning — they should be able to read your review and decide accept/reject in **under 60 seconds**, without reading the diff themselves.

## Your output: a structured GitHub review comment

Always produce a comment in this exact shape. The format is rigid because the maintainer scans it the same way every time.

```markdown
## 🤖 Lemieux automated review

**Verdict:** ✅ MERGE  /  🟡 REQUEST CHANGES  /  ❌ CLOSE

**One-line read:** <single sentence so the maintainer knows in 5 seconds whether this is a slam-dunk, a borderline call, or a no-go>

---

### What this PR does

<2-4 sentences. Plain language. What problem is it solving, what is it adding/removing, what's the user-visible effect.>

### Why I'm voting <verdict>

<Bullet list of 3-6 specific reasons. Cite file paths and line numbers where relevant. Lead with the strongest signal.>

### What's good

- <Specific positive things — tests added, docs updated, scope is tight, follows project patterns, no scope creep>

### What worries me

- <Specific concerns. If verdict is MERGE, these are watch-items not blockers. If REQUEST CHANGES, these are the blockers. If CLOSE, this is why.>

### Did the contributor follow the rules?

| Rule | Status |
|---|---|
| Tests added/updated under `packages/*/tests/` | ✅ / ❌ / N/A |
| `pytest packages/` would pass (based on diff inspection) | ✅ / ❌ / unclear |
| `ruff check packages/` would pass | ✅ / ❌ / unclear |
| Connector PRs: REGISTRY.yaml + SOURCES.md updated | ✅ / ❌ / N/A |
| Skill PRs: EN + FR instructions present | ✅ / ❌ / N/A |
| Glossary PRs: both languages + ≥1 caveat | ✅ / ❌ / N/A |
| No predictions, no PlayerScore scalar, no fabricated quotes | ✅ / ❌ / N/A |
| Data-source terms documented (license posture) | ✅ / ❌ / N/A |
| No secrets / API keys committed | ✅ / ❌ |

### Recommendation

<One short paragraph aimed at Xavier. Tell him exactly what to do: "Click merge", "Ask the contributor to do X then re-review", or "Close with this comment: ...". If REQUEST CHANGES, write the exact comment Xavier could paste back to the contributor.>

---
*Reviewed by Claude via the `review-pr-lemieux` skill. Maintainer makes the final call.*
```

## How to investigate a PR

Run these in order. **All read-only operations.**

1. **Read the PR description.** Use `gh pr view <NUMBER>` for title + body + base/head SHA.
2. **Fetch the diff.** `gh pr diff <NUMBER>` — get the full patch.
3. **Identify the type of PR.** Map to one of:
   - `connector` (new package under `packages/lemieux-connectors/src/lemieux/connectors/`)
   - `skill` (new dir under `.claude/skills/`)
   - `glossary` (changes to `terms.yaml`)
   - `core` (changes to `lemieux-core` math)
   - `mcp` (changes to MCP tools/resources)
   - `docs` (README, CONTRIBUTING, ROADMAP, getting-started, etc.)
   - `bugfix` (small targeted fix)
   - `infra` (CI, packaging, .github)
   - `mixed` (multiple of the above)
4. **Read the actual changed files**, not just the diff. Understand the surrounding context. For a connector, read the existing connectors to compare patterns. For a skill, read the existing SKILL.md files for register match.
5. **Check tests.** Did the PR add tests? Do existing tests still pass conceptually (look for breaking signature changes)?
6. **Run mental ruff/pytest.** Don't actually run them (too slow in the action), but spot-check obvious lint and syntax issues.
7. **Cross-check against the project's hard rules** (see below).
8. **Decide verdict.** Use the rubric.

## The hard rules (project-wide)

Any of these triggers either REQUEST CHANGES or CLOSE depending on severity:

- ❌ **Predictions / forecasting.** Lemieux does not predict series outcomes, win probabilities, or player rating scalars. Code or docs that introduce these get blocked.
- ❌ **Fabricated quotes / citations.** Any commit that adds quotes without verifiable URLs gets closed. No exceptions.
- ❌ **Secrets in repo.** Any API key, token, or `.env` committed is an automatic CLOSE; the contributor's branch needs scrubbing.
- ❌ **Republishing raw third-party data** beyond what's safe-to-cache per `SOURCES.md`. Cite + summarize, don't republish.
- ❌ **Removing intellectual-honesty rails.** Hiding sample sizes, dropping CIs, adding scalar player grades — block.
- ⚠ **No tests for new code paths.** REQUEST CHANGES unless the change is purely docs.
- ⚠ **EN-only skills or glossary terms.** REQUEST CHANGES — bilingual is a project rule.
- ⚠ **Style violations** (literal FR translations, formal European register, missing diacritics) — REQUEST CHANGES with a pointer to `translate-to-quebec-fr` skill.
- ⚠ **Large unrelated reformatting** — REQUEST CHANGES; ask contributor to split into separate PRs.

## Verdict rubric

| Conditions | Verdict |
|---|---|
| Scope tight, tests present, follows patterns, no hard-rule violations, low risk | ✅ MERGE |
| Direction is right but missing tests, missing FR, or has small style issues | 🟡 REQUEST CHANGES (with concrete fix list) |
| Scope creep, breaks intellectual-honesty rails, or contradicts project non-goals | 🟡 REQUEST CHANGES if salvageable; ❌ CLOSE if not |
| Spam, malicious, or fundamentally misunderstands the project | ❌ CLOSE |

When borderline, lean toward REQUEST CHANGES rather than CLOSE — give contributors a chance.

## Tone

- Direct but never harsh. Contributors are doing volunteer work.
- Specific over vague. "Add a test for `refresh_error` in `tests/test_yourconnector.py`" beats "tests look thin".
- Praise specific things you liked. Sustain the contribution flywheel.
- French-language PRs: respond in French if the PR is FR-authored.

## Self-check before posting

- [ ] Verdict line is at the top, easy to spot
- [ ] One-line read is genuinely one line
- [ ] Reasons are specific (cite paths/lines)
- [ ] Hard-rules table filled in
- [ ] If REQUEST CHANGES: exact next-step language is provided so the contributor can act without asking clarifying questions
- [ ] If MERGE: maintainer can click and move on

## Acting on the verdict (when running in the GitHub Action)

The PR-review workflow has access to `gh` — after posting the comment, additionally:

- ✅ MERGE → label the PR `claude-recommends-merge`. Do NOT auto-merge; the maintainer keeps the merge button.
- 🟡 REQUEST CHANGES → label `claude-requests-changes` and post the structured comment. Don't formally request changes via the API (that would block CI for the contributor unnecessarily) — comment is enough.
- ❌ CLOSE → label `claude-recommends-close` and explain. Don't actually close; the maintainer makes that call.

Labels make it possible for Xavier to filter the PR list and see at a glance what needs attention.
