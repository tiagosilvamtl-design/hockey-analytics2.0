// Branded EN+FR docx renderer for the three-layer swap projection.
// Reads gallagher_for_dach_three_layer.numbers.json (produced by the demo
// analyzer) and writes game-post-style docx files.
//
// This is the docx-format the propose-swap-scenario skill can drop into any
// pre-game brief once the comp engine + scouting tag corpus are mature.
//
// Run:
//   node examples/swap_with_comparables/build_three_layer_swap_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'gallagher_for_dach_three_layer.numbers.json'), 'utf8'));

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70', red: 'A6192E',
  ink: '111111', mute: '666666', rule: 'BFBFBF',
  good: 'E2F0D9', mid: 'FFF2CC', bad: 'F8CBAD',
  l1: 'EAF1FB', l2: 'F2E6F8', l3: 'FFF2CC',
};

const fmt = (n, p = 3) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const s = Number(n).toFixed(p);
  return (Number(n) > 0 ? '+' : '') + s;
};
const fmtFr = (n, p = 3) => fmt(n, p).replace('.', ',');

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
function para(t, opts = {}) { return new Paragraph({ spacing: { after: opts.after ?? 100 }, children: opts.italics ? [new TextRun({ text: t, italics: true, color: opts.color || BRAND.mute, font: 'Arial', size: 20 })] : md(t) }); }
function h1(t) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 140 }, children: [new TextRun({ text: t, bold: true, size: 30, color: BRAND.navy, font: 'Arial' })] }); }
function h2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: [new TextRun({ text: t, bold: true, size: 24, color: BRAND.navyLight, font: 'Arial' })] }); }
function bullets(items) { return items.map(s => new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 }, children: md(s) })); }

function dataTable(headers, rows, widths) {
  const headerRow = new TableRow({ tableHeader: true,
    children: headers.map(h => new TableCell({ borders: cellBorders,
      shading: { type: ShadingType.CLEAR, color: 'auto', fill: BRAND.navy }, verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ spacing: { before: 60, after: 60 },
        children: [new TextRun({ text: h, bold: true, color: 'FFFFFF', font: 'Arial', size: 18 })] })] })) });
  const bodyRows = rows.map(r => {
    const cells = Array.isArray(r) ? r : r.cells;
    const opts = Array.isArray(r) ? {} : (r._opts || {});
    return new TableRow({
      children: cells.map(c => {
        const isObj = c && typeof c === 'object' && !Array.isArray(c) && 'value' in c;
        const text = isObj ? String(c.value ?? '—') : String(c ?? '—');
        const fill = isObj && c.fill ? c.fill : opts.fill;
        const bold = !!(isObj && c.bold);
        return new TableCell({ borders: cellBorders,
          shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ spacing: { before: 40, after: 40 },
            children: [new TextRun({ text, font: 'Arial', size: 18, color: BRAND.ink, bold })] })] });
      }),
    });
  });
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, columnWidths: widths, rows: [headerRow, ...bodyRows] });
}

const T = {
  en: {
    title: 'Three-layer swap projection — Gallagher for Dach',
    subtitle: '14-minute/game slot, 5v5. Worked example of the comparable-engine + scouting-tag form-factor.',
    date: `Generated ${D.meta.as_of} · open-source · github.com/lemieuxAI/framework`,
    intro_title: 'What this is',
    intro: [
      `The framework is built around honest small-sample handling. A swap projection from one player's pooled iso alone — even with five years of NHL data — has CI bands wide enough to not commit to a direction. Layering in (a) a kNN comp cohort and (b) an archetype-level reg-to-playoff lift narrows that uncertainty, IF the data supports doing so.`,
      `This document shows the three layers stacked on a real swap query, with each layer's projection + 80% CI shown side-by-side. The reader can disagree with any layer; the methodology of each is independently auditable.`,
    ],
    layers_title: 'The three layers, projected',
    th_layer: 'Layer', th_dnet: 'Δ Net xG/game', th_ci: 'xGF 80% CI', th_ciw: 'CI width',
    layers_caveat: 'Layer 1 uses the player\'s 5-year pooled NHL iso. Layer 2 blends Layer 1 with the top-5 kNN comps\' pooled iso, weighted by sample size. Layer 3 adds an archetype-level reg-to-playoff lift derived from a tag-cohort split study.',
    cohort_title: 'Layer 2 — kNN comp cohort',
    cohort_intro: 'The five players closest to Gallagher in the comparable engine\'s feature space. Score is a CARMELO-style 0-100 similarity. TOI is the comp\'s pooled 5v5 minutes across the 5-year window — the larger the cohort\'s pooled minutes, the more the regularization tightens Layer 2\'s CI.',
    th_score: 'Score', th_name: 'Comp', th_pos: 'Pos', th_toi: 'Pooled 5v5 TOI',
    archetype_title: 'Layer 3 — archetype split-study',
    archetype_intro: `Gallagher's primary archetype tag is **${D.meta.archetype_lift?.tag || '(none)'}** (assigned from scouting text via WebSearch + GenAI extraction). For every player in the corpus tagged with the same archetype at confidence ≥ 0.6, we compute (playoff iso net − reg-season iso net) and aggregate the cohort's deltas with an 80% empirical CI.`,
    archetype_finding_template: 'Cohort N = {n}; mean lift {mean}; 80% CI [{lo}, {hi}].',
    archetype_caveat_n_small: 'Cohort N is {n} — way too small to publish this as a real finding. The framework grades the claim and reports the direction the data supports, not the direction we hypothesized. The Layer 3 result is correct as far as the four-player sample shows; the user should treat it as illustrative-of-the-pipeline rather than as a robust archetype-level claim until the corpus is larger.',
    honest_title: 'Honest read',
    honest: [
      `**All three layers agree directionally** if the archetype's lift CI is sign-consistent (i.e. doesn't straddle zero). When it does straddle, Layer 3 widens the projection's CI past zero — exactly what the framework should do when the archetype-layer adds more noise than signal.`,
      `**The framework grades, it doesn't manufacture.** If the archetype data says "this archetype underperforms in playoffs", the projection drops accordingly. The reader sees the direction the data actually supports, not the direction the user wanted.`,
    ],
    method_title: 'How each layer is computed',
    method: [
      `**Layer 1 (raw pooled iso):** \`build_pooled_player_impact()\` over 5 NHL seasons (21-22 → 25-26), at 5v5. Variance is Poisson-approximate on the player's events.`,
      `**Layer 2 (cohort-stabilized):** \`build_cohort_stabilized_impact()\` blends the target's iso with the kNN cohort's pooled iso. Blend weight is a sigmoid on log10(target TOI) around a 600-min pivot. Variance: \`σ² = w_t² × σ_target² + w_c² × σ_cohort²\`.`,
      `**Layer 3 (archetype-adjusted):** the cohort's reg-to-playoff lift is added on top of Layer 2's iso. Lift variance is approximated from the empirical 80% CI half-width as \`(half / 1.2816)²\`.`,
    ],
    sources_title: 'Sources',
    sources: [
      ['Comparable engine + plan', 'https://github.com/lemieuxAI/framework/blob/main/plans/want-to-build-an-cheeky-zebra.md'],
      ['Phase 1 working spike commit', 'https://github.com/lemieuxAI/framework/commit/c71845d'],
      ['Scouting corpus seed (12 players)', 'https://github.com/lemieuxAI/framework/commit/c7bb60b'],
      ['CARMELO methodology reference', 'https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/'],
    ],
    footer_left: 'Lemieux · three-layer swap projection',
    footer_right: 'Page',
  },
  fr: {
    title: 'Projection d\'échange à trois couches — Gallagher pour Dach',
    subtitle: 'Fenêtre de 14 minutes/match, 5 c. 5. Exemple travaillé du moteur de comparables + couche d\'archétype.',
    date: `Généré le ${D.meta.as_of} · code source ouvert · github.com/lemieuxAI/framework`,
    intro_title: 'De quoi il s\'agit',
    intro: [
      `Le cadriciel est bâti autour d\'un traitement honnête des petits échantillons. Une projection d\'échange basée uniquement sur l\'iso poolé d\'un joueur — même sur cinq ans de données LNH — donne des bandes IC trop larges pour s\'engager sur une direction. L\'ajout (a) d\'un trio de comparables kNN et (b) d\'un ajustement de niveau archétype pour le delta saison-régulière → séries rétrécit cette incertitude, SI les données le justifient.`,
      `Ce document montre les trois couches empilées sur une vraie requête d\'échange, avec la projection de chaque couche + son IC à 80 % côte à côte. Le lecteur peut être en désaccord avec n\'importe quelle couche; la méthodologie de chacune est indépendamment vérifiable.`,
    ],
    layers_title: 'Les trois couches, projetées',
    th_layer: 'Couche', th_dnet: 'Δ Net BA/match', th_ci: 'IC 80 % BAF', th_ciw: 'Largeur IC',
    layers_caveat: 'Couche 1 : iso poolé 5 ans LNH du joueur. Couche 2 : Couche 1 mélangée à l\'iso poolé des 5 comparables kNN les plus proches, pondérée par la taille d\'échantillon. Couche 3 : ajout du delta saison-régulière → séries au niveau archétype, dérivé d\'une étude de scission par tag.',
    cohort_title: 'Couche 2 — cohorte de comparables kNN',
    cohort_intro: 'Les cinq joueurs les plus proches de Gallagher dans l\'espace de caractéristiques du moteur. Le pointage est une similarité 0-100 style CARMELO. Le TG est le total à 5 c. 5 du comparable sur la fenêtre de 5 ans — plus la cohorte cumule de minutes, plus la régularisation rétrécit l\'IC de la Couche 2.',
    th_score: 'Pointage', th_name: 'Comparable', th_pos: 'Pos', th_toi: 'TG 5 c. 5 poolé',
    archetype_title: 'Couche 3 — étude de scission par archétype',
    archetype_intro: `L\'archétype principal de Gallagher est **${D.meta.archetype_lift?.tag || '(aucun)'}** (assigné à partir des textes de dépistage via WebSearch + extraction GenAI). Pour chaque joueur du corpus marqué du même archétype avec une confiance ≥ 0,6, on calcule (iso net en séries − iso net en saison régulière) et on agrège les deltas de la cohorte avec un IC empirique à 80 %.`,
    archetype_finding_template: 'N de la cohorte = {n}; lift moyen {mean}; IC 80 % [{lo}, {hi}].',
    archetype_caveat_n_small: 'Le N de la cohorte est de {n} — beaucoup trop petit pour publier ce résultat comme une véritable conclusion. Le cadriciel évalue la prétention et rapporte la direction que les données soutiennent, pas la direction qu\'on espérait. Le résultat de la Couche 3 est correct dans la limite de l\'échantillon de quatre joueurs; à traiter comme illustratif-du-pipeline plutôt que comme une affirmation robuste au niveau archétype tant que le corpus n\'est pas plus grand.',
    honest_title: 'Lecture honnête',
    honest: [
      `**Les trois couches s\'alignent directionnellement** si l\'IC du lift de l\'archétype est cohérent en signe (i.e. ne chevauche pas zéro). Quand il chevauche, la Couche 3 élargit l\'IC de la projection au-delà de zéro — exactement ce que le cadriciel doit faire quand la couche archétype ajoute plus de bruit que de signal.`,
      `**Le cadriciel évalue, il ne fabrique pas.** Si les données sur l\'archétype disent « cet archétype sous-performe en séries », la projection baisse en conséquence. Le lecteur voit la direction que les données soutiennent réellement, pas celle qu\'on aurait souhaitée.`,
    ],
    method_title: 'Comment chaque couche est calculée',
    method: [
      `**Couche 1 (iso poolé brut) :** \`build_pooled_player_impact()\` sur 5 saisons LNH (21-22 → 25-26), à 5 c. 5. Variance par approximation poissonnienne sur les événements du joueur.`,
      `**Couche 2 (stabilisée par cohorte) :** \`build_cohort_stabilized_impact()\` mélange l\'iso de la cible avec l\'iso poolé de la cohorte kNN. Poids du mélange : sigmoïde sur log10(TG cible) autour d\'un pivot de 600 min. Variance : \`σ² = w_t² × σ_cible² + w_c² × σ_cohorte²\`.`,
      `**Couche 3 (ajustée par archétype) :** le lift saison-régulière → séries de la cohorte est ajouté à la Couche 2. Variance du lift approximée à partir de la demi-largeur de l\'IC à 80 % par \`(demi / 1,2816)²\`.`,
    ],
    sources_title: 'Sources',
    sources: [
      ['Moteur de comparables + plan', 'https://github.com/lemieuxAI/framework/blob/main/plans/want-to-build-an-cheeky-zebra.md'],
      ['Commit du spike de la Phase 1', 'https://github.com/lemieuxAI/framework/commit/c71845d'],
      ['Seed du corpus de dépistage (12 joueurs)', 'https://github.com/lemieuxAI/framework/commit/c7bb60b'],
      ['Référence méthodologique CARMELO', 'https://fivethirtyeight.com/methodology/how-our-nba-predictions-work/'],
    ],
    footer_left: 'Lemieux · projection d\'échange à trois couches',
    footer_right: 'Page',
  },
};

function brandHeader() { return new Header({ children: [new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 80 }, children: [new TextRun({ text: 'LEMIEUX  ', bold: true, color: BRAND.red, font: 'Arial', size: 18 }), new TextRun({ text: '· hockey analytics', color: BRAND.mute, font: 'Arial', size: 16 })] })] }); }
function brandFooter(t) { return new Footer({ children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: t.footer_left, color: BRAND.mute, font: 'Arial', size: 16 }), new TextRun({ text: '   ·   ', color: BRAND.mute, font: 'Arial', size: 16 }), new TextRun({ text: t.footer_right + ' ', color: BRAND.mute, font: 'Arial', size: 16 }), new TextRun({ children: [PageNumber.CURRENT], color: BRAND.mute, font: 'Arial', size: 16 })] })] }); }

function layersTable(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const fillsByIdx = [BRAND.l1, BRAND.l2, BRAND.l3];
  const rows = (D.layers || []).map((L, i) => ({
    cells: [L.label, fmtN(L.delta_net, 3), `[${fmtN(L.ci_xgf[0], 3)}, ${fmtN(L.ci_xgf[1], 3)}]`, fmtN(L.ci_xgf_width, 3)],
    _opts: { fill: fillsByIdx[i] || BRAND.l1 },
  }));
  return [
    h1(t.layers_title),
    para(t.layers_caveat, { italics: true }),
    dataTable([t.th_layer, t.th_dnet, t.th_ci, t.th_ciw], rows, [4500, 1700, 2300, 1500]),
  ];
}

function cohortTable(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const rows = (D.meta.comp_cohort || []).map(c => [fmtN(c.score, 1), c.name, '—', fmtN(c.toi, 0)]);
  return [
    h1(t.cohort_title),
    para(t.cohort_intro, { italics: true }),
    dataTable([t.th_score, t.th_name, t.th_pos, t.th_toi], rows, [1300, 4500, 800, 3400]),
  ];
}

function archetypeSection(t, lang) {
  const out = [h1(t.archetype_title), para(t.archetype_intro, {})];
  const lift = D.meta.archetype_lift;
  if (lift) {
    const fmtN = lang === 'fr' ? fmtFr : fmt;
    const finding = t.archetype_finding_template
      .replace('{n}', String(lift.n_cohort))
      .replace('{mean}', fmtN(lift.mean_lift, 3))
      .replace('{lo}', fmtN(lift.ci80_low, 3))
      .replace('{hi}', fmtN(lift.ci80_high, 3));
    out.push(para(`**${finding}**`, {}));
    if (lift.n_cohort < 10) {
      out.push(para(t.archetype_caveat_n_small.replace('{n}', String(lift.n_cohort)), { italics: true, color: BRAND.mute }));
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
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 30, bold: true, color: BRAND.navy, font: 'Arial' }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 24, bold: true, color: BRAND.navyLight, font: 'Arial' }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      ],
    },
    numbering: { config: [{ reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '◆', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 280 } }, run: { color: BRAND.red } } }] }] },
    sections: [{
      properties: { page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
      headers: { default: brandHeader() }, footers: { default: brandFooter(t) },
      children: [
        new Paragraph({ children: [] }),
        new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: t.title, bold: true, color: BRAND.navy, font: 'Arial', size: 36 })] }),
        new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: t.subtitle, italics: true, color: BRAND.mute, font: 'Arial', size: 22 })] }),
        new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: t.date, color: BRAND.mute, font: 'Arial', size: 18 })] }),
        h1(t.intro_title), ...bullets(t.intro),
        ...layersTable(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...cohortTable(t, lang),
        ...archetypeSection(t, lang),
        h1(t.honest_title), ...bullets(t.honest),
        h1(t.method_title), ...bullets(t.method),
        h1(t.sources_title),
        ...t.sources.map(([txt, url]) => new Paragraph({
          numbering: { reference: 'bullets', level: 0 }, spacing: { after: 60 },
          children: [new ExternalHyperlink({ children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })], link: url })],
        })),
      ],
    }],
  });
}

(async () => {
  for (const lang of ['en', 'fr']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const out = path.join(__dirname, `gallagher_for_dach_three_layer_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
