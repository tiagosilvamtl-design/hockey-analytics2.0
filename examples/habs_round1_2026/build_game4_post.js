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
  return [
    `**TBL 3, MTL 2. Series tied 2–2; off to Tampa.** MTL had a two-goal lead with three minutes to play in the second period. They didn't have it for long. Crozier put Slafkovský on the bench in the neutral zone with 2:12 to go; Guentzel scored at four-on-four 78 seconds later; Hagel scored twice in the third — once on the power play, once redirecting Kucherov from the slot — to win it. Hagel now has six goals in four series games.`,
    `**Did the Habs crumble in the third? At even strength, no — and that's the surprise.** MTL's 5v5 Corsi share went **39 → 35 → 50** by period. The third was their best even-strength period of the night. What lost them the game was discipline: **three MTL penalties in twelve minutes**, and Hagel's tying goal came directly off the second power play. The other Hagel goal was Matheson failing to box him out of the slot — same deflection, same defender on-ice, ten minutes apart.`,
    `**The Slafkovský hit is the second time in this series Tampa has dropped a heavy contact event on him at a load-bearing moment.** Game 2 was the Hagel fight at P2 5:14, and the bucket split was visible (8 SOG / 3 goals before, 2 / 0 after). Game 4: Crozier finds Slaf's chest with MTL up 2–0. His individual line vanishes — 2 SOG before, **0 after**, ice-time share cut in half (39% → 21%). His line's possession actually improved on the small sample, so the Habs aren't lying when they say it didn't break the structure. But Slafkovský himself was a different player after the hit, and Bolduc was the only one in the room who admitted it.`,
  ];
};

const tldrFR = () => {
  const p3 = PRESS.claim_2_p3_collapse.data_check.all_strengths_by_period;
  return [
    `**TBL 3, CH 2. Série égale 2–2; cap sur Tampa.** Le CH avait une avance de deux buts avec trois minutes à faire en deuxième. Il ne l'a pas eue longtemps. Crozier envoie Slafkovský au banc dans la zone neutre à 2:12 du terme; Guentzel marque à 4 c. 4 78 secondes plus tard; Hagel marque deux fois en troisième — une en avantage numérique, une en faisant dévier un tir de Kucherov à partir de la zone payante — pour gagner le match. Hagel compte maintenant six buts en quatre matchs.`,
    `**Le CH s'est-il effondré en troisième? À forces égales, non — et c'est la surprise.** La part de Corsi à 5 c. 5 du CH a fait **39 → 35 → 50** par période. La troisième a été leur meilleure période à forces égales du match. Ce qui a perdu le match : la discipline. **Trois pénalités du CH en douze minutes**, et le but égalisateur de Hagel arrive sur la deuxième AN. L'autre but de Hagel : Matheson qui ne sort pas Hagel de la zone payante — même déviation, même défenseur sur la glace, à dix minutes d'intervalle.`,
    `**La mise en échec sur Slafkovský est la deuxième fois dans cette série que Tampa lui assène un événement de contact lourd à un moment chargé.** Le M2, c'était le combat avec Hagel à 5:14 de la P2, et le partage par tranche se voit dans les chiffres (8 TB / 3 buts avant, 2 / 0 après). M4 : Crozier trouve Slaf en pleine zone neutre, avec le CH menant 2–0. Sa fiche individuelle disparaît — 2 TB avant, **0 après**, sa part de temps de glace coupée de moitié (39 % → 21 %). La possession de son trio s'améliore en fait sur l'échantillon — donc le CH ne ment pas en disant que ça n'a pas brisé la structure. Mais Slafkovský lui-même n'était pas le même joueur après, et Bolduc a été le seul dans le vestiaire à l'admettre.`,
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
    story_title: '1. The two-goal lead that vanished in twelve minutes',
    story_intro: 'Goal sequence in chronological order, with the Crozier hit on Slafkovský embedded at its real timestamp so the 78-second window before the Guentzel goal is visible. Row colour reflects the team that scored; the amber row is the hit.',
    th_when: 'When', th_team: 'Team', th_scorer: 'Scorer / event', th_assists: 'Assists / detail', th_sit: 'Situation',
    story_takeaway_title: 'How it actually got away',
    story_takeaway: [
      `**For most of forty minutes the Habs were where they wanted to be.** Bolduc cashed a clean offensive-zone sequence at 10:06 of the second; Caufield made it 2–0 on the power play three and a half minutes later. Tampa was still drawing the wrong half of the territorial battle (Corsi 35–65 in their favour at 5v5 through two), but Dobeš and a quality-over-volume MTL approach had turned that into a two-goal lead.`,
      `**Then in three plays, the script flipped.** Crozier finishes Slafkovský through the chest in the neutral zone with 2:12 left. Slafkovský takes a long shift back to the bench. Seventy-eight seconds later, on a coincidental-minor 4-on-4, Guentzel beats Dobeš from a Moser feed — 2–1, with 54 seconds remaining in the period. Tampa keeps pressing; the buzzer is the only thing that saves the lead into intermission.`,
      `**The third period reads two ways depending on which lens you use.** At 5-on-5 the Habs were actually fine — Corsi% by period went 39 → 35 → **50**. Pure even-strength attempts in the third were 7–7. They didn't get hemmed in; they didn't run out of legs. What they did was take three penalties in twelve minutes. Hagel's tying goal at 1:40 came directly off the second of those power plays, redirecting Kucherov from the slot. His winner at 15:07 was almost the same shot, almost the same spot, **same defender (Matheson) on the ice unable to box him out**.`,
      `**The talk-radio line — "the Habs choked under pressure" — doesn't survive the 5v5 read.** Even-strength play wasn't the failure point; the failure points were a) staying out of the box and b) clearing the slot on Hagel. Both are addressable. Neither is a structural collapse.`,
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
    slaf_title: '6. The hit on Slafkovský — what it killed, what it didn\'t',
    slaf_intro: 'The visceral story of Game 4 is Crozier\'s hit on Slafkovský with two minutes left in the second, MTL up 2–0, the building loud. Tampa scored 78 seconds later. By the third period, Slafkovský was a different player. The question is whether the Habs were a different team — and there the data parts ways with the noise.',
    slaf_pattern: [
      `**The hit, in numbers.** Before: 11.55 min ice time (38.7% of game time elapsed), 2 SOG, MTL 1 / TBL 0 goals with him on the ice. After: 4.67 min (21.0% of remaining game time), **0 SOG, 0 missed, 0 takeaways or hits delivered**, and Tampa scored once with him on. His individual production line is the cleanest "before / after" you'll see in this series.`,
      `**His line, on the other hand, was fine.** With Slafkovský on the ice at 5v5, Montreal's Corsi share before the hit was 23% (3 attempts to Tampa's 10). After the hit it was 67% (4 to 2). Tiny sample, six minutes total — but the numbers say the line as a unit didn't crater. Slafkovský himself did. That is a precise distinction the locker-room quotes mostly missed: Matheson saying "I don't think so" maps to the team-level read; Bolduc saying "maybe it gave them some gas" is the player-level read, and Bolduc has it right.`,
      `**It is the second time this series Tampa has put a heavy contact event on Slafkovský at a load-bearing moment.** In Game 2 it was Hagel, fighting majors at 5:14 of the second. The bucket split there was clean: 8 shots and 3 goals before, 2 shots and 0 goals across the rest of that game and Game 3 combined. Now Game 4 produces the same individual-disappearance shape on a tighter window. Game 5 in Tampa is when you find out whether this is a deliberate target-and-erase plan or two opportunistic moments that happen to rhyme.`,
      `**Did the hit kill the Habs\' momentum?** Honest answer: it didn\'t kill the Habs, but it did kill Slafkovský for the night, and then four-on-four hockey did the rest. The Guentzel goal that landed 78 seconds later is the one that turned the lead from comfortable to brittle. Whether you put that goal at the foot of the hit or at the foot of the coincidental minors is a coaching-tape question, not a stats question. From here, the team-level structure held; only the discipline did not.`,
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
    story_title: '1. L\'avance de deux buts qui s\'évanouit en douze minutes',
    story_intro: 'Séquence des buts en ordre chronologique, avec la mise en échec de Crozier sur Slafkovský insérée à son moment réel pour rendre visible la fenêtre de 78 secondes avant le but de Guentzel. La couleur de la rangée indique l\'équipe qui marque; la rangée ambre est la mise en échec.',
    th_when: 'Moment', th_team: 'Équipe', th_scorer: 'Marqueur / événement', th_assists: 'Mentions / détail', th_sit: 'Situation',
    story_takeaway_title: 'Comment le match s\'est échappé',
    story_takeaway: [
      `**Pendant une bonne partie de quarante minutes, le CH était là où il voulait être.** Bolduc convertit une belle séquence en zone offensive à 10:06 de la P2; Caufield porte la marque à 2–0 en avantage numérique trois minutes et demie plus tard. Tampa tire toujours du mauvais côté de la bataille territoriale (Corsi 35–65 en sa faveur à 5 c. 5 sur deux périodes), mais Dobeš et un CH qui parie sur la qualité plutôt que le volume avaient transformé ça en avance de deux.`,
      `**Puis, en trois jeux, le scénario bascule.** Crozier termine Slafkovský en pleine poitrine dans la zone neutre à 2:12 du terme. Slafkovský prend une longue présence pour rejoindre le banc. Soixante-dix-huit secondes plus tard, sur un 4 c. 4 issu de pénalités coïncidentes, Guentzel bat Dobeš sur une passe de Moser — 2–1, avec 54 secondes à faire à la période. Tampa continue de pousser; seul le sifflet sauve l\'avance pour l\'entracte.`,
      `**La troisième période se lit en deux temps selon la lentille.** À 5 c. 5, le CH était bien — Corsi% par période : 39 → 35 → **50**. Les tentatives strictement à forces égales en troisième : 7–7. Le CH n\'est pas confiné en zone, ne s\'essouffle pas. Ce qu\'il fait : trois pénalités en douze minutes. Le but égalisateur de Hagel à 1:40 vient directement sur la deuxième de ces AN, en faisant dévier Kucherov à partir de la zone payante. Son but vainqueur à 15:07 est presque le même tir, presque le même endroit, **et le même défenseur (Matheson) sur la glace incapable de le sortir**.`,
      `**La ligne radio-poubelle — « le CH s\'est écroulé sous la pression » — ne survit pas à la lecture 5 c. 5.** Le jeu à forces égales n\'a pas été le point de rupture; les points de rupture ont été a) rester hors du banc des pénalités et b) sortir Hagel de la zone payante. Les deux sont corrigeables. Aucun n\'est un effondrement structurel.`,
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
    slaf_title: '6. La mise en échec sur Slafkovský — ce qu\'elle a tué, ce qu\'elle n\'a pas tué',
    slaf_intro: 'L\'image qui reste du Match 4, c\'est Crozier qui termine Slafkovský avec deux minutes à faire en deuxième, le CH menant 2–0, le Centre Bell debout. Tampa marque 78 secondes plus tard. Rendu en troisième, Slafkovský n\'était plus le même joueur. La question est de savoir si le CH non plus était la même équipe — et là, les chiffres se séparent du bruit ambiant.',
    slaf_pattern: [
      `**La mise en échec, en chiffres.** Avant : 11,55 min de temps de glace (38,7 % du temps écoulé), 2 tirs au but, le CH 1 but / le TBL 0 avec lui sur la glace. Après : 4,67 min (21,0 % du temps qu\'il restait), **0 TB, 0 raté, 0 récupération ou mise en échec donnée**, et Tampa marque une fois avec lui sur la glace. Sa fiche individuelle est la coupure « avant / après » la plus nette de la série.`,
      `**Son trio, par contre, s\'en est tiré.** Avec Slafkovský sur la glace à 5 c. 5, le Corsi du CH avant la mise en échec était à 23 % (3 tentatives contre 10). Après, il monte à 67 % (4 à 2). Petit échantillon — six minutes au total — mais les chiffres disent que le trio comme unité n\'a pas explosé. Slafkovský oui. C\'est une distinction précise que les citations du vestiaire ont surtout manquée : Matheson qui dit « Je ne pense pas » colle à la lecture d\'équipe; Bolduc qui dit « Peut-être que ça leur a donné un peu de gaz » colle à la lecture du joueur, et Bolduc a raison.`,
      `**C\'est la deuxième fois cette série que Tampa applique un événement de contact lourd à Slafkovský à un moment chargé.** Au Match 2, c\'était Hagel, combats simultanés à 5:14 de la P2. Le partage par tranche y était propre : 8 tirs et 3 buts avant, 2 tirs et 0 but sur le reste de ce match plus tout le M3. Le M4 produit la même forme de disparition individuelle, sur une fenêtre plus serrée. Le Match 5 à Tampa va dire si c\'est un plan « cibler-éteindre » délibéré ou deux moments opportunistes qui riment.`,
      `**La mise en échec a-t-elle tué le momentum du CH?** Réponse honnête : elle n\'a pas tué le CH, mais elle a tué Slafkovský pour la soirée, et le 4 c. 4 a fait le reste. Le but de Guentzel 78 secondes plus tard, c\'est celui qui transforme l\'avance de confortable en fragile. Mettre ce but au pied de la mise en échec ou au pied des pénalités coïncidentes, c\'est une question de bande vidéo, pas de chiffres. À partir de là, la structure d\'équipe a tenu; seule la discipline a craqué.`,
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
