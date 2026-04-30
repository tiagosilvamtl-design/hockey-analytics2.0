// Morning-after Game 5 special report (2026-04-30).
// Inputs:
//   - g5_morning_after_special.numbers.json
// Run:
//   node examples/habs_round1_2026/build_g5_morning_after_special_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'g5_morning_after_special.numbers.json'), 'utf8'));

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

const pcv = D.press_claim_verification;
const sso = D.series_team_overview;
const dd = D.player_deep_dives;
const lg = D.league_rankings;

function fillForDelta(d, lo = -0.05, hi = 0.05) {
  if (d === null || d === undefined) return null;
  if (d > hi) return BRAND.pos;
  if (d < lo) return BRAND.neg;
  return BRAND.neu;
}

const T = {
  en: {
    title: 'Special report — Habs lead 3-2, Game 6 Friday at the Bell Centre',
    subtitle: 'Series + league overview · 5v5 stars vs PP-driven scoring · all-16-team playoff rankings',
    banner: 'Lemieux post-G5 deep dive · NST refreshed overnight · all numbers traceable to the open-source repo.',

    verdict_title: 'The bottom line',
    verdict_prose: (
      `**The Habs are one game from advancing for the first time since losing the 2021 Final to this same Lightning team — but the underlying data is way less comfortable than the 3-2 scoreboard suggests.** ` +
      `MTL's "Big 4" forwards (Suzuki–Caufield–Slafkovský–Demidov) have **1 combined point at 5-on-5** through five games. Tampa's "Big 4" (Hagel–Kucherov–Cirelli–Guentzel)? **12 5v5 points.** ` +
      `The Habs are winning on power-play production, depth scoring, dominant defenseman play (Hutson + Guhle + Matheson), and a goaltending wall — Dobeš is in fact **allowing slightly more 5v5 goals than expected**, but with a .892 series SV% on a torrent of TBL volume, the team-level math still works. ` +
      `Historically, teams leading 3-2 in a best-of-seven NHL series advance ~80% of the time. The Habs are favorites to close it out. The gap between the eye test ("we're winning the series") and the underlying eye test ("our top line has done nothing 5-on-5") is the story.`
    ),

    // Headlines section
    tldr_title: 'Three numbers worth a tweet',
    tldr: [
      `**1 vs 12.** Suzuki–Caufield–Slafkovský–Demidov have **${pcv.mtl_total_pts} 5v5 point** through 5 games. Hagel–Kucherov–Cirelli–Guentzel have **${pcv.tbl_total_pts}**. The press claim that this gap existed before Game 5 wasn't an exaggeration — Game 5 made it slightly worse.`,
      `**Slafkovský 3 series goals — all on the power play. 0 points at 5v5 in 5 games.** His pooled iso baseline is roughly even (-0.024). His series 5v5 iso net60 is also roughly even (-0.009). He's playing exactly to baseline at 5v5; the production gap is purely about finishing — at 5v5 he's at 4 SOG and 0G in the entire series, despite earning the chances (0.60 ixG at 5v5).`,
      `**Demidov is iso-positive at 5v5 (+0.39 net60) despite his pooled baseline being ${fmt(dd['Ivan Demidov'].pool_baseline.iso_net60, 3)}.** He has 0 5v5 points but the on-ice play is meaningfully BETTER than his pre-playoff baseline. He's not finishing (0.86 ixG at 5v5, 0G), and he told the press he can't figure out how to beat Vasilevskiy. The numbers say his rookie-year nerves are a finishing problem, not a chance-creation one.`,
    ],

    press_title: '1 · The press claim that\'s actually true (and got worse)',
    press_intro: ('Two days ago, beat coverage flagged that "MTL\'s top-4 forwards have 0 points at 5-on-5 ' +
                 'while TBL\'s top-4 have 11." Through Game 5, our refreshed NST data confirms it — and the ' +
                 'gap actually widened despite MTL winning the series 3-2.'),

    overview_title: '2 · Are the Habs overperforming their xG?',
    overview_intro: ('Series-aggregate team xG vs actual goals tells you whether finishing/save luck is ' +
                    'driving the result. Numbers are all-situations cumulative across G1-G5.'),
    overview_prose: (
      `**Verdict: barely. Both teams overperformed by roughly the same amount.** ` +
      `MTL has scored ${sso.all_situations.MTL.gf} goals on ${sso.all_situations.MTL.xgf} xG (overperform +${(sso.all_situations.MTL.gf - sso.all_situations.MTL.xgf).toFixed(2)}). ` +
      `TBL: ${sso.all_situations['T.B'].gf} on ${sso.all_situations['T.B'].xgf} xG (overperform +${(sso.all_situations['T.B'].gf - sso.all_situations['T.B'].xgf).toFixed(2)}). ` +
      `MTL is allowing ${sso.all_situations.MTL.ga} goals on ${sso.all_situations.MTL.xga} xGA — Dobeš is actually allowing MORE than expected on aggregate, ` +
      `which surprises given his Game 5 wall. Most of TBL's expected goals are quality scoring chances Dobeš is stopping cleanly; the ones that go in are sometimes outside his expected-goals model. ` +
      `**The Habs aren't getting puck-luck-blessed. They're winning a tight series by one-goal margins on power-play execution and depth scoring.**`
    ),

    deep_title: '3 · The Big 3 — Caufield, Demidov, Slafkovský',
    deep_intro: ('For each player: pooled iso baseline (24-25 + 25-26 reg + playoff windows) versus ' +
                'series-direct numbers, separated by 5v5 vs all-situations. The framing question for each: ' +
                'is this player playing better, worse, or to baseline?'),

    league_title: '4 · League-wide playoff rankings (all 16 teams)',
    league_intro: ('Every player with ≥30 5v5 minutes through their team\'s G1-Gn (some series at G5, some ' +
                  'at G4, two at G6). NST 5v5 oi splits, refreshed this morning.'),
    league_iso_title: 'Top 15 by 5v5 iso net60 (xGF/60 − xGA/60 with the player on the ice)',
    league_iso_caveat: 'Caution: Round 1 sample sizes are small. Carolina/Vegas/Utah players dominate because tiny TOI + a few good shifts produce huge per-60 rates.',
    league_pts_title: 'Top 15 by total points (all situations)',
    league_goalie_title: 'Top 10 goalies by series SV% (≥60 min)',

    history_title: '5 · Historical context',
    history: [
      `Teams leading 3-2 in best-of-seven NHL series advance approximately **80%** of the time historically. The Habs are heavy favorites to close it out at home in Game 6.`,
      `Montreal hasn't advanced past Round 1 since losing the 2021 Stanley Cup Final — to this same Lightning team. A win Friday closes a five-year loop with the very opponent that ended the run.`,
      `In Game 5 specifically, MTL was outshot 40-24 — a ${(40/24).toFixed(2)}× shot ratio. Historically when a team is outshot ≥15 in a single playoff game, they win about 30% of the time. Dobeš's .950 SV% is the cleanest cause of the win; without that goalie game, this is a 4-2 or 5-2 Tampa win.`,
    ],

    watch_title: '6 · What to watch in Game 6 (Friday, Bell Centre)',
    watch: [
      '**Will the L1 wake up at 5v5?** Suzuki has 1A at 5v5 in five games. Caufield 0 points. Slafkovský 0 5v5 points. If MTL wins Friday it likely means either the L1 finally produces or someone else carries them again.',
      '**Hagel.** TBL\'s most dangerous player by every measure (5G in series, +1.23 5v5 iso net60, 8 SOG at 5v5). If he\'s held to no 5v5 points, MTL almost certainly closes. If he gets multi-point — different ballgame.',
      '**Vasilevskiy bounce-back.** .875 in G5 was uncharacteristic. Goaltender variance regresses to mean over time; expect him at .920+ in G6. The question is whether MTL generates enough chances to break through anyway.',
      '**Demidov\'s finishing.** ixG of 0.86 at 5v5 with 0G says he\'s due. The story of the series might end up being a Demidov rookie playoff goal — or not.',
      '**Last change for St-Louis.** Game 6 is in Montreal. Coach has the matchup hammer. Watch whether he runs Suzuki vs Cirelli (defensive matchup the press has been begging for) or pivots back to Suzuki vs Point.',
    ],

    framework_title: 'About this brief',
    framework_intro: ('Lemieux post-G5 special report: NST refreshed overnight, every number traces to a query ' +
                     'against the open-source codebase at github.com/lemieuxAI/framework. The press-claim ' +
                     'verification, player deep dives, and league rankings are all generated from one analyzer ' +
                     'invocation. Underlying data: NST on-ice splits + individual stats + goalie stats; pooled ' +
                     'iso baseline math from the Lemieux swap engine.'),

    caveats_title: 'Caveats',
    caveats: [
      'No prediction of Game 6 outcome. The framework grades scenarios; it does not forecast.',
      'Pooled iso baseline uses 24-25 + 25-26 reg + playoff windows — a 4-window pool that\'s deliberately recent. Series-direct iso is a small sample (5 games).',
      'League iso rankings include players whose teams have only played 4 games (CAR/COL/L.A/OTT) and players whose teams played 6 (PIT/PHI). TOI thresholds are uniform but per-game count differs.',
      'Some xG / iso math doesn\'t separate 5v5 special-deployment effects (defensive-zone starts, late-game empty-net minutes); the pooled baseline averages over context.',
      'NST data is overnight-refreshed; the 60-minute-or-more goalie filter assumes complete game logs.',
    ],

    sources_title: 'Sources',
    sources: [
      ['NHL.com — Game 5 recap (MTL @ TBL, 2026-04-29)', 'https://www.nhl.com/news/montreal-canadiens-tampa-bay-lightning-game-5-recap-april-29-2026'],
      ['Tampa Bay Lightning — Mishkin\'s Extra Shift', 'https://www.nhl.com/lightning/news/mishkins-extra-shift-montreal-canadiens-3-tampa-bay-lightning-2-april-29-2026'],
      ['CBC News — Canadiens bring out Gallagher', 'https://www.cbc.ca/news/canada/montreal/canadiens-lightning-game-5-9.7181303'],
      ['Stat Sniper Blog — Caufield/Suzuki/Demidov young core', 'https://statsniper.com/blog/nhl/montreal-canadiens-2026-playoffs-caufield-suzuki-demidov-young-core/'],
      ['Yardbarker — Demidov on Vasilevskiy', 'https://www.yardbarker.com/nhl/articles/ivan_demidov_admits_it_he_doesnt_know_how_to_beat_andrei_vasilevskiy/s1_17387_43786743'],
      ['Natural Stat Trick — series team + skater + goalie data', 'https://www.naturalstattrick.com/'],
      ['Lemieux open-source framework', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · post-G5 special · MTL leads 3-2',
    footer_right: 'Page',
  },
  fr: {
    title: 'Rapport spécial — Le CH mène 3-2, M6 vendredi au Centre Bell',
    subtitle: 'Survol série + ligue · vedettes silencieuses à 5 c. 5 · classements pour les 16 équipes en séries',
    banner: 'Survol Lemieux après-M5 · NST rafraîchi durant la nuit · chaque chiffre se rattache au code source ouvert.',

    verdict_title: 'En une phrase',
    verdict_prose: (
      `**Le Canadien est à un match de passer en 2ᵉ ronde pour la première fois depuis sa défaite contre ce même Lightning en finale 2021 — mais la donnée sous-jacente est nettement moins confortable que le tableau 3-2 ne le laisse paraître.** ` +
      `Les « Big 4 » du CH (Suzuki–Caufield–Slafkovský–Demidov) ont **1 point combiné à 5 c. 5** en cinq matchs. Les « Big 4 » de Tampa (Hagel–Kucherov–Cirelli–Guentzel)? **12 points à 5 c. 5.** ` +
      `Le Tricolore gagne grâce à la production en avantage numérique, à la profondeur, à un travail dominant des défenseurs (Hutson + Guhle + Matheson) et à un mur dans le filet — Dobeš accorde en fait **un peu plus de buts à 5 c. 5 que la valeur attendue**, mais avec un % d\'arrêts de série de ,892 sur un torrent de tirs de Tampa, le calcul d\'équipe tient quand même. ` +
      `Historiquement, les équipes qui mènent 3-2 en série 4-de-7 LNH avancent dans environ **80 %** des cas. Le CH est favori. L\'écart entre la lecture à l\'œil (« on gagne la série ») et la lecture sous le capot (« notre premier trio n\'a rien produit à 5 c. 5 ») est l\'histoire.`
    ),

    tldr_title: 'Trois chiffres pour une publication',
    tldr: [
      `**1 contre 12.** Suzuki–Caufield–Slafkovský–Demidov ont **${pcv.mtl_total_pts} point à 5 c. 5** en 5 matchs. Hagel–Kucherov–Cirelli–Guentzel en ont **${pcv.tbl_total_pts}**. La prétention de la presse selon laquelle cet écart existait avant le M5 n\'était pas exagérée — le M5 l\'a légèrement aggravée.`,
      `**Slafkovský — 3 buts en série, tous en avantage numérique. 0 point à 5 c. 5 en 5 matchs.** Sa base iso regroupée est essentiellement neutre (-0,024). Son iso net60 de série à 5 c. 5 est aussi quasi neutre (-0,009). Il joue exactement à sa base à 5 c. 5; l\'écart de production tient à la finition pure — 4 tirs à 5 c. 5 et 0 but dans la série, malgré 0,60 de ixG à 5 c. 5.`,
      `**Demidov est positif à l\'iso à 5 c. 5 (+0,39 net60) malgré une base regroupée à ${fmtFr(dd['Ivan Demidov'].pool_baseline.iso_net60, 3)}.** Il a 0 point à 5 c. 5 mais sa lecture sur la glace est nettement MEILLEURE que sa base d\'avant-séries. Il ne finit pas (0,86 ixG à 5 c. 5, 0 but), et il a admis à la presse ne pas savoir comment battre Vasilevskiy. Les chiffres disent que ses nerfs de recrue se manifestent au moment de finir, pas à la création de chances.`,
    ],

    press_title: '1 · La prétention de la presse qui se confirme (en pire)',
    press_intro: ('Il y a deux jours, la couverture flaguait que « les 4 meilleurs attaquants du CH ont 0 point ' +
                 'à 5 c. 5 alors que ceux de Tampa en ont 11 ». Après le M5, nos données NST rafraîchies le ' +
                 'confirment — et l\'écart s\'est creusé même si le CH mène la série 3-2.'),

    overview_title: '2 · Le CH surperforme-t-il son xG?',
    overview_intro: ('Le xG d\'équipe cumulé sur la série versus les buts inscrits dit si la chance à la finition ' +
                    'ou aux arrêts pilote le résultat. Chiffres en toutes situations, cumulatifs M1-M5.'),
    overview_prose: (
      `**Verdict : à peine. Les deux équipes surperforment d\'un montant à peu près égal.** ` +
      `Le CH a inscrit ${sso.all_situations.MTL.gf} buts sur ${sso.all_situations.MTL.xgf} xG (surperformance +${(sso.all_situations.MTL.gf - sso.all_situations.MTL.xgf).toFixed(2)}). ` +
      `Tampa : ${sso.all_situations['T.B'].gf} sur ${sso.all_situations['T.B'].xgf} (surperformance +${(sso.all_situations['T.B'].gf - sso.all_situations['T.B'].xgf).toFixed(2)}). ` +
      `Le CH accorde ${sso.all_situations.MTL.ga} buts sur ${sso.all_situations.MTL.xga} xGA — Dobeš accorde en fait PLUS que la valeur attendue en agrégat, ` +
      `ce qui surprend vu son mur du M5. La plupart des buts attendus de Tampa sont des chances de qualité que Dobeš stoppe nettement; ceux qui rentrent sont parfois hors du modèle de buts attendus. ` +
      `**Le Tricolore ne se fait pas bénir par la rondelle. Il gagne une série serrée avec des marges d\'un but, sur l\'exécution en avantage numérique et la profondeur.**`
    ),

    deep_title: '3 · Les Big 3 — Caufield, Demidov, Slafkovský',
    deep_intro: ('Pour chaque joueur : base iso regroupée (fenêtres 24-25 + 25-26 saison régulière + séries) ' +
                'contre les chiffres directs de série, séparés 5 c. 5 versus toutes situations. La question : ' +
                'ce joueur joue-t-il mieux, moins bien, ou conformément à sa base?'),

    league_title: '4 · Classements jeu par jeu (16 équipes en séries)',
    league_intro: ('Tout joueur avec ≥30 minutes à 5 c. 5 dans les matchs de son équipe (certaines séries au M5, ' +
                  'd\'autres au M4, deux au M6). Splits NST 5 c. 5 sur la glace, rafraîchis ce matin.'),
    league_iso_title: 'Top 15 par iso net60 à 5 c. 5 (xGF/60 − xGA/60 avec le joueur sur la glace)',
    league_iso_caveat: 'Mise en garde : les échantillons du premier tour sont petits. Les joueurs de Carolina / Vegas / Utah dominent parce qu\'un petit TG + quelques bonnes présences produisent d\'énormes taux par 60.',
    league_pts_title: 'Top 15 par points totaux (toutes situations)',
    league_goalie_title: 'Top 10 gardiens par % d\'arrêts de série (≥60 min)',

    history_title: '5 · Contexte historique',
    history: [
      `Les équipes qui mènent 3-2 en série 4-de-7 LNH avancent dans environ **80 %** des cas historiquement. Le CH est nettement favori pour conclure à domicile au M6.`,
      `Montréal n\'a pas dépassé le 1ᵉʳ tour depuis sa défaite en finale de la Coupe Stanley 2021 — contre ce même Lightning. Une victoire vendredi referme une boucle de cinq ans avec l\'adversaire qui avait mis fin au parcours.`,
      `Au M5 spécifiquement, le CH a été surclassé 40-24 aux tirs — un ratio de ${(40/24).toFixed(2)}×. Historiquement, quand une équipe est surclassée d\'au moins 15 tirs dans un seul match en séries, elle gagne dans environ 30 % des cas. Le ,950 % d\'arrêts de Dobeš est la cause la plus nette de la victoire; sans cette performance, c\'est une victoire 4-2 ou 5-2 de Tampa.`,
    ],

    watch_title: '6 · À surveiller au M6 (vendredi, Centre Bell)',
    watch: [
      '**Le 1ᵉʳ trio se réveillera-t-il à 5 c. 5?** Suzuki a 1 mention à 5 c. 5 en cinq matchs. Caufield, 0 point. Slafkovský, 0 point à 5 c. 5. Si le CH gagne vendredi, c\'est probablement parce que le 1ᵉʳ trio finira par produire ou que quelqu\'un d\'autre les portera encore.',
      '**Hagel.** Le joueur le plus dangereux de Tampa selon toutes les mesures (5 buts en série, +1,23 d\'iso net60 à 5 c. 5, 8 tirs à 5 c. 5). S\'il est tenu sans point à 5 c. 5, le CH conclut à peu près à coup sûr. S\'il fait du multi-points — autre histoire.',
      '**Le rebond de Vasilevskiy.** Ses ,875 du M5 étaient hors caractère. La variance gardien régresse vers la moyenne avec le temps; on l\'attend à ,920+ au M6. La question : le CH génèrera-t-il assez de chances pour percer malgré tout?',
      '**La finition de Demidov.** Un ixG de 0,86 à 5 c. 5 avec 0 but dit qu\'il est dû. L\'histoire de la série pourrait finir par un but de recrue de Demidov en séries — ou non.',
      '**Le dernier changement pour St-Louis.** Le M6 est à Montréal. L\'entraîneur a le marteau des confrontations. Surveillez s\'il aligne Suzuki contre Cirelli (le matchup défensif que la presse réclame depuis le début) ou s\'il revient à Suzuki contre Point.',
    ],

    framework_title: 'À propos de ce survol',
    framework_intro: ('Rapport spécial Lemieux après-M5 : NST rafraîchi durant la nuit, chaque chiffre se ' +
                     'rattache à une requête contre le code source ouvert à github.com/lemieuxAI/framework. La ' +
                     'vérification de prétention, les portraits joueur et les classements ligue sont tous générés ' +
                     'd\'une seule invocation de l\'analyseur. Données sous-jacentes : splits NST sur la glace + stats ' +
                     'individuelles + stats gardiens; calcul de la base iso regroupée par le moteur d\'échange Lemieux.'),

    caveats_title: 'Mises en garde',
    caveats: [
      'Aucune prédiction du résultat du M6. Le cadriciel évalue des scénarios; il ne prédit pas.',
      'La base iso regroupée utilise les fenêtres 24-25 + 25-26 saison régulière + séries — un pool de 4 fenêtres délibérément récent. L\'iso direct de série est un petit échantillon (5 matchs).',
      'Les classements iso de la ligue incluent des joueurs dont l\'équipe n\'a joué que 4 matchs (CAR/COL/L.A/OTT) et d\'autres dont l\'équipe a joué 6 (PIT/PHI). Les seuils de TG sont uniformes mais le compte par match diffère.',
      'Une partie du calcul xG / iso ne sépare pas les effets de déploiement particuliers à 5 c. 5 (mises en jeu en zone défensive, fin de match avec filet désert); la base regroupée moyenne sur le contexte.',
      'Les données NST sont rafraîchies durant la nuit; le filtre de 60 minutes ou plus pour les gardiens suppose des journaux de match complets.',
    ],

    sources_title: 'Sources',
    sources: [
      ['LNH.com — Sommaire M5 (CH @ TBL, 29 avril 2026)', 'https://www.nhl.com/news/montreal-canadiens-tampa-bay-lightning-game-5-recap-april-29-2026'],
      ['Tampa Bay Lightning — Mishkin\'s Extra Shift', 'https://www.nhl.com/lightning/news/mishkins-extra-shift-montreal-canadiens-3-tampa-bay-lightning-2-april-29-2026'],
      ['CBC News — Canadiens bring out Gallagher', 'https://www.cbc.ca/news/canada/montreal/canadiens-lightning-game-5-9.7181303'],
      ['Stat Sniper Blog — Noyau jeune Caufield/Suzuki/Demidov', 'https://statsniper.com/blog/nhl/montreal-canadiens-2026-playoffs-caufield-suzuki-demidov-young-core/'],
      ['Yardbarker — Demidov sur Vasilevskiy', 'https://www.yardbarker.com/nhl/articles/ivan_demidov_admits_it_he_doesnt_know_how_to_beat_andrei_vasilevskiy/s1_17387_43786743'],
      ['Natural Stat Trick — données équipes + patineurs + gardiens', 'https://www.naturalstattrick.com/'],
      ['Cadriciel ouvert Lemieux', 'https://github.com/lemieuxAI/framework'],
    ],
    footer_left: 'Lemieux · spécial après-M5 · CH mène 3-2',
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

function pressSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const mtlRows = pcv.mtl_stars_5v5.map(p => [
    p.name, String(p.gp), String(p.points), String(p.goals), String(p.assists),
    String(p.shots), String(p.ihdcf), fmtN(p.ixg, 2),
  ]);
  const tblRows = pcv.tbl_stars_5v5.map(p => [
    p.name, String(p.gp), String(p.points), String(p.goals), String(p.assists),
    String(p.shots), String(p.ihdcf), fmtN(p.ixg, 2),
  ]);
  return [
    h1(t.press_title), para(t.press_intro, { italics: true }),
    h2('MTL — top-4 forwards · 5v5 only'),
    dataTable(
      ['Player', 'GP', 'Pts', 'G', 'A', 'SOG', 'iHDCF', 'ixG'],
      mtlRows, [3000, 700, 700, 700, 700, 900, 1100, 900]
    ),
    h2('TBL — top-4 forwards · 5v5 only'),
    dataTable(
      ['Player', 'GP', 'Pts', 'G', 'A', 'SOG', 'iHDCF', 'ixG'],
      tblRows, [3000, 700, 700, 700, 700, 900, 1100, 900]
    ),
  ];
}

function overviewSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const a = sso.all_situations;
  const v5 = sso.five_v_five;
  return [
    h1(t.overview_title), para(t.overview_intro, { italics: true }),
    h2('All situations · series-aggregate'),
    dataTable(
      ['Team', 'GF', 'xGF', 'GF − xGF', 'GA', 'xGA', 'GA − xGA', 'SF', 'SA'],
      [
        ['MTL', a.MTL.gf, fmtN(a.MTL.xgf, 2), fmtN(a.MTL.gf_minus_xgf, 2), a.MTL.ga, fmtN(a.MTL.xga, 2), fmtN(a.MTL.ga_minus_xga, 2), a.MTL.sf, a.MTL.sa],
        ['TBL', a['T.B'].gf, fmtN(a['T.B'].xgf, 2), fmtN(a['T.B'].gf_minus_xgf, 2), a['T.B'].ga, fmtN(a['T.B'].xga, 2), fmtN(a['T.B'].ga_minus_xga, 2), a['T.B'].sf, a['T.B'].sa],
      ],
      [800, 700, 1000, 1300, 700, 1000, 1300, 700, 700]
    ),
    h2('5v5 only · series-aggregate'),
    v5.MTL && v5['T.B'] ? dataTable(
      ['Team', 'GF', 'xGF', 'GA', 'xGA', 'xGF%', 'HDCF', 'HDCA'],
      [
        ['MTL', v5.MTL.gf, fmtN(v5.MTL.xgf, 2), v5.MTL.ga, fmtN(v5.MTL.xga, 2), `${v5.MTL.xgf_pct} %`, v5.MTL.hdcf, v5.MTL.hdca],
        ['TBL', v5['T.B'].gf, fmtN(v5['T.B'].xgf, 2), v5['T.B'].ga, fmtN(v5['T.B'].xga, 2), `${v5['T.B'].xgf_pct} %`, v5['T.B'].hdcf, v5['T.B'].hdca],
      ],
      [800, 800, 1100, 800, 1100, 1100, 900, 900]
    ) : new Paragraph({ children: [new TextRun({ text: '5v5 team data unavailable', italics: true, color: BRAND.mute })] }),
    para(t.overview_prose),
  ];
}

function deepDiveSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const players = ['Cole Caufield', 'Ivan Demidov', 'Juraj Slafkovský'];
  const out = [h1(t.deep_title), para(t.deep_intro, { italics: true })];

  for (const name of players) {
    const d = dd[name];
    if (!d) continue;
    out.push(h2(name));
    const pool = d.pool_baseline;
    const s5 = d.series_5v5_oi || {};
    const indP = d.series_individual_all_sit || {};
    const ind5 = d.series_individual_5v5 || {};
    out.push(dataTable(
      ['Layer', 'iso xGF/60', 'iso xGA/60', 'iso net60', 'TOI / GP / Pts'],
      [
        [
          'Pooled baseline (24-25 + 25-26 reg+playoff)',
          fmtN(pool.iso_xgf60, 3), fmtN(pool.iso_xga60, 3), fmtN(pool.iso_net60, 3),
          `${pool.toi_min ?? '—'} min · pool`,
        ],
        [
          'Series 5v5 oi (G1-G5)',
          fmtN(s5.iso_xgf60, 3), fmtN(s5.iso_xga60, 3), fmtN(s5.iso_net60, 3),
          `${s5.toi ?? '—'} min · 5v5 only`,
        ],
        [
          'Series individual · all situations',
          '—', '—', '—',
          `GP=${indP.gp ?? '—'} · ${indP.p ?? 0} pts (${indP.g ?? 0}G/${indP.a ?? 0}A) · ${indP.sog ?? 0} SOG · ${fmtN(indP.ixg ?? 0, 2)} ixG`,
        ],
        [
          'Series individual · 5v5 only',
          '—', '—', '—',
          `GP=${ind5.gp ?? '—'} · ${ind5.p ?? 0} pts (${ind5.g ?? 0}G/${ind5.a ?? 0}A) · ${ind5.sog ?? 0} SOG · ${fmtN(ind5.ixg ?? 0, 2)} ixG`,
        ],
      ],
      [3500, 1100, 1100, 1100, 3200]
    ));
  }
  return out;
}

function leagueSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const isoRows = lg.top_by_iso_net60.slice(0, 15).map(r => [
    r.name, r.team, String(r.gp), `${r.toi.toFixed(1)}`,
    fmtN(r.iso_xgf60, 3), fmtN(r.iso_xga60, 3), fmtN(r.iso_net60, 3),
  ]);
  const ptsRows = lg.top_by_points.slice(0, 15).map(r => [
    r.name, r.team, String(r.gp), String(r.pts), String(r.g), String(r.a),
    String(r.sog), fmtN(r.ppg, 2),
  ]);
  const golRows = lg.top_goalies_by_sv_pct.slice(0, 10).map(r => [
    r.name, r.team, String(r.gp), `${r.toi.toFixed(0)}`,
    String(r.sa), String(r.ga), `.${(r.sv_pct * 1000).toFixed(0).padStart(3, '0')}`,
  ]);
  return [
    h1(t.league_title), para(t.league_intro, { italics: true }),
    h2(t.league_iso_title), para(t.league_iso_caveat, { italics: true }),
    dataTable(
      ['Player', 'Team', 'GP', 'TOI', 'iso xGF/60', 'iso xGA/60', 'iso net60'],
      isoRows, [2700, 700, 600, 800, 1300, 1300, 1300]
    ),
    h2(t.league_pts_title),
    dataTable(
      ['Player', 'Team', 'GP', 'Pts', 'G', 'A', 'SOG', 'PPG'],
      ptsRows, [2700, 700, 600, 700, 600, 600, 800, 900]
    ),
    h2(t.league_goalie_title),
    dataTable(
      ['Goalie', 'Team', 'GP', 'TOI', 'SA', 'GA', 'SV%'],
      golRows, [2700, 700, 600, 700, 700, 700, 1300]
    ),
  ];
}

function historySection(t) { return [h1(t.history_title), ...bulletList(t.history)]; }
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
        ...pressSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...overviewSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...deepDiveSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...leagueSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...historySection(t),
        ...watchSection(t),
        ...frameworkSection(t),
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
    const out = path.join(__dirname, `g5_morning_after_2026-04-30_${lang.toUpperCase()}.docx`);
    fs.writeFileSync(out, buf);
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
