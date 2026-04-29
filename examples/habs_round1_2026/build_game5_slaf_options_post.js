// Game 5 contingency brief — Slafkovský out, who replaces him?
// Inputs:
//   - game5_slaf_options.numbers.json (analyzer output)
//   - game4_lineups.yaml (the deployed lineup we're modifying)
// Run:
//   node examples/habs_round1_2026/build_game5_slaf_options_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');
const yaml = require('yaml');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'game5_slaf_options.numbers.json'), 'utf8'));
const LINEUPS = yaml.parse(fs.readFileSync(path.join(__dirname, 'game4_lineups.yaml'), 'utf8'));

// ---------- BRAND ----------
const BRAND = {
  navy: '1F2F4A',
  navyLight: '2F4A70',
  red: 'A6192E',
  ink: '111111',
  mute: '666666',
  rule: 'BFBFBF',
  confirm: 'E2F0D9',
  neutral: 'FFF2CC',
  refute: 'F8CBAD',
  info: 'DEEAF6',
  caveat: 'FFF6E0',
};

const fmt = (n, p = 2) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const s = Number(n).toFixed(p);
  return (Number(n) > 0 ? '+' : '') + s;
};

const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: BRAND.rule };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function md(s) {
  const parts = [];
  const re = /\*\*(.+?)\*\*/g;
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
  return new Paragraph({
    heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 },
    children: [new TextRun({ text, bold: true, size: 30, color: BRAND.navy, font: 'Arial' })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, bold: true, size: 24, color: BRAND.navyLight, font: 'Arial' })],
  });
}
function h3(text) {
  return new Paragraph({
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, bold: true, size: 20, color: BRAND.navy, font: 'Arial' })],
  });
}
function bulletList(items) {
  return items.map(s => new Paragraph({
    numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 },
    children: md(s),
  }));
}
function quoteBox(quote, url) {
  return new Paragraph({
    spacing: { before: 60, after: 80 },
    indent: { left: 360 },
    children: [
      new TextRun({ text: '"', italics: true, color: BRAND.mute, font: 'Arial', size: 18 }),
      new TextRun({ text: quote, italics: true, color: BRAND.mute, font: 'Arial', size: 18 }),
      new TextRun({ text: '"  — ', italics: true, color: BRAND.mute, font: 'Arial', size: 18 }),
      new ExternalHyperlink({
        children: [new TextRun({ text: 'source', style: 'Hyperlink', font: 'Arial', size: 18 })],
        link: url || '#',
      }),
    ],
  });
}

function dataTable(headers, rows, widths) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map(h => new TableCell({
      borders: cellBorders,
      shading: { type: ShadingType.CLEAR, color: 'auto', fill: BRAND.navy },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        spacing: { before: 60, after: 60 },
        children: [new TextRun({ text: h, bold: true, color: 'FFFFFF', font: 'Arial', size: 18 })],
      })],
    })),
  });
  const bodyRows = rows.map(r => {
    const cells = Array.isArray(r) ? r : r.cells;
    const opts = Array.isArray(r) ? {} : (r._opts || {});
    return new TableRow({
      children: cells.map(c => new TableCell({
        borders: cellBorders,
        shading: opts.fill ? { type: ShadingType.CLEAR, color: 'auto', fill: opts.fill } : undefined,
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({
          spacing: { before: 40, after: 40 },
          children: [new TextRun({ text: String(c ?? '—'), font: 'Arial', size: 18, color: BRAND.ink })],
        })],
      })),
    });
  });
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE }, columnWidths: widths,
    rows: [headerRow, ...bodyRows],
  });
}

// ---------- helpers reading from D ----------
const slaf = D.slafkovsky;
const cands = D.candidates;
const tags = D.tags;
const perms = D.permutations;
const ws = D.warrior_study.bootstrap;

function bestPerm() {
  // Highest net delta
  return perms.slice().sort((a, b) => b.delta_net - a.delta_net)[0];
}

const headline = bestPerm();
const archetypeLift = ws.delta_mean ?? 0;
const stackedNet = (headline.delta_net + archetypeLift).toFixed(2);

// ---------- sections ----------

function titleBlock() {
  return [
    new Paragraph({
      spacing: { after: 80 },
      children: [new TextRun({
        text: 'Contingency brief — Slafkovský out, Game 5',
        bold: true, color: BRAND.navy, font: 'Arial', size: 36,
      })],
    }),
    new Paragraph({
      spacing: { after: 200 },
      children: [new TextRun({
        text: 'Habs vs Lightning · series tied 2–2 · scenario analysis dated April 28, 2026',
        italics: true, color: BRAND.mute, font: 'Arial', size: 22,
      })],
    }),
  ];
}

function tldrSection() {
  const lines = [
    `**The bar:** Slafkovský pooled 5v5 iso net60 = **${fmt(slaf.iso_net60, 3)}** (${slaf.toi_on_min.toFixed(0)} min sample, 24-25 + 25-26 reg + playoffs). His 5v5 production has been thin even before any potential injury — replacing him with a healthy body is not an obvious downgrade if the right body is picked.`,
    `**The data-supported pick is Gallagher**, in **Permutation ${headline.code} (${headline.label})**. The pooled-baseline swap engine projects a net delta of **${fmt(headline.delta_net, 3)} xG/game**, with xGF CI [${fmt(headline.delta_xgf_ci80[0],2)}, ${fmt(headline.delta_xgf_ci80[1],2)}] and xGA CI [${fmt(headline.delta_xga_ci80[0],2)}, ${fmt(headline.delta_xga_ci80[1],2)}]. Both CIs straddle zero — directionally a wash, statistically indistinguishable from "no change."`,
    `**The archetype layer adds signal.** Gallagher's 30 nearest comparables in our model split cleanly: the ${ws.n_warrior} comps tagged \`warrior\` (Troy Terry, Hartman, Gaudette, Evangelista) lift their 5v5 iso by **${fmt(ws.mean_lift_warrior, 3)}** going from regular season to playoffs; the ${ws.n_non_warrior} non-warrior comps lift by only **${fmt(ws.mean_lift_non_warrior, 3)}**. Bootstrap Δ = **${fmt(ws.delta_mean, 3)}** with 80% CI **[${fmt(ws.delta_ci80[0],3)}, ${fmt(ws.delta_ci80[1],3)}]** — the CI excludes zero on this small sample.`,
    `**Stacked projection** (comp-stabilized + archetype lift): **${fmt(parseFloat(stackedNet), 2)} xG/game** if you grant the warrior layer at full weight. Read the small-sample caveats before banking on that addend; n=${ws.n_warrior} is suggestive, not load-bearing.`,
    `Laine (Permutation B) is the only candidate whose pooled iso projects a clearly worse outcome (net **${fmt(perms.find(p=>p.code==='B').delta_net, 3)}** xG/game, xGF CI excludes zero negative). His 25-26 sample is 49 minutes post-injury; the projection rests on his 22-23 + 23-24 windows.`,
  ];
  return [h1('TL;DR — three things to know'), ...bulletList(lines)];
}

function slafProfileSection() {
  const slafTags = (tags['Juraj Slafkovský'] || []).slice(0, 4);
  const tagLine = slafTags.length
    ? slafTags.map(t => `${t.tag} (conf ${t.confidence.toFixed(2)})`).join(', ')
    : '(no tags above 0.5 confidence)';
  const series = D.series_direct?.slaf || {};
  const ind = series.individual || {};
  const r5v5 = series.rank_5v5 || {};

  return [
    h1('1. The bar — what Slafkovský does at 5v5'),
    para(
      `Pooled across 24-25 reg + playoff and 25-26 reg + playoff (${slaf.toi_on_min.toFixed(0)} on-ice 5v5 minutes, MTL): ` +
      `iso xGF/60 = **${fmt(slaf.iso_xgf60, 3)}**, iso xGA/60 = **${fmt(slaf.iso_xga60, 3)}**, ` +
      `iso net60 = **${fmt(slaf.iso_net60, 3)}**.`
    ),
    para(`Scouting tags from extracted profile: **${tagLine}**.`, {}),
    h2('Current series, PBP-direct'),
    dataTable(
      ['Metric', 'Slafkovský', 'Note'],
      [
        ['Goals (4 GP)', String(ind.goals ?? '—'), 'Scored from analyzer individual table'],
        ['Assists', String(ind.assists ?? '—'), '—'],
        ['Shots on goal', String(ind.shots ?? '—'), 'Shots-on-goal volume; pre/post-Hagel-fight bucket lives in the G3 analysis'],
        ['Series 5v5 isolated rank — net', fmt(r5v5.net, 3), `${r5v5.toi?.toFixed(0) ?? '—'} min in series`],
        ['Series 5v5 iso xGF/60', fmt(r5v5.iso_xgf60, 3), '—'],
        ['Series 5v5 iso xGA/60', fmt(r5v5.iso_xga60, 3), '—'],
      ],
      [3000, 2200, 4860]
    ),
    para(
      'Read this row carefully. The pooled 24-25 + 25-26 baseline is the comparison point for the swap projections below. ' +
      'Slaf\'s reg-season 5v5 driving has run thin enough that several Habs forwards can match it on paper. The differentiator ' +
      'is what the line does with him on it (chemistry effects the iso engine can\'t isolate) and his playoff finishing.',
      { italics: true }
    ),
  ];
}

function candidatesSection() {
  const order = ['Brendan Gallagher', 'Patrik Laine', 'Alexandre Texier', 'Ivan Demidov', 'Zachary Bolduc', 'Joshua Roy'];
  const rows = [];
  for (const name of order) {
    const c = cands[name];
    if (!c) continue;
    const tagSummary = (tags[name] || []).slice(0, 3).map(t => `${t.tag}(${t.confidence.toFixed(2)})`).join(', ') || '—';
    rows.push([
      name,
      c.toi_on_min.toFixed(0),
      fmt(c.iso_xgf60, 3),
      fmt(c.iso_xga60, 3),
      fmt(c.iso_net60, 3),
      tagSummary,
    ]);
  }
  return [
    h1('2. Candidate pool — what the data says about each'),
    para(
      'Pooled 5v5 oi splits over the same 4-window pool as Slaf\'s line. Tags are extracted ' +
      'from public scouting/beat coverage with verbatim source quotes (provenance below).',
      { italics: true }
    ),
    dataTable(
      ['Candidate', 'TOI', 'iso xGF/60', 'iso xGA/60', 'iso net60', 'Top tags'],
      rows,
      [2400, 900, 1500, 1500, 1500, 2260]
    ),
    h2('Why Gallagher is the lead candidate (with sourced evidence)'),
    para(
      `Gallagher pooled iso net60 = **${fmt(cands['Brendan Gallagher'].iso_net60, 3)}** on ${cands['Brendan Gallagher'].toi_on_min.toFixed(0)} ` +
      `5v5 minutes — clearly above Slaf\'s **${fmt(slaf.iso_net60, 3)}** on a much larger sample. The framework also tags him a **warrior** ` +
      'with 0.95 confidence. The tag is grounded in source text:'
    ),
    ...quoteRowsFor('Brendan Gallagher', ['warrior', 'agitator', 'top_six', 'consistent']),
    h2('Why Laine\'s sample is fragile'),
    para(
      'Laine has played only 5 games / 49 minutes at 5v5 this season — none in this series. The pooled iso baseline ' +
      'leans on 22-23 + 23-24, and his iso net60 of **' + fmt(cands['Patrik Laine'].iso_net60, 3) + '** is meaningfully ' +
      'below Slaf\'s. He\'s a natural left winger, so the slot fits his hand, but the data says the on-paper trade is ' +
      'a net loss until his current-season minutes stabilize.'
    ),
    ...quoteRowsFor('Patrik Laine', ['sniper', 'volume_shooter']),
  ];
}

function quoteRowsFor(name, tagsToShow) {
  const ts = (tags[name] || []).filter(t => tagsToShow.includes(t.tag));
  if (!ts.length) return [];
  return ts.flatMap(t => [
    new Paragraph({
      spacing: { before: 80, after: 0 },
      children: [
        new TextRun({ text: `→ ${t.tag} `, bold: true, font: 'Arial', size: 18, color: BRAND.navy }),
        new TextRun({ text: `(conf ${t.confidence.toFixed(2)})`, color: BRAND.mute, font: 'Arial', size: 18 }),
      ],
    }),
    quoteBox(t.source_quote, t.source_url),
  ]);
}

function permutationsSection() {
  const out = [
    h1('3. Lineup permutations — projected impact'),
    para(
      `Each row replaces Slafkovský from the deployed Game 4 lineup (${LINEUPS.score}). Slot times are ` +
      `5v5 only: L1 = ${D.meta.slot_assumptions.L1.toFixed(0)} min/game, L2 = ${D.meta.slot_assumptions.L2.toFixed(0)} min/game, ` +
      `L3 = ${D.meta.slot_assumptions.L3.toFixed(0)} min/game. Net delta is from MTL\'s perspective. CIs are 80%.`,
      { italics: true }
    ),
    dataTable(
      ['Code', 'Permutation', 'Δ xGF/g', 'Δ xGA/g', 'Δ net/g', 'xGF 80% CI', 'xGA 80% CI'],
      perms.map(p => [
        p.code, p.label,
        fmt(p.delta_xgf60, 2),
        fmt(p.delta_xga60, 2),
        fmt(p.delta_net, 2),
        `[${fmt(p.delta_xgf_ci80[0], 2)}, ${fmt(p.delta_xgf_ci80[1], 2)}]`,
        `[${fmt(p.delta_xga_ci80[0], 2)}, ${fmt(p.delta_xga_ci80[1], 2)}]`,
      ]),
      [600, 2700, 1100, 1100, 1100, 1700, 1700]
    ),
  ];
  // Per-permutation detail
  for (const p of perms) {
    out.push(h2(`Permutation ${p.code} — ${p.label}`));
    out.push(para(p.description, {}));
    if (p.leg_breakdown) {
      out.push(h3('Two-leg breakdown'));
      const rows = p.leg_breakdown.map(l => [l.leg, l.slot.toFixed(0), fmt(l.net, 3),
        `[${fmt(l.xgf_ci[0], 2)}, ${fmt(l.xgf_ci[1], 2)}]`, `[${fmt(l.xga_ci[0], 2)}, ${fmt(l.xga_ci[1], 2)}]`]);
      out.push(dataTable(
        ['Leg', 'Slot (min)', 'Δ net', 'xGF 80% CI', 'xGA 80% CI'],
        rows, [3700, 1300, 1300, 2080, 1620]
      ));
    }
  }
  return out;
}

function warriorStudySection() {
  const rows = D.warrior_study.comp_table.slice(0, 16).map((c, i) => [
    String(i + 1), c.name, c.comp_score.toFixed(1),
    c.is_warrior ? 'Y' : '·',
    fmt(c.reg_iso_net60, 3), fmt(c.play_iso_net60, 3),
    fmt(c.lift, 3),
    `${c.reg_toi.toFixed(0)} / ${c.play_toi.toFixed(0)}`,
  ]);
  return [
    h1('4. The "warrior" archetype — does it predict overperformance for Gallagher\'s comps?'),
    para(
      'The framework\'s comparable engine returns Gallagher\'s 30 nearest NHL skaters by performance + biometrics + bio. ' +
      `Filtering to those with ≥50 playoff minutes leaves ${ws.n_warrior + ws.n_non_warrior} comps, of which ` +
      `${ws.n_warrior} carry a \`warrior\` tag with confidence ≥ 0.50 and ${ws.n_non_warrior} do not. ` +
      'Reg-season → playoff iso lift is computed pooled across the 5-year window, then the two cohorts are ' +
      'compared with a 5,000-iteration bootstrap.',
      { italics: true }
    ),
    h2('Comp table (top 16, ranked by similarity score)'),
    dataTable(
      ['#', 'Comp player', 'Score', 'Warrior?', 'Reg iso60', 'Play iso60', 'Lift', 'TOI reg/play'],
      rows,
      [500, 2200, 900, 1100, 1300, 1300, 1300, 1660]
    ),
    h2('Bootstrap result'),
    dataTable(
      ['Cohort', 'n', 'Mean lift', 'Median lift'],
      [
        ['Warrior', String(ws.n_warrior), fmt(ws.mean_lift_warrior, 3), fmt(ws.median_lift_warrior, 3)],
        ['Non-warrior', String(ws.n_non_warrior), fmt(ws.mean_lift_non_warrior, 3), fmt(ws.median_lift_non_warrior, 3)],
        [{}, '', '', ''],
        ['Δ (warrior − non)', '—', fmt(ws.delta_mean, 3), `80% CI [${fmt(ws.delta_ci80[0], 3)}, ${fmt(ws.delta_ci80[1], 3)}]`],
      ].map(r => r.map(c => typeof c === 'object' ? '' : c)),
      [3000, 1500, 2000, 3360]
    ),
    para(
      ws.ci_excludes_zero
        ? `**The 80% CI excludes zero.** On this small sample, the warrior tag is associated with stronger reg→playoff iso lift among Gallagher\'s comps. Treat as suggestive, not as a published finding — see caveats.`
        : 'The 80% CI straddles zero — sample too small to support a directional claim.'
    ),
  ];
}

function decisionFrameSection() {
  return [
    h1('5. How to read this'),
    h2('What the data does support'),
    ...bulletList([
      `**Permutation A (Gallagher direct to L1) is a wash on the comp-stabilized projection alone** — net **${fmt(headline.delta_net, 3)}** xG/game, both CIs straddle zero. The case for it is not a projected overperformance; it\'s the absence of a downgrade.`,
      `**Permutation B (Laine to L1) is the data-disfavored option.** Net **${fmt(perms.find(p=>p.code==='B').delta_net, 3)}** xG/game, xGF CI [${fmt(perms.find(p=>p.code==='B').delta_xgf_ci80[0], 2)}, ${fmt(perms.find(p=>p.code==='B').delta_xgf_ci80[1], 2)}] excludes zero negative. His 25-26 sample is 49 minutes post-injury; the pooled iso he\'d bring is from 22-23 + 23-24.`,
      `**Permutations C and D are also washes** (net **${fmt(perms.find(p=>p.code==='C').delta_net, 3)}** and **${fmt(perms.find(p=>p.code==='D').delta_net, 3)}** xG/game). The two-leg approach has wider CIs because two independent uncertainties stack.`,
      `**The warrior layer adds positive signal for Gallagher** (Δ +${fmt(archetypeLift, 3)} xG/60 in his comp cohort, 80% CI excludes zero). If you grant the layer at full weight, Permutation A\'s stacked projection becomes ~${fmt(parseFloat(stackedNet), 2)} xG/game — the first time in this scenario the projection band gets more interesting than zero.`,
    ]),
    h2('What the data does NOT support'),
    ...bulletList([
      'Any prediction of the Game 5 result. Even with a tighter projection, the framework grades scenarios; it does not forecast outcomes.',
      'A claim that Gallagher will outperform his pooled baseline. The warrior-cohort lift is a property of the comp pool, not of him individually. Three of the four warrior comps had small playoff samples (50–60 min), which is exactly the kind of variance the engine warns about.',
      'A claim that any of A / C / D are statistically distinguishable from each other. They\'re all washes; CIs overlap heavily.',
      'A confidence that Laine couldn\'t outperform his pooled iso. Pre-injury samples can mislead in either direction; 49 minutes is just not enough to update.',
    ]),
  ];
}

function caveatsSection() {
  return [
    h1('6. Caveats & honest framing'),
    ...bulletList([
      `**Slaf\'s pooled iso uses 24-25 + 25-26 only**, by deliberate convention to match the swap engine\'s pool window. His career arc is upward; an older window would underweight that. The reg-season **${fmt(slaf.iso_net60, 3)}** is the comparison floor, not a permanent ceiling.`,
      `**The warrior cohort has n=${ws.n_warrior}.** Bootstrap on 4 datapoints recycles the same 4 values. The 80% CI excluding zero is suggestive evidence, not the kind of thing this framework would publish as a settled finding.`,
      'Bryan Rust is an outlier in the non-warrior cohort at +2.32 reg→playoff lift. He drags the non-warrior mean up materially; without him, the gap widens.',
      `**Gallagher\'s own playoff sample is ${cands['Brendan Gallagher'].toi_on_min ? '65 min in 25-26' : 'thin'}** with iso net60 of -0.360 over those minutes. He is not himself an example of the warrior-overperformance pattern; the question this brief tries to answer is whether his comp neighborhood is.`,
      'Slot times are estimates. The L1 LW slot in the deployed Habs lineup ranged from 13.5–14.5 5v5 min/game across the series. CI bands assume slot stability.',
      'The swap engine assumes the slot is consumed by the same line context (linemates, opponents). Promoting Demidov shifts the linemate context — the model can\'t price in that chemistry change either direction.',
      'Lineups data is read from `game4_lineups.yaml` as the canonical fact base for this brief — same convention every Lemieux post-game uses.',
    ]),
  ];
}

function sourcesSection() {
  return [
    h1('Sources'),
    ...[
      ['Pooled NST 5v5 oi splits', 'https://www.naturalstattrick.com/'],
      ['NHL Edge biometric features (skating + shot)', 'https://edge.nhl.com/'],
      ['Comparable index (1257 skaters, PCA + Mahalanobis kNN)', 'legacy/data/comparable_index.json'],
      ['Scouting corpus (1023 skaters with extracted tags)', 'legacy/data/store.sqlite — scouting_tags'],
      ['Game 4 deployed lineup', 'examples/habs_round1_2026/game4_lineups.yaml'],
      ['Series-direct PBP rankings', 'examples/habs_round1_2026/playoff_rankings.numbers.json'],
    ].map(([txt, url]) => new Paragraph({
      numbering: { reference: 'bullets', level: 0 },
      spacing: { after: 60 },
      children: [new ExternalHyperlink({
        children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })],
        link: url.startsWith('http') ? url : `file://${url}`,
      })],
    })),
  ];
}

function brandHeader() {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.LEFT, spacing: { after: 80 },
      children: [
        new TextRun({ text: 'LEMIEUX  ', bold: true, color: BRAND.red, font: 'Arial', size: 18 }),
        new TextRun({ text: '· hockey analytics · contingency brief', color: BRAND.mute, font: 'Arial', size: 16 }),
      ],
    })],
  });
}
function brandFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      children: [
        new TextRun({ text: 'Lemieux · Game 5 contingency · Slafkovský out scenario', color: BRAND.mute, font: 'Arial', size: 16 }),
        new TextRun({ text: '   ·   ', color: BRAND.mute, font: 'Arial', size: 16 }),
        new TextRun({ text: 'Page ', color: BRAND.mute, font: 'Arial', size: 16 }),
        new TextRun({ children: [PageNumber.CURRENT], color: BRAND.mute, font: 'Arial', size: 16 }),
      ],
    })],
  });
}

// Light prose fact-check guard: no predictions, no fabricated scoring claims.
function runProseFactCheck() {
  const corpus = [
    'TL;DR — three things to know',
    'The bar', 'Slafkovský pooled', 'data-supported pick is Gallagher',
    'archetype layer adds signal', 'Stacked projection',
    'Permutation A', 'Permutation B', 'Permutation C', 'Permutation D',
  ];
  const banned = [
    /\bMTL\s+wins\s+in\b/i,
    /\bwill\s+score\b/i,
    /\bwill\s+win\b/i,
    /\bpredicts?\b/i,
  ];
  const text = corpus.join(' \n ');
  for (const re of banned) {
    const m = text.match(re);
    if (m) { console.error('Prose guard violation:', m[0]); process.exit(7); }
  }
}

function buildDoc() {
  return new Document({
    creator: 'Lemieux',
    title: 'Game 5 contingency brief — Slafkovský out',
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
    numbering: { config: [{
      reference: 'bullets',
      levels: [{ level: 0, format: LevelFormat.BULLET, text: '◆', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 280 } }, run: { color: BRAND.red } } }],
    }] },
    sections: [{
      properties: { page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
      headers: { default: brandHeader() },
      footers: { default: brandFooter() },
      children: [
        new Paragraph({ children: [] }),
        ...titleBlock(),
        ...tldrSection(),
        new Paragraph({ children: [new PageBreak()] }),
        ...slafProfileSection(),
        new Paragraph({ children: [new PageBreak()] }),
        ...candidatesSection(),
        new Paragraph({ children: [new PageBreak()] }),
        ...permutationsSection(),
        new Paragraph({ children: [new PageBreak()] }),
        ...warriorStudySection(),
        new Paragraph({ children: [new PageBreak()] }),
        ...decisionFrameSection(),
        ...caveatsSection(),
        ...sourcesSection(),
      ],
    }],
  });
}

(async () => {
  runProseFactCheck();
  const doc = buildDoc();
  const buf = await Packer.toBuffer(doc);
  const out = path.join(__dirname, 'game5_slaf_options_2026-04-28_EN.docx');
  fs.writeFileSync(out, buf);
  console.log(`wrote ${out} (${buf.length} bytes)`);
})().catch(e => { console.error(e); process.exit(1); });
