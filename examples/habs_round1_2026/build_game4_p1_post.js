// Game 4 Period 1 ranking report — both teams, EN + FR.
// Inputs:
//   - game4_period1.numbers.json (analyzer output: PBP + boxscore)
//   - game4_pregame_lineups.yaml (canonical line composition for MTL)
//
// Live-data caveat: per-player on-ice Corsi is NOT in the JSON because
// NHL.com shifts trail real-time PBP. Individual contribution + team
// totals are full P1.
//
// Run:
//   node examples/habs_round1_2026/build_game4_p1_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'game4_period1.numbers.json'), 'utf8'));

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70', red: 'A6192E',
  ink: '111111', mute: '666666', rule: 'BFBFBF',
  good: 'E2F0D9', mid: 'FFF2CC', bad: 'F8CBAD',
  mtlfill: 'EAF1FB', tblfill: 'F4E6E8',
};

const fmtNum = (n, p = 1) => (n === null || n === undefined) ? '—' : Number(n).toFixed(p);
const fmtFr = (n, p = 1) => fmtNum(n, p).replace('.', ',');
const teamFill = (t) => t === 'MTL' ? BRAND.mtlfill : BRAND.tblfill;

const thin = { style: BorderStyle.SINGLE, size: 4, color: BRAND.rule };
const cellBorders = { top: thin, bottom: thin, left: thin, right: thin };

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
function para(t, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 100 },
    children: opts.italics
      ? [new TextRun({ text: t, italics: true, color: opts.color || BRAND.mute, font: 'Arial', size: 20 })]
      : md(t),
  });
}
function h1(t) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 }, children: [new TextRun({ text: t, bold: true, size: 30, color: BRAND.navy, font: 'Arial' })] }); }
function h2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: [new TextRun({ text: t, bold: true, size: 24, color: BRAND.navyLight, font: 'Arial' })] }); }
function bullets(items) { return items.map(s => new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 }, children: md(s) })); }

function dataTable(headers, rows, widths) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map(h => new TableCell({
      borders: cellBorders,
      shading: { type: ShadingType.CLEAR, color: 'auto', fill: BRAND.navy },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ spacing: { before: 60, after: 60 }, children: [new TextRun({ text: h, bold: true, color: 'FFFFFF', font: 'Arial', size: 18 })] })],
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
        children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: [new TextRun({ text: String(c ?? '—'), font: 'Arial', size: 18, color: BRAND.ink })] })],
      })),
    });
  });
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, columnWidths: widths, rows: [headerRow, ...bodyRows] });
}

const tp1 = D.team_p1;
const homeA = D.meta.matchup.split(' @ ')[1]; // MTL
const awayA = D.meta.matchup.split(' @ ')[0]; // TBL

const T = {
  en: {
    title: 'Period 1 ranking — Habs vs Lightning, Game 4 (Apr 26, 2026)',
    subtitle: `${awayA} ${D.meta.score_after_p1[awayA]} – ${D.meta.score_after_p1[homeA]} ${homeA} after P1 · MTL leads series 2–1`,
    tldr_title: 'What P1 actually showed',
    tldr: [
      `**Score 0–0, but Tampa drove the period.** 5v5 Corsi: ${homeA} ${tp1[homeA].cf_5v5} – ${awayA} ${tp1[awayA].cf_5v5} (${fmtNum(tp1[homeA+'_cf_pct_5v5'], 1)}% MTL). High-danger attempts: ${homeA} ${tp1[homeA].hdcf_5v5} – ${awayA} ${tp1[awayA].hdcf_5v5}. The shutout is a Dobeš performance, not a Habs structure win.`,
      `**Brayden Point is the player of the period across both teams.** 5 individual high-danger attempts in 6:08 — more HD looks alone than any MTL skater generated. Kucherov / Hagel were active too. Tampa's top six ate.`,
      `**The pre-game thesis underperformed in P1.** Texier–Dach–Bolduc, fed against the new Lilleberg–Crozier pair, generated 1 SOG and 1 HD attempt as a unit (line score 2.2). The Suzuki line was MTL's best (4 SOG, 4 HD, score 6.5) — flipping the matchup pattern from Game 3.`,
    ],
    method_title: 'Method + caveats',
    method: [
      `Source: NHL.com play-by-play + boxscore (full P1). Per-player ON-ICE Corsi is not in this brief — the live shift chart trails the PBP and would mis-attribute. Individual contribution and team totals are complete.`,
      `Composite ranking score: G×3 + A×2 + SOG×0.5 + ind-HD×0.75 + (missed/blocked attempts)×0.15 + (hits + blocks)×0.25 − giveaways×0.5 + takeaways×0.5. Score-effects-uncontrolled (game tied 0–0 means little distortion).`,
      `Sample is a single 20-minute period. Read magnitudes as directional, not predictive.`,
    ],
    team_title: 'Team-level P1 (5v5 unless noted)',
    team_table_intro: 'All shot attempts (Corsi), high-danger attempts (HD = within ~22 ft of the goal), shots on goal, total hits, goals.',
    team_rows: [
      [homeA, tp1[homeA].cf_5v5, tp1[homeA].hdcf_5v5, tp1[homeA].sog, tp1[homeA].hits, tp1[homeA].goals],
      [awayA, tp1[awayA].cf_5v5, tp1[awayA].hdcf_5v5, tp1[awayA].sog, tp1[awayA].hits, tp1[awayA].goals],
    ],
    th_team: 'Team', th_cf: 'Corsi (5v5)', th_hd: 'HD attempts (5v5)', th_sog: 'SOG (all)', th_hits: 'Hits', th_g: 'Goals',
    rank_title: 'Combined ranking — both teams (top 12, bottom 5)',
    rank_intro: 'Sorted by composite score. Players with TOI < 1.0 minute filtered out.',
    rank_bottom_intro: 'Bottom 5 by score (skaters with ≥ 2 min TOI):',
    th_rank: '#', th_player: 'Player', th_pos: 'Pos', th_toi: 'TOI', th_g_a: 'G–A', th_sog2: 'SOG', th_ihd: 'iHD', th_blk: 'Blk', th_hit: 'Hit', th_take: 'Tk/Gv', th_score: 'Score',
    mtl_title: 'MTL — full ranking',
    tbl_title: 'TBL — full ranking',
    lines_title: 'MTL forward lines (sum of player score)',
    lines_intro: 'Aggregated line totals: sum of individual stats across the trio. Read with TOI in mind.',
    th_line: 'Line', th_players: 'Players', th_lg: 'G', th_la: 'A', th_lsog: 'SOG', th_lihd: 'iHD', th_lhits: 'Hits', th_lblk: 'Blocks', th_lscore: 'Score sum', th_ltoi: 'Sum TOI',
    pairs_title: 'MTL defense pairs',
    contradiction_title: 'Pre-game vs P1 — what changed in real time',
    contradiction_bullets: [
      `**The matchup lever didn\'t produce.** The pre-game brief argued for feeding Texier–Dach–Bolduc into the Lilleberg–Crozier pair. In P1 the Dach line generated 1 SOG / 1 HD attempt (score 2.2). The Suzuki line generated 4 SOG / 4 HD attempts (score 6.5). The line that was supposed to be the matchup beneficiary was the quieter MTL forward unit.`,
      `**Tampa\'s adjusted blue line did not look broken.** Crozier-in / Carlile-out projected to +0.11 net xG/game pre-game (CI straddling zero). In P1, Crozier specifically had no events on either side of the puck and TBL drove play. The "third pair in flux" framing is not yet validated by results.`,
      `**Point was the period.** 5 individual HD attempts in 6:08 of TOI is a heat-check rate. If P2 lets him near that ice time at any strength, MTL\'s P1 break (a 0–0 score against play) gets harder to repeat.`,
    ],
    sources_title: 'Sources',
    sources: [
      ['NHL.com — Game 4 play-by-play (live)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/play-by-play`],
      ['NHL.com — Game 4 boxscore (live)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/boxscore`],
      ['Game 4 pre-game brief — Lemieux', '(see game4_pregame_2026-04-26)'],
    ],
    footer_left: 'Lemieux · P1 ranking · Game 4 MTL @ TBL',
    footer_right: 'Page',
  },
  fr: {
    title: 'Classement de la 1ʳᵉ période — CH c. Lightning, Match 4 (26 avril 2026)',
    subtitle: `${awayA} ${D.meta.score_after_p1[awayA]} – ${D.meta.score_after_p1[homeA]} ${homeA} après P1 · le CH mène 2–1`,
    tldr_title: 'Ce que la P1 a révélé',
    tldr: [
      `**Marque 0–0, mais Tampa a dirigé la période.** Corsi 5 c. 5 : ${homeA} ${tp1[homeA].cf_5v5} – ${awayA} ${tp1[awayA].cf_5v5} (${fmtFr(tp1[homeA+'_cf_pct_5v5'], 1)} % CH). Tentatives à haut danger : ${homeA} ${tp1[homeA].hdcf_5v5} – ${awayA} ${tp1[awayA].hdcf_5v5}. Le blanchissage est une performance de Dobeš, pas une victoire structurelle du CH.`,
      `**Brayden Point est le joueur de la période, toutes équipes confondues.** 5 tentatives individuelles à haut danger en 6:08 — à lui seul plus de chances en zone payante que n\'importe quel patineur du CH. Kucherov / Hagel actifs aussi. Le top 6 de Tampa a mangé.`,
      `**La thèse d\'avant-match a sous-performé en P1.** Texier–Dach–Bolduc, lancé contre la nouvelle paire Lilleberg–Crozier, a généré 1 tir au but et 1 tentative à haut danger (pointage de trio 2,2). Le trio de Suzuki a été le meilleur du CH (4 TB, 4 CHD, pointage 6,5) — inversant le patron du M3.`,
    ],
    method_title: 'Méthode et mises en garde',
    method: [
      `Source : jeu par jeu + sommaire de match LNH.com (P1 complet). Le Corsi ON-ICE par joueur N\'EST PAS dans ce dossier — le tableau des présences en direct est en retard sur le JPJ et causerait une mauvaise attribution. Les contributions individuelles et les totaux d\'équipe sont complets.`,
      `Pointage composite : B×3 + A×2 + TB×0,5 + CHD-individuelles×0,75 + (tentatives ratées/bloquées)×0,15 + (mises en échec + blocages)×0,25 − revirements×0,5 + récupérations×0,5. Aucun ajustement pour effets de marque (la marque 0–0 limite les distorsions).`,
      `Échantillon : une seule période de 20 minutes. Lire les amplitudes comme directionnelles, pas prédictives.`,
    ],
    team_title: 'Niveau d\'équipe en P1 (5 c. 5 sauf indication)',
    team_table_intro: 'Toutes les tentatives (Corsi), tentatives à haut danger (CHD ≈ rondelles tirées à 22 pi ou moins du but), tirs au but, mises en échec, buts.',
    team_rows: [
      [homeA, tp1[homeA].cf_5v5, tp1[homeA].hdcf_5v5, tp1[homeA].sog, tp1[homeA].hits, tp1[homeA].goals],
      [awayA, tp1[awayA].cf_5v5, tp1[awayA].hdcf_5v5, tp1[awayA].sog, tp1[awayA].hits, tp1[awayA].goals],
    ],
    th_team: 'Équipe', th_cf: 'Corsi (5 c. 5)', th_hd: 'Tent. CHD (5 c. 5)', th_sog: 'TB (toutes)', th_hits: 'M.É.', th_g: 'Buts',
    rank_title: 'Classement combiné — les deux équipes (top 12, bas 5)',
    rank_intro: 'Trié par pointage composite. Patineurs sous 1,0 min de TG filtrés.',
    rank_bottom_intro: 'Bas 5 par pointage (patineurs avec ≥ 2 min de TG) :',
    th_rank: '#', th_player: 'Joueur', th_pos: 'Pos', th_toi: 'TG', th_g_a: 'B–A', th_sog2: 'TB', th_ihd: 'CHDi', th_blk: 'Blq', th_hit: 'M.É.', th_take: 'Réc/Rev', th_score: 'Pointage',
    mtl_title: 'CH — classement complet',
    tbl_title: 'TBL — classement complet',
    lines_title: 'Trios à l\'avant du CH (somme des pointages)',
    lines_intro: 'Totaux agrégés par trio : somme des stats individuelles. À lire avec le TG en tête.',
    th_line: 'Trio', th_players: 'Joueurs', th_lg: 'B', th_la: 'A', th_lsog: 'TB', th_lihd: 'CHDi', th_lhits: 'M.É.', th_lblk: 'Blq', th_lscore: 'Σ pointage', th_ltoi: 'Σ TG',
    pairs_title: 'Paires défensives du CH',
    contradiction_title: 'Avant-match c. P1 — ce qui a changé en temps réel',
    contradiction_bullets: [
      `**Le levier d\'appariement n\'a pas livré.** Le survol d\'avant-match plaidait pour servir Texier–Dach–Bolduc à la paire Lilleberg–Crozier. En P1, le trio de Dach a généré 1 TB / 1 tent. CHD (pointage 2,2). Le trio de Suzuki a généré 4 TB / 4 CHD (pointage 6,5). Le trio supposé bénéficiaire de l\'appariement a été l\'unité d\'avant la plus discrète du CH.`,
      `**La défense ajustée de Tampa n\'a pas paru cassée.** Crozier-pour-Carlile projetait +0,11 net BA/match (IC chevauchant zéro) avant le match. En P1 spécifiquement, Crozier n\'a aucun événement de chaque côté de la rondelle et le TBL a dirigé le jeu. La narration « 3ᵉ duo en pleine reconstruction » n\'est pas encore validée par les résultats.`,
      `**Point a été LA période.** 5 tentatives individuelles à haut danger en 6:08 de TG, c\'est un rythme de joueur en feu. Si la P2 lui redonne ce temps de glace à n\'importe quelle force, le sursis du CH (la marque 0–0 contre le jeu) devient plus difficile à reproduire.`,
    ],
    sources_title: 'Sources',
    sources: [
      ['LNH.com — JPJ Match 4 (en direct)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/play-by-play`],
      ['LNH.com — Sommaire Match 4 (en direct)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/boxscore`],
      ['Survol d\'avant-match Match 4 — Lemieux', '(voir game4_pregame_2026-04-26)'],
    ],
    footer_left: 'Lemieux · classement P1 · Match 4 CH c. TBL',
    footer_right: 'Page',
  },
};

function teamTable(t) {
  const rows = t.team_rows.map(r => ({ cells: r, _opts: { fill: teamFill(r[0]) } }));
  return [
    h1(t.team_title),
    para(t.team_table_intro, { italics: true }),
    dataTable([t.th_team, t.th_cf, t.th_hd, t.th_sog, t.th_hits, t.th_g], rows, [1500, 2000, 2200, 1800, 1400, 1180]),
  ];
}

function rankRows(rows, t, top = 12) {
  return rows.slice(0, top).map((r, i) => ({
    cells: [
      String(i + 1), `${r.team} ${r.name}`, r.position, fmtNum(r.toi_p1_min, 1),
      `${r.g}–${(r.a1 || 0) + (r.a2 || 0)}`, r.sog, r.ind_hd_attempts || 0,
      r.blocks_made || 0, r.hits_for || 0,
      `${r.takeaways || 0}/${r.giveaways || 0}`,
      fmtNum(r.score, 2),
    ],
    _opts: { fill: teamFill(r.team) },
  }));
}

function rankSection(t, lang) {
  const skaters = D.ranked_skaters_combined.filter(r => r.toi_p1_min >= 1.0);
  const top = rankRows(skaters, t, 12);
  const bot = rankRows(skaters.filter(r => r.toi_p1_min >= 2.0).slice(-5), t, 5);
  // For bottom rows, set numbers correctly (continuation)
  const bot2 = bot.map((row, i) => ({
    cells: [String(skaters.filter(r => r.toi_p1_min >= 2.0).length - 5 + i + 1), ...row.cells.slice(1)],
    _opts: row._opts,
  }));
  return [
    h1(t.rank_title),
    para(t.rank_intro, { italics: true }),
    dataTable(
      [t.th_rank, t.th_player, t.th_pos, t.th_toi, t.th_g_a, t.th_sog2, t.th_ihd, t.th_blk, t.th_hit, t.th_take, t.th_score],
      top,
      [600, 2700, 700, 800, 800, 700, 700, 700, 700, 900, 800]
    ),
    para(t.rank_bottom_intro, { italics: true }),
    dataTable(
      [t.th_rank, t.th_player, t.th_pos, t.th_toi, t.th_g_a, t.th_sog2, t.th_ihd, t.th_blk, t.th_hit, t.th_take, t.th_score],
      bot2,
      [600, 2700, 700, 800, 800, 700, 700, 700, 700, 900, 800]
    ),
  ];
}

function teamRankSection(title, rows, t) {
  const tableRows = rows.map((r, i) => ({
    cells: [
      String(i + 1), r.name, r.position, fmtNum(r.toi_p1_min, 1),
      `${r.g}–${(r.a1 || 0) + (r.a2 || 0)}`, r.sog, r.ind_hd_attempts || 0,
      r.blocks_made || 0, r.hits_for || 0,
      `${r.takeaways || 0}/${r.giveaways || 0}`,
      fmtNum(r.score, 2),
    ],
    _opts: { fill: teamFill(r.team) },
  }));
  return [
    h2(title),
    dataTable(
      [t.th_rank, t.th_player, t.th_pos, t.th_toi, t.th_g_a, t.th_sog2, t.th_ihd, t.th_blk, t.th_hit, t.th_take, t.th_score],
      tableRows,
      [600, 2700, 700, 800, 800, 700, 700, 700, 700, 900, 800]
    ),
  ];
}

function linesSection(t) {
  const rows = (D.mtl_lines_agg || []).map(L => [
    `L${L.line}`, L.players.join(' / '), L.g, L.a, L.sog, L.ind_hd_attempts, L.hits_for, L.blocks_made, fmtNum(L.score_sum, 2), fmtNum(L.toi_min_sum, 1),
  ]);
  return [
    h1(t.lines_title),
    para(t.lines_intro, { italics: true }),
    dataTable(
      [t.th_line, t.th_players, t.th_lg, t.th_la, t.th_lsog, t.th_lihd, t.th_lhits, t.th_lblk, t.th_lscore, t.th_ltoi],
      rows,
      [700, 4500, 600, 600, 600, 600, 600, 600, 800, 800]
    ),
  ];
}

function pairsSection(t) {
  const rows = (D.mtl_pairs_agg || []).map(P => [
    `P${P.pair}`, P.players.join(' / '), '—', '—', '—', P.ind_hd_attempts, P.hits_for, P.blocks_made, fmtNum(P.score_sum, 2), fmtNum(P.toi_min_sum, 1),
  ]);
  return [
    h2(t.pairs_title),
    dataTable(
      [t.th_line, t.th_players, t.th_lg, t.th_la, t.th_lsog, t.th_lihd, t.th_lhits, t.th_lblk, t.th_lscore, t.th_ltoi],
      rows,
      [700, 4500, 600, 600, 600, 600, 600, 600, 800, 800]
    ),
  ];
}

function brandHeader() {
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
      new TextRun({ text: t.footer_left, color: BRAND.mute, font: 'Arial', size: 16 }),
      new TextRun({ text: '   ·   ', color: BRAND.mute, font: 'Arial', size: 16 }),
      new TextRun({ text: t.footer_right + ' ', color: BRAND.mute, font: 'Arial', size: 16 }),
      new TextRun({ children: [PageNumber.CURRENT], color: BRAND.mute, font: 'Arial', size: 16 }),
    ],
  })] });
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
      headers: { default: brandHeader() }, footers: { default: brandFooter(t) },
      children: [
        new Paragraph({ children: [] }),
        new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: t.title, bold: true, color: BRAND.navy, font: 'Arial', size: 36 })] }),
        new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: t.subtitle, italics: true, color: BRAND.mute, font: 'Arial', size: 22 })] }),
        h1(t.tldr_title), ...bullets(t.tldr),
        ...teamTable(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...rankSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...teamRankSection(t.mtl_title, D.mtl_ranked, t),
        ...teamRankSection(t.tbl_title, D.tbl_ranked, t),
        new Paragraph({ children: [new PageBreak()] }),
        ...linesSection(t),
        ...pairsSection(t),
        h1(t.contradiction_title), ...bullets(t.contradiction_bullets),
        h1(t.method_title), ...bullets(t.method),
        h1(t.sources_title),
        ...t.sources.map(([txt, url]) => new Paragraph({
          numbering: { reference: 'bullets', level: 0 }, spacing: { after: 60 },
          children: url.startsWith('http')
            ? [new ExternalHyperlink({ children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })], link: url })]
            : [new TextRun({ text: txt, font: 'Arial', size: 18, color: BRAND.mute })],
        })),
      ],
    }],
  });
}

(async () => {
  for (const lang of ['en', 'fr']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const primary = path.join(__dirname, `game4_p1_2026-04-26_${lang.toUpperCase()}.docx`);
    let out = primary;
    try {
      fs.writeFileSync(primary, buf);
    } catch (e) {
      if (e.code === 'EBUSY' || e.code === 'EACCES') {
        out = path.join(__dirname, `game4_p1_2026-04-26_${lang.toUpperCase()}_v2.docx`);
        fs.writeFileSync(out, buf);
      } else throw e;
    }
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
