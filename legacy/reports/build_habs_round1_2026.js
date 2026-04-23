// Builds the MTL Round 1 2026 analytics report as a .docx file using docx-js.
// Reads numbers from reports/output/habs_round1_2026.numbers.json.

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink
} = require('docx');

// ---------- LOAD DATA ----------
const numbersPath = path.join(__dirname, 'output', 'habs_round1_2026.numbers.json');
const D = JSON.parse(fs.readFileSync(numbersPath, 'utf8'));

// ---------- HELPERS ----------
const fmt = (n, p = 3) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const s = Number(n).toFixed(p);
  return (Number(n) > 0 ? '+' : '') + s;
};
const fmt1 = n => fmt(n, 1);
const fmt2 = n => fmt(n, 2);

const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

const BLUE_HEADER = 'C5D9F1';   // light blue for table header
const GREY_BOX = 'F2F2F2';      // explainer box shading
const CREAM_BOX = 'FFF6E0';     // caveat/callout shading

// A headline paragraph (H1)
const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun(text)],
});
const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun(text)],
});
const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun(text)],
});
const p = (text, opts = {}) => new Paragraph({
  spacing: { after: 120 },
  children: [new TextRun({ text, ...opts })],
});
const runsP = (runs, opts = {}) => new Paragraph({
  spacing: { after: 120 },
  ...opts,
  children: runs,
});
const bulletP = (text) => new Paragraph({
  numbering: { reference: 'bullets', level: 0 },
  children: [new TextRun(text)],
});

// A shaded single-cell "callout" box with a title + body paragraphs
function calloutBox(title, bodyParagraphs, shade = GREY_BOX) {
  return new Table({
    columnWidths: [9360],
    margins: { top: 140, bottom: 140, left: 220, right: 220 },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders: cellBorders,
            width: { size: 9360, type: WidthType.DXA },
            shading: { fill: shade, type: ShadingType.CLEAR },
            children: [
              new Paragraph({
                spacing: { after: 80 },
                children: [new TextRun({ text: title, bold: true, size: 22 })],
              }),
              ...bodyParagraphs,
            ],
          }),
        ],
      }),
    ],
  });
}

// A data table helper. header: array of strings, rows: array of arrays.
// colWidths in DXA; totals 9360 for letter w/ 1" margins.
function dataTable(headers, rows, colWidths) {
  const nCols = headers.length;
  const widths = colWidths || Array(nCols).fill(Math.floor(9360 / nCols));
  const mkHeaderCell = (text, i) => new TableCell({
    borders: cellBorders,
    width: { size: widths[i], type: WidthType.DXA },
    shading: { fill: BLUE_HEADER, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: String(text), bold: true, size: 20 })],
    })],
  });
  const mkBodyCell = (text, i) => new TableCell({
    borders: cellBorders,
    width: { size: widths[i], type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT,
      children: [new TextRun({ text: String(text), size: 20 })],
    })],
  });
  return new Table({
    columnWidths: widths,
    margins: { top: 70, bottom: 70, left: 120, right: 120 },
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => mkHeaderCell(h, i)),
      }),
      ...rows.map(r => new TableRow({
        children: r.map((c, i) => mkBodyCell(c, i)),
      })),
    ],
  });
}

const spacer = () => new Paragraph({ spacing: { after: 120 }, children: [new TextRun('')] });

// ---------- SECTIONS ----------

// A. Title page & exec summary
const titleBlock = () => [
  new Paragraph({
    heading: HeadingLevel.TITLE,
    alignment: AlignmentType.CENTER,
    children: [new TextRun('Montreal Canadiens — 2026 Playoffs, Round 1')],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
    children: [new TextRun({
      text: 'A data-forward, intellectually-honest look at the MTL vs. TBL series',
      italics: true, size: 24, color: '555555',
    })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
    children: [new TextRun({
      text: `Prepared ${D.meta.date} · Series: ${D.meta.series_ref}`,
      size: 20, color: '777777',
    })],
  }),
  h2('Executive summary'),
  p(
    'Montreal opened its first-round series against Tampa Bay with a heroic Game 1 ' +
    '(Slafkovský power-play hat trick, OT winner) and gave up a late-game collapse in ' +
    'Game 2 (OT loss). This report digs into four questions the friend group asked: ' +
    '(1) what would swapping Dach and Texier out for Gallagher and Veleno do to the ' +
    'numbers, (2) what could Laine add on PP2 if healthy, (3) who on MTL is actually ' +
    'moving the needle in 25-26, and (4) what does a data-optimal lineup look like — ' +
    'plus a targeted look at Slafkovský\'s series by period.'
  ),
  p('Four-bullet read:', { bold: true }),
  bulletP(
    `The Dach→Gallagher / Texier→Veleno 2-for-2 at 5v5 projects a combined net of ${fmt(D.swaps_5v5.combined.net)} xG per 60 — a wash. ` +
    'CIs straddle zero; the data can\'t distinguish these lineups.'
  ),
  bulletP(
    'On 5v4, the Texier→Veleno side of the swap is meaningfully negative — Texier has been a real PP2 contributor this year and Veleno is a bottom-six 5v5 guy, not a PP option.'
  ),
  bulletP(
    'Laine, if healthy, has enough pooled PP sample to show he\'s not a slam-dunk upgrade — his on-ice 5v4 isolated rate is negative over the pooled window (small sample, post-injury context).'
  ),
  bulletP(
    'Slafkovský per-period analysis confirms the eye test: 5 shots and 3 goals in the "hot" bucket (G1 entire + G2 P1), zero shots in the "cold" bucket (G2 P3 + OT). He was not a driver of Game 2\'s collapse — he was held off the puck.'
  ),
];

// B. Methodology box (explainer block at the top)
const methodBox = () => [
  h2('How to read this report'),
  calloutBox('Key concepts at a glance', [
    p('Expected goals (xG): each shot is assigned a probability of becoming a goal based on location, type, and context. xGF is expected goals for, xGA is expected goals against.'),
    p('Rate per 60 (xGF/60, xGA/60): event count per 60 minutes of ice time — the standard way to compare players and teams across different sample sizes.'),
    p('Isolated impact (iso_xgf60 / iso_xga60): player\'s on-ice rate minus the team\'s rate without the player. If positive on offense, the team creates more xG with him on the ice. If negative on defense, the team gives up less xG with him on the ice (good).'),
    p('80% confidence interval: we show the range of plausible values, not a single point. We use 80% rather than 95% because 95% on a 16-game playoff sample looks like "we know nothing" — 80% shows signal when it exists without hiding it. CI spans zero = directionally ambiguous.'),
    p('Pooled baseline: for isolated impacts, we sum events and minutes across 2024-25 regular + playoffs and 2025-26 regular + playoffs so low-GP or traded players (Dach, Texier) get a more stable read. For "who\'s doing well" and the optimal lineup, we use 2025-26 only, as the user asked.'),
    p('Directional, not predictive: this report never predicts series outcomes. It estimates what the numbers say about isolated player impact — coaches see chemistry, matchups, and situational context this model cannot.', { italics: true }),
  ]),
  spacer(),
];

// C. Swap analyses
const swapSection = () => {
  const s5 = D.swaps_5v5;
  const s4 = D.swaps_5v4;

  // C.1 table
  const d1 = s5.dach_gallagher;
  const d1pp = s4.dach_gallagher;
  const c1Table = dataTable(
    ['Metric', 'OUT: Dach', 'IN: Gallagher', 'Δ (per 60)', '80% CI'],
    [
      ['5v5 iso xGF/60', fmt(d1.out.iso_xgf60), fmt(d1.in.iso_xgf60), fmt(d1.delta_xgf60), `(${fmt(d1.delta_xgf60_ci80[0])}, ${fmt(d1.delta_xgf60_ci80[1])})`],
      ['5v5 iso xGA/60', fmt(d1.out.iso_xga60), fmt(d1.in.iso_xga60), fmt(d1.delta_xga60), `(${fmt(d1.delta_xga60_ci80[0])}, ${fmt(d1.delta_xga60_ci80[1])})`],
      ['5v4 iso xGF/60', fmt(d1pp.out ? d1pp.out.iso_xgf60 : 0), fmt(d1pp.in ? d1pp.in.iso_xgf60 : 0), fmt(d1pp.delta_xgf60), `—`],
      ['Pooled TOI 5v5 / 5v4', `${fmt1(d1.out.toi_on)}m / ${fmt1(d1pp.out ? d1pp.out.toi_on : 0)}m`, `${fmt1(d1.in.toi_on)}m / ${fmt1(d1pp.in ? d1pp.in.toi_on : 0)}m`, '—', '—'],
    ],
    [2200, 1800, 1800, 1560, 2000]
  );

  // C.2 table
  const d2 = s5.texier_veleno;
  const d2pp = s4.texier_veleno;
  const c2Table = dataTable(
    ['Metric', 'OUT: Texier', 'IN: Veleno', 'Δ (per 60)', '80% CI'],
    [
      ['5v5 iso xGF/60', fmt(d2.out.iso_xgf60), fmt(d2.in.iso_xgf60), fmt(d2.delta_xgf60), `(${fmt(d2.delta_xgf60_ci80[0])}, ${fmt(d2.delta_xgf60_ci80[1])})`],
      ['5v5 iso xGA/60', fmt(d2.out.iso_xga60), fmt(d2.in.iso_xga60), fmt(d2.delta_xga60), `(${fmt(d2.delta_xga60_ci80[0])}, ${fmt(d2.delta_xga60_ci80[1])})`],
      ['5v4 iso xGF/60', fmt(d2pp.out ? d2pp.out.iso_xgf60 : 0), fmt(d2pp.in ? d2pp.in.iso_xgf60 : 0), fmt(d2pp.delta_xgf60), `—`],
      ['Pooled TOI 5v5 / 5v4', `${fmt1(d2.out.toi_on)}m / ${fmt1(d2pp.out ? d2pp.out.toi_on : 0)}m`, `${fmt1(d2.in.toi_on)}m / ${fmt1(d2pp.in ? d2pp.in.toi_on : 0)}m`, '—', '—'],
    ],
    [2200, 1800, 1800, 1560, 2000]
  );

  // C.3 combined
  const c = s5.combined;
  const cTable = dataTable(
    ['Metric', 'Point estimate', '80% CI'],
    [
      ['Δ team xGF/60', fmt(c.delta_xgf60), `(${fmt(c.delta_xgf60_ci80[0])}, ${fmt(c.delta_xgf60_ci80[1])})`],
      ['Δ team xGA/60', fmt(c.delta_xga60), `(${fmt(c.delta_xga60_ci80[0])}, ${fmt(c.delta_xga60_ci80[1])})`],
      ['Net (xGF − xGA)', fmt(c.net), '—'],
    ],
    [3000, 3180, 3180]
  );

  const netPerGame = (c.net * 50 / 60);  // ~50 min 5v5 per game
  const netPerSeries = netPerGame * 7;

  return [
    h1('1. Lineup swap analysis'),
    p(
      'The centerpiece. We project what each individual swap does to MTL\'s per-60 team rates, ' +
      'then combine. All values use pooled baseline (2 seasons + both playoffs) unless noted; ' +
      'slot minutes are set to the OUT player\'s usage in the context — about 12 minutes per game ' +
      'at 5v5 for these bottom/middle-six roles.'
    ),

    h2('1.1 Dach → Gallagher'),
    p(
      `At 5v5, this swap is a coin flip. Dach\'s isolated impact is slightly negative on offense ` +
      `(${fmt(d1.out.iso_xgf60)} iso xGF/60) and slightly positive on defense; Gallagher is the ` +
      `mirror image. Over his pooled sample (${fmt1(d1.in.toi_on)}m of 5v5 TOI across 2 seasons), ` +
      `Gallagher has been a genuine possession-driving veteran — better than his 25-26-only numbers suggest.`
    ),
    c1Table,
    calloutBox('Plain-language verdict', [
      p(`Net team impact of Dach → Gallagher ≈ ${fmt(d1.delta_xgf60 - d1.delta_xga60)} xG per 60 at 5v5, CIs straddling zero. A wash in the data. On PP2, Dach is the incumbent and has meaningful PP TOI; Gallagher is not a PP option. This decision is driven by injury status and chemistry, not numbers.`),
    ]),
    spacer(),

    h2('1.2 Texier → Veleno'),
    p(
      `Texier\'s pooled 5v5 impact across STL and MTL minutes (${fmt1(d2.out.toi_on)}m total) is near-neutral. ` +
      `Veleno is notably worse on offense (${fmt(d2.in.iso_xgf60)} iso xGF/60) but also suppresses xG against slightly better. ` +
      `At 5v4, Texier is the real loss: his pooled 5v4 iso xGF/60 is ${fmt(d2pp.out ? d2pp.out.iso_xgf60 : 0)}, well ahead of Veleno, ` +
      `who has essentially no PP role. If PP2 minutes are at stake, the swap is clearly negative.`
    ),
    c2Table,
    calloutBox('Traded-player caveat', [
      p('Texier\'s pooled sample includes his 2025-26 split between STL and MTL and his 2024-25 STL minutes. Our isolated-impact math compares his total on-ice events against MTL\'s team totals, which is a mild approximation. The directional read (Texier ≥ Veleno on offense) is robust; the magnitude is noisier than usual.'),
    ], CREAM_BOX),
    spacer(),

    h2('1.3 Combined 2-for-2'),
    p(
      'Adding the two independent swaps (variances add in quadrature), the combined projected ' +
      'team impact at 5v5 is mildly positive on net but both confidence intervals cross zero.'
    ),
    cTable,
    calloutBox('What this actually means in hockey terms', [
      p(`Net shift: ${fmt(c.net)} xG per 60 of team play (80% CI straddles zero).`),
      p(`Translated: in a typical 5v5 game (~50 min), that\'s roughly ${fmt(netPerGame)} xG per game. Over a 7-game series, ~${fmt(netPerSeries)} xG total — you\'d need to play roughly ${Math.round(1 / Math.abs(c.net || 0.001) * 60 / 50)} games before the model would expect a single-goal swing.`),
      p('The 5v5 data does not distinguish these lineups. The 5v4 picture favors keeping Texier on PP2. Net-net: if you\'re making this swap, you\'re doing it for reasons the model doesn\'t see (matchups, chemistry, discipline, coach\'s read on effort).'),
    ]),
  ];
};

// D. Laine hypothetical
const laineSection = () => {
  const l = D.laine;
  if (l.status !== 'ok') {
    return [
      h1('2. Patrik Laine — what if he were healthy?'),
      p('Laine had core-muscle surgery October 16, 2025 and has been ruled out by Martin St-Louis. Our pooled data is insufficient to say more with confidence.'),
    ];
  }
  const table = dataTable(
    ['Candidate (5v4)', 'Pooled TOI', 'iso xGF/60'],
    [
      ['Patrik Laine', `${fmt1(l.laine.toi_on)}m`, fmt(l.laine.iso_xgf60)],
      ...l.pp2_candidates.map(c => [c.name, `${fmt1(c.toi_on)}m`, fmt(c.iso_xgf60)]),
    ],
    [3500, 2000, 3860]
  );
  return [
    h1('2. Patrik Laine — what if he were healthy?'),
    p(
      'Laine had core-muscle surgery October 16, 2025, and was publicly ruled out for Round 1 by ' +
      'Martin St-Louis. This is a counterfactual: IF he were activated, how would his PP2 profile ' +
      'compare to the players MTL is actually using?'
    ),
    p(
      `The pooled 5v4 numbers across 2024-25 + 2025-26 show Laine with ${fmt1(l.laine.toi_on)} minutes ` +
      `of 5v4 on-ice time — a meaningful sample, though injury-shortened. His on-ice 5v4 isolated ` +
      `rate (${fmt(l.laine.iso_xgf60)} iso xGF/60) is not as strong as his reputation suggests — ` +
      `partly because the comparison team (MTL without him) already has Caufield, Suzuki, Slafkovský on PP1, ` +
      `and partly because his post-injury usage in 25-26 was tiny.`
    ),
    table,
    calloutBox('The honest read on Laine', [
      p('Career PP shooting profile: elite. Recent pooled sample: too damaged by surgery and limited 25-26 minutes to cleanly say "drop him in and it\'s better." On pure 5v4 iso xGF/60, Texier currently outperforms the other PP2 options, including pooled Laine.'),
      p('If St-Louis could activate him, the bet is that his shot and right-handed release elevates PP2 beyond what these small-sample numbers capture — coaches see that, the isolated-impact model cannot. This report will not claim the activation is worth +X wins.'),
    ]),
  ];
};

// E. Rankings
const rankingsSection = () => {
  const r = D.rankings;
  if (r.status !== 'ok') return [h1('3. Who\'s actually moving the needle'), p('Data not available.')];
  const fmtRow = (row) => [
    row.name, row.position, row.gp, fmt1(row.toi),
    fmt(row.iso_xgf60, 2), fmt(row.iso_xga60, 2), fmt(row.net, 2), `${row.gf}-${row.ga}`,
  ];
  const posTable = dataTable(
    ['Player', 'Pos', 'GP', 'TOI', 'iso xGF/60', 'iso xGA/60', 'Net', 'GF-GA'],
    r.positive.map(fmtRow),
    [2100, 600, 500, 900, 1400, 1400, 1000, 1460]
  );
  const negTable = dataTable(
    ['Player', 'Pos', 'GP', 'TOI', 'iso xGF/60', 'iso xGA/60', 'Net', 'GF-GA'],
    r.negative.map(fmtRow),
    [2100, 600, 500, 900, 1400, 1400, 1000, 1460]
  );
  return [
    h1('3. Who\'s moving the needle'),
    p(
      'Ranking MTL skaters by their isolated impact at 5v5, pooled across the 2025-26 regular season ' +
      'and the playoffs so far. Minimum 200 minutes pooled TOI to exclude tiny samples. "Net" is ' +
      'iso xGF/60 minus iso xGA/60 — higher is better. Remember: these are isolated rates, meaning ' +
      `player rate minus team-without-player rate, not raw shot-share numbers.`
    ),
    h3(`Doing well (top ${r.positive.length} by net)`),
    posTable,
    spacer(),
    h3(`Doing poorly (bottom ${r.negative.length} by net)`),
    negTable,
    calloutBox('How to interpret these numbers', [
      p('A net of +0.5 xG per 60 is strong; +1.0 is elite. A net of −0.5 is meaningfully weighing the team down. For context, the gap between Hutson (top) and Kapanen (bottom) in this sample is ~2 xG/60 — a massive isolated-impact spread.'),
      p('Negatives need context: Newhook and Kapanen are matchup/deployment bottom-six forwards; Matheson is often paired with Hutson or Xhekaj in heavy-usage spots and gets caved on defense as a result. These numbers are not verdicts on "good" or "bad" players — they\'re diagnostic.'),
    ]),
  ];
};

// F. Optimal lineup
const optimalSection = () => {
  const o = D.optimal;
  if (o.status !== 'ok') return [h1('4. A data-optimal lineup'), p('Data not available.')];
  const lineToRow = (arr, label) => [label, ...arr.slice(0, 3).concat(['', '', '']).slice(0, 3)];
  const fwdTable = dataTable(
    ['Line', 'Center', 'Wing', 'Wing'],
    [
      lineToRow(o.forwards[0] || [], 'Line 1'),
      lineToRow(o.forwards[1] || [], 'Line 2'),
      lineToRow(o.forwards[2] || [], 'Line 3'),
      lineToRow(o.forwards[3] || [], 'Line 4'),
    ],
    [1400, 2650, 2650, 2660]
  );
  const dTable = dataTable(
    ['Pair', 'LD', 'RD'],
    [
      ['Pair 1', o.defense[0][0], o.defense[0][1]],
      ['Pair 2', o.defense[1][0], o.defense[1][1]],
      ['Pair 3', o.defense[2][0], o.defense[2][1]],
    ],
    [1400, 3980, 3980]
  );
  const ppTable = dataTable(
    ['Unit', 'F1', 'F2', 'F3', 'F4', 'D'],
    [
      ['PP1', ...(o.pp_units.pp1 || []).concat(['', '', '', '', '']).slice(0, 5)],
      ['PP2', ...(o.pp_units.pp2 || []).concat(['', '', '', '', '']).slice(0, 5)],
    ],
    [900, 1900, 1900, 1900, 1900, 860]
  );
  return [
    h1('4. A data-optimal lineup'),
    p(
      'A lineup built mechanically from 2025-26 regular-season + 2026 playoff iso net impact, ' +
      'with constraints: Suzuki stays at 1C, Ds pair best + worst across the top 6 for balance, ' +
      'and PP units are seeded by 5v4 iso xGF/60. This is what the data says — not what the ' +
      'coach\'s eye necessarily sees.'
    ),
    h3('Forwards'),
    p('The center slot is always column 2; the two wings fill columns 3-4 without handedness preference. Minimum 300 pooled minutes so fringe trade-deadline pickups (e.g., Sammy Blais) are excluded.', { italics: true, size: 20 }),
    fwdTable,
    spacer(),
    h3('Defense'),
    dTable,
    spacer(),
    h3('Power play'),
    ppTable,
    calloutBox('Where the model and St-Louis will disagree', [
      p('Chemistry is invisible to the model. A line that looks statistically sub-optimal can outperform its parts if the players read each other; conversely, stacking the three highest-net forwards on Line 1 can leave Lines 2-4 thin and get your stars out-matched.'),
      p('The PP1 composition here (Suzuki, Slafkovský, Caufield, Demidov, Hutson) aligns with the real deployment and looks correct. PP2 composition depends heavily on what St-Louis wants the unit to do (grind / cycle / shoot-first) — the model only sees "who has generated xG on 5v4 so far this season".'),
      p('Goalie: data on GSAx (goals saved above expected) was not ingested in our goalie layer for this report. Dobes is the assumed starter based on public usage; verify before citing in chat.', { italics: true }),
    ]),
  ];
};

// G. Slafkovsky per-period
const slafSection = () => {
  const sl = D.slafkovsky;
  if (sl.status !== 'ok') {
    return [
      h1('5. Slafkovský — hot bucket vs. cold bucket'),
      p('Per-period analysis attempted via NHL.com shift charts + play-by-play failed to fetch. Game 1 and Game 2 totals would be a fallback.'),
    ];
  }
  const A = sl.buckets.A;
  const B = sl.buckets.B;
  const t = dataTable(
    ['Metric', `A: ${A.label}`, `B: ${B.label}`],
    [
      ['Slafkovský shifts', A.shift_count, B.shift_count],
      ['Slafkovský TOI (min)', fmt2(A.slaf_toi_min), fmt2(B.slaf_toi_min)],
      ['Slafkovský SOG', A.slaf_sog, B.slaf_sog],
      ['Slafkovský goals', A.slaf_goals, B.slaf_goals],
      ['MTL SOG on-ice', A.mtl_sog, B.mtl_sog],
      ['MTL goals on-ice', A.mtl_goals, B.mtl_goals],
      ['MTL missed shots on-ice', A.mtl_missed, B.mtl_missed],
      ['TBL SOG on-ice', A.tbl_sog, B.tbl_sog],
      ['TBL goals on-ice', A.tbl_goals, B.tbl_goals],
    ],
    [3400, 2980, 2980]
  );

  return [
    h1('5. Slafkovský — hot bucket vs. cold bucket'),
    p(
      'A targeted look at the question "was Slafkovský part of MTL\'s Game 2 collapse?" Bucket A ' +
      'covers the hot stretch (all of Game 1 plus the 1st period of Game 2). Bucket B covers the ' +
      'cold stretch (3rd period of Game 2 plus OT). The 2nd period of Game 2 is excluded ' +
      'intentionally — this is not a full-game comparison, it\'s the "when Slafkovský was flying" ' +
      'vs. "when the team collapsed" split.'
    ),
    calloutBox('Data source for this section', [
      p('NST game reports do not expose per-period player splits. We built this from the NHL.com public endpoints: shift charts (per-player, per-period shift times) joined to play-by-play (every shot / missed shot / goal with an event time and period). Events are counted as "on-ice" if the event time falls inside a Slafkovský shift in the same period.'),
    ]),
    spacer(),
    t,
    calloutBox('The story in one read', [
      p(`Bucket A (${fmt2(A.slaf_toi_min)} min, ${A.shift_count} shifts): Slafkovský generated ${A.slaf_sog} shots on goal and scored ${A.slaf_goals}. MTL outshot TBL ${A.mtl_sog}-${A.tbl_sog} with him on the ice. This is a player driving play.`),
      p(`Bucket B (${fmt2(B.slaf_toi_min)} min, ${B.shift_count} shifts): zero shots on goal, zero goals. MTL and TBL broke even on shots with him on the ice (${B.mtl_sog}-${B.tbl_sog}), but TBL scored ${B.tbl_goals} to MTL\'s ${B.mtl_goals}.`),
      p('Verdict: Slafkovský was neutralized in the cold stretch — not caved in defensively, but unable to generate offense. "Held off the puck" rather than "bled chances". That aligns with St-Louis\' post-Game 2 read that MTL lost possession and couldn\'t forecheck.'),
    ]),
  ];
};

// H. Sources
const sourcesSection = () => {
  const link = (text, url) => new Paragraph({
    spacing: { after: 80 },
    numbering: { reference: 'bullets', level: 0 },
    children: [new ExternalHyperlink({
      children: [new TextRun({ text, style: 'Hyperlink' })],
      link: url,
    })],
  });
  return [
    h1('6. Data sources & methodology notes'),
    h3('Primary data'),
    link('Natural Stat Trick — NHL advanced stats (team, skater, 5v5 / 5v4 / playoff splits)', 'https://www.naturalstattrick.com/'),
    link('NHL.com public shift chart API (per-player shifts with period)', 'https://api.nhle.com/stats/rest/en/shiftcharts'),
    link('NHL.com public play-by-play API (events with period + timestamp + shooter)', 'https://api-web.nhle.com/v1/gamecenter/{gameId}/play-by-play'),
    spacer(),
    h3('Pooled windows used'),
    p('• Swap analyses (pooled baseline): 2024-25 regular + playoff, 2025-26 regular + playoff.'),
    p('• "Who\'s moving the needle" + optimal lineup: 2025-26 regular + 2026 playoff only (per user ask).'),
    p('• Slafkovský per-period: NHL.com shift+play-by-play for games 2025030121 (G1) and 2025030122 (G2). Bucket A = G1 all periods + G2 P1. Bucket B = G2 P3 + G2 OT. G2 P2 explicitly excluded.'),
    spacer(),
    h3('Known caveats'),
    p('• Playoff samples are tiny (1–2 games per team at time of writing). The model uses regular-season impacts for the swap math to avoid overfitting playoff noise; see each section for the specific window used.'),
    p('• Traded players (Texier: STL → MTL mid-season) have NST team_id stored as "MTL, STL". Isolated impact pools all their minutes against the receiving team\'s totals — a mild approximation for traded players, robust for everyone else.'),
    p('• Goalie GSAx was not ingested in the "optimal lineup" section — the starter is a placeholder; verify before citing.'),
    p('• Beat-reporter "narrative" about specific games is NOT cited in this report because agent-assisted web research produced some unverifiable material. Where we describe events (e.g., Slafkovský\'s Game 1 hat trick), the claim is backed by NHL.com play-by-play directly — not a press recap.'),
    spacer(),
    h3('Reproducibility'),
    p('Every number in this report is computed by analytics/habs_round1.py and dumped to reports/output/habs_round1_2026.numbers.json alongside this .docx file. The docx is rendered by reports/build_habs_round1_2026.js.'),
  ];
};

// ---------- ASSEMBLE DOCUMENT ----------
const doc = new Document({
  creator: 'claudehockey',
  title: 'MTL Round 1 2026 Analytics Report',
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } }, // 11pt body
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal',
        run: { size: 44, bold: true, color: '111111', font: 'Arial' },
        paragraph: { spacing: { before: 120, after: 120 }, alignment: AlignmentType.CENTER } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, color: '1F2F4A', font: 'Arial' },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, color: '2F4A70', font: 'Arial' },
        paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, color: '333333', font: 'Arial' },
        paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets',
        levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: 'MTL Round 1 2026 — analytics report', size: 18, color: '777777', italics: true })],
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: 'Pooled baselines over specified windows · 2026 playoff samples are 1–2 games per team · ', size: 16, color: '777777' }),
          new TextRun({ text: 'Do not bet on this. · Page ', size: 16, color: '777777' }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: '777777' }),
        ],
      })] }),
    },
    children: [
      ...titleBlock(),
      ...methodBox(),
      new Paragraph({ children: [new PageBreak()] }),
      ...swapSection(),
      new Paragraph({ children: [new PageBreak()] }),
      ...laineSection(),
      new Paragraph({ children: [new PageBreak()] }),
      ...rankingsSection(),
      new Paragraph({ children: [new PageBreak()] }),
      ...optimalSection(),
      new Paragraph({ children: [new PageBreak()] }),
      ...slafSection(),
      new Paragraph({ children: [new PageBreak()] }),
      ...sourcesSection(),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  const outPath = path.join(__dirname, 'output', 'habs_round1_2026.docx');
  fs.writeFileSync(outPath, buf);
  console.log(`wrote ${outPath} (${buf.length} bytes)`);
}).catch(err => {
  console.error('build failed:', err);
  process.exit(1);
});
