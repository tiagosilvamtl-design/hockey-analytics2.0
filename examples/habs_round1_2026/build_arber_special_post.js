// Arber Xhekaj special — chum-au-bar register.
// Run: node examples/habs_round1_2026/build_arber_special_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'arber_special.numbers.json'), 'utf8'));

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70',
  red: 'A6192E', ink: '111111', mute: '666666', rule: 'BFBFBF',
  pos: 'C9E5C2', neg: 'F8CBAD', neu: 'FFF2CC', info: 'DEEAF6', gold: 'FFE699',
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
  const parts = []; const re = /\*\*(.+?)\*\*/g; let last = 0; let m;
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
function quoteBox(text, fill = BRAND.info) {
  return new Paragraph({
    spacing: { before: 80, after: 200 }, indent: { left: 240, right: 240 },
    shading: { type: ShadingType.CLEAR, color: 'auto', fill },
    children: md(text),
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

const pool = D.pooled_baseline_24_25_25_26;
const series5 = D.series_5v5_oi;
const seriesInd = D.series_individual_all_sit;
const ext = D.fun_extrapolation;
const comps = D.knn_comps;
const topD = D.league_top_d_pooled;
const tags = D.tags;
const history = D.career_history;

const T = {
  fr: {
    title: 'Arber Xhekaj est-il vraiment dans le top 10 de la ligue?',
    subtitle: 'Spoiler : non. Mais le chiffre qui dit ça est quand même vrai. Décortiquons.',
    banner: 'Survol Lemieux · registre chronique · chiffres ouverts, lecture honnête.',

    // 1. Le chiffre brut
    h_chiffre: 'Le chiffre qui fait jaser',
    chiffre_box: (
      `Quand Arber Xhekaj est sur la glace à 5 c. 5 dans cette série, le Canadien crée ` +
      `**${fmtFr(series5.iso_net60, 3)} but attendu de plus par 60 minutes** que le Lightning. ` +
      `Pour mettre ça en perspective : **Adam Fox**, le défenseur le plus dominant de la LNH ` +
      `selon ce critère sur deux saisons, est à **${fmtFr(topD[0].iso_net60, 3)}**. ` +
      `Donc oui — sur le tableau, Xhekaj joue à environ **${ext.multiple_of_league_top_d}× la cadence d'Adam Fox**. ` +
      `Avant qu'on s'emballe : **49 minutes à 5 c. 5 sur 5 matchs**. C'est ça l'échantillon.`
    ),

    // 2. Pour le fun — l'extrapolation
    h_extrapolation: 'L\'extrapolation pour le fun',
    extrapolation_intro: (
      `Question naïve mais amusante : si Xhekaj **maintenait** ce rythme sur une saison de 82 matchs ` +
      `(disons ~12 minutes à 5 c. 5 par match, comme un 6ᵉ ou 3ᵉ duo régulier), à quoi ressemblerait ` +
      `son année?`
    ),
    extrapolation_math: (
      `**Calcul rapide** : 82 matchs × 12 min = ${ext.total_5v5_min_82gp.toFixed(0)} minutes à 5 c. 5. ` +
      `À ${fmtFr(series5.iso_net60, 3)} buts attendus net par 60 minutes, ça donne ` +
      `**${fmtFr(ext.extrapolated_season_xg_net, 1)} buts attendus net** sur la saison. ` +
      `Pour comparer : Cale Makar à plein régime, **environ +20 buts attendus net** sur une saison.`
    ),
    extrapolation_punchline: (
      `Traduction : si Xhekaj soutenait ça, ce serait **un défenseur qui n'existe pas dans l'histoire de la LNH**. ` +
      `Pas Cale Makar, pas Adam Fox, pas Quinn Hughes. Quelque chose au-dessus. ` +
      `Évidemment, il ne soutiendra pas. C'est l'illustration parfaite de pourquoi un taux par 60 sur ` +
      `**49 minutes** ne se traduit pas en saison complète. Un seul but évité dans une mauvaise rebondissement, ` +
      `ou une présence où Hutson fait toute la job, et la moyenne saute de ±0,5.`
    ),

    // 3. Sa carrière dit quoi
    h_carriere: 'Mais sa carrière dit quoi, au juste?',
    carriere_intro: (
      `Voici l'historique d'Xhekaj à 5 c. 5 sur la glace, saison par saison. Si on enlève les 49 minutes ` +
      `de cette série (l'aberration), tout le reste raconte une autre histoire :`
    ),

    h_pool_baseline: 'Sa base pondérée (1 738 minutes à 5 c. 5)',
    pool_box: (
      `Sur les deux dernières saisons combinées (régulière + séries), avec **${pool.toi.toFixed(0)} minutes** ` +
      `à 5 c. 5 — un échantillon **35× plus grand** que ses 49 minutes de séries actuelles — son iso net60 est de ` +
      `**${fmtFr(pool.iso_net60, 3)}**. C'est-à-dire : quand il est sur la glace, le CH se fait dominer par environ ` +
      `0,5 but attendu par 60 minutes. C'est cohérent avec un 6ᵉ défenseur de profil physique. C'est exactement ` +
      `ce qu'on attend d'Arber Xhekaj.`
    ),

    // 4. Qui sont ses comps?
    h_comps: 'Ses comparables dans le modèle (kNN sur 24 caractéristiques)',
    comps_intro: (
      `Le moteur de comparables Lemieux place Xhekaj dans son voisinage de joueurs similaires. Ce sont ` +
      `des défenseurs avec des profils statistiques et physiques semblables aux siens. Aucun n'est élite :`
    ),
    comps_punchline: (
      `**Voilà le contexte vrai.** Cal Foote, Logan Stanley, Joel Edmundson, Philippe Myers, Nicolas Hague — ` +
      `c'est l'archétype : grands gabarits, bras longs, plus à l'aise à dégager qu'à transporter. Tous ont ` +
      `des bases iso négatives. Aucun n'a jamais flirté avec +2. Si on veut savoir quel genre de saison ` +
      `Xhekaj produit *vraiment* sur 82 matchs, c'est dans cette liste qu'il faut regarder, pas dans la ` +
      `colonne « Adam Fox ».`
    ),

    // 5. Mais il fait sa job
    h_job: 'Cela dit — il fait sa job en série',
    job_intro: (
      `On ne va pas lui enlever son crédit non plus. Voici ce qu'il a livré en 5 matchs, en environ ` +
      `${seriesInd.toi.toFixed(0)} minutes totales :`
    ),
    job_box: (
      `**${seriesInd.hits} mises en échec en 5 matchs** (4,8/match), ${seriesInd.pim} minutes de pénalité, ` +
      `1 mention d'aide. Plus important : **+1 ou +2 chaque fois** qu'il est dans la colonne du différentiel. ` +
      `Quand St-Louis le déploie — généralement contre les 3ᵉ et 4ᵉ trios de Tampa, dans des minutes protégées — ` +
      `la rondelle ne sort pas du bon côté. C'est ce qu'on demande à un 6ᵉ défenseur. Le +2,01 est artificiel ` +
      `comme métrique élite, mais comme signal de « Xhekaj n'est pas un passif dans son rôle », c'est tout à ` +
      `fait justifié.`
    ),

    // 6. Verdict
    h_verdict: 'Le verdict en deux phrases',
    verdict: (
      `**Xhekaj n'est pas dans le top 10 de la ligue.** Mais dans cette série, dans son rôle, dans ses ` +
      `minutes protégées, il fait exactement ce qu'on lui demande — et le tableau récompense ça avec un ` +
      `chiffre absurde qui dit plus sur la taille de l'échantillon que sur le talent du joueur. ` +
      `C'est le piège classique des stats avancées en petit volume : la **direction** est juste (Xhekaj joue ` +
      `bien dans son rôle), l'**ampleur** est du bruit. Lisez le ton, pas le numéro.`
    ),

    // Sources
    h_sources: 'Sources',
    sources: [
      ['Données NST · skater_stats 24-25 + 25-26 (5 c. 5 sur la glace)', 'https://www.naturalstattrick.com/'],
      ['Données NST · skater_individual_stats (mises en échec, MP, ixG)', 'https://www.naturalstattrick.com/'],
      ['Index de comparables Lemieux (PCA + kNN sur 24 caractéristiques)', 'https://github.com/lemieuxAI/framework/blob/main/legacy/data/comparable_index.json'],
      ['Cadriciel ouvert Lemieux', 'https://github.com/lemieuxAI/framework'],
    ],

    footer_left: 'Lemieux · chronique stat · Arber Xhekaj',
    footer_right: 'Page',
  },
  en: {
    title: 'Is Arber Xhekaj actually a top-10 league defenseman?',
    subtitle: 'Spoiler: no. But the number that says he is, is real. Let\'s walk through it.',
    banner: 'Lemieux brief · column register · open numbers, honest read.',

    h_chiffre: 'The number people are talking about',
    chiffre_box: (
      `When Arber Xhekaj is on the ice 5-on-5 in this playoff series, Montreal generates ` +
      `**${fmt(series5.iso_net60, 3)} more expected goals per 60 minutes** than Tampa. ` +
      `For context: **Adam Fox**, the league's most dominant defenseman by this metric over two seasons, ` +
      `sits at **${fmt(topD[0].iso_net60, 3)}**. So yes — on paper, Xhekaj is playing at roughly ` +
      `**${ext.multiple_of_league_top_d}× Adam Fox's pace**. Before we get too excited: ` +
      `**49 minutes of 5-on-5 across 5 games**. That's the sample.`
    ),

    h_extrapolation: 'The fun extrapolation',
    extrapolation_intro: (
      `Naïve but fun question: if Xhekaj **maintained** this rate across 82 games (let's say ~12 minutes ` +
      `at 5-on-5 per game, like a regular 3rd-pair or 6/7 D), what would his season look like?`
    ),
    extrapolation_math: (
      `**Quick math:** 82 games × 12 min = ${ext.total_5v5_min_82gp.toFixed(0)} 5v5 minutes. ` +
      `At ${fmt(series5.iso_net60, 3)} expected goals net per 60, that's ` +
      `**${fmt(ext.extrapolated_season_xg_net, 1)} expected goals net** for the season. ` +
      `For comparison: Cale Makar at full tilt produces **roughly +20 expected goals net** over a full season.`
    ),
    extrapolation_punchline: (
      `Translation: if Xhekaj sustained this, he'd be **a defenseman that doesn't exist in NHL history**. ` +
      `Not Cale Makar, not Adam Fox, not Quinn Hughes. Something above. ` +
      `Obviously he won't sustain it. This is the perfect illustration of why a per-60 rate on **49 minutes** ` +
      `doesn't translate to a full season. One unlucky bounce, or one shift where Hutson does all the work, ` +
      `and the rate moves ±0.5.`
    ),

    h_carriere: 'But what does his career actually say?',
    carriere_intro: (
      `Here's Xhekaj's 5v5 on-ice history, season by season. Strip out these 49 minutes of playoff outlier, ` +
      `and the rest tells a different story:`
    ),

    h_pool_baseline: 'His pooled baseline (1,738 5v5 minutes)',
    pool_box: (
      `Across the two most recent seasons combined (reg + playoff), with **${pool.toi.toFixed(0)} minutes** ` +
      `at 5v5 — a sample **35× larger** than these 49 series minutes — his iso net60 is ` +
      `**${fmt(pool.iso_net60, 3)}**. Meaning: when he's on the ice, MTL is being outchanced by about ` +
      `0.5 expected goals per 60. That's consistent with a physical 6th defenseman. That's exactly what ` +
      `we expect from Arber Xhekaj.`
    ),

    h_comps: 'His comps in our model (kNN over 24 features)',
    comps_intro: (
      `The Lemieux comparable engine puts Xhekaj's nearest neighbors in the league. These are defensemen ` +
      `with the most similar statistical and physical profiles to his. None are elite:`
    ),
    comps_punchline: (
      `**There's the real context.** Cal Foote, Logan Stanley, Joel Edmundson, Philippe Myers, Nicolas Hague — ` +
      `that's the archetype: big bodies, long reach, more comfortable clearing than carrying. All have negative ` +
      `iso baselines. None have ever flirted with +2. If you want to know what kind of season Xhekaj actually ` +
      `produces over 82 games, it's that list — not the "Adam Fox" column.`
    ),

    h_job: 'Look — he\'s doing his job in this series',
    job_intro: (
      `Let's not take credit away from him. Here's what he delivered across 5 games and roughly ` +
      `${seriesInd.toi.toFixed(0)} total minutes of ice time:`
    ),
    job_box: (
      `**${seriesInd.hits} hits in 5 games** (4.8/game), ${seriesInd.pim} penalty minutes, 1 assist. ` +
      `More importantly: **+1 or +2 every time** he shows up in the plus/minus column. ` +
      `When St-Louis deploys him — usually against Tampa's 3rd and 4th lines, in sheltered minutes — ` +
      `the puck comes out the right way. That's exactly what you ask of a 6th defenseman. The +2.01 is ` +
      `noise as an "elite" metric, but as a signal that "Xhekaj isn't a liability in his role" it's ` +
      `entirely justified.`
    ),

    h_verdict: 'Two-sentence verdict',
    verdict: (
      `**Xhekaj is not a top-10 league defenseman.** But in this series, in his role, in his sheltered ` +
      `minutes, he's doing exactly what's asked — and the math rewards that with an absurd number that ` +
      `says more about sample size than talent. Classic small-sample advanced-stats trap: the **direction** ` +
      `is right (Xhekaj is playing well in his role), the **magnitude** is noise. Read the tone, not the number.`
    ),

    h_sources: 'Sources',
    sources: [
      ['NST data · skater_stats 24-25 + 25-26 (5v5 on-ice)', 'https://www.naturalstattrick.com/'],
      ['NST data · skater_individual_stats (hits, PIM, ixG)', 'https://www.naturalstattrick.com/'],
      ['Lemieux comparable index (PCA + kNN over 24 features)', 'https://github.com/lemieuxAI/framework/blob/main/legacy/data/comparable_index.json'],
      ['Lemieux open-source framework', 'https://github.com/lemieuxAI/framework'],
    ],

    footer_left: 'Lemieux · stat column · Arber Xhekaj',
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

function chiffreSection(t) {
  return [
    h1(t.h_chiffre, BRAND.red),
    quoteBox(t.chiffre_box, BRAND.gold),
  ];
}

function extrapolationSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  return [
    h1(t.h_extrapolation),
    para(t.extrapolation_intro),
    para(t.extrapolation_math),
    quoteBox(t.extrapolation_punchline, BRAND.neg),
    h2(lang === 'fr' ? 'Pour ancrer : les vrais top-D de la ligue' : 'To anchor: the actual league top-D'),
    para(lang === 'fr'
      ? 'Iso net60 regroupé sur les 24-25 + 25-26 (saison régulière + séries), pour les défenseurs avec ≥1 500 minutes à 5 c. 5.'
      : 'Pooled iso net60 over 24-25 + 25-26 (reg + playoff) for defensemen with ≥1,500 5v5 minutes.',
      { italics: true }),
    dataTable(
      [lang === 'fr' ? 'Défenseur' : 'Defenseman',
       lang === 'fr' ? 'TG (5 c. 5)' : 'TOI (5v5)',
       'iso net60'],
      topD.slice(0, 8).map(d => [
        d.name, `${d.toi.toFixed(0)}`, fmtN(d.iso_net60, 3),
      ]),
      [4500, 2500, 3000]
    ),
  ];
}

function carriereSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const rows = history.map(h => {
    const fill = h.iso_net60 > 0.5 ? BRAND.pos : (h.iso_net60 < -0.3 ? BRAND.neg : BRAND.neu);
    return {
      cells: [h.label, String(h.gp), `${h.toi.toFixed(0)}`, fmtN(h.iso_net60, 3)],
      _opts: { fills: [null, null, null, fill] },
    };
  });
  return [
    h1(t.h_carriere),
    para(t.carriere_intro),
    dataTable(
      [lang === 'fr' ? 'Saison · contexte' : 'Season · context',
       'GP',
       lang === 'fr' ? 'TG (5 c. 5)' : 'TOI (5v5)',
       'iso net60'],
      rows, [4500, 1500, 2000, 2000]
    ),
    h2(t.h_pool_baseline),
    quoteBox(t.pool_box, BRAND.info),
  ];
}

function compsSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  return [
    h1(t.h_comps),
    para(t.comps_intro),
    dataTable(
      [lang === 'fr' ? 'Comp' : 'Comp',
       'Score',
       lang === 'fr' ? 'TG regroupé' : 'Pooled TOI',
       'iso xGF/60', 'iso xGA/60', 'iso net60'],
      comps.slice(0, 8).map(c => [
        c.name, `${c.score.toFixed(1)}`, `${c.pooled_toi_5v5.toFixed(0)}`,
        fmtN(c.iso_xgf60, 3), fmtN(c.iso_xga60, 3), fmtN(c.iso_net60, 3),
      ]),
      [3000, 900, 1500, 1500, 1500, 1600]
    ),
    para(t.comps_punchline),
  ];
}

function jobSection(t, lang) {
  return [
    h1(t.h_job),
    para(t.job_intro),
    quoteBox(t.job_box, BRAND.pos),
  ];
}

function verdictSection(t) {
  return [
    h1(t.h_verdict, BRAND.red),
    quoteBox(t.verdict, BRAND.info),
  ];
}

function sourcesSection(t) {
  const out = [h1(t.h_sources)];
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
        ...chiffreSection(t),
        ...extrapolationSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...carriereSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...compsSection(t, lang),
        ...jobSection(t, lang),
        ...verdictSection(t),
        ...sourcesSection(t),
      ],
    }],
  });
}

(async () => {
  for (const lang of ['fr', 'en']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const out = path.join(__dirname, `arber_special_2026-04-30_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
