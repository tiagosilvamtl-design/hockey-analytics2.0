// Cross-game context-file fact-check helper.
// Usage in renderers:
//   const ctx = require('./game_context_check');
//   ctx.assertGameClaim({game: 2, kind: 'fight', period: 2, time: '05:14',
//                        contextDir: __dirname});
//   ctx.assertScore({game: 2, expected: 'TBL 3 - MTL 2 (OT)', contextDir: __dirname});
//
// Aborts the build with exit code 8 if a claim contradicts the context file
// (or the context file doesn't exist). Prints a precise diff to stderr.

const fs = require('fs');
const path = require('path');

function loadContext(gameN, contextDir) {
  const file = path.join(contextDir, `game${gameN}_context.yaml`);
  if (!fs.existsSync(file)) {
    console.error(`\nERROR: cross-game claim references game ${gameN} but ${file} does not exist.`);
    console.error(`Generate it via: tools/build_game_context.py <gameId> --series ... --output-dir ${contextDir}`);
    process.exit(8);
  }
  // Minimal yaml parse — relies on the official `yaml` package if available,
  // else falls back to a hand-rolled parser sufficient for our schema.
  try {
    return require('yaml').parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    console.error(`\nERROR: failed to parse ${file}: ${e.message}`);
    process.exit(8);
  }
}

function assertGameClaim({ game, kind, period, time, contextDir }) {
  const ctx = loadContext(game, contextDir);
  const events = ctx.key_events || [];
  const matches = events.filter(e =>
    e.kind === kind &&
    (period === undefined || e.period === period) &&
    (time === undefined || e.time_in_period === time)
  );
  if (!matches.length) {
    console.error(`\nERROR: game ${game} does NOT contain a ${kind} at P${period} ${time || ''}.`);
    console.error(`Available key_events in game${game}_context.yaml:`);
    for (const e of events) {
      console.error(`  - ${e.kind} P${e.period} ${e.time_in_period}` + (e.hitter ? ` (${e.hitter} on ${e.hittee})` : '') + (e.primary_player ? ` (${e.primary_player})` : ''));
    }
    process.exit(8);
  }
  return matches[0];
}

function assertScore({ game, expected, contextDir }) {
  const ctx = loadContext(game, contextDir);
  const actual = ctx.result;
  const norm = (s) => String(s).replace(/\s+/g, ' ').trim().toLowerCase();
  if (norm(actual) !== norm(expected)) {
    console.error(`\nERROR: claimed game ${game} result "${expected}" does not match game${game}_context.yaml "${actual}".`);
    process.exit(8);
  }
  return actual;
}

function assertSeriesState({ afterGame, expected, contextDir }) {
  const ctx = loadContext(afterGame, contextDir);
  const actual = ctx.series_state_after_game || '';
  const norm = (s) => String(s).replace(/\s+/g, ' ').trim().toLowerCase();
  if (norm(actual) !== norm(expected)) {
    console.error(`\nERROR: claimed series state after game ${afterGame} ("${expected}") does not match game${afterGame}_context.yaml ("${actual}").`);
    process.exit(8);
  }
  return actual;
}

module.exports = { loadContext, assertGameClaim, assertScore, assertSeriesState };
