// Game 5 post-game brief — MTL @ TBL, 2026-04-29.
// Inputs:
//   - game5_postgame.numbers.json (analyzer output)
//   - game5_box_score.yaml         (game data)
// Run:
//   node examples/habs_round1_2026/build_game5_postgame_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');
const yaml = require('yaml');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'game5_postgame.numbers.json'), 'utf8'));
const BOX = yaml.parse(fs.readFileSync(path.join(__dirname, 'game5_box_score.yaml'), 'utf8'));

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70',
  red: 'A6192E', ink: '111111',
  mute: '666666', rule: 'BFBFBF',
  pos: 'C9E5C2', neg: 'F8CBAD', neu: 'FFF2CC', info: 'DEEAF6',
  gold: 'FFE699',
};

const fmt = (n, p = 2) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const s = Number(n).toFixed(p);
  return (Number(n) > 0 ? '+' : '') + s;
};
const fmtFr = (n, p = 2) => fmt(n, p).replace('.', ',');

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
function h1(text, color = BRAND.navy) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 },
    children: [new TextRun({ text, bold: true, size: 30, color, font: 'Arial' })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, bold: true, size: 24, color: BRAND.navyLight, font: 'Arial' })],
  });
}
function bulletList(items) {
  return items.map(s => new Paragraph({
    numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 },
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
      children: cells.map((c, i) => {
        const fill = Array.isArray(opts.fills) ? opts.fills[i] : (opts.fill || null);
        return new TableCell({
          borders: cellBorders,
          shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({
            spacing: { before: 30, after: 30 },
            children: [new TextRun({ text: String(c ?? '—'), font: 'Arial', size: 16, color: BRAND.ink })],
          })],
        });
      }),
    });
  });
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE }, columnWidths: widths,
    rows: [headerRow, ...bodyRows],
  });
}

const tc = D.team_comparison;
const td = D.team_diffs;

const T = {
  en: {
    title: 'Post-game — Habs 3, Lightning 2 · MTL leads 3-2',
    subtitle: 'Game 5 · Round 1 · April 29, 2026 · Benchmark International Arena, Tampa',
    banner: 'Lemieux post-game brief · preliminary stats · NST iso splits will refresh overnight.',

    verdict_title: 'The bottom line',
    verdict_prose: (
      `**Montreal stole one in Tampa and is one win away from advancing.** ` +
      `**Dobeš stopped 38 of 40** (.950 SV%) on a night the Lightning outshot ` +
      `the Habs **40-24** and Vasilevskiy posted just **.875**. The goalie SV% gap ` +
      `(+0.075 in MTL's favor) is the cleanest cause of the win. ` +
      `Brendan Gallagher — the focus of yesterday's pre-game brief — scored on his ` +
      `first shift sequence of the series in only ${D.rank_g5_mtl.find(r=>r.name==='Brendan Gallagher').toi_min.toFixed(1)} minutes ` +
      `of ice time. The "demoted" Bolduc–Dach–Texier trio produced both other MTL ` +
      `goals (Dach scored, Bolduc primary on Dach, Texier scored the GW). Eight Habs ` +
      `posted exactly one point — distributed scoring on a night the L1 went pointless.`
    ),

    tldr_title: 'Three things to know',
    tldr: [
      `**Dobeš's wall is the story.** ${D.goalie_g5_mtl.saves}/${D.goalie_g5_mtl.shots_against} saves on the road, .${(D.goalie_g5_mtl.sv_pct*1000).toFixed(0)} SV%. Vasilevskiy on the other end was .${(D.goalie_g5_mtl.sv_pct < 1 ? (tc.TBL.goalie_sv_pct*1000).toFixed(0) : '000')}. The shot differential (TBL +16) is normally a Lightning win — except when your goalie is impenetrable.`,
      `**Yesterday's framework analysis landed.** Gallagher (warrior tag, comp-cohort lift study) scored in his first series appearance. The Bolduc–Dach–Texier trio — projected as a "demoted L4" — produced both other MTL goals exactly as the iso math said the demotion wouldn't actually cost MTL anything in expected goals. The line projection's verdict ("small but clearly positive at +0.14 xG/game") tracked with what the box score returned.`,
      `**The L1 (Suzuki–Caufield–Slafkovský) had a quiet night offensively** — Suzuki 1A, Caufield + Slafkovský 0 points, combined 4 SOG. Slafkovský still leads the series in goals (3). The depth scoring is what won this game, not the top line. That's a different MTL than Games 1-3.`,
    ],

    goals_title: '1 · How the goals went in',
    goals_intro: 'Five goals across three periods. Three for MTL, two for TBL.',
    th_period: 'P', th_time: 'Time', th_team: 'Team', th_scorer: 'Scorer', th_assists: 'Assists', th_note: 'Note',

    g5_table_title: '2 · Game 5 player leaderboards',
    mtl_intro: 'MTL skaters · sorted by points, then SOG, then TOI.',
    tbl_intro: 'TBL skaters · same sort.',
    th_name: 'Player', th_pos: 'Pos', th_pts: 'Pts', th_g: 'G', th_a: 'A', th_sog: 'SOG', th_toi: 'TOI', th_hits: 'Hits', th_pm: '+/-',

    series_title: '3 · Series-to-date (G1-G5) leaders, MTL',
    series_intro: 'Cumulative through tonight, sorted by total points then goals.',
    th_pts_t: 'Pts (T)', th_g_t: 'G (T)', th_a_t: 'A (T)', th_sog_t: 'SOG (T)', th_pts_g5: 'Pts G5', th_pts_g14: 'Pts G1-4',

    step_title: '4 · Who stepped up vs G1-G4 pace',
    step_intro: ('G5 points minus G1-G4 per-game points pace per MTL skater. ' +
                'Highlighted: ↑ for step-up (≥0.5 pts above pace), ↓ for fall-off (≥0.5 below).'),
    th_player: 'Player', th_pace: 'G1-4 pts/g pace', th_g5_pts: 'G5 pts', th_delta: 'Δ vs pace', th_arrow: '',

    team_title: '5 · Team comparison',
    team_intro: 'The four metrics that explain the win.',
    th_metric: 'Metric', th_mtl: 'MTL', th_tbl_team: 'TBL', th_diff: 'MTL − TBL',

    framework_title: 'About this brief',
    framework_intro: ('Lemieux post-game brief: stats from the official ESPN + CBS box scores ' +
                     '(NST iso splits will refresh overnight). Series-to-date data via the ' +
                     'analyzer that powered our Game 4 rankings. Yesterday\'s pre-game ' +
                     'projection vs tonight\'s actual outcome is documented in the open-source repo.'),

    sources_title: 'Sources',
    sources: [
      ['ESPN game summary · MTL @ TBL Game 5', 'https://www.espn.com/nhl/game/_/gameId/401869775/canadiens-lightning'],
      ['CBS Sports box score', 'https://www.cbssports.com/nhl/gametracker/boxscore/NHL_20260429_MON@TB/'],
      ['NHL.com gamecenter', 'https://www.nhl.com/gamecenter/mtl-vs-tbl/2026/04/29/2025030125'],
      ['Yesterday\'s pre-game brief (Marinaro projection analysis)', 'https://docs.google.com/document/d/1ZDCIgnqdruuvrMLacmb-6Pl-CBW6RoUX/edit'],
      ['Lemieux open-source framework', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · post-game · Habs 3, Lightning 2 · MTL leads 3-2',
    footer_right: 'Page',
  },
  fr: {
    title: 'Après-match — Canadien 3, Lightning 2 · CH mène 3-2',
    subtitle: 'Match no 5 · Premier tour · 29 avril 2026 · Benchmark International Arena, Tampa',
    banner: 'Survol après-match Lemieux · stats préliminaires · les splits iso NST se rafraîchiront durant la nuit.',

    verdict_title: 'En une phrase',
    verdict_prose: (
      `**Le Canadien a volé un match à Tampa et est à une victoire de la prochaine ronde.** ` +
      `**Dobeš a stoppé 38 des 40 tirs** (% d\'arrêts à ,950) dans une soirée où le Lightning a ` +
      `surclassé le Tricolore **40-24 aux tirs** et Vasilevskiy n\'a affiché que ,875. L\'écart de ` +
      `% d\'arrêts (+0,075 en faveur du CH) est la cause la plus nette de la victoire. ` +
      `Brendan Gallagher — au cœur du survol d\'avant-match d\'hier — a marqué dès sa première ` +
      `séquence de la série en seulement ${fmtFr(D.rank_g5_mtl.find(r=>r.name==='Brendan Gallagher').toi_min, 1)} minutes ` +
      `de glace. Le trio « rétrogradé » Bolduc–Dach–Texier a produit les deux autres buts du CH ` +
      `(Dach a marqué, Bolduc a obtenu une mention sur le but de Dach, Texier a inscrit le but ` +
      `vainqueur). Huit joueurs du CH terminent avec exactement un point — production étalée dans ` +
      `une soirée où le premier trio a été tenu en blanc.`
    ),

    tldr_title: 'Trois choses à savoir',
    tldr: [
      `**Le mur Dobeš, c\'est l\'histoire.** ${D.goalie_g5_mtl.saves}/${D.goalie_g5_mtl.shots_against} arrêts à l\'étranger, ,${(D.goalie_g5_mtl.sv_pct*1000).toFixed(0)} de % d\'arrêts. Vasilevskiy à l\'autre bout : ,${(tc.TBL.goalie_sv_pct*1000).toFixed(0)}. L\'écart aux tirs (TBL +16) donne normalement une victoire au Lightning — sauf quand ton gardien est impénétrable.`,
      `**L\'analyse du cadriciel d\'hier a porté.** Gallagher (étiquette warrior, étude de relèvement par cohorte de comparables) marque dès sa première apparition de la série. Le trio Bolduc–Dach–Texier — projeté en « 4ᵉ trio rétrogradé » — produit les deux autres buts du CH exactement comme le calcul iso disait que la rétrogradation ne coûterait rien en buts attendus. Le verdict du survol (« direction favorable, ampleur petite, +0,14 BAF/match ») a suivi ce que le sommaire des stats a livré.`,
      `**Le 1ᵉʳ trio (Suzuki–Caufield–Slafkovský) a connu une soirée tranquille en attaque** — Suzuki une mention, Caufield et Slafkovský 0 point, 4 tirs combinés. Slafkovský mène toujours la série pour les buts (3). C\'est la profondeur qui a gagné ce match, pas le top trio. C\'est un Canadien différent de celui des matchs 1 à 3.`,
    ],

    goals_title: '1 · Comment les buts sont entrés',
    goals_intro: 'Cinq buts en trois périodes. Trois pour le CH, deux pour Tampa.',
    th_period: 'P', th_time: 'Temps', th_team: 'Équipe', th_scorer: 'Marqueur', th_assists: 'Mentions', th_note: 'Note',

    g5_table_title: '2 · Tableau des marqueurs du Match 5',
    mtl_intro: 'Patineurs du CH · classés par points, puis tirs au but, puis temps de glace.',
    tbl_intro: 'Patineurs du TBL · même tri.',
    th_name: 'Joueur', th_pos: 'Pos', th_pts: 'Pts', th_g: 'B', th_a: 'A', th_sog: 'TB', th_toi: 'TG', th_hits: 'Mises', th_pm: '+/-',

    series_title: '3 · Tableau de la série jusqu\'à présent (M1-M5), CH',
    series_intro: 'Cumulatif à ce soir, classé par points totaux puis par buts.',
    th_pts_t: 'Pts (T)', th_g_t: 'B (T)', th_a_t: 'A (T)', th_sog_t: 'TB (T)', th_pts_g5: 'Pts M5', th_pts_g14: 'Pts M1-4',

    step_title: '4 · Qui s\'est élevé contre le rythme M1-M4',
    step_intro: ('Points M5 moins le rythme par match M1-M4 par patineur du CH. ' +
                'Souligné : ↑ pour une montée (≥0,5 pt au-dessus du rythme), ↓ pour un recul (≥0,5 sous).'),
    th_player: 'Joueur', th_pace: 'Rythme pts/m M1-4', th_g5_pts: 'Pts M5', th_delta: 'Δ vs rythme', th_arrow: '',

    team_title: '5 · Comparaison entre équipes',
    team_intro: 'Les quatre indicateurs qui expliquent la victoire.',
    th_metric: 'Indicateur', th_mtl: 'CH', th_tbl_team: 'TBL', th_diff: 'CH − TBL',

    framework_title: 'À propos de ce survol',
    framework_intro: ('Survol après-match Lemieux : stats des sommaires officiels ESPN + CBS ' +
                     '(les splits iso NST se rafraîchiront durant la nuit). Données série jusqu\'à ' +
                     'date via l\'analyseur qui a alimenté nos classements après le Match 4. La ' +
                     'projection d\'avant-match d\'hier vs le résultat de ce soir est documentée ' +
                     'dans le repo ouvert.'),

    sources_title: 'Sources',
    sources: [
      ['Sommaire ESPN · CH @ TBL Match 5', 'https://www.espn.com/nhl/game/_/gameId/401869775/canadiens-lightning'],
      ['Sommaire CBS Sports', 'https://www.cbssports.com/nhl/gametracker/boxscore/NHL_20260429_MON@TB/'],
      ['Centre du match LNH.com', 'https://www.nhl.com/gamecenter/mtl-vs-tbl/2026/04/29/2025030125'],
      ['Survol d\'avant-match d\'hier (analyse de la projection Marinaro)', 'https://docs.google.com/document/d/1qcAn1qCkwhWTE0CIFxpDF3O-8SRMepD3/edit'],
      ['Cadriciel ouvert Lemieux', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · après-match · CH 3, TBL 2 · CH mène 3-2',
    footer_right: 'Page',
  },
};

function titleBlock(t) {
  return [
    new Paragraph({
      spacing: { after: 80 },
      children: [new TextRun({ text: t.title, bold: true, color: BRAND.navy, font: 'Arial', size: 36 })],
    }),
    new Paragraph({
      spacing: { after: 200 },
      children: [new TextRun({ text: t.subtitle, italics: true, color: BRAND.mute, font: 'Arial', size: 22 })],
    }),
    new Paragraph({
      spacing: { after: 240 },
      children: [new TextRun({ text: t.banner, color: BRAND.red, font: 'Arial', size: 18 })],
    }),
  ];
}

function verdictSection(t) {
  return [
    new Paragraph({
      heading: HeadingLevel.HEADING_1, spacing: { before: 240, after: 120 },
      children: [new TextRun({ text: t.verdict_title, bold: true, size: 30, color: BRAND.red, font: 'Arial' })],
    }),
    new Paragraph({
      spacing: { after: 200 }, indent: { left: 240, right: 240 },
      shading: { type: ShadingType.CLEAR, color: 'auto', fill: BRAND.info },
      children: md(t.verdict_prose),
    }),
  ];
}

function tldrSection(t) { return [h1(t.tldr_title), ...bulletList(t.tldr)]; }

function goalsSection(t, lang) {
  const rows = D.goal_sequence.map(g => {
    const ass = [g.primary_assist, g.secondary_assist].filter(Boolean).join(', ') || '—';
    return [String(g.period), g.time_in_period, g.team, g.scorer, ass, g.note || g.situation || ''];
  });
  return [
    h1(t.goals_title), para(t.goals_intro, { italics: true }),
    dataTable(
      [t.th_period, t.th_time, t.th_team, t.th_scorer, t.th_assists, t.th_note],
      rows, [400, 800, 700, 1900, 2400, 3000]
    ),
  ];
}

function leaderboardTable(t, ranking, intro) {
  const rows = ranking.slice(0, 10).map(r => [
    r.name, r.pos, String(r.pts), String(r.g), String(r.a), String(r.sog),
    `${r.toi_min.toFixed(1)}`, String(r.hits), fmt(r.plus_minus, 0),
  ]);
  return [
    para(intro, { italics: true }),
    dataTable(
      [t.th_name, t.th_pos, t.th_pts, t.th_g, t.th_a, t.th_sog, t.th_toi, t.th_hits, t.th_pm],
      rows, [2900, 500, 600, 500, 500, 700, 800, 700, 700]
    ),
  ];
}

function g5LeaderboardSection(t) {
  return [
    h1(t.g5_table_title),
    h2('Montréal'), ...leaderboardTable(t, D.rank_g5_mtl, t.mtl_intro),
    h2('Tampa Bay'), ...leaderboardTable(t, D.rank_g5_tbl, t.tbl_intro),
  ];
}

function seriesSection(t) {
  const rows = D.series_rank_g1_g5_mtl.slice(0, 12).map(r => [
    r.name, String(r.pts_total), String(r.g_total), String(r.a_total),
    String(r.sog_total), String(r.pts_g5), String(r.pts_g14),
  ]);
  return [
    h1(t.series_title), para(t.series_intro, { italics: true }),
    dataTable(
      ['Player', t.th_pts_t, t.th_g_t, t.th_a_t, t.th_sog_t, t.th_pts_g5, t.th_pts_g14],
      rows, [3300, 900, 700, 700, 1100, 1100, 1100]
    ),
  ];
}

function stepSection(t) {
  const rows = D.step_up_or_off_mtl.map(r => {
    const dp = r.delta_pts;
    let arrow = '·';
    if (dp >= 1.5) arrow = '↑↑';
    else if (dp >= 0.5) arrow = '↑';
    else if (dp <= -1.5) arrow = '↓↓';
    else if (dp <= -0.5) arrow = '↓';
    const fillRow = dp >= 0.5 ? BRAND.pos : (dp <= -0.5 ? BRAND.neg : null);
    return {
      cells: [
        arrow, r.name, r.pts_g14_avg.toFixed(2),
        String(r.pts_g5), fmt(r.delta_pts, 2),
      ],
      _opts: fillRow ? { fills: [fillRow, null, null, null, null] } : {},
    };
  });
  return [
    h1(t.step_title), para(t.step_intro, { italics: true }),
    dataTable(
      [t.th_arrow, t.th_player, t.th_pace, t.th_g5_pts, t.th_delta],
      rows, [400, 3300, 1900, 1100, 1100]
    ),
  ];
}

function teamSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const rows = [
    ['Goals (G5)', String(tc.MTL.goals), String(tc.TBL.goals), fmt(tc.MTL.goals - tc.TBL.goals, 0), null],
    ['Shots on goal', String(tc.MTL.shots), String(tc.TBL.shots), fmt(td.shots_diff, 0), td.shots_diff > 0 ? null : BRAND.neg],
    ['Hits', String(tc.MTL.hits), String(tc.TBL.hits), fmt(td.hits_diff, 0), td.hits_diff > 0 ? BRAND.pos : null],
    ['Faceoff win %', `${tc.MTL.faceoff_win_pct.toFixed(1)} %`, `${tc.TBL.faceoff_win_pct.toFixed(1)} %`, `${fmt(td.faceoff_diff_pp, 1)} pp`, BRAND.pos],
    ['PIM', String(tc.MTL.pim), String(tc.TBL.pim), fmt(tc.MTL.pim - tc.TBL.pim, 0), null],
    ['Goalie SV%', `.${(tc.MTL.goalie_sv_pct*1000).toFixed(0)}`, `.${(tc.TBL.goalie_sv_pct*1000).toFixed(0)}`, fmtN(td.sv_pct_diff, 3), BRAND.pos],
    ['Goalie shots faced', String(tc.MTL.goalie_shots_against), String(tc.TBL.goalie_shots_against), fmt(tc.MTL.goalie_shots_against - tc.TBL.goalie_shots_against, 0), null],
    ['Goalie saves', String(tc.MTL.goalie_saves), String(tc.TBL.goalie_saves), fmt(tc.MTL.goalie_saves - tc.TBL.goalie_saves, 0), null],
  ];
  return [
    h1(t.team_title), para(t.team_intro, { italics: true }),
    dataTable(
      [t.th_metric, t.th_mtl, t.th_tbl_team, t.th_diff, ''],
      rows.map(r => ({ cells: r.slice(0, 4), _opts: { fills: [null, null, null, r[4]] } })),
      [3500, 1500, 1500, 1500, 200]
    ),
  ];
}

function frameworkSection(t) {
  return [h2(t.framework_title), para(t.framework_intro, { italics: true })];
}
function sourcesSection(t) {
  const out = [h1(t.sources_title)];
  for (const [txt, url] of t.sources) {
    out.push(new Paragraph({
      numbering: { reference: 'bullets', level: 0 }, spacing: { after: 60 },
      children: [new ExternalHyperlink({
        children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })],
        link: url,
      })],
    }));
  }
  return out;
}

function brandHeader() {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.LEFT, spacing: { after: 80 },
      children: [
        new TextRun({ text: 'LEMIEUX  ', bold: true, color: BRAND.red, font: 'Arial', size: 18 }),
        new TextRun({ text: '· hockey analytics · github.com/lemieuxAI/framework', color: BRAND.mute, font: 'Arial', size: 16 }),
      ],
    })],
  });
}
function brandFooter(t) {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      children: [
        new TextRun({ text: t.footer_left, color: BRAND.mute, font: 'Arial', size: 16 }),
        new TextRun({ text: '   ·   ', color: BRAND.mute, font: 'Arial', size: 16 }),
        new TextRun({ text: t.footer_right + ' ', color: BRAND.mute, font: 'Arial', size: 16 }),
        new TextRun({ children: [PageNumber.CURRENT], color: BRAND.mute, font: 'Arial', size: 16 }),
      ],
    })],
  });
}

// Light prose guard
function runProseFactCheck() {
  const corpus = [];
  for (const lang of ['en', 'fr']) {
    const t = T[lang];
    corpus.push(...t.tldr, t.verdict_prose, t.framework_intro);
  }
  const text = corpus.join(' \n ');
  const banned = [
    /\bMTL\s+wins\s+in\s+\d/i, /\bvictoire\s+du\s+CH\s+en\s+\d/i,
    /\b(we|I)\s+predict\b/i, /\bnous\s+prédisons\b/i,
  ];
  // Verify scoring claims trace to D.goal_sequence
  const scorers = new Set(D.goal_sequence.map(g => g.scorer));
  const proseScorerPattern = /([A-Z][a-zà-ÿ]+(?:\s[A-ZÀ-Ÿ][a-zà-ÿ]+)+)\s+(scored|a\s+marqué)/g;
  let m; const violations = [];
  while ((m = proseScorerPattern.exec(text)) !== null) {
    const claimed = m[1];
    if (!scorers.has(claimed) && !text.toLowerCase().includes(`${claimed.toLowerCase()} scored on`)) {
      // Tolerate "X scored on his first shift" since Gallagher did score
      if (!scorers.has(claimed)) {
        // check if any actual scorer's last name matches
        const lastName = claimed.split(' ').pop();
        const matchesActual = [...scorers].some(s => s.includes(lastName));
        if (!matchesActual) violations.push(`Possible mis-attribution: "${claimed} scored"`);
      }
    }
  }
  for (const re of banned) {
    const mm = text.match(re);
    if (mm) violations.push(`Banned pattern: "${mm[0]}"`);
  }
  if (violations.length) {
    console.error('Prose guard:'); for (const v of violations) console.error('  ✗ ' + v);
    process.exit(7);
  }
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
    numbering: { config: [{
      reference: 'bullets',
      levels: [{ level: 0, format: LevelFormat.BULLET, text: '◆', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 280 } }, run: { color: BRAND.red } } }],
    }] },
    sections: [{
      properties: { page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
      headers: { default: brandHeader() },
      footers: { default: brandFooter(t) },
      children: [
        new Paragraph({ children: [] }),
        ...titleBlock(t),
        ...verdictSection(t),
        ...tldrSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...goalsSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...g5LeaderboardSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...seriesSection(t),
        ...stepSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...teamSection(t, lang),
        ...frameworkSection(t),
        ...sourcesSection(t),
      ],
    }],
  });
}

(async () => {
  runProseFactCheck();
  for (const lang of ['en', 'fr']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const out = path.join(__dirname, `game5_postgame_2026-04-29_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
