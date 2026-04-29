// Game 5 pre-game brief — MTL @ TBL, 2026-04-29.
// Inputs:
//   - game5_pregame_lineups.yaml  (canonical projected lineup)
//   - game5_pregame.numbers.json  (analyzer output)
// Run:
//   node examples/habs_round1_2026/build_game5_pregame_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');
const yaml = require('yaml');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'game5_pregame.numbers.json'), 'utf8'));
const LINEUPS = yaml.parse(fs.readFileSync(path.join(__dirname, 'game5_pregame_lineups.yaml'), 'utf8'));

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70',
  red: 'A6192E', ink: '111111',
  mute: '666666', rule: 'BFBFBF',
  pos:  'C9E5C2',   // green tint for positive
  neg:  'F8CBAD',   // red tint for negative
  neu:  'FFF2CC',   // yellow tint for neutral
  info: 'DEEAF6',   // blue tint for headers
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
function bulletList(items) {
  return items.map(s => new Paragraph({
    numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 },
    children: md(s),
  }));
}
function quoteBox(quote, url) {
  return new Paragraph({
    spacing: { before: 60, after: 80 }, indent: { left: 360 },
    children: [
      new TextRun({ text: '"' + quote + '"  — ', italics: true, color: BRAND.mute, font: 'Arial', size: 18 }),
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
      children: cells.map((c, i) => {
        // Cell-level fill via array of fills
        const fill = Array.isArray(opts.fills) ? opts.fills[i] : (opts.fill || null);
        return new TableCell({
          borders: cellBorders,
          shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({
            spacing: { before: 40, after: 40 },
            children: [new TextRun({ text: String(c ?? '—'), font: 'Arial', size: 18, color: BRAND.ink })],
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

// ---------- helpers ----------
const swapA = D.swap_a_kapanen_for_gallagher;
const swapB = D.swap_b_dach_demotion;
const swapC = D.swap_c_demidov_promotion;
const ws = D.warrior_study.bootstrap;
const tags = D.tags;
const g4 = D.g4_line_iso;
const g5 = D.g5_line_iso;
const V = D.verdict;

function lineIsoSwing(role) {
  const a = g4[role]?.avg_iso_net60 ?? 0;
  const b = g5[role]?.avg_iso_net60 ?? 0;
  return b - a;
}
function fillForDelta(d) {
  if (Math.abs(d) < 0.05) return BRAND.neu;
  return d > 0 ? BRAND.pos : BRAND.neg;
}

// ---------- I18N ----------
const T = {
  en: {
    title: 'Pre-game brief — Habs @ Lightning, Game 5 (Apr 29, 2026)',
    subtitle: 'Amalie Arena · series tied 2–2 · Tampa has last change',
    banner: ('Lemieux pre-game brief · projection-driven, framework-graded · ' +
             'every number traces to a query in our open-source codebase.'),
    verdict_title: 'The bottom line',
    verdict_prose: (
      `**Do these lineup changes help the Habs? Yes — slightly.** The projected ` +
      `lineup grades as a **small but clearly positive** change vs Game 4: about ` +
      `**${fmt(V.stacked_total_xg_per_game, 2)} expected xG/game** at 5v5 once you stack the pure ` +
      `iso math (${fmt(V.total_iso_swing_xg_per_game, 2)} xG/g) with the archetype layer on Gallagher ` +
      `(${fmt(V.warrior_layer_xg_per_game, 2)} xG/g). The win is concentrated on the third line: ` +
      `Anderson–Danault–Gallagher is, on paper, a much better trio than Newhook–Kapanen–Demidov, ` +
      `and that win is bigger than the cost of demoting the Dach line and promoting Demidov to L2. ` +
      `The Dach demotion barely moves the needle in pure iso terms — the trio's positive iso ` +
      `doesn't accumulate enough on 4.5 fewer minutes to matter; the real gamble is finishing ` +
      `variance the model can't see. Translation: directionally favourable, magnitude small, ` +
      `nothing here that swings a series on its own.`
    ),
    tldr_title: 'Three things to watch for',
    tldr: [
      `**The L3 rebuild is the headline call.** Replacing Newhook–Kapanen–Demidov with **Anderson–Danault–Gallagher** swings the trio's pooled iso net60 from **${fmt(g4.L3.avg_iso_net60, 3)}** to **${fmt(g5.L3.avg_iso_net60, 3)}** — a **${fmt(lineIsoSwing('L3'), 3)}** swing in trio quality. That's the largest single-move iso shift any forward line has produced this series.`,
      `**The Dach line drops to L4 intact and the math says it costs less than it looks.** ${swapB.minutes_lost_per_game.toFixed(1)} fewer 5v5 min/game on a trio with **${fmt(swapB.trio_avg_iso_net60, 3)}** iso net60 = projected demotion cost of **${fmt(swapB.per_game_xg_cost, 2)} xG/game**. Almost zero, because the cohort's positive iso barely accumulates over 4.5 minutes. The cost is in *finishing variance*, not in iso math.`,
      `**Gallagher's archetype layer adds suggestive lift on top of his pooled iso.** Of his 30 nearest comparables in our model, the ${ws.n_warrior} carrying a \`warrior\` tag lift their playoff 5v5 iso by **${fmt(ws.mean_lift_warrior, 2)}** vs reg-season; the ${ws.n_non_warrior} non-warriors lift only **${fmt(ws.mean_lift_non_warrior, 2)}**. Bootstrap Δ = **${fmt(ws.delta_mean, 3)}** with 80% CI **[${fmt(ws.delta_ci80[0], 2)}, ${fmt(ws.delta_ci80[1], 2)}]** — the CI excludes zero on n=4. Suggestive, not load-bearing.`,
    ],

    lineup_title: '1 · The lineup, before and after',
    lineup_intro: ('Tony Marinaro projected this morning; practice reshuffles + Pierre LeBrun ' +
                  'flagging Gallagher\'s absence at optional skate corroborate. ' +
                  'Final lines confirmed at puck-drop.'),
    th_role: 'Role',
    th_g4: 'Game 4 deployed',
    th_g4_iso: 'G4 trio iso',
    th_g5: 'Game 5 projected',
    th_g5_iso: 'G5 trio iso',
    th_swing: 'Δ trio iso',

    swaps_title: '2 · The math behind the moves',
    swaps_intro: ('Three swap-engine projections, all at 80% CI, all from pooled NST 5v5 oi splits ' +
                 'over 24-25 reg+playoff and 25-26 reg+playoff.'),

    l3_title: '3 · Why the L3 rebuild is the call of the night',
    l3_intro: (`Look at the L3 trio's pooled iso net60: G4 deployed (Newhook–Kapanen–Demidov) at ` +
              `${fmt(g4.L3.avg_iso_net60, 3)}, G5 projected (Anderson–Danault–Gallagher) at ` +
              `${fmt(g5.L3.avg_iso_net60, 3)}. That ` +
              `${fmt(lineIsoSwing('L3'), 3)} swing is bigger than any other lineup change MTL has ` +
              `made this series. The reason is two-fold: getting Kapanen out (he carried negative ` +
              `iso pull on his line) AND getting three positive-iso skaters together.`),
    warrior_intro: 'And then there\'s the archetype layer. Gallagher\'s scouting profile has him at:',

    dach_title: '4 · The Dach line drops to L4 — what it actually costs',
    dach_intro: (`The line that produced both 5v5 goals plus the OT setup in Game 3 — Texier–Dach–Bolduc — ` +
                `gets demoted intact to L4 minutes. The math says the cost is small in iso terms ` +
                `because: (a) trio iso net60 of ${fmt(swapB.trio_avg_iso_net60, 3)} is positive but ` +
                `not huge, and (b) ${swapB.minutes_lost_per_game.toFixed(1)} fewer 5v5 minutes ` +
                `accumulates only ${fmt(swapB.per_game_xg_cost, 2)} expected goals/game in the ` +
                `model. The actual risk is what the model can't capture: clutch finishing variance ` +
                `and the cascading effect of putting your hot line behind two lines that haven't ` +
                `produced 5v5 goals yet this series.`),

    demidov_title: '5 · Demidov\'s promotion is the trade for the L3 rebuild',
    demidov_intro: (`Promoting Demidov from L3 to L2 buys the Anderson–Danault–Gallagher reunion. ` +
                   `The Newhook–Evans–Demidov trio's pooled iso net60 of ` +
                   `${fmt(g5.L2.avg_iso_net60, 3)} is the math cost (vs G4 L2's ` +
                   `${fmt(g4.L2.avg_iso_net60, 3)}, the Texier–Dach–Bolduc trio that's now on L4). ` +
                   `That ${fmt(g5.L2.avg_iso_net60 - g4.L2.avg_iso_net60, 3)} hit on the L2 slot is ` +
                   `the cost; the +${fmt(lineIsoSwing('L3'), 3)} L3 win is the gain. Net: ` +
                   `**${fmt(lineIsoSwing('L2') + lineIsoSwing('L3'), 3)}** combined L2+L3 swing.`),
    demidov_caveat: ('Caveat: Demidov\'s pooled 5v5 sample is small and the iso engine assumes per-60 ' +
                    'rates hold across competition tiers. Top-six minutes against Cernák / Sergachev ' +
                    'are not the same as L3 minutes against Tampa\'s third pair — the model can\'t ' +
                    'isolate quality-of-competition shift.'),

    watch_title: '6 · What to watch',
    watch: [
      '**Anderson–Danault–Gallagher matchup deployment.** Cooper has last change. If Tampa runs Cirelli\'s defensive C against this trio, the warrior-line read is being respected. If they get Cirelli on Suzuki instead, MTL is exposed where the projection liked it.',
      '**Demidov\'s 5v5 minutes against Cernák / Sergachev.** Top-pair exposure is the test. If Demidov accumulates positive 5v5 events against the top D, the L2 promotion earns its keep. If he\'s under sustained pressure, expect a re-shuffle by P3.',
      '**Dach line\'s L4 deployment.** If they get power-play scraps and matchup-favorable shifts, the iso math is friendly. If they\'re reduced to forecheck-and-die L4 minutes, the producing trio\'s playoff finishing rate gets buried under low TOI.',
      '**Gallagher PK + PP2 minutes.** If he\'s on PP2 and PK, the projection assumed L3 5v5 minutes only — extra-strength deployment is upside not modeled.',
      '**Slafkovský side flip on L1.** Same trio as G4, sides reversed. The on-ice effect is small in iso terms but carry-side and entry preferences shift.',
    ],

    framework_title: 'About this brief',
    framework_intro: ('Lemieux is an open-source hockey analytics framework: kNN comparable engine ' +
                     'over standardized features, GenAI-extracted scouting tags with verbatim ' +
                     'provenance, swap engine with pooled-baseline 80% CIs, and tag-cohort effect ' +
                     'studies that test whether qualitative descriptors actually predict behavior. ' +
                     'Every number above traces to a query against the open-source codebase.'),

    caveats_title: 'Caveats',
    caveats: [
      `Marinaro's projection is **one** source. Final lines confirmed at puck-drop. The brief flips defaults to "Marinaro projection" in confidence; if other lines deploy, the analysis re-runs.`,
      'Pooled iso assumes per-60 rates hold across line + competition contexts. Real chemistry effects are not captured.',
      'Slot-time assumptions: L1=14 / L2=12 / L3=10 / L4=7.5 5v5 min/game. CI bands assume slot stability — Cooper can compress L4 minutes well below 7.5 in matchup-driven games.',
      'Gallagher hasn\'t played in this series. Pooled iso uses 24-25 + 25-26 reg+playoff. Sample stability claim is on the comp cohort, not on him individually.',
      'Warrior cohort lift study: n=4 warriors. CI excludes zero, but bootstrap on 4 datapoints recycles the same 4 values. Suggestive, not load-bearing.',
      'No prediction of Game 5 outcome. The framework grades scenarios; it does not forecast.',
    ],

    sources_title: 'Sources',
    sources: [
      ['Tony Marinaro · The Sick Podcast (lineup projection, X.com)', 'https://x.com/TonyMarinaro'],
      ['Pierre LeBrun · TSN — Gallagher likely IN', 'https://www.tsn.ca/nhl/article/ice-chips-hagel-will-play-in-game-5-dastous-a-gtd-hedman-still-out-for-lightning/'],
      ['Practice reshuffle reports · Montreal Hockey Fanatics', 'https://www.montrealhockeyfanatics.com/'],
      ['Lemieux open-source framework + data model', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · pre-game brief · MTL @ TBL G5',
    footer_right: 'Page',
  },
  fr: {
    title: 'Survol d\'avant-match — Canadien @ Lightning, Match no 5 (29 avril 2026)',
    subtitle: 'Amalie Arena · série égale 2–2 · Tampa a le dernier changement',
    banner: ('Survol d\'avant-match Lemieux · piloté par projection, vérifié par le cadriciel · ' +
             'chaque chiffre se rattache à une requête dans notre code source ouvert.'),
    verdict_title: 'En une phrase',
    verdict_prose: (
      `**Est-ce que ces changements aident le Canadien? Oui — légèrement.** La formation ` +
      `projetée se lit comme une amélioration **nette mais petite** par rapport au Match 4 : ` +
      `environ **${fmtFr(V.stacked_total_xg_per_game, 2)} buts attendus par match** à 5 c. 5 une fois ` +
      `empilés le calcul iso pur (${fmtFr(V.total_iso_swing_xg_per_game, 2)} BAF/match) et la couche ` +
      `d'archétype pour Gallagher (${fmtFr(V.warrior_layer_xg_per_game, 2)} BAF/match). Le gain est ` +
      `concentré sur le 3ᵉ trio : Anderson–Danault–Gallagher est, sur papier, un trio nettement ` +
      `meilleur que Newhook–Kapanen–Demidov, et ce gain dépasse le coût de rétrograder le trio de ` +
      `Dach et de promouvoir Demidov au 2ᵉ. La descente du trio de Dach ne bouge presque pas l'aiguille ` +
      `en iso pur — l'iso positif du trio s'accumule à peine sur 4,5 minutes de moins pour faire la ` +
      `différence. Le vrai pari, c'est la variance de finition que le modèle ne voit pas. Traduction : ` +
      `direction favorable, ampleur petite, rien ici qui renverse une série à lui seul.`
    ),
    tldr_title: 'Trois choses à surveiller',
    tldr: [
      `**La reconstruction du 3ᵉ trio, c\'est le coup de tête de la soirée.** Remplacer Newhook–Kapanen–Demidov par **Anderson–Danault–Gallagher** fait passer l\'iso net60 regroupé du trio de **${fmtFr(g4.L3.avg_iso_net60, 3)}** à **${fmtFr(g5.L3.avg_iso_net60, 3)}** — un écart de **${fmtFr(lineIsoSwing('L3'), 3)}** sur la qualité du trio. C\'est la plus grosse oscillation iso d\'un seul changement de trio dans la série.`,
      `**Le trio de Dach descend en bloc au 4ᵉ trio et les mathématiques disent que ça coûte moins cher qu\'il en a l\'air.** ${swapB.minutes_lost_per_game.toFixed(1).replace('.', ',')} minutes de moins à 5 c. 5 par match sur un trio à **${fmtFr(swapB.trio_avg_iso_net60, 3)}** d\'iso net60 = un coût de rétrogradation projeté de **${fmtFr(swapB.per_game_xg_cost, 2)} BAF/match**. Quasi nul, parce que l\'iso positif du trio s\'accumule à peine sur 4,5 minutes. Le vrai risque, c\'est la variance de finition, pas l\'iso.`,
      `**La couche d\'archétype de Gallagher ajoute un relèvement suggestif par-dessus son iso regroupé.** Sur ses 30 plus proches comparables dans notre modèle, les ${ws.n_warrior} qui portent l\'étiquette \`warrior\` relèvent leur iso 5 c. 5 en séries de **${fmtFr(ws.mean_lift_warrior, 2)}** par rapport à la saison régulière; les ${ws.n_non_warrior} non-warriors ne relèvent que de **${fmtFr(ws.mean_lift_non_warrior, 2)}**. Bootstrap Δ = **${fmtFr(ws.delta_mean, 3)}** avec IC à 80 % de **[${fmtFr(ws.delta_ci80[0], 2)}, ${fmtFr(ws.delta_ci80[1], 2)}]** — l\'IC exclut zéro sur n=4. Suggestif, pas porteur.`,
    ],

    lineup_title: '1 · La formation, avant et après',
    lineup_intro: ('Tony Marinaro a projeté ces trios ce matin; les remaniements à l\'entraînement ' +
                  'd\'hier et Pierre LeBrun signalant l\'absence de Gallagher au patinage matinal ' +
                  'corroborent. Les trios finaux sont confirmés à la mise au jeu.'),
    th_role: 'Trio',
    th_g4: 'M4 — déployé',
    th_g4_iso: 'M4 iso trio',
    th_g5: 'M5 — projeté',
    th_g5_iso: 'M5 iso trio',
    th_swing: 'Δ iso trio',

    swaps_title: '2 · Les chiffres derrière les mouvements',
    swaps_intro: ('Trois projections du moteur d\'échange, toutes à IC 80 %, toutes à partir des splits ' +
                 'NST 5 c. 5 sur la glace regroupés sur 24-25 saison régulière + séries et 25-26 ' +
                 'saison régulière + séries.'),

    l3_title: '3 · Pourquoi la reconstruction du 3ᵉ trio, c\'est le coup de la soirée',
    l3_intro: (`Regardez l\'iso net60 regroupé du 3ᵉ trio : M4 déployé (Newhook–Kapanen–Demidov) à ` +
              `${fmtFr(g4.L3.avg_iso_net60, 3)}, M5 projeté (Anderson–Danault–Gallagher) à ` +
              `${fmtFr(g5.L3.avg_iso_net60, 3)}. Cet écart de ` +
              `${fmtFr(lineIsoSwing('L3'), 3)} dépasse celui de tout autre changement de formation ` +
              `du Canadien dans cette série. La raison est double : sortir Kapanen (qui pesait ` +
              `sur l\'iso de son trio) ET réunir trois patineurs à iso positif.`),
    warrior_intro: 'Puis il y a la couche d\'archétype. Le profil scouting de Gallagher dit :',

    dach_title: '4 · Le trio de Dach descend au 4ᵉ — ce que ça coûte vraiment',
    dach_intro: (`Le trio qui a inscrit les deux buts à 5 c. 5 plus la mise en place du but de la ` +
                `prolongation au M3 — Texier–Dach–Bolduc — descend intact à des minutes de 4ᵉ trio. ` +
                `Les mathématiques disent que le coût est faible en termes d\'iso parce que : ` +
                `(a) un iso net60 de ${fmtFr(swapB.trio_avg_iso_net60, 3)} pour le trio est positif mais pas ` +
                `énorme, et (b) ${swapB.minutes_lost_per_game.toFixed(1).replace('.', ',')} minutes ` +
                `de moins à 5 c. 5 n\'accumulent que ${fmtFr(swapB.per_game_xg_cost, 2)} buts attendus/match ` +
                `dans le modèle. Le vrai risque, c\'est ce que le modèle ne peut pas capter : la ` +
                `variance de finition décisive et l\'effet en cascade de mettre votre trio en feu derrière ` +
                `deux trios qui n\'ont pas marqué à 5 c. 5 dans la série.`),

    demidov_title: '5 · La promotion de Demidov, c\'est l\'échange pour la reconstruction du 3ᵉ',
    demidov_intro: (`Promouvoir Demidov du 3ᵉ au 2ᵉ trio, c\'est ce qui rend la réunion ` +
                   `Anderson–Danault–Gallagher possible. L\'iso net60 regroupé du trio Newhook–Evans–Demidov à ` +
                   `${fmtFr(g5.L2.avg_iso_net60, 3)} est le coût mathématique (contre ` +
                   `${fmtFr(g4.L2.avg_iso_net60, 3)} pour le 2ᵉ trio du M4, le Texier–Dach–Bolduc qui se ` +
                   `retrouve au 4ᵉ). Cet écart de ${fmtFr(g5.L2.avg_iso_net60 - g4.L2.avg_iso_net60, 3)} ` +
                   `sur le créneau du 2ᵉ trio, c\'est le coût; le gain de ${fmtFr(lineIsoSwing('L3'), 3)} ` +
                   `au 3ᵉ trio, c\'est le bénéfice. Net : **${fmtFr(lineIsoSwing('L2') + lineIsoSwing('L3'), 3)}** ` +
                   `combiné sur les créneaux 2ᵉ + 3ᵉ trios.`),
    demidov_caveat: ('Mise en garde : l\'échantillon 5 c. 5 regroupé de Demidov est petit et le moteur ' +
                    'iso suppose que les taux par 60 tiennent à travers les niveaux de compétition. ' +
                    'Des minutes de top-6 contre Cernák / Sergachev ne sont pas équivalentes à des ' +
                    'minutes de 3ᵉ trio contre le 3ᵉ duo de Tampa — le modèle ne peut isoler le saut ' +
                    'de qualité d\'opposition.'),

    watch_title: '6 · À surveiller',
    watch: [
      '**Le déploiement du trio Anderson–Danault–Gallagher contre quoi.** Cooper a le dernier changement. S\'il aligne le C défensif Cirelli contre ce trio, on respecte la lecture du trio de warriors. S\'il met plutôt Cirelli sur Suzuki, le Canadien est exposé là où la projection l\'aimait.',
      '**Les minutes de Demidov à 5 c. 5 contre Cernák / Sergachev.** L\'exposition au premier duo, c\'est le test. Si Demidov accumule des évènements positifs contre le top D, sa promotion au 2ᵉ trio paie sa place. S\'il subit une pression soutenue, attendez-vous à un brassage avant la 3ᵉ.',
      '**Le déploiement du trio de Dach au 4ᵉ.** S\'ils héritent de restes d\'avantage numérique et de présences avantageuses au matchup, le calcul iso reste favorable. Si on les réduit à du forecheck-et-mourir de 4ᵉ trio, le taux de finition en séries du trio producteur s\'enterre sous un faible temps de glace.',
      '**Les minutes en désavantage et au PP2 de Gallagher.** S\'il est au PP2 et au DN, la projection ne supposait que des minutes de 3ᵉ trio à 5 c. 5 — un déploiement à forces inégales devient une plus-value non modélisée.',
      '**Le changement de côté de Slafkovský au 1ᵉʳ trio.** Même trio qu\'au M4, côtés inversés. L\'effet sur l\'iso est petit, mais les préférences de transport et d\'entrée changent.',
    ],

    framework_title: 'À propos de ce survol',
    framework_intro: ('Lemieux est un cadriciel d\'analyse hockey à code source ouvert : moteur de ' +
                     'comparables kNN sur caractéristiques standardisées, étiquettes scouting ' +
                     'extraites par GenAI avec citation textuelle de provenance, moteur d\'échange ' +
                     'avec IC à 80 % sur base regroupée, et études d\'effet par cohorte d\'étiquettes ' +
                     'qui vérifient si les descripteurs qualitatifs prédisent réellement le ' +
                     'comportement. Chaque chiffre du survol se rattache à une requête contre le ' +
                     'code source ouvert.'),

    caveats_title: 'Mises en garde',
    caveats: [
      `La projection de Marinaro est **une** source. Les trios finaux sont confirmés à la mise au jeu. Le survol calque ses suppositions sur la projection de Marinaro; si d\'autres trios sont déployés, l\'analyse roule à nouveau.`,
      'L\'iso regroupé suppose que les taux par 60 tiennent à travers les contextes de trio + compétition. Les vrais effets de chimie ne sont pas capturés.',
      'Suppositions de temps de glace : L1=14 / L2=12 / L3=10 / L4=7,5 minutes 5 c. 5 par match. Les bandes d\'IC supposent la stabilité du créneau — Cooper peut compresser les minutes de 4ᵉ trio bien sous 7,5 dans des matchs pilotés par les confrontations.',
      'Gallagher n\'a pas joué dans cette série. L\'iso regroupé utilise 24-25 + 25-26 saison régulière + séries. La prétention de stabilité d\'échantillon porte sur la cohorte de comparables, pas sur lui individuellement.',
      'Étude de relèvement par cohorte warrior : n=4 warriors. L\'IC exclut zéro, mais un bootstrap sur 4 valeurs recycle les mêmes 4 points. Suggestif, pas porteur.',
      'Aucune prédiction du résultat du M5. Le cadriciel évalue des scénarios; il ne prédit pas.',
    ],

    sources_title: 'Sources',
    sources: [
      ['Tony Marinaro · The Sick Podcast (projection des trios, X.com)', 'https://x.com/TonyMarinaro'],
      ['Pierre LeBrun · TSN — Gallagher probablement IN', 'https://www.tsn.ca/nhl/article/ice-chips-hagel-will-play-in-game-5-dastous-a-gtd-hedman-still-out-for-lightning/'],
      ['Rapports de remaniement à l\'entraînement · Montreal Hockey Fanatics', 'https://www.montrealhockeyfanatics.com/'],
      ['Cadriciel ouvert Lemieux + modèle de données', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · survol d\'avant-match · CH @ TBL M5',
    footer_right: 'Page',
  },
};

// ---------- sections ----------
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
  // Inline-styled prose with a colored callout box feel — branded, easy to scan.
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

function lineupSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const join = (line) => line.map(p => p.split(' ').slice(-1)[0]).join(' – ');
  const rows = ["L1", "L2", "L3", "L4"].map(role => {
    const swing = lineIsoSwing(role);
    const opts = { fills: [
      null, null,
      g4[role]?.avg_iso_net60 > 0 ? BRAND.pos : (g4[role]?.avg_iso_net60 < 0 ? BRAND.neg : null),
      null,
      g5[role]?.avg_iso_net60 > 0 ? BRAND.pos : (g5[role]?.avg_iso_net60 < 0 ? BRAND.neg : null),
      fillForDelta(swing),
    ] };
    return {
      cells: [
        role,
        join(D.lines_g4[role]),
        fmtN(g4[role]?.avg_iso_net60, 3),
        join(D.lines_g5_projected[role]),
        fmtN(g5[role]?.avg_iso_net60, 3),
        fmtN(swing, 3),
      ],
      _opts: opts,
    };
  });
  return [
    h1(t.lineup_title), para(t.lineup_intro, { italics: true }),
    dataTable(
      [t.th_role, t.th_g4, t.th_g4_iso, t.th_g5, t.th_g5_iso, t.th_swing],
      rows, [600, 2400, 1100, 2400, 1100, 1100]
    ),
  ];
}

function swapsSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const r1 = [
    'A · Kapanen → Gallagher (mechanical 18th-forward swap, 10-min L3 slot)',
    fmtN(swapA.delta_xgf60, 2),
    fmtN(swapA.delta_xga60, 2),
    fmtN(swapA.delta_net, 2),
    `[${fmtN(swapA.delta_xgf_ci80[0], 2)}, ${fmtN(swapA.delta_xgf_ci80[1], 2)}]`,
    `[${fmtN(swapA.delta_xga_ci80[0], 2)}, ${fmtN(swapA.delta_xga_ci80[1], 2)}]`,
  ];
  const r2 = [
    `B · Dach trio L2 → L4 (-${swapB.minutes_lost_per_game.toFixed(1)} min/game, same per-60 iso)`,
    '—',
    '—',
    fmtN(swapB.per_game_xg_cost, 2),
    '—',
    '—',
  ];
  const r3 = [
    `C · Demidov L3 → L2 (+${swapC.minutes_gained_per_game.toFixed(1)} min/game, same per-60 iso)`,
    '—',
    '—',
    fmtN(swapC.per_game_xg_delta, 2),
    '—',
    '—',
  ];
  return [
    h1(t.swaps_title), para(t.swaps_intro, { italics: true }),
    dataTable(
      ['Move', 'Δ xGF/g', 'Δ xGA/g', 'Δ net/g', 'xGF 80% CI', 'xGA 80% CI'],
      [r1, r2, r3], [4500, 900, 900, 900, 1300, 1300]
    ),
  ];
}

function l3Section(t, lang) {
  const out = [h1(t.l3_title), para(t.l3_intro)];
  out.push(para(t.warrior_intro));
  // Show warrior tag with source quote — provenance rail
  const warriorTag = (tags['Brendan Gallagher'] || []).find(tg => tg.tag === 'warrior');
  if (warriorTag) {
    out.push(new Paragraph({
      spacing: { before: 80, after: 0 },
      children: [
        new TextRun({ text: `→ warrior `, bold: true, font: 'Arial', size: 18, color: BRAND.navy }),
        new TextRun({ text: `(conf ${warriorTag.confidence.toFixed(2)})`, color: BRAND.mute, font: 'Arial', size: 18 }),
      ],
    }));
    out.push(quoteBox(warriorTag.source_quote, warriorTag.source_url));
  }
  // Top-7 warrior comp drill-down
  const comps = D.warrior_study.comp_table.filter(c => c.is_warrior).slice(0, 8);
  if (comps.length) {
    out.push(h2('Gallagher\'s `warrior` comps in our model'));
    const rows = comps.map(c => [
      c.name, c.comp_score.toFixed(1),
      (lang === 'fr' ? fmtFr : fmt)(c.reg_iso_net60, 2),
      (lang === 'fr' ? fmtFr : fmt)(c.play_iso_net60, 2),
      (lang === 'fr' ? fmtFr : fmt)(c.lift, 2),
    ]);
    out.push(dataTable(
      ['Comp', 'Score', 'Reg iso/60', 'Play iso/60', 'Lift'],
      rows, [3000, 900, 1300, 1300, 1300]
    ));
  }
  return out;
}

function dachSection(t) { return [h1(t.dach_title), para(t.dach_intro)]; }
function demidovSection(t) {
  return [h1(t.demidov_title), para(t.demidov_intro), para(t.demidov_caveat, { italics: true })];
}
function watchSection(t) { return [h1(t.watch_title), ...bulletList(t.watch)]; }
function frameworkSection(t) { return [h2(t.framework_title), para(t.framework_intro, { italics: true })]; }
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

function runProseFactCheck() {
  // Pre-game: no scoring claims, no predictions of outcome.
  const corpus = [];
  for (const lang of ['en', 'fr']) {
    const t = T[lang];
    corpus.push(...t.tldr, ...t.watch, ...t.caveats, t.l3_intro, t.dach_intro, t.demidov_intro);
  }
  const text = corpus.join(' \n ');
  // Patterns that indicate a forbidden prediction. We exclude "we don't predict" /
  // "il ne prédit pas" — the framework's own anti-prediction rail uses those phrases.
  const banned = [
    /\bMTL\s+wins?\s+in\b/i, /\bvictoire\s+du\s+CH\s+en\b/i,
    /\bwill\s+win\b/i, /\bgagnera\b/i,
    /\b(we|I)\s+predict\b/i, /\bnous\s+prédisons\b/i,
  ];
  const violations = [];
  for (const re of banned) {
    const m = text.match(re);
    if (m) violations.push(`Banned pattern: "${m[0]}" (regex ${re.source})`);
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
        ...lineupSection(t, lang),
        ...swapsSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...l3Section(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...dachSection(t),
        ...demidovSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...watchSection(t),
        ...frameworkSection(t),
        ...caveatsSection(t),
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
    const out = path.join(__dirname, `game5_pregame_2026-04-29_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
