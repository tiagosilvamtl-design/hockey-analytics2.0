// Habs playoff player-rankings report (after Game 3, 2026-04-26).
// Branded EN+FR docx, prose-fact-check guard active.
//
// Run: node examples/habs_round1_2026/build_playoff_rankings_post.js

const fs = require('fs');
const path = require('path');
const yaml = require('yaml');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'playoff_rankings.numbers.json'), 'utf8'));
const LINEUPS = yaml.parse(fs.readFileSync(path.join(__dirname, 'game3_lineups.yaml'), 'utf8'));

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70', red: 'A6192E', ink: '111111',
  mute: '666666', rule: 'BFBFBF',
  pos: 'E2F0D9', neg: 'F8CBAD', neutral: 'FFF2CC',
  info: 'DEEAF6', explainer: 'F2F2F2',
};
const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: BRAND.rule };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

const fmt = (n, p = 2, lang = 'en') => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  let s = Number(n).toFixed(p);
  if (Number(n) > 0) s = '+' + s;
  if (lang === 'fr') s = s.replace('.', ',');
  return s;
};
const fmt1 = (n, l) => fmt(n, 1, l);

// ---------- Prose fact-check guard ----------
function runProseFactCheck(allCorpus) {
  const scorers = new Set((D.individual || []).filter(p => p.g > 0).map(p => p.name));
  const rosterNames = new Set();
  const collect = (team) => {
    for (const line of (team.forwards || [])) for (const p of (line.players || [])) if (p.name) rosterNames.add(p.name);
    for (const pair of (team.defense || [])) for (const p of (pair.players || [])) if (p.name) rosterNames.add(p.name);
  };
  for (const t of ['MTL', 'TBL']) collect((LINEUPS.teams || {})[t] || {});

  const text = allCorpus.join('\n\n');
  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const errors = [];
  for (const name of rosterNames) {
    if (scorers.has(name)) continue;
    const last = name.split(' ').slice(-1)[0];
    for (const cand of [name, last].filter(s => s && s.length >= 3)) {
      const c = escapeRe(cand);
      const direct = new RegExp(
        `(?<![-])\\b${c}\\b\\s+(?:has\\s+|have\\s+|had\\s+|also\\s+|just\\s+|will\\s+)?` +
        `(?:scored|opened the scoring|tied it|tied the game|notched (?:a |his |the )?goal|` +
        `a marqu(?:é|e)|marque\\b|a inscrit|égalise|inscrit (?:le|son) (?:but|filet))`, 'i'
      );
      const coord = new RegExp(
        `(?<![-])\\b${c}\\b[^.;!?\\n]{0,40}\\b(?:have|had|ont)\\s+(?:all|both|tous)\\s+` +
        `(?:also\\s+)?(?:scored|marqu(?:é|e))\\b`, 'i'
      );
      const m = text.match(direct) || text.match(coord);
      if (m) {
        errors.push(`[${name}] "${m[0].slice(0, 80)}" — appears as scoring subject but D.individual shows 0 goals.`);
        break;
      }
    }
  }
  if (errors.length > 0) {
    console.error('\n========== BUILD ABORTED: prose fact-check failures ==========');
    for (const e of errors) console.error('  ' + e);
    console.error('\nSource of truth: D.individual goals from NHL.com PBP.\n');
    process.exit(7);
  }
  console.log(`prose fact-check passed (${rosterNames.size} roster names; ${scorers.size} confirmed scorers)`);
}

// ---------- Doc helpers ----------
const r = (text, opts = {}) => new TextRun({ text, font: 'Arial', size: 20, ...opts });
const para = (text, opts = {}) => new Paragraph({ spacing: { after: 100 }, children: [r(text, opts)] });
const h1 = (txt) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: txt, font: 'Arial', size: 30, bold: true, color: BRAND.navy })] });
const h2 = (txt) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: txt, font: 'Arial', size: 24, bold: true, color: BRAND.navyLight })] });

function md(text) {
  const out = [];
  const re = /\*\*(.+?)\*\*/g;
  let last = 0; let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(r(text.slice(last, m.index)));
    out.push(r(m[1], { bold: true }));
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(r(text.slice(last)));
  return out;
}

function calloutBox(title, bodies, fill) {
  return new Table({
    columnWidths: [9360],
    margins: { top: 140, bottom: 140, left: 220, right: 220 },
    rows: [new TableRow({ children: [new TableCell({
      borders: cellBorders,
      width: { size: 9360, type: WidthType.DXA },
      shading: { fill, type: ShadingType.CLEAR },
      children: [
        ...(title ? [new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: title, bold: true, size: 22, font: 'Arial', color: BRAND.ink })] })] : []),
        ...bodies,
      ],
    })] })],
  });
}

function dataTable(headers, rows, widths) {
  const w = widths || Array(headers.length).fill(Math.floor(9360 / headers.length));
  const header = (text, i) => new TableCell({
    borders: cellBorders,
    width: { size: w[i], type: WidthType.DXA },
    shading: { fill: BRAND.navy, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: String(text), bold: true, size: 18, font: 'Arial', color: 'FFFFFF' })] })],
  });
  const body = (text, i, opts) => new TableCell({
    borders: cellBorders,
    width: { size: w[i], type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    shading: opts && opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({ alignment: AlignmentType.LEFT,
      children: typeof text === 'object' && text.runs ? text.runs : [new TextRun({ text: String(text), size: 18, font: 'Arial' })] })],
  });
  return new Table({
    columnWidths: w, margins: { top: 70, bottom: 70, left: 120, right: 120 },
    rows: [
      new TableRow({ tableHeader: true, children: headers.map(header) }),
      ...rows.map(rw => {
        const opts = (rw && rw._opts) || {};
        const cells = (rw && rw.cells) || rw;
        return new TableRow({ children: cells.map((c, i) => body(c, i, opts)) });
      }),
    ],
  });
}

// ---------- Translations ----------
const T = {
  en: {
    brand: 'LEMIEUX · Habs playoff rankings',
    title: 'Habs playoff player rankings',
    subtitle: 'Three games of advanced analytics — who is moving the needle for Montreal',
    date: `Published 2026-04-26 · ${D.meta.series} · After ${D.meta.games_played} games`,
    tldr: 'Top-line read',
    tldr_bullets: () => {
      const t3 = D.rank_5v5.slice(0, 3);
      const b3 = D.rank_5v5.slice(-3).reverse();
      const top_scorer = D.individual[0];
      return [
        `**Top three by 5v5 isolated net impact: ${t3.map(x => x.name.split(' ').slice(-1)[0]).join(', ')}.** Bolduc leads at +${t3[0].net.toFixed(2)} xG/60 net (xGF/60 ${fmt(t3[0].iso_xgf60)}, xGA/60 ${fmt(t3[0].iso_xga60)}); Xhekaj second at +${t3[1].net.toFixed(2)}; Struble third at +${t3[2].net.toFixed(2)}. None of the three were on MTL's first PP unit; all are 4th-line forwards or third-pair defensemen by deployment. The depth tier is doing the underlying work.`,
        `**Bottom three by 5v5 net: ${b3.map(x => x.name.split(' ').slice(-1)[0]).join(', ')}.** Newhook is the worst at ${b3[0].net.toFixed(2)} (heavily negative xGF/60 *and* positive xGA/60); Guhle and Matheson — the two defensemen carrying the heaviest minutes after Hutson — are both underwater at high TOI. Hutson sits 4th-from-bottom at ${D.rank_5v5[D.rank_5v5.length-4].net.toFixed(2)} despite his goals — his 59 minutes carry the team's most defensive exposure.`,
        `**Top three by points: ${D.individual.slice(0,3).map(p => `${p.name.split(' ').slice(-1)[0]} (${p.g}G ${p.a}A)`).join(', ')}.** Three players tied at 3 points each, but the breakdown matters — Slafkovský is all goals (3G/0A), Hutson is 2G/1A, Caufield is 0G/3A. Suzuki is also at 3 points (0G/3A); the captain is creating without finishing.`,
        `**Sample size disclosure:** every iso-impact number here is built on 15-60 minutes of 5v5 time per player. CIs are wide; rankings will reshuffle in single games. Treat the directions, not the magnitudes, as informative.`,
      ];
    },
    methodology_title: 'How to read this',
    methodology: [
      '**Iso-impact** = on-ice rate minus team-without-player rate. iso_xGF/60 is offensive (higher is better); iso_xGA/60 is defensive (lower is better — negative is good). Net = iso_xGF/60 − iso_xGA/60.',
      '**Sample**: 3 playoff games. Per-player 5v5 TOI ranges from 15 to 60 minutes. Tiny by any standard. Iso-impact rates are stable directionally over this window but noisy in magnitude.',
      '**Source data**: NST 2025-26 playoff totals (5v5 / 5v4) and NHL.com play-by-play (individual goals + assists). Goalie SV% computed directly from PBP shot/goal events.',
    ],
    h_5v5: '1. Five-on-five — full ranking',
    h_5v5_intro: 'All MTL skaters with at least 15 minutes of 5v5 time. Sorted by net iso impact (descending). Green rows = positive net; red rows = negative.',
    h_5v4: '2. Power play (5v4) — iso-offense ranking',
    h_5v4_intro: 'iso_xGF/60 only at 5v4 (defense isn\'t the question on the power play). Note: PP samples per skater are 5–20 minutes — these numbers swing wildly with one or two extra chances. Use as a deployment readout, not a verdict on PP1 vs PP2 effectiveness.',
    h_indiv: '3. Individual production',
    h_indiv_intro: 'Goals, primary assists, secondary assists, shots on goal — all situations, derived directly from NHL.com play-by-play scorer / assist credits.',
    h_progression: '4. Compared to the regular season',
    h_progression_intro: 'For each player with ≥ 200 regular-season 5v5 minutes and ≥ 15 playoff minutes, change in net iso impact (playoff minus regular). Up-movers exceeding their season standard; down-movers below it.',
    h_goalie: '5. Goalies',
    h_goalie_intro: 'Dobeš has played all three games. Save percentage is implied (1 − GA/SF) on shots faced from the play-by-play.',
    h_cant: '6. What the data can\'t tell us yet',
    cant: [
      'Whether the depth-led 5v5 production is signal or sequencing — it\'s held three games but could just be the schedule of opponent matchups.',
      'How much of the stars\' iso regression is matchup-driven (Cooper sending top-line minutes against them) vs. structural drift.',
      'Whether the PP1 numbers reflect repeatable chance creation or a couple of hot looks per game. PP samples are tiny.',
      'Goalie comparison vs. Vasilevskiy: cumulative SV% across the series is essentially identical (both around .89), but per-game variance is large. Single-game contests will reshape this view fast.',
    ],
    h_sources: '7. Sources',
    sources: [
      ['Natural Stat Trick — 25-26 NHL playoff team and skater totals', 'https://www.naturalstattrick.com/'],
      ['NHL.com play-by-play API (per-game events, assist credits, shot detail)', 'https://api-web.nhle.com/v1/gamecenter/'],
      ['Lemieux framework — analyzer at examples/habs_round1_2026/playoff_rankings.py', 'https://github.com/lemieuxAI/framework'],
    ],
    footer: 'Lemieux · open-source hockey analytics · github.com/lemieuxAI/framework',
    page: 'Page',
    th_p: 'Player', th_pos: 'Pos', th_gp: 'GP', th_toi: 'TOI',
    th_xgf60: 'iso xGF/60', th_xga60: 'iso xGA/60', th_net: 'Net',
    th_g: 'G', th_a1: 'A1', th_a2: 'A2', th_pts: 'Pts', th_sog: 'SOG',
    th_reg: 'Reg net', th_plf: 'Playoff net', th_delta: 'Δ',
  },
  fr: {
    brand: 'LEMIEUX · Classement séries CH',
    title: 'Classement des joueurs du CH — séries 2026',
    subtitle: 'Trois matchs de statistiques avancées — qui fait bouger l\'aiguille à Montréal',
    date: `Publié 2026-04-26 · ${D.meta.series} · Après ${D.meta.games_played} matchs`,
    tldr: 'L\'essentiel',
    tldr_bullets: () => {
      const t3 = D.rank_5v5.slice(0, 3);
      const b3 = D.rank_5v5.slice(-3).reverse();
      return [
        `**Trois meilleurs en impact net isolé à 5 c. 5 : ${t3.map(x => x.name.split(' ').slice(-1)[0]).join(', ')}.** Bolduc en tête à +${t3[0].net.toFixed(2).replace('.', ',')} xG/60 net (xGF/60 ${fmt(t3[0].iso_xgf60, 2, 'fr')}, xGA/60 ${fmt(t3[0].iso_xga60, 2, 'fr')}); Xhekaj deuxième à +${t3[1].net.toFixed(2).replace('.', ',')}; Struble troisième à +${t3[2].net.toFixed(2).replace('.', ',')}. Aucun des trois n'est sur la première unité d'avantage numérique; tous sont quatrièmes attaquants ou troisièmes défenseurs par déploiement. La profondeur fait le travail sous-jacent.`,
        `**Trois pires en impact net : ${b3.map(x => x.name.split(' ').slice(-1)[0]).join(', ')}.** Newhook est le plus négatif à ${b3[0].net.toFixed(2).replace('.', ',')} (xGF/60 fortement négatif *et* xGA/60 positif); Guhle et Matheson — les deux défenseurs avec les plus grosses minutes après Hutson — sont sous l'eau à temps de glace élevé. Hutson est 4e en partant du bas à ${D.rank_5v5[D.rank_5v5.length-4].net.toFixed(2).replace('.', ',')} malgré ses buts — ses 59 minutes lui donnent l'exposition défensive la plus lourde de l'équipe.`,
        `**Trois meilleurs au pointage : ${D.individual.slice(0,3).map(p => `${p.name.split(' ').slice(-1)[0]} (${p.g}B ${p.a}P)`).join(', ')}.** Trois joueurs à égalité avec 3 points, mais la décomposition compte — Slafkovský n'a que des buts (3B/0A), Hutson 2B/1A, Caufield 0B/3A. Suzuki est aussi à 3 points (0B/3A); le capitaine crée sans finir.`,
        `**Avis sur la taille d'échantillon :** chaque chiffre d'impact isolé ici repose sur 15 à 60 minutes de 5 c. 5 par joueur. Les intervalles de confiance sont larges; les classements peuvent basculer en un seul match. Lisez les directions, pas les amplitudes.`,
      ];
    },
    methodology_title: 'Comment lire ce rapport',
    methodology: [
      '**Impact isolé** = taux sur la glace moins taux de l\'équipe sans le joueur. iso_xGF/60 = offensive (haut = mieux); iso_xGA/60 = défensive (bas = mieux — négatif est bon). Net = iso_xGF/60 − iso_xGA/60.',
      '**Échantillon** : 3 matchs des séries. Le TG à 5 c. 5 par joueur va de 15 à 60 minutes. Petit selon n\'importe quel critère. Les taux d\'impact isolé sont stables directionnellement, bruyants en amplitude.',
      '**Sources** : totaux NST 25-26 séries (5 c. 5 / 5 c. 4) et API jeu par jeu de LNH.com (buts et passes individuels). Le pourcentage d\'arrêts du gardien est calculé directement à partir des événements PBP.',
    ],
    h_5v5: '1. À 5 c. 5 — classement complet',
    h_5v5_intro: 'Tous les patineurs du CH avec au moins 15 minutes à 5 c. 5. Triés par impact net isolé (décroissant). Lignes vertes = net positif; rouges = négatif.',
    h_5v4: '2. Avantage numérique (5 c. 4) — classement offensif',
    h_5v4_intro: 'iso_xGF/60 seulement à 5 c. 4 (la défense n\'est pas la question en avantage numérique). Note : les échantillons PP par joueur vont de 5 à 20 minutes — ces chiffres bougent énormément avec une ou deux occasions de plus. À lire comme un portrait de déploiement, pas comme un verdict sur PP1 contre PP2.',
    h_indiv: '3. Production individuelle',
    h_indiv_intro: 'Buts, passes principales, passes secondaires, tirs au but — toutes situations, dérivés directement des événements de but et des passes du jeu par jeu LNH.com.',
    h_progression: '4. Comparaison avec la saison régulière',
    h_progression_intro: 'Pour chaque joueur avec ≥ 200 minutes de 5 c. 5 en saison et ≥ 15 minutes en séries, écart d\'impact net isolé (séries moins saison). Progressions positives : au-dessus du standard de saison; négatives : en deçà.',
    h_goalie: '5. Les gardiens',
    h_goalie_intro: 'Dobeš a joué les trois matchs. Le pourcentage d\'arrêts est implicite (1 − BC/TS) à partir des tirs subis dans le jeu par jeu.',
    h_cant: '6. Ce que les chiffres ne disent pas encore',
    cant: [
      'Si la production de la profondeur à 5 c. 5 est signal ou séquençage — elle tient sur trois matchs mais peut être une question de confrontations.',
      'Combien de la régression des vedettes vient des confrontations imposées par Cooper plutôt que d\'une dérive structurelle.',
      'Si les chiffres PP1 reflètent une création répétable ou quelques bonnes chances. Les échantillons PP sont minuscules.',
      'Comparaison gardiens vs. Vasilevskiy : les pourcentages d\'arrêts cumulés sur la série sont presque identiques (les deux autour de ,89), mais la variance par match est grande. Les prochains matchs vont vite remodeler cette vue.',
    ],
    h_sources: '7. Sources',
    sources: [
      ['Natural Stat Trick — totaux d\'équipe et de joueurs séries LNH 25-26', 'https://www.naturalstattrick.com/'],
      ['API jeu par jeu LNH.com (événements, passes, tirs)', 'https://api-web.nhle.com/v1/gamecenter/'],
      ['Cadriciel Lemieux — analyseur à examples/habs_round1_2026/playoff_rankings.py', 'https://github.com/lemieuxAI/framework'],
    ],
    footer: 'Lemieux · analytique de hockey à code source ouvert · github.com/lemieuxAI/framework',
    page: 'Page',
    th_p: 'Joueur', th_pos: 'Pos', th_gp: 'PJ', th_toi: 'TG',
    th_xgf60: 'iso xGF/60', th_xga60: 'iso xGA/60', th_net: 'Net',
    th_g: 'B', th_a1: 'A1', th_a2: 'A2', th_pts: 'Pts', th_sog: 'TC',
    th_reg: 'Net rég', th_plf: 'Net séries', th_delta: 'Δ',
  },
};

// Run prose fact-check on every visible string before any rendering
function collectAllProse() {
  const all = [];
  for (const lang of ['en', 'fr']) {
    const t = T[lang];
    const walk = (o) => {
      if (typeof o === 'string') all.push(o);
      else if (typeof o === 'function') { try { walk(o()); } catch (e) {} }
      else if (Array.isArray(o)) o.forEach(walk);
      else if (o && typeof o === 'object') for (const k of Object.keys(o)) try { walk(o[k]); } catch (e) {}
    };
    walk(t);
  }
  return all;
}
runProseFactCheck(collectAllProse());

// ---------- Section builders ----------
function brandHeader(t) {
  return new Header({ children: [new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 0 },
    children: [
      new TextRun({ text: '◆  ', font: 'Arial', size: 16, color: BRAND.red }),
      new TextRun({ text: t.brand, font: 'Arial', size: 16, bold: true, color: BRAND.navy, characterSpacing: 60 }),
    ] })] });
}
function brandFooter(t) {
  return new Footer({ children: [new Paragraph({ alignment: AlignmentType.LEFT,
    children: [
      new TextRun({ text: t.footer + '   ', font: 'Arial', size: 14, color: BRAND.mute }),
      new TextRun({ text: t.page + ' ', font: 'Arial', size: 14, color: BRAND.mute }),
      new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 14, color: BRAND.mute }),
    ] })] });
}
function titleBlock(t) {
  return [
    new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: t.title, font: 'Arial', size: 44, bold: true, color: BRAND.navy })] }),
    new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: t.subtitle, font: 'Arial', size: 24, italics: true, color: BRAND.navyLight })] }),
    new Paragraph({ spacing: { after: 240 },
      border: { bottom: { color: BRAND.red, space: 4, style: BorderStyle.SINGLE, size: 12 } },
      children: [new TextRun({ text: t.date, font: 'Arial', size: 18, color: BRAND.mute })] }),
  ];
}
function tldrSection(t) {
  return [h2(t.tldr), ...t.tldr_bullets().map(b => new Paragraph({
    numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 }, children: md(b),
  }))];
}
function methodologySection(t) {
  return [h2(t.methodology_title), calloutBox('', t.methodology.map(s => new Paragraph({ spacing: { after: 60 }, children: md(s) })), BRAND.explainer)];
}
function rankingSection5v5(t, lang) {
  const headers = [t.th_p, t.th_pos, t.th_gp, t.th_toi, t.th_xgf60, t.th_xga60, t.th_net];
  const widths = [2400, 600, 500, 900, 1500, 1500, 1960];
  const rows = D.rank_5v5.map(r => ({
    cells: [r.name, r.position, String(r.gp), `${r.toi.toFixed(1)}m`,
      fmt(r.iso_xgf60, 2, lang), fmt(r.iso_xga60, 2, lang), fmt(r.net, 2, lang)],
    _opts: { fill: r.net > 0 ? BRAND.pos : r.net < 0 ? BRAND.neg : BRAND.neutral },
  }));
  return [h1(t.h_5v5), para(t.h_5v5_intro, { italics: true, color: BRAND.mute }), dataTable(headers, rows, widths)];
}
function rankingSection5v4(t, lang) {
  const headers = [t.th_p, t.th_pos, t.th_toi, t.th_xgf60];
  const widths = [3500, 800, 1500, 3560];
  const rows = D.rank_5v4.slice(0, 12).map(r => ({
    cells: [r.name, r.position, `${r.toi.toFixed(1)}m`, fmt(r.iso_xgf60, 2, lang)],
    _opts: { fill: r.iso_xgf60 > 0 ? BRAND.pos : BRAND.neg },
  }));
  return [h1(t.h_5v4), para(t.h_5v4_intro, { italics: true, color: BRAND.mute }), dataTable(headers, rows, widths)];
}
function indivSection(t) {
  const headers = [t.th_p, t.th_g, t.th_a1, t.th_a2, t.th_pts, t.th_sog];
  const widths = [3700, 800, 800, 800, 1000, 2260];
  const rows = D.individual.slice(0, 14).map((p, i) => ({
    cells: [p.name, String(p.g), String(p.a1), String(p.a2), String(p.points), String(p.sog)],
    _opts: { fill: i < 3 ? BRAND.pos : undefined },
  }));
  return [h1(t.h_indiv), para(t.h_indiv_intro, { italics: true, color: BRAND.mute }), dataTable(headers, rows, widths)];
}
function progressionSection(t, lang) {
  const headers = [t.th_p, t.th_pos, 'TOI', t.th_reg, t.th_plf, t.th_delta];
  const widths = [2700, 600, 1100, 1500, 1500, 1960];
  const rows = D.progression.map((row, i) => ({
    cells: [row.name, row.position, `${row.toi_r.toFixed(0)} / ${row.toi_p.toFixed(0)}`,
      fmt(row.net_r, 2, lang), fmt(row.net_p, 2, lang), fmt(row.delta, 2, lang)],
    _opts: { fill: row.delta > 0 ? BRAND.pos : row.delta < 0 ? BRAND.neg : BRAND.neutral },
  }));
  return [h1(t.h_progression), para(t.h_progression_intro, { italics: true, color: BRAND.mute }), dataTable(headers, rows, widths)];
}
function goalieSection(t, lang) {
  const g = D.goalie;
  const sv = lang === 'fr' ? g.sv_pct.toString().replace('.', ',') : g.sv_pct.toString();
  return [
    h1(t.h_goalie), para(t.h_goalie_intro, { italics: true, color: BRAND.mute }),
    dataTable(
      [t.th_p, lang === 'fr' ? 'Matchs' : 'Games', lang === 'fr' ? 'TS' : 'SF',
       lang === 'fr' ? 'BA' : 'GA', lang === 'fr' ? '% arrêts' : 'SV%'],
      [[g.name, String(g.games), String(g.shots_faced), String(g.goals_against), sv]],
      [3000, 1300, 1700, 1700, 1660]
    ),
  ];
}
function cantSection(t) {
  return [h1(t.h_cant), ...t.cant.map(b => new Paragraph({
    numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 }, children: md(b),
  }))];
}
function sourcesSection(t) {
  return [
    h1(t.h_sources),
    ...t.sources.map(([txt, url]) => new Paragraph({
      numbering: { reference: 'bullets', level: 0 }, spacing: { after: 60 },
      children: [new ExternalHyperlink({ children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })], link: url })],
    })),
  ];
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
      headers: { default: brandHeader(t) }, footers: { default: brandFooter(t) },
      children: [
        new Paragraph({ children: [] }),
        ...titleBlock(t),
        ...tldrSection(t),
        ...methodologySection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...rankingSection5v5(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...rankingSection5v4(t, lang),
        ...indivSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...progressionSection(t, lang),
        ...goalieSection(t, lang),
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
    const out = path.join(__dirname, `playoff_rankings_2026-04-26_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
