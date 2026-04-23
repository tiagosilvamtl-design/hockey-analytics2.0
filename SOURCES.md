# Data sources — terms & caveats

This is the authoritative registry of every data source Lemieux connects to. Each connector package references this file. If a source's terms change, update here first; the connector follows.

**Rule of thumb**: Lemieux is MIT-licensed code. The data is NOT. Respect each source's terms, rate limits, robots.txt, and redistribution policy. When in doubt, link out rather than republish.

---

## NHL.com — public API (`api-web.nhle.com` / `api.nhle.com/stats`)

- **What's there**: Play-by-play, shift charts, rosters, schedules, standings, gamecenter, NHL EDGE (shot speed, skate speed).
- **Access**: Free, undocumented, unauthenticated. No API key required.
- **Rate limit**: Unofficial. Community practice: ≤10 req/sec sustained, cache aggressively.
- **Redistribution**: Not for commercial redistribution. Citing counts, linking to NHL.com, and caching for personal/analytic use are fine.
- **Stability**: Unofficial. Endpoints can change without notice. Schema drift is a real risk — we abstract via a connector and test nightly.
- **Docs (community)**: [Zmalski/NHL-API-Reference](https://github.com/Zmalski/NHL-API-Reference), [dword4/nhlapi](https://github.com/dword4/nhlapi)
- **Connector**: `lemieux-connectors/nhl_api`
- **Safe to cache**: Yes, indefinitely for game-completed data.

## Natural Stat Trick (`data.naturalstattrick.com`)

- **What's there**: Team + skater + goalie advanced stats, line combinations, defensive pairs, per-strength-state splits, historical data back to 2007-08.
- **Access**: Requires a personal access key requested via an NST user profile. Free (donations accepted), not a paid tier.
- **Rate limit**: Community norm ~1 req/sec with polite backoff. NST's scraping policy at [naturalstattrick.com/scraping.php](https://www.naturalstattrick.com/scraping.php) explicitly authorizes automated traffic on `data.naturalstattrick.com` with a key; main site is strictly controlled.
- **Redistribution**: Do NOT redistribute raw tables. Derived analyses that cite NST are expected and welcomed.
- **Connector**: `lemieux-connectors/nst`
- **Safe to cache**: Yes; TTL by staleness (live games 6h, completed 7d, historical 30d).
- **Key handling**: Each user supplies their own key via `.env`. Never commit a key. Never share across users.

## MoneyPuck (`moneypuck.com/data.htm`)

- **What's there**: CSV dumps of player stats, team stats, shot data, goalie stats using MoneyPuck's xG model (differs from NST's — useful for cross-validation).
- **Access**: Free. Nightly updates.
- **Rate limit**: Implicit. Cache files locally; don't re-hit per-query.
- **Redistribution**: Document source; do not republish raw files.
- **Connector**: `lemieux-connectors/moneypuck`
- **Safe to cache**: Yes.

## PWHL (`thepwhl.com/en/stats`, `pwhl.hockey-statistics.com`)

- **What's there**: Women's league (Professional Women's Hockey League) — team and player stats, 2025-26 season live.
- **Access**: Free, public.
- **Rate limit**: Unofficial; be polite.
- **Redistribution**: Cite source.
- **Connector**: `lemieux-connectors/pwhl` (roadmap)
- **Why it matters**: Almost zero public analytics tooling covers PWHL. This is a deliberate differentiator.

## All Three Zones (Corey Sznajder) — **subscription-gated**

- **What's there**: Hand-tracked microstats — zone entries/exits, scoring chances, passing. Unique depth, no equivalent public source.
- **Access**: Patreon subscription (~$5-20/month tiers). Data distributed via Dropbox/Google Drive links.
- **Redistribution**: Absolutely not. Data is paywalled; each user brings their own subscription.
- **Connector**: `lemieux-connectors/all_three_zones` (roadmap, opt-in)
- **Design**: Connector reads files from a user-supplied local path — we never hit Patreon's API nor redistribute a single row.

## Hockey-Reference (`hockey-reference.com`)

- **What's there**: Historical stats, rosters, season summaries, records.
- **Access**: Free scraping; bot policy at [sports-reference.com/bot-traffic.html](https://www.sports-reference.com/bot-traffic.html) enforces 20 req/min.
- **Redistribution**: Sports-Reference family doesn't love redistribution. Cite, link, cache locally.
- **Connector**: `lemieux-connectors/hockey_reference` (roadmap)

## Evolving-Hockey (`evolving-hockey.com`)

- **Status**: Dashboard-only as of 2026. No CSV export, no public API. RAPM model is widely cited.
- **Use in Lemieux**: Manual reference only. We do not scrape Evolving-Hockey. The glossary cites their RAPM methodology where relevant.

## HockeyViz (`hockeyviz.com` — Micah McCurdy)

- **Status**: Subscription visualizations. Not integrable.
- **Use in Lemieux**: Cited in docs when contextualizing our isolated-impact approach.

## Big Data Cup (Stathletes — `stathletes.com/big-data-cup`)

- **What's there**: Annual public research datasets with detailed event tracking.
- **Access**: Free downloads via GitHub ([bigdatacup repos](https://github.com/bigdatacup)).
- **Use in Lemieux**: Flat-file loader, not live connector. Good for reproducible research exercises.

## Sportlogiq, PuckPedia, CapFriendly

- **Status**: Paywalled / partnership-gated. Not integrated in V1. Documented here so users know why.

---

## General stance

- **Respect robots.txt.** If a source's robots.txt disallows a path, we don't scrape it, period.
- **Respect rate limits.** Our rate limiter defaults are conservative; users override at their own risk.
- **Never bypass paywalls.** Subscription-gated sources require user-supplied credentials/data.
- **Cache aggressively.** One fetch per unique query per TTL window. Don't be a jerk to upstream providers.
- **Fail visibly.** If a source returns an unexpected schema, connectors raise a clear error and log the first diff — so you know something changed rather than silently ingesting garbage.

If a source operator contacts us asking us to remove a connector or change behaviour, we do so without argument. Open an issue to report any concern: `sources@lemieux-ai` (placeholder — replace with actual contact once public).
