// Branded EN+FR docx for a tag-cohort split study.
// Reads the JSON path from argv[2].

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const BRAND = { navy:'1F2F4A', navyLight:'2F4A70', red:'A6192E',
  ink:'111111', mute:'666666', rule:'BFBFBF',
  good:'E2F0D9', mid:'FFF2CC', bad:'F8CBAD' };
const fmt = (n,p=3)=>n==null||Number.isNaN(n)?'—':((n>0?'+':'')+Number(n).toFixed(p));
const fmtFr = (n,p=3)=>fmt(n,p).replace('.',',');
const thin = { style: BorderStyle.SINGLE, size:4, color: BRAND.rule };
const cellBorders = { top:thin, bottom:thin, left:thin, right:thin };

function md(s){
  const parts=[]; const re=/\*\*(.+?)\*\*/g; let last=0,m;
  while((m=re.exec(s))!==null){
    if(m.index>last) parts.push(new TextRun({text:s.slice(last,m.index), font:'Arial', size:20, color:BRAND.ink}));
    parts.push(new TextRun({text:m[1], bold:true, font:'Arial', size:20, color:BRAND.ink}));
    last = re.lastIndex;
  }
  if(last<s.length) parts.push(new TextRun({text:s.slice(last), font:'Arial', size:20, color:BRAND.ink}));
  return parts;
}
const para=(t,opt={})=>new Paragraph({spacing:{after:opt.after??100}, children: opt.italics?
  [new TextRun({text:t, italics:true, color:opt.color||BRAND.mute, font:'Arial', size:20})]: md(t)});
const h1=t=>new Paragraph({heading:HeadingLevel.HEADING_1, spacing:{before:280,after:140},
  children:[new TextRun({text:t, bold:true, size:30, color:BRAND.navy, font:'Arial'})]});
const h2=t=>new Paragraph({heading:HeadingLevel.HEADING_2, spacing:{before:200,after:100},
  children:[new TextRun({text:t, bold:true, size:24, color:BRAND.navyLight, font:'Arial'})]});
const bullets = arr => arr.map(s=>new Paragraph({numbering:{reference:'bullets',level:0}, spacing:{after:80}, children:md(s)}));

function table(headers, rows, widths){
  const head = new TableRow({tableHeader:true, children: headers.map(h=>new TableCell({borders:cellBorders,
    shading:{type:ShadingType.CLEAR, color:'auto', fill:BRAND.navy},
    verticalAlign:VerticalAlign.CENTER,
    children:[new Paragraph({spacing:{before:60,after:60}, children:[new TextRun({text:h, bold:true, color:'FFFFFF', font:'Arial', size:18})]})]}))});
  const body = rows.map(r=>{
    const cells = Array.isArray(r)?r:r.cells;
    const opts = Array.isArray(r)?{}:(r._opts||{});
    return new TableRow({children: cells.map(c=>{
      const isObj = c && typeof c==='object' && !Array.isArray(c) && 'value' in c;
      const text = isObj?String(c.value??'—'):String(c??'—');
      const fill = isObj && c.fill ? c.fill : opts.fill;
      const bold = !!(isObj && c.bold);
      return new TableCell({borders:cellBorders,
        shading: fill?{type:ShadingType.CLEAR, color:'auto', fill}:undefined,
        verticalAlign:VerticalAlign.CENTER,
        children:[new Paragraph({spacing:{before:40,after:40}, children:[new TextRun({text, font:'Arial', size:18, color:BRAND.ink, bold})]})]});
    })});
  });
  return new Table({width:{size:100, type:WidthType.PERCENTAGE}, columnWidths:widths, rows:[head, ...body]});
}

const T = {
  en: {
    title: `Tag-cohort split study — ${D.tag}`,
    subtitle: `Reg-season vs playoff iso-net for the '${D.tag}' archetype`,
    intro_title: 'What this answers',
    intro: [
      `For every player tagged **${D.tag}** in the scouting corpus at confidence ≥ ${D.min_confidence}, this report computes their (playoff iso net) − (reg-season iso net) — the **playoff lift**. Aggregating across the cohort tells us whether the archetype as a whole tends to over- or under-deliver in playoffs.`,
      `Honest framing: the framework grades the claim, doesn't manufacture it. If the cohort's lift CI straddles zero, the report says so. The size of the cohort and its CI width are shown so you can decide how seriously to take the directional finding.`,
    ],
    cohort_title: 'Tagged cohort',
    cohort_intro: `Players carrying the '${D.tag}' tag at confidence ≥ ${D.min_confidence}, with the source quote that triggered the tag.`,
    th_player: 'Player', th_pos: 'Pos', th_conf: 'Conf', th_quote: 'Source quote',
    study_title: 'Reg→Playoff iso-net deltas',
    study_intro: `Of the cohort, ${D.study.n_players} players had both ≥ 200 5v5 reg-season minutes AND ≥ 50 5v5 playoff minutes in the 5-year window. Their per-player deltas:`,
    th_reg: 'Reg-season iso net (xG/60)', th_play: 'Playoff iso net (xG/60)', th_delta: 'Δ (playoff − reg)',
    summary_title: 'Cohort aggregate',
    th_metric: 'Metric', th_value: 'Value',
    finding_title: 'The finding',
    method_title: 'Method',
    method: [
      `**Tag assignment**: an LLM-extracted classification from beat-coverage and scouting-report text, with the verbatim source quote stored as provenance. Re-extractable with \`tools/build_scouting_corpus.py\`.`,
      `**Iso net**: at 5v5 strength, (player on-ice xG/60) − (team-without-player xG/60), per the standard isolated-impact decomposition. Same primitive used by the swap engine.`,
      `**80% CI**: empirical 10th and 90th percentiles of the cohort's delta distribution. Not bootstrapped — reflects observed dispersion rather than hypothetical resampling.`,
    ],
    sources_title: 'Sources',
    footer: 'Lemieux · cohort-study report',
  },
  fr: {
    title: `Étude de scission par cohorte d'archétype — ${D.tag}`,
    subtitle: `Iso net saison régulière vs séries pour l'archétype '${D.tag}'`,
    intro_title: 'Ce que ce rapport répond',
    intro: [
      `Pour chaque joueur marqué **${D.tag}** dans le corpus de dépistage avec une confiance ≥ ${D.min_confidence}, ce rapport calcule (iso net en séries) − (iso net en saison régulière) — le **lift en séries**. Agrégé sur la cohorte, on voit si l'archétype dans son ensemble tend à sur- ou sous-livrer en séries.`,
      `Cadrage honnête : le cadriciel évalue la prétention, il ne la fabrique pas. Si l'IC du lift de la cohorte chevauche zéro, le rapport le dit. La taille de la cohorte et la largeur de l'IC sont montrées pour qu'on décide combien sérieusement prendre la direction.`,
    ],
    cohort_title: 'Cohorte marquée',
    cohort_intro: `Joueurs portant l'étiquette '${D.tag}' avec une confiance ≥ ${D.min_confidence}, avec la citation source qui a déclenché l'étiquetage.`,
    th_player: 'Joueur', th_pos: 'Pos', th_conf: 'Conf', th_quote: 'Citation source',
    study_title: 'Deltas iso-net saison régulière → séries',
    study_intro: `Parmi la cohorte, ${D.study.n_players} joueurs avaient à la fois ≥ 200 minutes à 5 c. 5 en saison ET ≥ 50 minutes à 5 c. 5 en séries dans la fenêtre de 5 ans. Leurs deltas par joueur :`,
    th_reg: 'Iso net saison rég. (BA/60)', th_play: 'Iso net séries (BA/60)', th_delta: 'Δ (séries − rég.)',
    summary_title: 'Agrégé de la cohorte',
    th_metric: 'Mesure', th_value: 'Valeur',
    finding_title: 'La conclusion',
    method_title: 'Méthode',
    method: [
      `**Attribution d'étiquette** : classification extraite par LLM des textes de dépistage et de couverture, avec la citation source stockée comme provenance. Ré-extractible via \`tools/build_scouting_corpus.py\`.`,
      `**Iso net** : à 5 c. 5, (BAF/60 sur la glace du joueur) − (BAF/60 équipe-sans-joueur), selon la décomposition standard d'impact isolé. Même primitive que le moteur d'échange.`,
      `**IC 80 %** : 10ᵉ et 90ᵉ percentiles empiriques de la distribution des deltas de la cohorte. Pas de rééchantillonnage — reflète la dispersion observée plutôt qu'un rééchantillonnage hypothétique.`,
    ],
    sources_title: 'Sources',
    footer: 'Lemieux · rapport d\'étude de cohorte',
  },
};

function buildDoc(lang) {
  const t = T[lang];
  const fmtN = lang==='fr'?fmtFr:fmt;
  const cohortRows = D.cohort.map(c => [
    c.name, c.position, fmtN(c.confidence,2), c.source_quote.slice(0,150) + (c.source_quote.length>150?'…':''),
  ]);
  const sortedDeltas = [...D.study.per_player].sort((a,b)=>b.delta-a.delta);
  const fillForDelta = d => d>=0.05?BRAND.good:(d<=-0.05?BRAND.bad:BRAND.mid);
  const studyRows = sortedDeltas.map(r => ({
    cells: [r.name, fmtN(r.reg_iso_net,3), fmtN(r.playoff_iso_net,3), fmtN(r.delta,3)],
    _opts: { fill: fillForDelta(r.delta) },
  }));
  const summaryRows = [
    [lang==='fr'?'N (cohorte avec saison + séries)':'N (cohort with both reg + playoff)', String(D.study.n_players)],
    [lang==='fr'?'Δ moyen':'Mean Δ', fmtN(D.study.mean_delta_iso_net,3)],
    [lang==='fr'?'Δ médian':'Median Δ', fmtN(D.study.median_delta_iso_net,3)],
    [lang==='fr'?'IC 80 % bas':'80% CI low', fmtN(D.study.ci80_low,3)],
    [lang==='fr'?'IC 80 % haut':'80% CI high', fmtN(D.study.ci80_high,3)],
    [lang==='fr'?'IC exclut zéro':'CI excludes zero', D.study.ci80_excludes_zero?(lang==='fr'?'oui':'yes'):(lang==='fr'?'non — chevauche zéro':'no — straddles zero')],
  ];
  const finding = (() => {
    if (D.study.n_players < 3) return [
      lang==='fr'?`**N=${D.study.n_players} est trop petit pour un IC informatif.** Une cohorte plus large rendrait cette étude défendable.`
                 :`**N=${D.study.n_players} is too small for an informative CI.** A larger cohort would make this study defensible.`,
    ];
    const dir = D.study.mean_delta_iso_net > 0 ? (lang==='fr'?'sur-performance':'over-performance')
                                                : (lang==='fr'?'sous-performance':'under-performance');
    if (D.study.ci80_excludes_zero) {
      return lang==='fr'?[
        `**Direction confirmée** : à N=${D.study.n_players}, l'IC 80 % de [${fmtFr(D.study.ci80_low,3)}, ${fmtFr(D.study.ci80_high,3)}] est cohérent en signe — la cohorte montre une ${dir} en séries de **${fmtFr(D.study.mean_delta_iso_net,3)} BA/60** en moyenne.`,
        `Cela alimente une couche d'archétype dans le moteur d'échange : un joueur portant cette étiquette voit sa projection ajustée de ce delta avec sa propre incertitude.`,
      ] : [
        `**Direction confirmed**: at N=${D.study.n_players}, the 80% CI of [${fmt(D.study.ci80_low,3)}, ${fmt(D.study.ci80_high,3)}] is sign-consistent — the cohort shows ${dir} in playoffs of **${fmt(D.study.mean_delta_iso_net,3)} xG/60** on average.`,
        `This feeds an archetype layer in the swap engine: a player carrying this tag has their projection adjusted by this delta with its own uncertainty propagated.`,
      ];
    }
    return lang==='fr'?[
      `**IC chevauche zéro** : à N=${D.study.n_players}, l'IC 80 % de [${fmtFr(D.study.ci80_low,3)}, ${fmtFr(D.study.ci80_high,3)}] traverse zéro. La direction (${dir} moyenne de ${fmtFr(D.study.mean_delta_iso_net,3)}) n'est pas statistiquement informative à cette taille de cohorte.`,
      `Le moteur d'échange peut malgré tout afficher cette couche d'archétype, mais en montrant explicitement que l'IC chevauche zéro — élargissant la projection au lieu de la rétrécir.`,
    ] : [
      `**CI straddles zero**: at N=${D.study.n_players}, the 80% CI of [${fmt(D.study.ci80_low,3)}, ${fmt(D.study.ci80_high,3)}] crosses zero. The direction (mean ${dir} of ${fmt(D.study.mean_delta_iso_net,3)}) is not statistically informative at this cohort size.`,
      `The swap engine can still surface this archetype layer, but only with explicit "CI straddles zero" framing — widening the projection rather than tightening it.`,
    ];
  })();

  return new Document({
    creator:'Lemieux', title:t.title,
    styles: { default:{document:{run:{font:'Arial', size:20, color:BRAND.ink}}},
      paragraphStyles:[
        {id:'Heading1',name:'Heading 1',basedOn:'Normal',next:'Normal',quickFormat:true,
         run:{size:30,bold:true,color:BRAND.navy,font:'Arial'}, paragraph:{spacing:{before:280,after:140}, outlineLevel:0}},
        {id:'Heading2',name:'Heading 2',basedOn:'Normal',next:'Normal',quickFormat:true,
         run:{size:24,bold:true,color:BRAND.navyLight,font:'Arial'}, paragraph:{spacing:{before:200,after:100}, outlineLevel:1}},
      ]},
    numbering: { config:[{reference:'bullets', levels:[{level:0,format:LevelFormat.BULLET,text:'◆',alignment:AlignmentType.LEFT,
      style:{paragraph:{indent:{left:540,hanging:280}}, run:{color:BRAND.red}}}]}]},
    sections: [{
      properties:{page:{margin:{top:1080,right:1080,bottom:1080,left:1080}}},
      headers:{default: new Header({children:[new Paragraph({alignment:AlignmentType.LEFT, spacing:{after:80},
        children:[new TextRun({text:'LEMIEUX  ', bold:true, color:BRAND.red, font:'Arial', size:18}),
                  new TextRun({text:'· hockey analytics', color:BRAND.mute, font:'Arial', size:16})]})]})},
      footers:{default: new Footer({children:[new Paragraph({alignment:AlignmentType.LEFT,
        children:[new TextRun({text:t.footer, color:BRAND.mute, font:'Arial', size:16}),
                  new TextRun({text:'   ·   ', color:BRAND.mute, font:'Arial', size:16}),
                  new TextRun({text:'Page ', color:BRAND.mute, font:'Arial', size:16}),
                  new TextRun({children:[PageNumber.CURRENT], color:BRAND.mute, font:'Arial', size:16})]})]})},
      children: [
        new Paragraph({children:[]}),
        new Paragraph({spacing:{after:80}, children:[new TextRun({text:t.title, bold:true, color:BRAND.navy, font:'Arial', size:36})]}),
        new Paragraph({spacing:{after:200}, children:[new TextRun({text:t.subtitle, italics:true, color:BRAND.mute, font:'Arial', size:22})]}),
        h1(t.intro_title), ...bullets(t.intro),
        h1(t.cohort_title), para(t.cohort_intro,{italics:true}),
        table([t.th_player, t.th_pos, t.th_conf, t.th_quote], cohortRows, [2400, 600, 800, 6200]),
        h1(t.study_title), para(t.study_intro),
        table([t.th_player, t.th_reg, t.th_play, t.th_delta], studyRows, [2700, 2400, 2400, 2500]),
        h2(t.summary_title),
        table([t.th_metric, t.th_value], summaryRows, [5000, 5000]),
        h1(t.finding_title), ...bullets(finding),
        h1(t.method_title), ...bullets(t.method),
      ],
    }],
  });
}

(async () => {
  for (const lang of ['en','fr']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const out = path.join(path.dirname(process.argv[2]), `${D.tag}_split_study_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e=>{console.error(e); process.exit(1);});
