// Special report: how do the 16 playoff teams' L1 trios stack up?
// Inputs:
//   - first_lines_compare.numbers.json (analyzer output)
// Run:
//   node examples/playoffs_2026/build_first_lines_compare_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'first_lines_compare.numbers.json'), 'utf8'));

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

const teams = D.teams;
const summary = D.league_summary;
const tags = D.tag_summary_top10;

function fillForIso(iso) {
  if (iso > 0.30) return BRAND.pos;
  if (iso > 0.10) return null;
  if (iso > -0.05) return BRAND.neu;
  return BRAND.neg;
}

const T = {
  en: {
    title: 'Special report — How does each playoff team\'s top line stack up?',
    subtitle: '2026 NHL Round 1 · 16 teams · 5v5 isolated impact compared',
    banner: ('A Lemieux framework demo. Pooled NST iso baselines, press-confirmed L1 trios, ' +
             'archetype tags from the GenAI scouting layer.'),
    tldr_title: 'Headlines',
    tldr: [
      `**Spread is bigger than the league average.** From Edmonton's Hyman–McDavid–Podkolzin at **${fmt(summary.best_trio_iso_net60, 3)}** iso net60 down to Philadelphia's Cates–Zegras–Konecny at **${fmt(summary.worst_trio_iso_net60, 3)}**, the gap between best and worst L1 in this playoff field is **${fmt(summary.spread, 2)} xG/60** — almost a full expected-goal-per-60 of variance just at the top-line level.`,
      `**Two of the top three top lines face each other in our showcase series.** Edmonton (#1, +0.72) is on a different planet, but Tampa Bay's Hagel–Point–Kucherov (#2, +0.46) and Montreal's Slafkovský–Suzuki–Caufield (#3, +0.45) are within 0.01 xG/60 of each other in pooled iso terms. The MTL @ TBL Round 1 series isn't being decided by L1 talent disparity — it's being decided by everything else.`,
      `**Crosby's line is below the playoff median.** Rakell–Crosby–Rust (PIT, #13, +0.14) carries strong xGF/60 but bleeds at xGA/60. Same story for Vegas (#12), Dallas (#11). When a star's line is offense-only, the playoff iso tightens; defense-leaky L1s land in the bottom third.`,
    ],

    table_title: 'All 16 playoff L1 trios, ranked',
    table_intro: ('Each team\'s heuristic L1 = top-1 C + top-1 L + top-1 R by 25-26 5v5 TOI. Three teams ' +
                 'have manual press-confirmed overrides where the heuristic diverged from actual deployment ' +
                 '(PIT, MIN, T.B — flagged in the table). Iso is pooled across 24-25 + 25-26 reg + playoff.'),
    th_rank: '#', th_team: 'Team', th_line: 'L1 trio (L–C–R)',
    th_xgf: 'iso xGF/60', th_xga: 'iso xGA/60', th_net: 'iso net60',
    th_toi: '25-26 5v5 TOI (avg)',

    top3_title: 'The top three',
    top3_intro: 'What separates the elite L1s from the rest of the field.',
    bottom3_title: 'The bottom three',
    bottom3_intro: 'Where the L1 is a liability — even on a playoff team.',
    archetypes_title: 'Archetypes across the 48 playoff L1 forwards',
    archetypes_intro: ('Tag frequencies pulled from our GenAI scouting layer (Sonnet-extracted, ' +
                      'with verbatim source quotes per tag). What does a "playoff first-line forward" ' +
                      'look like in the descriptive vocabulary? Top hits below.'),
    th_tag: 'Archetype tag', th_count: 'Forwards carrying it',

    method_title: 'Method',
    method: [
      'Universe: 16 NHL teams in the 2026 Round 1 playoffs (8 East + 8 West).',
      '"Most typical L1" heuristic: top-1 C + top-1 L + top-1 R by 25-26 5v5 TOI (regular season + playoffs combined). Approximates canonical L1 by deployment without play-by-play shift-overlap data.',
      'Three press-confirmed overrides (PIT, MIN, T.B) where the heuristic mis-stitched the trio because of injury-driven TOI patterns or mid-season position changes. Sources cited in the table footnotes.',
      'Iso impact: pooled 5v5 on-ice xGF/60 and xGA/60 across the 4-window pool (24-25 reg + playoff, 25-26 reg + playoff). Trio iso = average of the three players. Same math as the Lemieux swap engine.',
      'Archetype tags: extracted by Claude Sonnet 4.5 from public web scouting text via DuckDuckGo search. Each tag carries its verbatim source quote and source URL — provenance enforced by framework rail.',
    ],

    caveats_title: 'Caveats',
    caveats: [
      'Pooled iso averages the trio equally — real chemistry effects (linemate quality, line context) are not isolated.',
      'The heuristic might miss-stitch a trio when a team\'s top-TOI player at one position doesn\'t actually play with the top-TOI player at another. We applied 3 press-confirmed overrides; the other 13 may still mismatch real-world deployment slightly.',
      'Round 1 sample sizes are small — current-series numbers will move significantly. The pooled baseline holds because it spans 4 windows, but in-series swings are not in this report.',
      'No prediction of which playoff team will win. The framework grades L1 quality on iso terms; it doesn\'t forecast outcomes.',
    ],

    sources_title: 'Sources',
    sources: [
      ['Natural Stat Trick — pooled 5v5 oi splits', 'https://www.naturalstattrick.com/'],
      ['Pittsburgh Penguins playoff roster · NHL.com', 'https://www.nhl.com/news/pittsburgh-penguins-2026-stanley-cup-playoff-roster-at-a-glance'],
      ['Daily Faceoff — PIT vs PHI series preview', 'https://www.dailyfaceoff.com/news/2026-stanley-cup-playoffs-penguins-vs-flyers-series-preview-prediction-schedule-crosby-malkin-karlsson-zegras-martone-tocchet'],
      ['Hockey Wilderness — Wild playoff coverage', 'https://hockeywilderness.com/'],
      ['Daily Faceoff — TBL vs MTL series preview', 'https://www.dailyfaceoff.com/'],
      ['Lemieux open-source framework', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · special report · playoff L1 comparison',
    footer_right: 'Page',
  },
  fr: {
    title: 'Rapport spécial — Comment se classent les premiers trios des équipes en séries?',
    subtitle: 'Premier tour LNH 2026 · 16 équipes · impact isolé à 5 c. 5 comparé',
    banner: ('Une démonstration du cadriciel Lemieux. Bases iso NST regroupées, ' +
             'trios L1 confirmés par la presse, étiquettes d\'archétypes via la couche scouting GenAI.'),
    tldr_title: 'Les manchettes',
    tldr: [
      `**L\'écart est plus grand que la moyenne de la ligue.** D\'Hyman–McDavid–Podkolzin d\'Edmonton à **${fmtFr(summary.best_trio_iso_net60, 3)}** d\'iso net60 jusqu\'à Cates–Zegras–Konecny de Philadelphie à **${fmtFr(summary.worst_trio_iso_net60, 3)}**, l\'écart entre le meilleur et le pire premier trio de ce tableau de séries est de **${fmtFr(summary.spread, 2)} BAF/60** — presque un but attendu par 60 minutes de variance au seul niveau du premier trio.`,
      `**Deux des trois meilleurs premiers trios s\'affrontent dans notre série vedette.** Edmonton (n°1, +0,72) est sur une autre planète, mais le Hagel–Point–Kucherov de Tampa (n°2, +0,46) et le Slafkovský–Suzuki–Caufield du Canadien (n°3, +0,45) sont à 0,01 BAF/60 l\'un de l\'autre en termes d\'iso regroupé. La série Tampa-Montréal du premier tour ne se décide pas sur l\'écart de talent au L1 — elle se décide sur tout le reste.`,
      `**Le trio de Crosby est sous la médiane des séries.** Rakell–Crosby–Rust (PIT, n°13, +0,14) génère un fort xGF/60 mais perd au xGA/60. Même histoire à Vegas (n°12), à Dallas (n°11). Quand le trio d\'une vedette ne fait que de l\'offensive, l\'iso en séries se resserre; les L1 qui fuient en défense terminent dans le tiers inférieur.`,
    ],

    table_title: 'Les 16 premiers trios des séries, classés',
    table_intro: ('Le L1 heuristique de chaque équipe = top-1 C + top-1 G + top-1 D par minutes à 5 c. 5 ' +
                 'en 25-26 (saison régulière + séries combinées). Trois équipes ont des corrections ' +
                 'manuelles confirmées par la presse là où l\'heuristique divergeait du déploiement réel ' +
                 '(PIT, MIN, T.B — signalées dans le tableau). L\'iso est regroupé sur 24-25 + 25-26 ' +
                 'saison régulière + séries.'),
    th_rank: 'Rang', th_team: 'Équipe', th_line: 'Trio L1 (G–C–D)',
    th_xgf: 'iso BAF/60', th_xga: 'iso BAC/60', th_net: 'iso net60',
    th_toi: 'TG 5 c. 5 25-26 (moy)',

    top3_title: 'Le top trois',
    top3_intro: 'Ce qui sépare les premiers trios élites du reste du tableau.',
    bottom3_title: 'Le bas trois',
    bottom3_intro: 'Là où le premier trio est un passif — même pour une équipe en séries.',
    archetypes_title: 'Les archétypes parmi les 48 attaquants de premiers trios',
    archetypes_intro: ('Fréquences d\'étiquettes tirées de notre couche scouting GenAI (extraites par ' +
                      'Sonnet, avec citations textuelles des sources par étiquette). À quoi ressemble ' +
                      'un « attaquant de premier trio en séries » dans le vocabulaire descriptif? ' +
                      'Les principaux résultats ci-dessous.'),
    th_tag: 'Étiquette d\'archétype', th_count: 'Attaquants qui la portent',

    method_title: 'Méthode',
    method: [
      'Univers : 16 équipes LNH au premier tour des séries 2026 (8 Est + 8 Ouest).',
      'Heuristique « L1 le plus typique » : top-1 C + top-1 G + top-1 D par TG 5 c. 5 en 25-26 (saison régulière + séries combinées). Approxime le L1 canonique par déploiement sans données de chevauchement de présences au jeu par jeu.',
      'Trois corrections confirmées par la presse (PIT, MIN, T.B) là où l\'heuristique a mal tissé le trio à cause de patrons de TG perturbés par des blessures ou de changements de position en cours de saison. Sources citées dans les notes du tableau.',
      'Impact isolé : xGF/60 et xGA/60 sur la glace à 5 c. 5 regroupés sur le pool de 4 fenêtres (24-25 saison régulière + séries, 25-26 saison régulière + séries). Iso du trio = moyenne des trois joueurs. Même calcul que le moteur d\'échange Lemieux.',
      'Étiquettes d\'archétypes : extraites par Claude Sonnet 4.5 à partir de texte scouting public sur le web via DuckDuckGo. Chaque étiquette porte sa citation textuelle et l\'URL source — provenance imposée par la règle du cadriciel.',
    ],

    caveats_title: 'Mises en garde',
    caveats: [
      'L\'iso regroupé fait la moyenne du trio à parts égales — les vrais effets de chimie (qualité du compagnon de trio, contexte du trio) ne sont pas isolés.',
      'L\'heuristique peut mal tisser un trio quand le joueur d\'une équipe avec le plus de TG à une position ne joue pas vraiment avec celui qui en a le plus à une autre. On a appliqué 3 corrections confirmées par la presse; les 13 autres peuvent encore diverger légèrement du déploiement réel.',
      'Les échantillons du premier tour sont petits — les chiffres de la série en cours bougent significativement. La base regroupée tient parce qu\'elle s\'étend sur 4 fenêtres, mais les oscillations en série ne sont pas dans ce rapport.',
      'Aucune prédiction de l\'équipe gagnante en séries. Le cadriciel évalue la qualité des L1 en termes d\'iso; il ne prédit pas les résultats.',
    ],

    sources_title: 'Sources',
    sources: [
      ['Natural Stat Trick — splits 5 c. 5 sur la glace regroupés', 'https://www.naturalstattrick.com/'],
      ['Composition des Penguins en séries · NHL.com', 'https://www.nhl.com/news/pittsburgh-penguins-2026-stanley-cup-playoff-roster-at-a-glance'],
      ['Daily Faceoff — survol PIT vs PHI', 'https://www.dailyfaceoff.com/news/2026-stanley-cup-playoffs-penguins-vs-flyers-series-preview-prediction-schedule-crosby-malkin-karlsson-zegras-martone-tocchet'],
      ['Hockey Wilderness — couverture Wild en séries', 'https://hockeywilderness.com/'],
      ['Daily Faceoff — survol TBL vs MTL', 'https://www.dailyfaceoff.com/'],
      ['Cadriciel ouvert Lemieux', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · rapport spécial · comparaison L1 en séries',
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

function tldrSection(t) { return [h1(t.tldr_title), ...bulletList(t.tldr)]; }

function tableSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const rows = teams.map((team, i) => {
    const c = team.line.C.name, l = team.line.L.name, r = team.line.R.name;
    const overridden = team.line.L._overridden_from || team.line.C._overridden_from || team.line.R._overridden_from;
    const teamLabel = overridden ? `${team.team_name} *` : team.team_name;
    const lineStr = `${l} – ${c} – ${r}`;
    const fillNet = fillForIso(team.trio_avg_iso_net60);
    return {
      cells: [
        String(i + 1), teamLabel, lineStr,
        fmtN(team.trio_avg_iso_xgf60, 3),
        fmtN(team.trio_avg_iso_xga60, 3),
        fmtN(team.trio_avg_iso_net60, 3),
        team.trio_avg_2526_5v5_toi.toString(),
      ],
      _opts: { fills: [null, null, null, null, null, fillNet, null] },
    };
  });
  return [
    h1(t.table_title), para(t.table_intro, { italics: true }),
    dataTable(
      [t.th_rank, t.th_team, t.th_line, t.th_xgf, t.th_xga, t.th_net, t.th_toi],
      rows, [600, 1700, 4000, 1100, 1100, 1100, 1500]
    ),
    para(' * = press-confirmed override applied (heuristic diverged from real deployment)',
         { italics: true }),
  ];
}

function spotlight(team, rank) {
  // Minor narrative per top/bottom team
  const c = team.line.C.name, l = team.line.L.name, r = team.line.R.name;
  const cTags = (team.line.C.tags || []).map(tg => tg.tag).slice(0, 2).join(', ');
  const lTags = (team.line.L.tags || []).map(tg => tg.tag).slice(0, 2).join(', ');
  const rTags = (team.line.R.tags || []).map(tg => tg.tag).slice(0, 2).join(', ');
  return new Paragraph({
    spacing: { before: 100, after: 80 },
    indent: { left: 240, right: 240 },
    shading: { type: ShadingType.CLEAR, color: 'auto', fill: BRAND.info },
    children: [
      new TextRun({ text: `#${rank} ${team.team_name} — ${l} · ${c} · ${r}`, bold: true, font: 'Arial', size: 20, color: BRAND.navy }),
      new TextRun({ text: `\n  iso net60 = ${fmt(team.trio_avg_iso_net60, 3)} (xGF ${fmt(team.trio_avg_iso_xgf60, 3)}, xGA ${fmt(team.trio_avg_iso_xga60, 3)})`, font: 'Arial', size: 18, color: BRAND.ink }),
      new TextRun({ text: `\n  Tags: L=${lTags || '—'} | C=${cTags || '—'} | R=${rTags || '—'}`, italics: true, font: 'Arial', size: 18, color: BRAND.mute }),
    ],
  });
}

function topBottomSection(t) {
  const top3 = teams.slice(0, 3);
  const bottom3 = teams.slice(-3);
  return [
    h1(t.top3_title), para(t.top3_intro),
    ...top3.map((team, i) => spotlight(team, i + 1)),
    h1(t.bottom3_title), para(t.bottom3_intro),
    ...bottom3.map((team, i) => spotlight(team, teams.length - 2 + i)),
  ];
}

function archetypesSection(t) {
  const rows = tags.map(tg => [tg.tag, tg.count.toString()]);
  return [
    h1(t.archetypes_title), para(t.archetypes_intro, { italics: true }),
    dataTable([t.th_tag, t.th_count], rows, [5000, 5000]),
  ];
}

function methodSection(t) { return [h1(t.method_title), ...bulletList(t.method)]; }
function caveatsSection(t) { return [h1(t.caveats_title), ...bulletList(t.caveats)]; }
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
        ...tldrSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...tableSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...topBottomSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...archetypesSection(t),
        ...methodSection(t),
        ...caveatsSection(t),
        ...sourcesSection(t),
      ],
    }],
  });
}

(async () => {
  for (const lang of ['en', 'fr']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const out = path.join(__dirname, `playoff_first_lines_2026-04-29_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
