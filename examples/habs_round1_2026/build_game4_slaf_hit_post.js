// Slafkovský pre/post Crozier-hit special analysis (Game 4, P2 17:48).
// Tight EN+FR doc focused on the bucket comparison and the recurring
// game-after-game pattern (G2 Hagel fight + G4 Crozier hit).
//
// Run:
//   node examples/habs_round1_2026/build_game4_slaf_hit_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'game4_slaf_hit.numbers.json'), 'utf8'));
let G3 = null;
try {
  G3 = JSON.parse(fs.readFileSync(path.join(__dirname, 'game3_analysis.numbers.json'), 'utf8'));
} catch (e) { /* optional */ }

// Cross-game context fact-check — abort the build if any claim contradicts
// the canonical game{N}_context.yaml files.
const ctxCheck = require('./game_context_check');
ctxCheck.assertGameClaim({ game: 2, kind: 'fight', period: 2, time: '05:14', contextDir: __dirname });
ctxCheck.assertGameClaim({ game: 4, kind: 'hit', period: 2, time: '17:48', contextDir: __dirname });
ctxCheck.assertScore({ game: 4, expected: 'TBL 3 - MTL 2', contextDir: __dirname });

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70', red: 'A6192E',
  ink: '111111', mute: '666666', rule: 'BFBFBF',
  prefill: 'FFF2CC', postfill: 'F8CBAD',
  highlight: 'DEEAF6',
};

const fmtNum = (n, p = 1) => (n === null || n === undefined) ? '—' : Number(n).toFixed(p);
const fmtFr = (n, p = 1) => fmtNum(n, p).replace('.', ',');

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
  const headerRow = new TableRow({ tableHeader: true,
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
      children: cells.map(c => {
        const isObj = c && typeof c === 'object' && !Array.isArray(c) && 'value' in c;
        const text = isObj ? String(c.value ?? '—') : String(c ?? '—');
        const fill = isObj && c.fill ? c.fill : opts.fill;
        const bold = !!(isObj && c.bold);
        return new TableCell({
          borders: cellBorders,
          shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: [new TextRun({ text, font: 'Arial', size: 18, color: BRAND.ink, bold })] })],
        });
      }),
    });
  });
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, columnWidths: widths, rows: [headerRow, ...bodyRows] });
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

const pre = D.pre, post = D.post, dlt = D.deltas;
const preToiPct = pre.slaf_toi_min / 29.8;   // 29:48 of game elapsed pre-hit
const postToiPct = post.slaf_toi_min / 22.2; // 22:12 game time post-hit

function bucketTable(t, lang) {
  const fmt = lang === 'fr' ? fmtFr : fmtNum;
  const rows = [
    {
      cells: [
        t.row_window,
        { value: pre.period_range, fill: BRAND.prefill },
        { value: post.period_range, fill: BRAND.postfill },
        '—',
      ],
    },
    {
      cells: [
        t.row_toi,
        `${fmt(pre.slaf_toi_min, 2)} (${(preToiPct * 100).toFixed(0)}%)`,
        `${fmt(post.slaf_toi_min, 2)} (${(postToiPct * 100).toFixed(0)}%)`,
        `${fmt(post.slaf_toi_min - pre.slaf_toi_min, 2)} min · ${((postToiPct - preToiPct) * 100).toFixed(1)} pp`,
      ],
    },
    {
      cells: [
        t.row_shifts,
        pre.shifts_count, post.shifts_count, post.shifts_count - pre.shifts_count,
      ],
    },
    {
      cells: [
        t.row_individual,
        `${pre.slaf_goals}G / ${pre.slaf_sog} SOG / ${pre.slaf_missed} missed`,
        `${post.slaf_goals}G / ${post.slaf_sog} SOG / ${post.slaf_missed} missed`,
        `Δ SOG ${post.slaf_sog - pre.slaf_sog}`,
      ],
      _opts: { fill: BRAND.highlight },
    },
    {
      cells: [
        t.row_hits_taken,
        pre.slaf_hits_against, post.slaf_hits_against,
        `+${post.slaf_hits_against - pre.slaf_hits_against}`,
      ],
    },
    {
      cells: [
        t.row_hits_for,
        pre.slaf_hits_for, post.slaf_hits_for,
        `${post.slaf_hits_for - pre.slaf_hits_for}`,
      ],
    },
    {
      cells: [
        t.row_oi_corsi,
        `${pre.mtl_cf_5v5}–${pre.tbl_cf_5v5} (${fmt(pre.mtl_cf_pct_5v5, 1)}%)`,
        `${post.mtl_cf_5v5}–${post.tbl_cf_5v5} (${fmt(post.mtl_cf_pct_5v5, 1)}%)`,
        `${dlt.mtl_cf_pct_5v5_pp >= 0 ? '+' : ''}${fmt(dlt.mtl_cf_pct_5v5_pp, 1)} pp`,
      ],
      _opts: { fill: BRAND.highlight },
    },
    {
      cells: [
        t.row_oi_hdcf,
        `${pre.mtl_hdcf_5v5}–${pre.tbl_hdcf_5v5} (${fmt(pre.mtl_hdcf_pct_5v5, 1)}%)`,
        `${post.mtl_hdcf_5v5}–${post.tbl_hdcf_5v5} (${fmt(post.mtl_hdcf_pct_5v5, 1)}%)`,
        `${dlt.mtl_hdcf_pct_5v5_pp >= 0 ? '+' : ''}${fmt(dlt.mtl_hdcf_pct_5v5_pp, 1)} pp`,
      ],
    },
    {
      cells: [
        t.row_oi_goals,
        `MTL ${pre.mtl_goals_oi} – ${pre.tbl_goals_oi} TBL`,
        `MTL ${post.mtl_goals_oi} – ${post.tbl_goals_oi} TBL`,
        '—',
      ],
    },
  ];
  return [
    h2(t.bucket_table_title),
    para(t.bucket_table_intro, { italics: true }),
    dataTable([t.th_metric, t.th_pre, t.th_post, t.th_delta], rows, [3000, 2700, 2700, 1600]),
  ];
}

function game3CompareTable(t, lang) {
  if (!G3 || !G3.slaf_fight_buckets) return [];
  const sb = G3.slaf_fight_buckets;
  const fmt = lang === 'fr' ? fmtFr : fmtNum;
  const rows = [
    {
      cells: [
        t.row_g3_event,
        '21 avr. 2026 · M2, P2 5:14 (Hagel-fight)',
        '26 avr. 2026 · M4, P2 17:48 (Crozier-hit)',
      ],
    },
    {
      cells: [
        t.row_g3_window,
        `pre ${fmt(sb.pre.toi_min, 1)} min · post ${fmt(sb.post.toi_min, 1)} min`,
        `pre ${fmt(pre.slaf_toi_min, 1)} min · post ${fmt(post.slaf_toi_min, 1)} min`,
      ],
    },
    {
      cells: [
        t.row_g3_sog,
        `pre 8 · post 2`,
        `pre ${pre.slaf_sog} · post ${post.slaf_sog}`,
      ],
      _opts: { fill: BRAND.highlight },
    },
    {
      cells: [
        t.row_g3_goals,
        `pre 3 · post 0`,
        `pre ${pre.slaf_goals} · post ${post.slaf_goals}`,
      ],
    },
    {
      cells: [
        t.row_g3_pattern,
        t.row_g3_pattern_g3,
        t.row_g3_pattern_g4,
      ],
    },
  ];
  return [
    h2(t.g3_compare_title),
    para(t.g3_compare_intro, { italics: true }),
    dataTable([t.th_metric, 'Game 2 (Hagel fight)', 'Game 4 (Crozier hit)'], rows, [3000, 3500, 3500]),
  ];
}

const T = {
  en: {
    title: 'Slafkovský pre/post Crozier-hit — Game 4 special',
    subtitle: 'Hit at P2 17:48 (2:12 remaining), neutral zone · TBL 3, MTL 2 (final)',
    summary_title: 'The hit and what happened next',
    summary: [
      `**The event**: At 2:12 remaining in P2, **Max Crozier** — Tampa's lineup-change-in for Game 4, the very defenseman the swap engine projected as a marginal upgrade — finished a heavy hit on Juraj Slafkovský in the neutral zone. (PBP timestamp: P2 17:48, hitter id 8481719, hittee id 8483515.)`,
      `**The hook**: this is a recurring pattern from earlier in the series. **Game 2** (TBL 3, MTL 2 OT) was the Hagel-Slafkovský fight at P2 5:14; Game 4 is the Crozier hit. Two contact events, two different TBL skaters, same shape after — Slafkovský's offense disappears. (Source: examples/habs_round1_2026/game2_context.yaml.)`,
      `**The honest caveat first**: pre-hit Slafkovský was already underwater on 5v5 territorial impact. He was on the ice for a 3–10 Corsi and 0–5 HDCF differential before the hit. Post-hit Corsi flipped to 4–2 (66.7% MTL) on a 4.67-min sample — too small to read as a structural shift, and the goals on-ice tally went from MTL 1 / TBL 0 (he was on for the Bolduc goal) to MTL 0 / TBL 1.`,
    ],
    bucket_table_title: 'Game 4 — pre vs post the Crozier hit',
    bucket_table_intro: 'Bucket boundary: P2 17:48. PRE = P1 + P2 up to that moment. POST = P2 from 17:48 + P3.',
    th_metric: 'Metric', th_pre: 'PRE-hit', th_post: 'POST-hit', th_delta: 'Δ',
    row_window: 'Window',
    row_toi: 'Slafkovský TOI (min, % of game time in window)',
    row_shifts: 'Slafkovský shifts',
    row_individual: 'Individual offense (G / SOG / missed)',
    row_hits_taken: 'Hits taken by Slafkovský',
    row_hits_for: 'Hits delivered by Slafkovský',
    row_oi_corsi: '5v5 Corsi while on-ice (MTL–TBL, MTL%)',
    row_oi_hdcf: '5v5 HDCF while on-ice (MTL–TBL, MTL%)',
    row_oi_goals: 'Goals on-ice (any strength)',
    interpretation_title: 'How to read it',
    interpretation: [
      `**TOI dropped sharply.** Pre-hit he played 11.55 min over 29:48 of game time (38.7% of available time). Post-hit, 4.67 min over 22:12 (21.0%). MTL was trailing in P3 — and Slaf still got fewer minutes per minute available. That's a coaching choice, not a chance pattern.`,
      `**Individual stat line vanishes post-hit.** 0 SOG, 0 missed, 0 hits delivered, 0 takeaways/giveaways. Two more hits taken. The shape mirrors the Hagel-fight pattern from **Game 2** at P2 5:14 (across the G2-post + G3 buckets: 8 → 2 SOG, 3 → 0 goals).`,
      `**Possession with him on improved post-hit, but on a fragile sample.** 5v5 Corsi flipped from 23.1% (3-10) to 66.7% (4-2). HDCF stayed at zero MTL high-danger looks both buckets. Read that as: when he's on, MTL still doesn't generate quality from his line — only volume changed, on a 5-min sample.`,
      `**The Crozier connection**: Crozier was Tampa's only lineup change for this game. The swap engine projected his presence at +0.11 net xG/game with the 80% CI straddling zero. He delivered a hit that contributed to MTL's most dangerous winger going invisible for a half-period. That's an effect the iso-impact framework cannot price.`,
    ],
    g3_compare_title: 'Game 2 (Hagel fight) vs Game 4 (Crozier hit) — the recurring pattern',
    g3_compare_intro: 'Two games, two heavy contact events on Slafkovský, same shape after. Source files: game2_context.yaml + game4_context.yaml.',
    row_g3_event: 'Event',
    row_g3_window: 'Bucket TOI',
    row_g3_sog: 'Slafkovský SOG (pre · post)',
    row_g3_goals: 'Slafkovský goals (pre · post)',
    row_g3_pattern: 'Pattern',
    row_g3_pattern_g3: 'Heavy hit / fight → individual offense disappears',
    row_g3_pattern_g4: 'Same pattern, different defenseman',
    pattern_title: 'What the framework can\'t tell us — and what to ask the broadcast',
    pattern: [
      `**Is he hurt?** The data shows TOI loss + offensive shutdown. The data does NOT diagnose injury. Watch St-Louis\'s post-game presser; track Game-5 morning skate participation.`,
      `**Is Tampa specifically targeting him?** Two games in a row a different TBL skater put a marquee hit on Slafkovský. That\'s not a tactic the framework can validate from one series — but a deployment-pattern check on a Game 5 sample, plus film review, would close the loop.`,
      `**Is the pattern an artifact of how the buckets cut?** Both games\' "post" buckets include the third period, where teams trail / lead and play differently. We\'re not score-effect-controlling. The pattern survives the caveat directionally, not necessarily mechanically.`,
    ],
    method_title: 'Method',
    method: [
      'Source: NHL.com play-by-play + post-game shift chart (complete for P1, P2, P3).',
      'On-ice 5v5 events use NHL.com situationCode = 1551. HDCF proxy: shot from ≤22 ft of net.',
      'TOI percentages computed against elapsed game time in each window (pre = 29:48, post = 22:12).',
      'No xG model applied — NST publishes a few hours post-game; this brief uses Corsi + HDCF count as the available rigor.',
    ],
    sources_title: 'Sources',
    sources: [
      ['NHL.com — Game 4 play-by-play', `https://api-web.nhle.com/v1/gamecenter/2025030124/play-by-play`],
      ['NHL.com — Game 4 shift chart', `https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=2025030124`],
      ['Game 2 context (Hagel-Slafkovský fight, P2 5:14)', '(see examples/habs_round1_2026/game2_context.yaml)'],
      ['Game 4 context', '(see examples/habs_round1_2026/game4_context.yaml)'],
      ['Game 2 / G3 fight bucket analysis (built off the G2 fight)', '(see game3_analysis.numbers.json -> slaf_fight_buckets)'],
    ],
    footer_left: 'Lemieux · Slafkovský pre/post-hit · Game 4',
    footer_right: 'Page',
  },
  fr: {
    title: 'Slafkovský avant/après la mise en échec de Crozier — spécial Match 4',
    subtitle: 'Mise en échec à 17:48 de la P2 (2:12 à faire), zone neutre · TBL 3, CH 2 (final)',
    summary_title: 'L\'événement et ce qui suit',
    summary: [
      `**L\'événement** : à 2:12 à faire en P2, **Max Crozier** — le défenseur que Tampa a inséré pour le Match 4, celui-là même que le moteur d\'échange projetait comme une amélioration marginale — applique une lourde mise en échec à Juraj Slafkovský dans la zone neutre. (Horodatage JPJ : P2 17:48, hitter id 8481719, hittee id 8483515.)`,
      `**L\'angle** : un patron récurrent depuis le début de la série. Le **Match 2** (TBL 3, CH 2 PR) abritait le combat Hagel-Slafkovský à 5:14 de la P2; le M4, c\'est la mise en échec de Crozier. Deux événements de contact, deux patineurs TBL différents, même forme ensuite — l\'offensive de Slafkovský disparaît. (Source : examples/habs_round1_2026/game2_context.yaml.)`,
      `**La mise en garde honnête d\'abord** : avant la mise en échec, Slafkovský était déjà en déficit territorial à 5 c. 5. Il était sur la glace pour un 3–10 au Corsi et 0–5 aux CHD avant le coup. Après, le Corsi a basculé à 4–2 (66,7 % CH) sur un échantillon de 4,67 minutes — trop petit pour y lire un déplacement structurel; et les buts sur la glace sont passés de CH 1 / TBL 0 (il était sur la glace pour le but de Bolduc) à CH 0 / TBL 1.`,
    ],
    bucket_table_title: 'M4 — avant vs après la mise en échec de Crozier',
    bucket_table_intro: 'Frontière : P2 17:48. AVANT = P1 + P2 jusqu\'à ce moment. APRÈS = P2 à partir de 17:48 + P3.',
    th_metric: 'Mesure', th_pre: 'AVANT', th_post: 'APRÈS', th_delta: 'Δ',
    row_window: 'Fenêtre',
    row_toi: 'TG Slafkovský (min, % du temps de match dans la fenêtre)',
    row_shifts: 'Présences Slafkovský',
    row_individual: 'Production individuelle (B / TB / ratés)',
    row_hits_taken: 'Mises en échec subies par Slafkovský',
    row_hits_for: 'Mises en échec données par Slafkovský',
    row_oi_corsi: 'Corsi 5 c. 5 sur la glace (CH–TBL, % CH)',
    row_oi_hdcf: 'CHD 5 c. 5 sur la glace (CH–TBL, % CH)',
    row_oi_goals: 'Buts sur la glace (toutes forces)',
    interpretation_title: 'Comment le lire',
    interpretation: [
      `**Le TG chute fortement.** Avant la mise en échec, il a joué 11,55 min sur 29:48 de temps écoulé (38,7 % du temps disponible). Après : 4,67 min sur 22:12 (21,0 %). Le CH tirait de l\'arrière en P3 — et Slaf jouait quand même proportionnellement moins. C\'est un choix de banc, pas un effet du hasard.`,
      `**La fiche individuelle disparaît.** 0 TB, 0 raté, 0 mise en échec donnée, 0 récupération/revirement. Deux mises en échec subies de plus. Le patron est le même qu\'au **Match 2** après le combat de Hagel à 5:14 de la P2 (sur les tranches G2-post + G3 : 8 → 2 TB, 3 → 0 buts).`,
      `**La possession avec lui sur la glace s\'améliore après, mais sur un échantillon fragile.** Corsi 5 c. 5 passe de 23,1 % (3-10) à 66,7 % (4-2). Le CHD reste à zéro chance à haut danger pour le CH dans les deux tranches. Lecture : quand il est sur la glace, le CH ne génère toujours pas de qualité avec son trio — seul le volume a changé, sur 5 min.`,
      `**Le lien avec Crozier** : Crozier était le seul changement de Tampa pour ce match. Le moteur d\'échange projetait sa présence à +0,11 BA net/match avec un IC à 80 % chevauchant zéro. Il livre une mise en échec qui contribue à faire disparaître l\'ailier le plus dangereux du CH pendant une demi-période. C\'est un effet que le cadre d\'impact isolé ne sait pas chiffrer.`,
    ],
    g3_compare_title: 'M2 (combat Hagel) c. M4 (mise en échec Crozier) — le patron récurrent',
    g3_compare_intro: 'Deux matchs, deux événements de contact lourd sur Slafkovský, même forme après. Sources : game2_context.yaml + game4_context.yaml.',
    row_g3_event: 'Événement',
    row_g3_window: 'TG des tranches',
    row_g3_sog: 'TB Slafkovský (avant · après)',
    row_g3_goals: 'Buts Slafkovský (avant · après)',
    row_g3_pattern: 'Patron',
    row_g3_pattern_g3: 'Coup lourd / combat → la production individuelle disparaît',
    row_g3_pattern_g4: 'Même patron, défenseur différent',
    pattern_title: 'Ce que le cadre ne peut pas dire — et quoi demander à la diffusion',
    pattern: [
      `**Est-il blessé?** Les données montrent une perte de TG + un arrêt offensif. Les données NE diagnostiquent PAS une blessure. Surveiller le point de presse de St-Louis; suivre la participation au patinage matinal du M5.`,
      `**Tampa le cible-t-il spécifiquement?** Deux matchs d\'affilée, un patineur différent du TBL livre un coup marquant à Slafkovský. Ce n\'est pas une tactique que le cadre peut valider sur une seule série — mais une vérification du patron de déploiement sur le M5 + révision vidéo fermerait la boucle.`,
      `**Le patron est-il un artefact de la coupure des tranches?** Dans les deux matchs, la tranche « après » inclut la 3ᵉ période, où les équipes mènent / tirent de l\'arrière et jouent différemment. On ne contrôle pas pour les effets de marque. Le patron survit à la mise en garde directionnellement, pas mécaniquement.`,
    ],
    method_title: 'Méthode',
    method: [
      'Source : JPJ et tableau des présences post-match LNH.com (complets P1, P2, P3).',
      'Événements 5 c. 5 : situationCode = 1551. CHD : tirs à ≤ 22 pi du but.',
      'Pourcentages de TG calculés contre le temps écoulé du match dans chaque fenêtre (avant = 29:48, après = 22:12).',
      'Aucun modèle xG appliqué — NST publie quelques heures après le match; ce dossier utilise Corsi + comptage CHD comme rigueur disponible.',
    ],
    sources_title: 'Sources',
    sources: [
      ['LNH.com — JPJ Match 4', `https://api-web.nhle.com/v1/gamecenter/2025030124/play-by-play`],
      ['LNH.com — Présences Match 4', `https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=2025030124`],
      ['Contexte Match 2 (combat Hagel-Slafkovský, P2 5:14)', '(voir examples/habs_round1_2026/game2_context.yaml)'],
      ['Contexte Match 4', '(voir examples/habs_round1_2026/game4_context.yaml)'],
      ['Analyse pré/post combat (basée sur le combat du M2)', '(voir game3_analysis.numbers.json -> slaf_fight_buckets)'],
    ],
    footer_left: 'Lemieux · Slafkovský pré/post-mise en échec · Match 4',
    footer_right: 'Page',
  },
};

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
        h1(t.summary_title), ...bullets(t.summary),
        h1(t.bucket_table_title.replace('Game 4 — ', '').replace('M4 — ', '')),
        ...bucketTable(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...game3CompareTable(t, lang),
        h1(t.interpretation_title), ...bullets(t.interpretation),
        h1(t.pattern_title), ...bullets(t.pattern),
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
    const primary = path.join(__dirname, `game4_slaf_hit_2026-04-26_${lang.toUpperCase()}.docx`);
    let out = primary;
    try {
      fs.writeFileSync(primary, buf);
    } catch (e) {
      if (e.code === 'EBUSY' || e.code === 'EACCES') {
        out = path.join(__dirname, `game4_slaf_hit_2026-04-26_${lang.toUpperCase()}_v2.docx`);
        fs.writeFileSync(out, buf);
      } else throw e;
    }
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
