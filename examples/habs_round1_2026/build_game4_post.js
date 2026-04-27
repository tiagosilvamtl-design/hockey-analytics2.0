// Build branded EN + FR Word reports for the MTL vs. TBL Game 4 comprehensive
// post-game analysis. Mirrors build_game3_post.js patterns + adds:
//   - Cross-game context-file guards (assertGameClaim, assertScore)
//   - Pre-game thesis check section (Crozier swap projection vs reality)
//   - Slafkovský pre/post-Crozier-hit teaser linking to the companion brief
//   - Tier-color the per-period composite score for MOTM (Hagel)
//
// Run:
//   node examples/habs_round1_2026/build_game4_post.js

const fs = require('fs');
const path = require('path');
const yaml = require('yaml');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'game4_analysis.numbers.json'), 'utf8'));
const LINEUPS = yaml.parse(fs.readFileSync(path.join(__dirname, 'game4_lineups.yaml'), 'utf8'));
const BAREME = JSON.parse(fs.readFileSync(path.join(__dirname, 'score_bareme.json'), 'utf8'));
const PRESS = JSON.parse(fs.readFileSync(path.join(__dirname, 'game4_press_validation.numbers.json'), 'utf8'));
const CLAIMS_YAML = yaml.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'research', '2025030124_claims.yaml'), 'utf8'));

// Cross-game context fact-check — must succeed before any docx is written.
const ctxCheck = require('./game_context_check');
ctxCheck.assertGameClaim({ game: 2, kind: 'fight', period: 2, time: '05:14', contextDir: __dirname });
ctxCheck.assertGameClaim({ game: 4, kind: 'hit',   period: 2, time: '17:48', contextDir: __dirname });
ctxCheck.assertScore({ game: 4, expected: 'TBL 3 - MTL 2', contextDir: __dirname });
ctxCheck.assertSeriesState({ afterGame: 4, expected: 'tied 2-2', contextDir: __dirname });
ctxCheck.assertSeriesState({ afterGame: 3, expected: 'MTL leads 2-1', contextDir: __dirname });

// ---------- BRAND ----------
const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70', red: 'A6192E',
  ink: '111111', mute: '666666', rule: 'BFBFBF',
  confirm: 'E2F0D9', neutral: 'FFF2CC', refute: 'F8CBAD',
  info: 'DEEAF6', caveat: 'FFF6E0', explainer: 'F2F2F2',
  mtlfill: 'EAF1FB', tblfill: 'F4E6E8',
  upfill: 'D4EDDA', downfill: 'F5C6CB',
};

const fmt = (n, p = 3) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const s = Number(n).toFixed(p);
  return (Number(n) > 0 ? '+' : '') + s;
};
const pct = (n, p = 1) => n === null || n === undefined ? '—' : Number(n).toFixed(p) + '%';
const pctFr = (n, p = 1) => n === null || n === undefined ? '—' : (Number(n).toFixed(p) + ' %').replace('.', ',');
const fmtFr = (n, p = 3) => fmt(n, p).replace('.', ',');

const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: BRAND.rule };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

// ---------- bareme helpers ----------
function tierFor(score) {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  const t = BAREME.tiers;
  if (score < t.Awful.max) return 'Awful';
  if (score < t.Mediocre.max) return 'Mediocre';
  if (score < t.Good.max) return 'Good';
  return 'Excellent';
}
function tierFill(score) { const t = tierFor(score); return t ? BAREME.tiers[t].color_hex : undefined; }
function tierLabel(score, lang) {
  const t = tierFor(score); if (!t) return '—';
  return BAREME.tiers[t][lang === 'fr' ? 'label_fr' : 'label_en'];
}

// ---------- docx primitives ----------
function md(s) {
  const parts = []; const re = /\*\*(.+?)\*\*/g;
  let last = 0; let m;
  while ((m = re.exec(s)) !== null) {
    if (m.index > last) parts.push(new TextRun({ text: s.slice(last, m.index), font: 'Arial', size: 20, color: BRAND.ink }));
    parts.push(new TextRun({ text: m[1], bold: true, font: 'Arial', size: 20, color: BRAND.ink }));
    last = re.lastIndex;
  }
  if (last < s.length) parts.push(new TextRun({ text: s.slice(last), font: 'Arial', size: 20, color: BRAND.ink }));
  return parts;
}
function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 100 },
    children: opts.italics
      ? [new TextRun({ text, italics: true, color: opts.color || BRAND.mute, font: 'Arial', size: 20 })]
      : md(text),
  });
}
function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 },
    children: [new TextRun({ text, bold: true, size: 30, color: BRAND.navy, font: 'Arial' })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, bold: true, size: 24, color: BRAND.navyLight, font: 'Arial' })] });
}
function bullets(items) {
  return items.map(s => new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    spacing: { after: 80 },
    children: md(s),
  }));
}

function dataTable(headers, rows, widths) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map(h => new TableCell({
      borders: cellBorders,
      shading: { type: ShadingType.CLEAR, color: 'auto', fill: BRAND.navy },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ spacing: { before: 60, after: 60 },
        children: [new TextRun({ text: h, bold: true, color: 'FFFFFF', font: 'Arial', size: 18 })] })],
    })),
  });
  const bodyRows = rows.map(r => {
    const cells = Array.isArray(r) ? r : r.cells;
    const opts = Array.isArray(r) ? {} : (r._opts || {});
    return new TableRow({
      children: cells.map(c => {
        const isObj = c && typeof c === 'object' && !Array.isArray(c) && 'value' in c;
        const text = isObj ? String(c.value ?? '—') : String(c ?? '—');
        const fill = isObj && c.fill ? c.fill : opts.fill;
        const bold = !!(isObj && c.bold);
        return new TableCell({
          borders: cellBorders,
          shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ spacing: { before: 40, after: 40 },
            children: [new TextRun({ text, font: 'Arial', size: 18, color: BRAND.ink, bold })] })],
        });
      }),
    });
  });
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, columnWidths: widths, rows: [headerRow, ...bodyRows] });
}

// ---------- prose fact-check guard ----------
// Block 1: scoring claims about non-scorers.
function runProseFactCheck() {
  const goalcounts = {};
  for (const team of ['MTL', 'TBL']) {
    for (const [name, g] of Object.entries(D.series_goalscorers[team] || {})) {
      goalcounts[name.split(' ').slice(-1)[0]] = (goalcounts[name.split(' ').slice(-1)[0]] || 0) + g;
    }
  }
  // Names from lineups that have 0 goals in the series:
  const lineupNames = [];
  for (const team of ['MTL', 'TBL']) {
    for (const grp of ['forwards', 'defense']) {
      for (const item of (LINEUPS.teams[team][grp] || [])) {
        for (const p of (item.players || [])) {
          lineupNames.push(p.name);
        }
      }
    }
  }
  const corpus = [];
  for (const lang of ['en', 'fr']) {
    const t = T[lang];
    for (const k of Object.keys(t)) {
      const v = t[k];
      if (typeof v === 'string') corpus.push(v);
      else if (Array.isArray(v)) for (const item of v) if (typeof item === 'string') corpus.push(item);
    }
  }
  const blob = corpus.join(' \n ');
  const violations = [];
  for (const fullname of lineupNames) {
    const lastName = fullname.split(' ').slice(-1)[0];
    const goals = goalcounts[lastName] || 0;
    if (goals > 0) continue;
    // Patterns: <Name> scored | tied it | a marqué | etc, but NOT preceded by a hyphen (avoid trio labels)
    const rePatterns = [
      new RegExp(`(?<![\\-A-Za-zÀ-ÿ])${lastName} (?:[a-zà-ÿ ]{0,15} )?(?:scored|tied it|opened the scoring|a marqué|égale|ouvre la marque|inscrit)`, 'i'),
    ];
    for (const re of rePatterns) {
      const m = blob.match(re);
      if (m) violations.push(`Non-scorer "${fullname}" appears as scoring subject: "${m[0]}"`);
    }
  }
  if (violations.length) {
    console.error('\nProse fact-check guard: violations found.');
    for (const v of violations) console.error('  ✗ ' + v);
    process.exit(7);
  }
}

// ---------- I18N ----------
const tldrEN = () => {
  const p3 = PRESS.claim_2_p3_collapse.data_check.all_strengths_by_period;
  const p35v5 = PRESS.claim_2_p3_collapse.data_check.p3_5v5_only;
  return [
    `**TBL 3, MTL 2. Series tied 2–2; Game 5 in Tampa.** MTL led 2–0 in the second period, gave up a 4v4 goal with 54 seconds left in P2, then conceded twice to Hagel in the third (1:40 PP, 15:07 5v5). Hagel now has 6 goals in 4 series games.`,
    `**Did the Habs crash in P3? At 5v5, no.** MTL Corsi% by period: ${p3.mtl_corsi_pct_p1.toFixed(1)} → ${p3.mtl_corsi_pct_p2.toFixed(1)} → **${p3.mtl_corsi_pct_p3.toFixed(1)}%** in P3. Pure 5v5 in the third was even (${p35v5.mtl_attempts_5v5}–${p35v5.tbl_attempts_5v5} shot attempts). The damage was on **special teams + a deflection**, not on territorial collapse. **Three MTL penalties in P3** put Tampa on the man advantage — Hagel's tying goal came directly off the second of those.`,
    `**The Slafkovský hit is the second framework-anchor contact event of the series, not the second straight game.** The Hagel-Slafkovský fight was in **Game 2** (P2 5:14); Game 3 had no comparable event. Game 4: Crozier hit at P2 17:48 (with MTL still up 2–0). The Guentzel 4v4 goal landed **78 seconds later**. The press is treating it as a "triad" turning point — the data refines that to: hit + 4v4 goal + P3 PP discipline failures.`,
  ];
};

const tldrFR = () => {
  const p3 = PRESS.claim_2_p3_collapse.data_check.all_strengths_by_period;
  const p35v5 = PRESS.claim_2_p3_collapse.data_check.p3_5v5_only;
  return [
    `**TBL 3, CH 2. Série égale 2–2; M5 à Tampa.** Le CH menait 2–0 en deuxième, accorde un but à 4 c. 4 avec 54 secondes à faire en P2, puis encaisse deux fois Hagel en troisième (1:40 en AN, 15:07 à 5 c. 5). Hagel compte maintenant 6 buts en 4 matchs.`,
    `**Le CH s'est-il écroulé en P3? À 5 c. 5, non.** Corsi% du CH par période : ${pctFr(p3.mtl_corsi_pct_p1, 1)} → ${pctFr(p3.mtl_corsi_pct_p2, 1)} → **${pctFr(p3.mtl_corsi_pct_p3, 1)}** en P3. À 5 c. 5 strict en troisième, c'était égal (${p35v5.mtl_attempts_5v5}–${p35v5.tbl_attempts_5v5} tentatives). Les dégâts viennent des **équipes spéciales + une déviation**, pas d'un effondrement territorial. **Trois pénalités du CH en P3** mettent Tampa sur l'AN — le but égalisateur de Hagel arrive directement sur la deuxième.`,
    `**La mise en échec de Slafkovský est le 2ᵉ événement d'ancrage cadriciel de la série, pas le « 2ᵉ match consécutif ».** Le combat Hagel-Slafkovský était au **Match 2** (P2 5:14); le M3 n'avait aucun événement comparable. M4 : Crozier frappe à 17:48 de la P2 (avec le CH menant 2–0). Le but de Guentzel à 4 c. 4 suit **78 secondes plus tard**. La presse parle d'une « triade » qui a tourné le match — les données affinent : mise en échec + but à 4 c. 4 + indiscipline en P3.`,
  ];
};

const T = {
  en: {
    brand: 'LEMIEUX · Game 4 Analysis',
    title: 'Game 4 — Lightning at Canadiens',
    subtitle: 'Same data, four games in. Series tied; Game 5 in Tampa.',
    date: 'Published 2026-04-27 · TBL 3, MTL 2 · Series tied 2–2',
    tldr_title: 'Top-line read',
    tldr: tldrEN(),
    method_title: 'How to read this report',
    method: [
      '**Sources.** 5v5 / 5v4 series totals from Natural Stat Trick (refreshed 2026-04-27, season 25-26 stype=3). Goalscorers and goalie SV% are PBP-direct from NHL.com per CLAUDE.md §3.',
      '**Cross-game integrity.** Any reference to events from prior games of the series resolves through `game{N}_context.yaml`. The build aborts (exit 8) if a claim contradicts the context file.',
      '**No predictions.** Four games is still a small sample; iso-impact magnitudes are directional.',
    ],
    story_title: '1. The timeline of a 2–0 lead that vanished',
    story_intro: 'Goal sequence chronological + the Crozier hit on Slafkovský embedded at its actual timestamp. The 78-second window between the hit and the Guentzel 4v4 goal is the question Marc Antoine Godin (Radio-Canada) calls "the triad" — the data is below.',
    th_when: 'When', th_team: 'Team', th_scorer: 'Scorer / event', th_assists: 'Assists / detail', th_sit: 'Situation',
    story_takeaway_title: 'Did the Habs crash?',
    story_takeaway: [
      `**At 5v5, no.** MTL Corsi% by period went 39.1 → 35.3 → **50.0**. Pure 5v5 attempts in the third were 7–7 even. MTL was actually MORE balanced at even strength in the third than in the first two periods.`,
      `**On special teams, yes.** Three MTL penalties in P3 (vs 1 in P1, 0 in P2). Hagel's tying goal at P3 1:40 came on the second of those PPs. The "veteran-team-punishes-undisciplined-hockey" line St-Louis used post-game survives the data — that's the actual mechanism.`,
      `**The 4v4 stretch was the inflection.** From 2–0 with 9:54 left in P2 to 2–1 with 0:54 left, in a sequence that included the Crozier hit. Once it became a one-goal game, Tampa had Hagel + Kucherov together for stretches in P3, and one PP goal + one slot deflection got it done. **Matheson was on-ice for both Hagel goals.** Both shots were deflections from inside ~15 ft of the net.`,
      `**What didn't happen.** MTL did not get blown out of P3 5v5. The story isn't "the Habs collapsed under pressure" — it's "Tampa converted three discipline lapses + one defensive-zone lapse into a comeback while MTL kept playing roughly even hockey at even strength."`,
    ],
    thesis_title: '2. Pre-game thesis check — Crozier-for-Carlile',
    thesis_intro: 'The pre-game brief projected the announced TBL change as a marginal upgrade with the CI band straddling zero. Reality:',
    th_metric: 'Metric', th_value: 'Value', th_note: 'Note',
    thesis_takeaway: [
      `**Verdict: thesis confirmed directionally and ineffectively.** Crozier was on-ice for ${D.crozier_on_ice.goals_for_oi} TBL goal and ${D.crozier_on_ice.goals_against_oi} MTL goal. Net effect on this game's scoreline: zero. The CI on the projection always straddled zero — this is the result the framework predicted.`,
      `**Where the actual P3 swing came from**: Hagel and Kucherov, not the third pair. The framework cannot price physicality (Crozier's hit on Slafkovský in P2 — see §6) into the iso-impact engine, but the line of attack on Tampa's projected upgrade was always going to be top-six emergence rather than depth-pair stabilization.`,
    ],
    series_title: '3. Series state of play (5v5 + 5v4, four games)',
    series_intro: 'NST through Game 4. The pattern from the first three games — Tampa drives volume, Montreal generates quality — survives.',
    series_5v5_title: '5v5 (4 games, ~180 minutes per side)',
    series_5v4_title: '5v4 — special teams',
    th_team_full: 'Team', th_gp: 'GP', th_toi: 'TOI', th_gf_ga: 'GF–GA',
    th_xgf: 'xGF', th_xga: 'xGA', th_cf_pct: 'CF%', th_hdcf_pct: 'HDCF%', th_xgf_pct: 'xGF%',
    goalies_title: '4. Goalies — series-to-date (PBP-direct)',
    goalies_intro: 'Through 4 games the implied save percentages are essentially identical. The pre-series claim that Vasilevskiy was the more reliable option no longer holds; nor does the post-G3 inversion that Dobeš was definitively ahead. The goalie battle is a dead heat, and that is the honest read.',
    th_goalie: 'Goalie', th_sf: 'Shots faced', th_ga: 'GA', th_svp: 'SV%', th_games: 'Games',
    motm_title: '5. Player of the match — Brandon Hagel',
    motm_intro: 'Hagel\'s composite score by period: quiet through 40, then a top-decile period in P3. The recipe captures both individual offense and on-ice contribution.',
    th_period: 'Period', th_lg: 'G', th_la: 'A', th_lsog: 'SOG', th_lihd: 'iHD', th_score: 'Score', th_tier: 'Tier',
    motm_caveat: 'Hagel now has 6 goals through 4 games of the series. That is the kind of conversion rate the framework cannot project before-the-fact (it would have failed the no-predictions rail to suggest it pre-series). What it CAN do is grade the magnitude after-the-fact: a 99th-percentile P3 shift composite, on a calibration sample of 4 879 playoff player-period observations.',
    slaf_title: '6. Slafkovský and the contact-event pattern (corrected)',
    slaf_intro: 'The framework treats Game 4 (Crozier hit) and Game 2 (Hagel fight) as bucket-cut anchors. **This is not "two straight games" — Game 3 had no comparable event.** The cross-game timeline:',
    slaf_pattern: [
      `**Game 1** (MTL 4–3 OT) · Slafkovský hat-trick · Cernak hit at P1 0:20 — too early to be an anchor.`,
      `**Game 2** (TBL 3–2 OT) · **Hagel-Slafkovský fight at P2 5:14** · Pre-bucket (G1 + G2 to fight): 8 SOG, 3 goals over 29.9 min. Post-bucket (G2 from 5:14 + G3): 2 SOG, 0 goals over 35.0 min. Source: \`game2_context.yaml\`.`,
      `**Game 3** (MTL 3–2 OT) · No framework-anchor contact event. Routine forecheck-level hits only. Source: \`game3_context.yaml\`.`,
      `**Game 4** (TBL 3–2) · **Crozier hit on Slafkovský at P2 17:48**, MTL leading 2–0. Pre-hit: 11.55 min TOI, 2 SOG, MTL 1 / TBL 0 on-ice goals. Post-hit: 4.67 min TOI (TOI share dropped from 38.7% to 21.0% of available time), 0 SOG, MTL 0 / TBL 1 on-ice goals. **Slafkovský-on-ice 5v5 Corsi actually IMPROVED post-hit (3-10 → 4-2 on a 4.67-min sample) — but his individual offense vanished and TOI was halved.** Source: \`game4_context.yaml\` + companion brief.`,
      `**Press read vs data read.** Marc Antoine Godin called it part of "the triad" that flipped the game. Habs players denied an effect (Matheson "Je ne pense pas"). Bolduc allowed: "maybe it gave them some gas." **The data-honest read**: Bolduc was right. The hit (17:48) preceded the Guentzel 4v4 goal (19:06) by **78 seconds**. Slaf-on-ice possession improved on tiny TOI; his individual production tanked. The "second straight game" framing some are using is wrong — the framework anchors are G2 and G4 with G3 in between.`,
    ],
    claims_title: '5. Press claims ledger — interesting only',
    claims_intro: 'Six analytical claims pulled from RDS, Radio-Canada, NHL.com, Habs Eyes On The Prize, CBC and Tampa Bay Times. Boring claims (lineup matches what was reported, Hutson played a lot of minutes) are excluded by editorial rule. Color codes: green = data confirms, amber = mixed/partial, red = data refutes.',
    claims_caveat: 'Verdicts are computed in `game4_press_validation.numbers.json`. Each claim row is one source quote vs the data check.',
    th_claim: 'Press claim', th_verdict: 'Verdict', th_data: 'What the data shows',
    progression_title: '7. MTL skater progression — regular season vs 2026 playoffs (4 games)',
    progression_intro: 'Isolated net impact at 5v5 (iso xGF/60 − iso xGA/60), regular season vs the four playoff games. Up-movers exceed their reg-season impact; down-movers are below it. Minimum 200 reg-season minutes and 15 playoff minutes.',
    th_player: 'Player', th_pos: 'Pos', th_toi_p: 'P TOI', th_toi_r: 'R TOI',
    th_net_r: 'Net (R)', th_net_p: 'Net (P)', th_delta: 'Δ',
    progression_movers_up: 'Top 5 movers UP (over-performing reg season)',
    progression_movers_down: 'Top 5 movers DOWN (under-performing)',
    progression_caveat: 'The down-mover list still includes MTL\'s top-line stars (Caufield, Suzuki, Hutson) — and Hutson + Caufield have both produced goals (Hutson G2 + G3 OT; Caufield G4 PP). The iso-impact regression measures the team\'s underlying expected-goals share when each is on the ice, not their goal totals. The two facts coexist; they have not stopped converting, but the underlying play with them on is below the regular-season standard.',
    cant_title: '8. What four games can\'t tell us yet',
    cant: [
      'Whether MTL\'s structural xG edge (52.96% xGF, 60.47% HDCF at 5v5) is sustainable against a Vasilevskiy who has yet to play his series ceiling.',
      'Whether Hagel\'s 6-goals-in-4-games conversion rate continues, regresses, or accelerates further.',
      'Whether Slafkovský\'s post-contact offensive shutdowns (now twice in the series) are physical/injury-related, tactical (Tampa shading attention), or sample noise.',
      'How TBL\'s 3rd defensive pair plays on home ice in Game 5 with Cooper getting last change for the first time in three games.',
    ],
    sources_title: '9. Sources',
    sources_groups: [
      { heading: 'Data',
        items: [
          ['Natural Stat Trick — 25-26 NHL playoff team and skater totals (refreshed 2026-04-27)', 'https://www.naturalstattrick.com/'],
          ['NHL.com play-by-play API', 'https://api-web.nhle.com/v1/gamecenter/2025030124/play-by-play'],
          ['NHL.com boxscore API', 'https://api-web.nhle.com/v1/gamecenter/2025030124/boxscore'],
          ['NHL.com shift charts (post-game complete)', 'https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=2025030124'],
        ],
      },
      { heading: 'Francophone press', items: CLAIMS_YAML.source_groups.francophone },
      { heading: 'Anglophone press', items: CLAIMS_YAML.source_groups.anglophone },
      { heading: 'Cross-game context (canonical fact base)',
        items: [
          ['game2_context.yaml — Hagel-Slafkovský fight reference', '(see examples/habs_round1_2026/game2_context.yaml)'],
          ['game3_context.yaml — line-reshuffle reference', '(see examples/habs_round1_2026/game3_context.yaml)'],
          ['game4_context.yaml — Crozier-hit reference', '(see examples/habs_round1_2026/game4_context.yaml)'],
        ],
      },
      { heading: 'Companion analyses',
        items: [
          ['Pre-game brief (swap engine projection)', '(see game4_pregame_2026-04-26_{EN,FR}.docx)'],
          ['Live multi-period (P1+P2+P3 + barème legend + thesis check)', '(see game4_periods_p1-p3_2026-04-26_{EN,FR}.docx)'],
          ['Slafkovský pre/post-hit special', '(see game4_slaf_hit_2026-04-26_{EN,FR}.docx)'],
          ['Press validation analyzer audit trail', '(see game4_press_validation.numbers.json)'],
          ['Research-game claims yaml', '(see research/2025030124_claims.yaml)'],
        ],
      },
    ],
    footer: 'Lemieux · open-source hockey analytics · github.com/lemieuxAI/framework',
    page: 'Page',
  },
  fr: {
    brand: 'LEMIEUX · Analyse du Match no 4',
    title: 'Match no 4 — Lightning au Canadien',
    subtitle: 'Quatre matchs, mêmes chiffres. Série égale; Match 5 à Tampa.',
    date: 'Publié le 27 avril 2026 · TBL 3, CH 2 · Série égale 2–2',
    tldr_title: 'L\'essentiel',
    tldr: tldrFR(),
    method_title: 'Comment lire ce rapport',
    method: [
      '**Sources.** Totaux 5 c. 5 / 5 c. 4 de Natural Stat Trick (rafraîchis le 27 avril 2026, saison 25-26 stype=3). Marqueurs et % d\'arrêts des gardiens calculés directement depuis le JPJ de LNH.com (méthode canonique CLAUDE.md §3).',
      '**Intégrité multimatchs.** Toute référence à des événements de matchs précédents de la série passe par `game{N}_context.yaml`. La construction interrompt (code 8) si une affirmation contredit le fichier de contexte.',
      '**Aucune prédiction.** Quatre matchs reste un petit échantillon; les amplitudes d\'impact isolé sont directionnelles.',
    ],
    story_title: '1. La chronologie d\'une avance de 2–0 qui s\'évanouit',
    story_intro: 'Séquence des buts en ordre chronologique + la mise en échec de Crozier sur Slafkovský insérée à son moment réel. La fenêtre de 78 secondes entre la mise en échec et le but de Guentzel à 4 c. 4, c\'est ce que Marc Antoine Godin (Radio-Canada) appelle « la triade » — les chiffres sont plus bas.',
    th_when: 'Moment', th_team: 'Équipe', th_scorer: 'Marqueur / événement', th_assists: 'Mentions / détail', th_sit: 'Situation',
    story_takeaway_title: 'Le CH s\'est-il écroulé?',
    story_takeaway: [
      `**À 5 c. 5, non.** Corsi% du CH par période : 39,1 → 35,3 → **50,0**. À 5 c. 5 strict en troisième, c\'était égal — 7–7 en tentatives. Le CH a été plus équilibré à forces égales en P3 qu\'en P1 ou P2.`,
      `**Aux spéciales, oui.** Trois pénalités du CH en P3 (vs 1 en P1, 0 en P2). Le but égalisateur de Hagel à 1:40 de la P3 vient sur la deuxième de ces AN. La ligne « équipe vétérane qui punit l\'indiscipline » de St-Louis après-match survit aux chiffres — c\'est exactement le mécanisme.`,
      `**La phase 4 c. 4 a été le point d\'inflexion.** De 2–0 avec 9:54 à faire en P2 à 2–1 avec 0:54 à faire, dans une séquence qui inclut la mise en échec de Crozier. Une fois ramené à un but d\'écart, Tampa a fait jouer Hagel et Kucherov ensemble par séquences en P3, et un but en AN + une déviation de zone offensive ont suffi. **Matheson était sur la glace pour les deux buts de Hagel.** Les deux tirs étaient des déviations à environ 15 pi du filet.`,
      `**Ce qui ne s\'est pas produit.** Le CH n\'a pas explosé en P3 à 5 c. 5. L\'histoire n\'est pas « le CH s\'effondre sous la pression » — c\'est « Tampa convertit trois manques de discipline + une perte en zone défensive en remontée pendant que le CH continue de jouer à peu près à égalité à forces égales ».`,
    ],
    thesis_title: '2. Vérification de la thèse d\'avant-match — Crozier pour Carlile',
    thesis_intro: 'Le survol d\'avant-match projetait le changement annoncé du TBL comme une amélioration marginale, IC chevauchant zéro. Réalité :',
    th_metric: 'Mesure', th_value: 'Valeur', th_note: 'Note',
    thesis_takeaway: [
      `**Verdict : thèse confirmée directionnellement et sans effet.** Crozier sur la glace pour ${D.crozier_on_ice.goals_for_oi} but de TBL et ${D.crozier_on_ice.goals_against_oi} but du CH. Effet réel sur le pointage : zéro. L\'IC chevauchait toujours zéro — c\'est exactement ce que le cadriciel prédisait.`,
      `**D\'où vient le swing réel de la P3** : Hagel et Kucherov, pas le 3ᵉ duo. Le cadre ne sait pas chiffrer la physicalité (la mise en échec de Crozier sur Slafkovský en P2 — voir §6) dans le moteur d\'impact isolé, mais l\'angle d\'attaque sur l\'amélioration projetée de Tampa allait toujours passer par l\'émergence du top 6, pas par la stabilisation d\'un duo de soutien.`,
    ],
    series_title: '3. État de la série (5 c. 5 + 5 c. 4, 4 matchs)',
    series_intro: 'NST sur 4 matchs. Le patron des 3 premiers matchs — Tampa génère le volume, le CH génère la qualité — survit.',
    series_5v5_title: '5 c. 5 (4 matchs, ~180 min par camp)',
    series_5v4_title: '5 c. 4 — équipes spéciales',
    th_team_full: 'Équipe', th_gp: 'PJ', th_toi: 'TG', th_gf_ga: 'BP–BC',
    th_xgf: 'BAF', th_xga: 'BAC', th_cf_pct: '% Corsi', th_hdcf_pct: '% CHD', th_xgf_pct: '% BA',
    goalies_title: '4. Les gardiens — cumulé série (méthode JPJ-direct)',
    goalies_intro: 'Sur 4 matchs, les pourcentages d\'arrêts implicites sont essentiellement identiques. L\'argument d\'avant-série voulant Vasilevskiy plus fiable ne tient plus; pas plus que l\'inversion post-M3 voulant Dobeš définitivement devant. La bataille des gardiens est une égalité — c\'est la lecture honnête.',
    th_goalie: 'Gardien', th_sf: 'Tirs subis', th_ga: 'BC', th_svp: '% arrêts', th_games: 'Matchs',
    motm_title: '5. Joueur du match — Brandon Hagel',
    motm_intro: 'Pointage composite de Hagel par période : silencieux pendant 40 minutes, puis une période au sommet décile en P3. La recette capte à la fois sa production individuelle et sa contribution sur la glace.',
    th_period: 'Période', th_lg: 'B', th_la: 'A', th_lsog: 'TB', th_lihd: 'CHDi', th_score: 'Pointage', th_tier: 'Niveau',
    motm_caveat: 'Hagel compte maintenant 6 buts en 4 matchs de la série. C\'est le genre de taux de conversion que le cadriciel ne peut pas projeter avant-coup (cela violerait la règle « aucune prédiction » de le suggérer pré-série). Ce qu\'il PEUT faire : noter l\'amplitude après-coup. Une période en P3 dans le 99ᵉ percentile, sur un échantillon de calibration de 4 879 observations joueur-période en séries.',
    slaf_title: '6. Slafkovský et le patron des événements de contact (correction)',
    slaf_intro: 'Le cadriciel traite le M4 (mise en échec de Crozier) et le M2 (combat avec Hagel) comme des points d\'ancrage de tranche. **Ce n\'est pas « deux matchs consécutifs » — le M3 n\'avait aucun événement comparable.** Chronologie multimatchs :',
    slaf_pattern: [
      `**Match 1** (CH 4–3 PR) · Tour du chapeau de Slafkovský · Mise en échec de Cernak à 0:20 de la P1 — trop tôt dans la série pour être un ancrage.`,
      `**Match 2** (TBL 3–2 PR) · **Combat Hagel-Slafkovský à 5:14 de la P2** · Tranche avant (M1 + M2 jusqu\'au combat) : 8 TB, 3 buts en 29,9 min. Tranche après (M2 dès 5:14 + M3) : 2 TB, 0 but en 35,0 min. Source : \`game2_context.yaml\`.`,
      `**Match 3** (CH 3–2 PR) · Aucun événement de contact d\'ancrage cadriciel. Que des contacts de niveau échec-avant routinier. Source : \`game3_context.yaml\`.`,
      `**Match 4** (TBL 3–2) · **Mise en échec de Crozier sur Slafkovský à 17:48 de la P2**, le CH menant 2–0. Avant : 11,55 min de TG, 2 TB, 1 but du CH / 0 du TBL sur la glace. Après : 4,67 min de TG (la part de TG passe de 38,7 % à 21,0 % du temps disponible), 0 TB, 0 / 1 sur la glace. **Le Corsi 5 c. 5 du trio de Slaf s\'est en fait AMÉLIORÉ après (3-10 → 4-2 sur 4,67 min) — mais sa production individuelle disparaît et son TG est coupé de moitié.** Source : \`game4_context.yaml\` + dossier compagnon.`,
      `**Lecture de la presse vs lecture des données.** Marc Antoine Godin parle de « la triade » qui a tourné le match. Les joueurs nient un effet (Matheson : « Je ne pense pas »). Bolduc admet : « Peut-être que ça leur a donné un peu de gaz. » **La lecture honnête des données** : Bolduc avait raison. La mise en échec (17:48) précède le but de Guentzel à 4 c. 4 (19:06) de **78 secondes**. La possession à 5 c. 5 du trio de Slaf s\'améliore sur un mini-échantillon; sa production individuelle se tarit. Le cadre « 2ᵉ match consécutif » utilisé dans certains comptes-rendus est faux — les ancrages cadriciels sont M2 et M4, avec le M3 entre les deux.`,
    ],
    claims_title: '5. Tableau des affirmations de la presse — uniquement les intéressantes',
    claims_intro: 'Six affirmations analytiques tirées de RDS, Radio-Canada, LNH.com, Habs Eyes On The Prize, CBC et Tampa Bay Times. Les affirmations banales (la formation correspond au rapporté, Hutson a joué beaucoup) sont exclues par règle éditoriale. Codes couleur : vert = confirmée par les chiffres, ambre = mitigée/partielle, rouge = infirmée.',
    claims_caveat: 'Verdicts calculés dans `game4_press_validation.numbers.json`. Chaque ligne associe une citation à la vérification analytique.',
    th_claim: 'Affirmation', th_verdict: 'Verdict', th_data: 'Ce que disent les chiffres',
    progression_title: '7. Progression des patineurs du CH — saison régulière vs séries 2026 (4 matchs)',
    progression_intro: 'Impact net isolé à 5 c. 5 (iso BAF/60 − iso BAC/60), saison régulière vs les 4 matchs des séries. Hausse : surperforme la saison; baisse : sous la saison. Minimum 200 minutes de saison et 15 minutes en séries.',
    th_player: 'Patineur', th_pos: 'Pos', th_toi_p: 'TG (S)', th_toi_r: 'TG (R)',
    th_net_r: 'Net (R)', th_net_p: 'Net (S)', th_delta: 'Δ',
    progression_movers_up: 'Top 5 hausses (au-dessus de la saison)',
    progression_movers_down: 'Top 5 baisses (sous la saison)',
    progression_caveat: 'La liste des baisses inclut toujours les vedettes du premier trio (Caufield, Suzuki, Hutson) — et Hutson + Caufield ont tous deux marqué (Hutson au M2 + en prolongation au M3; Caufield en AN au M4). La régression d\'impact isolé mesure la part de buts attendus de l\'équipe quand chacun est sur la glace, pas leur total de buts. Les deux faits coexistent : ils continuent de marquer, mais le jeu sous-jacent avec eux sur la glace est sous le standard de saison.',
    cant_title: '8. Ce que 4 matchs ne disent toujours pas',
    cant: [
      'Si l\'avantage structurel xG du CH (52,96 % BA, 60,47 % CHD à 5 c. 5) tient contre un Vasilevskiy qui n\'a pas encore joué son sommet de série.',
      'Si le rythme de Hagel (6 buts en 4 matchs) se poursuit, régresse ou s\'accélère.',
      'Si la disparition offensive de Slafkovský après contact (deux fois dans la série) est physique/blessure, tactique (Tampa modifie son attention) ou bruit d\'échantillon.',
      'Comment le 3ᵉ duo défensif de TBL joue à domicile au M5 avec Cooper qui obtient le dernier changement pour la première fois en 3 matchs.',
    ],
    sources_title: '9. Sources',
    sources_groups: [
      { heading: 'Données',
        items: [
          ['Natural Stat Trick — totaux d\'équipe et de joueurs des séries LNH 25-26 (rafraîchis 2026-04-27)', 'https://www.naturalstattrick.com/'],
          ['API jeu par jeu LNH.com', 'https://api-web.nhle.com/v1/gamecenter/2025030124/play-by-play'],
          ['API sommaire LNH.com', 'https://api-web.nhle.com/v1/gamecenter/2025030124/boxscore'],
          ['Tableau des présences LNH.com', 'https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=2025030124'],
        ],
      },
      { heading: 'Presse francophone', items: CLAIMS_YAML.source_groups.francophone },
      { heading: 'Presse anglophone', items: CLAIMS_YAML.source_groups.anglophone },
      { heading: 'Contexte multimatchs (base canonique)',
        items: [
          ['game2_context.yaml — référence du combat Hagel-Slafkovský', '(voir examples/habs_round1_2026/game2_context.yaml)'],
          ['game3_context.yaml — référence du brassage des trios', '(voir examples/habs_round1_2026/game3_context.yaml)'],
          ['game4_context.yaml — référence de la mise en échec de Crozier', '(voir examples/habs_round1_2026/game4_context.yaml)'],
        ],
      },
      { heading: 'Analyses compagnons',
        items: [
          ['Survol d\'avant-match (projection moteur d\'échange)', '(voir game4_pregame_2026-04-26_{EN,FR}.docx)'],
          ['Multi-période en direct (P1+P2+P3 + légende du barème + vérif. de la thèse)', '(voir game4_periods_p1-p3_2026-04-26_{EN,FR}.docx)'],
          ['Spécial Slafkovský pré/post-mise en échec', '(voir game4_slaf_hit_2026-04-26_{EN,FR}.docx)'],
          ['Audit de l\'analyseur de validation de la presse', '(voir game4_press_validation.numbers.json)'],
          ['Affirmations en yaml de l\'habileté research-game', '(voir research/2025030124_claims.yaml)'],
        ],
      },
    ],
    footer: 'Lemieux · analytique de hockey à code source ouvert · github.com/lemieuxAI/framework',
    page: 'Page',
  },
};

// Now run the prose fact-check guard before any docx is built.
runProseFactCheck();

// ---------- sections ----------
function brandHeader(t) {
  return new Header({ children: [new Paragraph({
    alignment: AlignmentType.LEFT, spacing: { after: 80 },
    children: [
      new TextRun({ text: 'LEMIEUX  ', bold: true, color: BRAND.red, font: 'Arial', size: 18 }),
      new TextRun({ text: '· hockey analytics', color: BRAND.mute, font: 'Arial', size: 16 }),
    ],
  })] });
}
function brandFooter(t) {
  return new Footer({ children: [new Paragraph({
    alignment: AlignmentType.LEFT,
    children: [
      new TextRun({ text: t.footer, color: BRAND.mute, font: 'Arial', size: 16 }),
      new TextRun({ text: '   ·   ', color: BRAND.mute, font: 'Arial', size: 16 }),
      new TextRun({ text: t.page + ' ', color: BRAND.mute, font: 'Arial', size: 16 }),
      new TextRun({ children: [PageNumber.CURRENT], color: BRAND.mute, font: 'Arial', size: 16 }),
    ],
  })] });
}

function titleBlock(t) {
  return [
    new Paragraph({ spacing: { after: 80 },
      children: [new TextRun({ text: t.title, bold: true, color: BRAND.navy, font: 'Arial', size: 36 })] }),
    new Paragraph({ spacing: { after: 80 },
      children: [new TextRun({ text: t.subtitle, italics: true, color: BRAND.mute, font: 'Arial', size: 22 })] }),
    new Paragraph({ spacing: { after: 200 },
      children: [new TextRun({ text: t.date, color: BRAND.mute, font: 'Arial', size: 18 })] }),
  ];
}

function tldrSection(t) {
  return [h1(t.tldr_title), ...bullets(t.tldr)];
}

function methodSection(t) {
  return [h1(t.method_title), ...bullets(t.method)];
}

function storySection(t, lang) {
  const teamFill = (team) => team === 'MTL' ? BRAND.mtlfill : BRAND.tblfill;
  // Build chronological events: goals + the Slaf hit + the score-state markers.
  const events = (D.goal_sequence || []).map(g => ({
    period: g.period, sec: parseInt(g.time.split(':')[0]) * 60 + parseInt(g.time.split(':')[1]),
    time: g.time, kind: 'goal', g,
  }));
  // Insert the Crozier hit at P2 17:48
  events.push({
    period: 2, sec: 17 * 60 + 48, time: '17:48', kind: 'hit',
    detail: lang === 'fr'
      ? { team: 'TBL', label: '⚡ Crozier · mise en échec sur Slafkovský', extra: 'zone neutre · CH menait alors 2–0' }
      : { team: 'TBL', label: '⚡ Crozier hit on Slafkovský', extra: 'neutral zone · MTL led 2–0 at the time' },
  });
  events.sort((a, b) => a.period - b.period || a.sec - b.sec);

  const rows = events.map(e => {
    if (e.kind === 'goal') {
      const g = e.g;
      return {
        cells: [
          `P${g.period} ${g.time}`, g.owner, g.scorer || '—',
          [g.assist1, g.assist2].filter(Boolean).join(', ') || '—',
          g.situation,
        ],
        _opts: { fill: teamFill(g.owner) },
      };
    }
    return {
      cells: [`P${e.period} ${e.time}`, e.detail.team, e.detail.label, e.detail.extra, '—'],
      _opts: { fill: BRAND.caveat },
    };
  });
  return [
    h1(t.story_title),
    para(t.story_intro, { italics: true }),
    dataTable([t.th_when, t.th_team, t.th_scorer, t.th_assists, t.th_sit], rows, [1300, 800, 2700, 4000, 1200]),
    h2(t.story_takeaway_title),
    ...bullets(t.story_takeaway),
  ];
}

function thesisSection(t, lang) {
  const sw = D.swap_projection;
  const cz = D.crozier_on_ice;
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const rows = [
    [
      lang === 'fr' ? 'Δ net BA/match projeté pour TBL' : 'Projected Δ net xG/game for TBL',
      fmtN(sw.delta_net_per_game, 2),
      lang === 'fr' ? `IC 80 % BAF [${fmtFr(sw.delta_xgf_ci80[0], 2)}, ${fmtFr(sw.delta_xgf_ci80[1], 2)}] — chevauche zéro` : `80% CI on xGF [${fmt(sw.delta_xgf_ci80[0], 2)}, ${fmt(sw.delta_xgf_ci80[1], 2)}] — straddles zero`,
    ],
    [
      lang === 'fr' ? 'Buts TBL avec Crozier sur la glace' : 'TBL goals while Crozier on-ice',
      cz.goals_for_oi,
      lang === 'fr' ? 'Mesuré via présences post-match' : 'Measured via post-game shifts',
    ],
    [
      lang === 'fr' ? 'Buts CH avec Crozier sur la glace' : 'MTL goals while Crozier on-ice',
      cz.goals_against_oi,
      lang === 'fr' ? 'Mesuré via présences post-match' : 'Measured via post-game shifts',
    ],
  ];
  return [
    h1(t.thesis_title),
    para(t.thesis_intro, {}),
    dataTable([t.th_metric, t.th_value, t.th_note], rows.map(r => ({cells: r})), [4400, 1500, 4100]),
    ...bullets(t.thesis_takeaway),
  ];
}

function seriesSection(t, lang) {
  const fmtN = lang === 'fr' ? pctFr : pct;
  const fmtX = lang === 'fr' ? fmtFr : fmt;
  const m5 = D.series_5v5.MTL || {}; const t5 = D.series_5v5['T.B'] || {};
  const m4 = D.series_5v4.MTL || {}; const t4 = D.series_5v4['T.B'] || {};
  const r5 = [
    {
      cells: ['MTL', m5.gp, fmtX(m5.toi_min, 1), `${m5.gf}–${m5.ga}`, fmtX(m5.xgf, 2), fmtX(m5.xga, 2),
              fmtN(m5.cf_pct), fmtN(m5.hdcf_pct), fmtN(m5.xgf_pct)],
      _opts: { fill: BRAND.mtlfill },
    },
    {
      cells: ['TBL', t5.gp, fmtX(t5.toi_min, 1), `${t5.gf}–${t5.ga}`, fmtX(t5.xgf, 2), fmtX(t5.xga, 2),
              fmtN(t5.cf_pct), fmtN(t5.hdcf_pct), fmtN(t5.xgf_pct)],
      _opts: { fill: BRAND.tblfill },
    },
  ];
  const r4 = [
    {
      cells: ['MTL', m4.gp, fmtX(m4.toi_min, 1), `${m4.gf}–${m4.ga}`, fmtX(m4.xgf, 2), fmtX(m4.xga, 2),
              fmtN(m4.cf_pct), fmtN(m4.hdcf_pct), fmtN(m4.xgf_pct)],
      _opts: { fill: BRAND.mtlfill },
    },
    {
      cells: ['TBL', t4.gp, fmtX(t4.toi_min, 1), `${t4.gf}–${t4.ga}`, fmtX(t4.xgf, 2), fmtX(t4.xga, 2),
              fmtN(t4.cf_pct), fmtN(t4.hdcf_pct), fmtN(t4.xgf_pct)],
      _opts: { fill: BRAND.tblfill },
    },
  ];
  const headers = [t.th_team_full, t.th_gp, t.th_toi, t.th_gf_ga, t.th_xgf, t.th_xga, t.th_cf_pct, t.th_hdcf_pct, t.th_xgf_pct];
  const widths = [800, 600, 900, 900, 900, 900, 1100, 1200, 1100];
  return [
    h1(t.series_title), para(t.series_intro, {}),
    h2(t.series_5v5_title),
    dataTable(headers, r5, widths),
    h2(t.series_5v4_title),
    dataTable(headers, r4, widths),
  ];
}

function goaliesSection(t, lang) {
  const fmtX = lang === 'fr' ? fmtFr : fmt;
  const rows = [
    {
      cells: ['Jakub Dobeš', D.goalies['Dobeš'].shots_faced, D.goalies['Dobeš'].goals_against,
              fmtX(D.goalies['Dobeš'].sv_pct, 3), D.goalies['Dobeš'].games],
      _opts: { fill: BRAND.mtlfill },
    },
    {
      cells: ['Andrei Vasilevskiy', D.goalies['Vasilevskiy'].shots_faced, D.goalies['Vasilevskiy'].goals_against,
              fmtX(D.goalies['Vasilevskiy'].sv_pct, 3), D.goalies['Vasilevskiy'].games],
      _opts: { fill: BRAND.tblfill },
    },
  ];
  return [
    h1(t.goalies_title),
    para(t.goalies_intro, {}),
    dataTable([t.th_goalie, t.th_sf, t.th_ga, t.th_svp, t.th_games], rows, [3500, 1900, 1500, 1500, 1000]),
  ];
}

function motmSection(t, lang) {
  const h = D.hagel_by_period || {};
  const rows = ['P1', 'P2', 'P3'].map(k => {
    const r = h[k] || { score: 0, g: 0, a: 0, sog: 0, ind_hd_attempts: 0 };
    return {
      cells: [
        k, r.g, r.a, r.sog, r.ind_hd_attempts,
        { value: (lang === 'fr' ? fmtFr : fmt)(r.score, 2), fill: tierFill(r.score), bold: true },
        { value: tierLabel(r.score, lang), fill: tierFill(r.score) },
      ],
    };
  });
  return [
    h1(t.motm_title),
    para(t.motm_intro, {}),
    dataTable([t.th_period, t.th_lg, t.th_la, t.th_lsog, t.th_lihd, t.th_score, t.th_tier], rows, [1200, 700, 700, 700, 900, 1000, 1500]),
    para(t.motm_caveat, { italics: true, color: BRAND.mute }),
  ];
}

function slafSection(t, lang) {
  return [
    h1(t.slaf_title),
    para(t.slaf_intro, {}),
    ...bullets(t.slaf_pattern),
  ];
}

function pressClaimsSection(t, lang) {
  // Build a verdict-color-coded claims table
  const verdictColor = (verdict) => {
    if (/CONFIRMED/.test(verdict) && !/PARTIALLY/.test(verdict) && !/MIXED/.test(verdict)) return BRAND.confirm;
    if (/REFUTED/.test(verdict)) return BRAND.refute;
    return BRAND.neutral; // mixed / partial
  };
  const verdictWord = (verdict, lang) => {
    if (lang === 'fr') {
      if (/PARTIALLY CONFIRMED/.test(verdict)) return 'Partiellement confirmée';
      if (/CONFIRMED/.test(verdict)) return 'Confirmée';
      if (/REFUTED/.test(verdict)) return 'Infirmée';
      return 'Mitigée';
    }
    if (/PARTIALLY CONFIRMED/.test(verdict)) return 'Partially confirmed';
    if (/CONFIRMED/.test(verdict)) return 'Confirmed';
    if (/REFUTED/.test(verdict)) return 'Refuted';
    return 'Mixed';
  };

  const claimEntries = [
    { id: 'claim_1_crozier_hit_turned_game' },
    { id: 'claim_2_p3_collapse' },
    { id: 'claim_3_penalty_discipline' },
    { id: 'claim_4_matheson_hagel_crease' },
    { id: 'claim_5_top_line_surge' },
    { id: 'claim_6_habs_unaffected_by_hit' },
  ];

  const rows = claimEntries.map(({ id }) => {
    const c = PRESS[id];
    const verdict = verdictWord(c.data_verdict, lang);
    const verdictHead = (c.data_verdict.match(/^([A-Z ]+CONFIRMED|[A-Z ]+REFUTED|MIXED|PARTIALLY CONFIRMED)/) || [''])[0];
    const fill = verdictColor(c.data_verdict);
    return {
      cells: [
        c.claim,
        { value: c.press_source.split(' · ')[0], fill: undefined },
        { value: verdict, fill, bold: true },
        c.data_verdict.replace(/^[A-Z ]+(CONFIRMED|REFUTED|MIXED|PARTIALLY CONFIRMED)\.?\s*/, ''),
      ],
    };
  });
  return [
    h1(t.claims_title),
    para(t.claims_intro, { italics: true }),
    dataTable(
      [t.th_claim, t.th_source, t.th_verdict, t.th_data],
      rows,
      [3200, 1500, 1500, 4500]
    ),
    para(t.claims_caveat, { italics: true, color: BRAND.mute }),
  ];
}

function progressionSection(t, lang) {
  const prog = D.mtl_progression || {};
  const fmtX = lang === 'fr' ? fmtFr : fmt;
  const upRows = (prog.movers_up || []).map(r => ({
    cells: [r.name, r.position, fmtX(r.toi_p, 1), fmtX(r.toi_r, 1),
            fmtX(r.net_r, 2), fmtX(r.net_p, 2), fmtX(r.delta, 2)],
    _opts: { fill: BRAND.upfill },
  }));
  const downRows = (prog.movers_down || []).map(r => ({
    cells: [r.name, r.position, fmtX(r.toi_p, 1), fmtX(r.toi_r, 1),
            fmtX(r.net_r, 2), fmtX(r.net_p, 2), fmtX(r.delta, 2)],
    _opts: { fill: BRAND.downfill },
  }));
  const headers = [t.th_player, t.th_pos, t.th_toi_p, t.th_toi_r, t.th_net_r, t.th_net_p, t.th_delta];
  const widths = [3000, 700, 1100, 1100, 1300, 1300, 1100];
  return [
    h1(t.progression_title),
    para(t.progression_intro, {}),
    h2(t.progression_movers_up),
    dataTable(headers, upRows, widths),
    h2(t.progression_movers_down),
    dataTable(headers, downRows, widths),
    para(t.progression_caveat, { italics: true, color: BRAND.mute }),
  ];
}

function cantSection(t) {
  return [h1(t.cant_title), ...bullets(t.cant)];
}

function sourcesSection(t) {
  const out = [h1(t.sources_title)];
  for (const group of t.sources_groups) {
    out.push(new Paragraph({ spacing: { before: 120, after: 60 },
      children: [new TextRun({ text: group.heading, bold: true, font: 'Arial', size: 22, color: BRAND.navyLight })] }));
    for (const [txt, url] of group.items) {
      const isLink = url.startsWith('http');
      out.push(new Paragraph({
        numbering: { reference: 'bullets', level: 0 }, spacing: { after: 60 },
        children: isLink
          ? [new ExternalHyperlink({ children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })], link: url })]
          : [new TextRun({ text: txt, font: 'Arial', size: 18, color: BRAND.mute })],
      }));
    }
  }
  return out;
}

function buildDoc(lang) {
  const t = T[lang];
  return new Document({
    creator: 'Lemieux',
    title: t.title,
    styles: {
      default: { document: { run: { font: 'Arial', size: 20, color: BRAND.ink } } },
      paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 30, bold: true, color: BRAND.navy, font: 'Arial' },
          paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 24, bold: true, color: BRAND.navyLight, font: 'Arial' },
          paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      ],
    },
    numbering: { config: [{ reference: 'bullets',
      levels: [{ level: 0, format: LevelFormat.BULLET, text: '◆', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 280 } }, run: { color: BRAND.red } } }] }] },
    sections: [{
      properties: { page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
      headers: { default: brandHeader(t) }, footers: { default: brandFooter(t) },
      children: [
        new Paragraph({ children: [] }),
        ...titleBlock(t),
        ...tldrSection(t),
        ...methodSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...storySection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...thesisSection(t, lang),
        ...seriesSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...goaliesSection(t, lang),
        ...motmSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...pressClaimsSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...slafSection(t, lang),
        ...progressionSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...cantSection(t),
        ...sourcesSection(t),
      ],
    }],
  });
}

(async () => {
  for (const lang of ['en', 'fr']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const primary = path.join(__dirname, `game4_post_2026-04-26_${lang.toUpperCase()}.docx`);
    let out = primary;
    try { fs.writeFileSync(primary, buf); }
    catch (e) {
      if (e.code === 'EBUSY' || e.code === 'EACCES') {
        out = path.join(__dirname, `game4_post_2026-04-26_${lang.toUpperCase()}_v2.docx`);
        fs.writeFileSync(out, buf);
        console.log('(primary file locked — wrote alternate)');
      } else throw e;
    }
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
