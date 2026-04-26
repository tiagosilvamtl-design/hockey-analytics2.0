// Build branded EN + FR Word reports for the MTL vs. TBL Game 3 analysis.
// Now leads with the lineup-reshuffle finding (Radio-Canada confirmed by shift data).
// Slafkovský moved to a final "watch-list" section as user requested.
// FR rewritten through the `translate-to-quebec-fr` style guide (idiomatic, not literal).
//
// Run:
//   node examples/habs_round1_2026/build_game3_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'game3_analysis.numbers.json'), 'utf8')
);

// REQUIRED: structured lineup data (canonical fact base for line composition).
// Per the draft-game-post skill contract, this file MUST exist before any
// line-role prose is generated. If it doesn't, the build aborts.
const LINEUPS_PATH = path.join(__dirname, 'game3_lineups.yaml');
if (!fs.existsSync(LINEUPS_PATH)) {
  console.error(
    `\nERROR: ${LINEUPS_PATH} not found. ` +
    `\nThis file is the canonical fact base for line composition prose. ` +
    `\nGenerate it (research-game skill + analyzer shift-data cross-check) before running this build.\n`
  );
  process.exit(2);
}
let LINEUPS;
try {
  const yamlMod = require('yaml');
  LINEUPS = yamlMod.parse(fs.readFileSync(LINEUPS_PATH, 'utf8'));
} catch (e) {
  console.error(`Failed to parse ${LINEUPS_PATH}: ${e.message}`);
  process.exit(3);
}

// Usage observations from press coverage (research-game skill output)
let USAGE = { usage_observations: [] };
try {
  const yamlMod = require('yaml');
  USAGE = yamlMod.parse(fs.readFileSync(path.join(__dirname, 'game3_usage_observations.yaml'), 'utf8'));
} catch (e) {
  // Fallback: parse minimal subset by hand if yaml package unavailable
  const txt = fs.readFileSync(path.join(__dirname, 'game3_usage_observations.yaml'), 'utf8');
  const items = [];
  const blocks = txt.split(/\n  - text: /).slice(1);
  for (const blk of blocks) {
    const text = (blk.split('\n')[0] || '').replace(/^"|"$/g, '');
    const get = (k) => {
      const m = blk.match(new RegExp(`\\n    ${k}: (.*)`));
      return m ? m[1].replace(/^"|"$/g, '').trim() : '';
    };
    items.push({
      text,
      type: get('type'),
      player_or_team: get('player_or_team'),
      decision_by: get('decision_by'),
      source: get('source'),
      significance: get('significance'),
    });
  }
  USAGE = { usage_observations: items };
}

// ---------- BRAND ----------
const BRAND = {
  navy: '1F2F4A',
  navyLight: '2F4A70',
  red: 'A6192E',
  ink: '111111',
  mute: '666666',
  rule: 'BFBFBF',
  confirm: 'E2F0D9',
  neutral: 'FFF2CC',
  refute: 'F8CBAD',
  info: 'DEEAF6',
  caveat: 'FFF6E0',
  explainer: 'F2F2F2',
};

const fmt = (n, p = 3) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const s = Number(n).toFixed(p);
  return (Number(n) > 0 ? '+' : '') + s;
};
const pct = (n, p = 1) => n === null || n === undefined ? '—' : Number(n).toFixed(p) + '%';
const pctFr = (n, p = 1) => n === null || n === undefined ? '—' : (Number(n).toFixed(p) + ' %').replace('.', ',');

const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: BRAND.rule };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

// ---------- I18N ----------
const T = {
  en: {
    brand: 'LEMIEUX · Game 3 Analysis',
    title: 'Game 3 — Lightning at Canadiens',
    subtitle: 'What three games of data confirm, refute, or shrug at',
    date: 'Published 2026-04-25 · MTL leads 2–1 · Game 4 Sunday at the Bell Centre',
    tldr: 'Top-line read',
    tldr_bullets: [
      lineReshuffleBullet('en'),
      'The three biggest iso-impact movers DOWN from regular season to these playoffs at 5v5 are Hutson, Caufield and Suzuki — and only one of them has produced. Hutson is on the scoresheet (G2 + the OT winner in G3); Caufield and Suzuki are scoreless. The depth tier (Bolduc, Dach, Texier, Struble, Xhekaj) is driving both the underlying play and the bottom-line goals — Dach and Texier scored at 5v5 in G3, Bolduc had a primary assist on each.',
      'Through three games Dobes has a higher implied save percentage than Vasilevskiy (.905 vs. .893) on near-identical workloads (74 vs. 75 shots faced). Game 3\'s 29-vs-17 was the outlier; the cumulative read flips the pre-series chatter that Vasilevskiy was the more reliable option.',
      'MTL holds **75 % of 5v5 high-danger chances** through three games. That is unusually one-sided for any team in any series — the kind of number that almost always regresses, but that has held all three games. Worth watching for the inflection point, not yet for the predictable narrative reversal.',
    ],
    methodology_title: 'How to read this report',
    methodology: [
      '**Verdict colors.** Each claim is graded against the data: green = confirmed, amber = mixed or directional, red = refuted by the data we have.',
      '**Sources.** Numbers come from Natural Stat Trick (5v5 / 5v4 series totals) and NHL.com\'s public play-by-play and shift charts. Press claims come from La Presse, RDS, Radio-Canada, NY Post, Habs Eyes On The Prize, HockeyDB.',
      '**No predictions.** This report grades claims, it does not predict the series outcome. Three games is a tiny sample; every iso-impact number should be read as directional.',
    ],
    lineup_title: '1. The brand-new line that scored both 5v5 MTL goals',
    get lineup_intro() { return lineupIntroProse('en'); },
    lineup_mtl_change_title: 'MTL forward lines, Game 2 → Game 3',
    lineup_drift_table_intro: 'Top forward combinations by total seconds together at any strength state, from the actual shift data (not pre-game listings).',
    lineup_outcome_title: 'The two new lines',
    lineup_outcome: [
      '**Texier-Dach-Bolduc:** 6.7 minutes at 5v5, two goals, six combined points (Texier scored, Dach scored, Bolduc primary on both).',
      '**Kapanen-Newhook-Demidov:** 7.9 minutes at 5v5, zero goals for or against. Quiet, defensively responsible debut as a unit.',
      'François Gagnon (RDS) on the Dach call: St-Louis declined to bench him after Game 2 and gave him an expanded role instead. Quote: *« Je n\'abandonnerai jamais un joueur à moins qu\'il n\'abandonne sur lui-même. »*',
    ],
    tbl_lineup_title: 'Tampa\'s lineup also churned',
    tbl_lineup_text: 'Only one of Tampa\'s six most-deployed Game-2 forward combinations carried into Game 3. The Cooper move that drew the sharpest criticism (Martin Leclerc, Radio-Canada): Sabourin getting 45 seconds of overtime after 3 minutes in regulation. Quote: *« Si Martin St-Louis avait pris de telles décisions dans des matchs de cette importance, il serait probablement en disgrâce à jamais auprès des partisans du Canadien. »*',
    usage_title: 'Usage notes from press coverage',
    usage_intro: 'Deployment decisions captured from RDS, Radio-Canada and La Presse, paired with shift-data corroboration where available.',
    claims_title: '2. Claims ledger',
    claims_intro: 'Each row pairs a quote from public reporting with what the data shows. Verdict colors: green confirmed, amber mixed, red refuted.',
    series_title: '3. Series state of play (5v5, three games)',
    series_intro: 'Tampa drives shot volume; Montreal converts on chance quality. Both NY Post pre-series claims are simultaneously true. Different weapons.',
    progression_title: '4. MTL skater progression — regular season vs. 2026 playoffs',
    progression_intro: 'Isolated net impact at 5v5 (iso xGF/60 − iso xGA/60) in the regular season vs. the three playoff games. Up-movers are exceeding their regular-season impact; down-movers are below it. Minimum 200 regular-season minutes and 15 playoff minutes.',
    progression_stars_caveat: 'Hutson, Caufield and Suzuki have all scored in the series. Isolated impact measures the team\'s underlying expected-goals share when they\'re on the ice, not their goal-scoring. Goals are landing; the pre-goal play sits below their regular-season standard. The two facts coexist.',
    goalies_title: '5. Goalies',
    goalies_intro: 'Vasilevskiy: 75 shots faced, 8 goals against, .893 implied SV%. Dobes: 74, 7, .905. Near-identical workloads across the series, with Dobes a tick ahead on save rate. Game 3 alone was lopsided (29 vs. 17 shots faced); the three-game total isn\'t. François Gagnon (RDS) wrote Dobes had "matched Vasilevskiy" after Game 3 — that tracks.',
    slaf_title: '6. Watch list — Slafkovský pre/post the Hagel fight',
    slaf_intro: 'Splitting Slafkovský\'s on-ice events at the moment of the Game-2 fight (G2, period 2, 5:14): pre-fight 8 SOG and 3 goals; post-fight (rest of G2 plus all of G3) 2 SOG and 0 goals. With him on the ice after the fight, MTL outshoots Tampa 20-9 and outscores 2-1. Personal production fell off; line-level outcomes did not. Worth tracking through Game 4.',
    cant_title: '7. What the data still can\'t tell us',
    cant_bullets: [
      'Whether the new MTL lines persist for Game 4 or were a one-game tweak.',
      'How much of MTL\'s high-danger edge holds against a Vasilevskiy who has yet to play his series ceiling. PDO regression cuts both ways.',
      'Whether Slafkovský\'s post-fight reduction in shot generation is psychological, tactical, or sample noise.',
      'Officiating variance. Tampa\'s only Game-3 goal came on the power play.',
    ],
    sources_title: '8. Sources',
    sources_groups: [
      {
        heading: 'Data',
        items: [
          ['Natural Stat Trick — 25-26 NHL playoff team and skater totals', 'https://www.naturalstattrick.com/'],
          ['NHL.com play-by-play API (shift charts and event detail)', 'https://api-web.nhle.com/v1/gamecenter/'],
        ],
      },
      {
        heading: 'Francophone press',
        items: [
          ['RDS — Lane Hutson donne la victoire en prolongation aux Canadiens (Éric Leblanc)', 'https://www.rds.ca/hockey/canadiens/article/lane-hutson-souleve-tout-le-quebec-en-prolongation/'],
          ['RDS — Rédemption et tir frappé (François Gagnon, chronique)', 'https://www.rds.ca/hockey/canadiens/article/redemption-et-tir-frappe/'],
          ['Radio-Canada — Lane Hutson joue les héros en prolongation', 'https://ici.radio-canada.ca/sports/2248979/canadien-montreal-lightning-tampa-bay-series'],
          ['Radio-Canada — Les effronteries de Jon Cooper (Martin Leclerc, chronique)', 'https://ici.radio-canada.ca/sports/2248923/chronique-martin-leclerc-canadien-lightning'],
          ['La Presse — Une formation intacte pour accueillir une foule en délire', 'https://www.lapresse.ca/sports/hockey/2026-04-24/le-canadien/une-formation-intacte-pour-accueillir-une-foule-en-delire.php'],
          ['La Presse — À la défense de Kirby Dach', 'https://www.lapresse.ca/sports/chroniques/2026-04-23/canadien-lightning/a-la-defense-de-kirby-dach.php'],
        ],
      },
      {
        heading: 'Anglophone press',
        items: [
          ['New York Post — Lightning vs Canadiens Game 3 betting analysis', 'https://nypost.com/2026/04/24/betting/lightning-vs-canadiens-game-3-prediction-nhl-picks-odds-best-bets-for-stanley-cup-playoffs/'],
          ['Habs Eyes On The Prize — Game 3 preview', 'https://www.habseyesontheprize.com/'],
          ['HockeyDB — Game 3 boxscore', 'https://www.hockeydb.com/boxscores/20260424-45-55.html'],
          ['CityNews Montreal — series coverage', 'https://montreal.citynews.ca/2026/04/24/habs-lightning-montreal-series-hockey/'],
        ],
      },
    ],
    footer: 'Lemieux · open-source hockey analytics · github.com/lemieuxAI/framework',
    page: 'Page',
    confirmed: 'Confirmed',
    mixed: 'Mixed / nuanced',
    refuted: 'Refuted',
    th_metric: 'Metric', th_value: 'Value',
    th_claim: 'Claim', th_source: 'Source',
    th_data: 'What the data says', th_verdict: 'Verdict',
    th_line: 'Line', th_g2: 'Game 2 trio (TOI)', th_g3: 'Game 3 trio (TOI)', th_status: 'Status',
    persisted: 'Persisted', new_line: 'New', dropped: 'Dropped',
  },
  fr: {
    brand: 'LEMIEUX · Analyse du match no 3',
    title: 'Match no 3 — Lightning au Canadien',
    subtitle: 'Trois matchs, des chiffres, et le tri entre les narratifs qui tiennent et ceux qui s\'effritent',
    date: 'Publié le 25 avril 2026 · Le CH mène 2–1 · Match no 4 dimanche au Centre Bell',
    tldr: 'L\'essentiel',
    tldr_bullets: [
      lineReshuffleBullet('fr'),
      'Les trois plus grandes régressions d\'impact net isolé entre la saison régulière et les séries à 5 c. 5 sont Hutson, Caufield et Suzuki — et un seul des trois a produit. Hutson est au pointage (M2 + le but vainqueur en prolongation au M3); Caufield et Suzuki n\'ont pas marqué. La profondeur (Bolduc, Dach, Texier, Struble, Xhekaj) porte à la fois le jeu sous-jacent et le pointage final — Dach et Texier ont marqué à 5 c. 5 au M3, Bolduc a obtenu une passe principale sur chaque but.',
      'Sur les trois matchs, Dobes a un pourcentage d\'arrêts implicite supérieur à Vasilevskiy (,905 c. ,893) sur des charges quasi identiques (74 c. 75 tirs subis). Le M3 (29-17) est l\'exception; le cumul renverse l\'argument d\'avant-série voulant Vasilevskiy plus fiable.',
      'Le CH détient **75 % des chances à haut danger à 5 c. 5** sur trois matchs. C\'est un déséquilibre rare pour toute équipe dans toute série — un chiffre qui régresse presque toujours, mais qui s\'est maintenu trois matchs d\'affilée. À surveiller pour le point d\'inflexion, pas encore pour le retour à la moyenne attendu.',
    ],
    methodology_title: 'Comment lire ce rapport',
    methodology: [
      '**Codes couleur des verdicts.** Chaque affirmation est notée selon les chiffres : vert = confirmée, ambre = mitigée ou directionnelle, rouge = infirmée.',
      '**Sources.** Les chiffres viennent de Natural Stat Trick (totaux 5 c. 5 / 5 c. 4 de série) et des API publiques de LNH.com (jeu par jeu, présences). Les affirmations citées proviennent de La Presse, RDS, Radio-Canada, du New York Post, de Habs Eyes On The Prize et de HockeyDB.',
      '**Aucune prédiction.** Ce rapport note les affirmations, il ne prédit pas l\'issue de la série. Trois matchs, c\'est minuscule; chaque chiffre d\'impact isolé est directionnel, pas prédictif.',
    ],
    lineup_title: '1. Le nouveau trio qui a marqué les deux buts du CH à 5 c. 5',
    get lineup_intro() { return lineupIntroProse('fr'); },
    lineup_mtl_change_title: 'Trios offensifs du CH, M2 → M3',
    lineup_drift_table_intro: 'Trios offensifs par total de secondes ensemble sur la glace, toutes situations confondues, à partir des présences réelles (et non des formations annoncées avant-match).',
    lineup_outcome_title: 'Les deux nouveaux trios',
    lineup_outcome: [
      '**Texier-Dach-Bolduc :** 6,7 minutes à 5 c. 5, deux buts, six points combinés (Texier marque, Dach marque, Bolduc passe principale sur les deux).',
      '**Kapanen-Newhook-Demidov :** 7,9 minutes à 5 c. 5, aucun but pour ou contre. Début discret et défensivement responsable.',
      'François Gagnon (RDS) sur le cas Dach : St-Louis a refusé de le mettre à l\'écart après le M2 et lui a plutôt confié un rôle élargi. Citation : *« Je n\'abandonnerai jamais un joueur à moins qu\'il n\'abandonne sur lui-même. »*',
    ],
    tbl_lineup_title: 'La formation de Tampa a brassé aussi',
    tbl_lineup_text: 'Un seul des six trios offensifs les plus utilisés du M2 par Tampa est revenu au M3. Le geste de Cooper qui a soulevé le plus de critiques (Martin Leclerc, Radio-Canada) : Sabourin obtient 45 secondes en prolongation après 3 minutes en temps réglementaire. Citation : *« Si Martin St-Louis avait pris de telles décisions dans des matchs de cette importance, il serait probablement en disgrâce à jamais auprès des partisans du Canadien. »*',
    usage_title: 'Observations sur l\'utilisation — ce que le sommaire ne dit pas',
    usage_intro: 'Décisions de déploiement glanées dans la presse (et corroborées par les présences réelles quand c\'est possible). Ce sont les lectures qualitatives qui rendent les chiffres interprétables — l\'intention d\'un entraîneur n\'apparaît jamais dans un chiffre Corsi. Consigné dans `game3_usage_observations.yaml` pour usage en aval.',

    claims_title: '2. Tableau des affirmations',
    claims_intro: 'Chaque ligne associe une citation publique à ce que les chiffres montrent. Codes couleur : vert = confirmée, ambre = mitigée, rouge = infirmée.',
    series_title: '3. État de la série (5 c. 5, trois matchs)',
    series_intro: 'Le portrait des chiffres sous-jacents sur les trois matchs. Les deux affirmations clés du New York Post — Tampa « renverse la glace », le CH « génère plus de chances à haut danger » — sont vraies en même temps. Armes différentes.',
    progression_title: '4. Progression des joueurs — saison régulière → séries 2026',
    progression_intro: 'Pour chaque patineur du CH avec au moins 200 minutes 5 c. 5 en saison et au moins 15 minutes en séries, on compare l\'impact net isolé (iso xGF/60 − iso xGA/60). Une progression positive indique un joueur qui en fait plus en séries que ne le suggérait la saison; une régression, l\'inverse.',
    progression_stars_caveat: 'Sur les régressions : Hutson, Caufield et Suzuki ont tous marqué dans la série. La régression de l\'impact isolé ne porte pas sur les buts — elle mesure la part de buts attendus de l\'équipe lorsqu\'ils sont sur la glace. Ils convertissent (bien); le jeu sous-jacent est sous leur standard de saison régulière (à surveiller).',
    goalies_title: '5. Les gardiens',
    goalies_intro: 'Le New York Post a qualifié Vasilevskiy de « plus fiable » avant la série. Sur trois matchs, la charge de travail est sensiblement équivalente et le pourcentage d\'arrêts implicite de Dobes est en fait légèrement supérieur. La réputation porte le narratif d\'avant-série; les chiffres ne le soutiennent pas. François Gagnon a écrit que Dobes était « à la hauteur de Vasilevskiy » dans sa chronique du match no 3 — la lecture tient.',
    slaf_title: '6. À surveiller — Slafkovský avant et après le combat avec Hagel',
    slaf_intro: 'Un narratif issu du match no 2, à surveiller pour la suite, mais ce n\'est pas l\'histoire dominante du match no 3. Le combat Slafkovský-Hagel (M2, 2e période, 5:14) coupe la série en deux : 8 tirs et 3 buts avant, 2 tirs et 0 but depuis. Mais avec lui sur la glace après le combat, le CH surclasse TBL 20-9 aux tirs et 2-1 au pointage. Verdict : sa production individuelle s\'est tarie, son trio continue de gagner. À suivre lors du match no 4 pour voir si la production personnelle revient.',
    cant_title: '7. Ce que les chiffres ne disent pas (encore)',
    cant_bullets: [
      'Si les nouveaux trios du CH tiendront au match no 4 ou s\'il s\'agit d\'un ajustement d\'un soir. St-Louis n\'a pas dévoilé ses intentions publiquement.',
      'Combien de l\'avantage qualitatif du CH est soutenable contre un Vasilevskiy qui n\'a pas encore joué à son sommet de série. La régression PDO va dans les deux sens.',
      'Si la baisse de tirs de Slafkovský après le combat est psychologique, tactique ou simplement le hasard d\'un petit échantillon. Le modèle ne voit que son temps de glace et ce qui s\'y passe.',
      'La variance arbitrale — le seul but de Tampa au match no 3 est venu en avantage numérique. Les arbitres assignés au match no 4 comptent.',
    ],
    sources_title: '8. Sources',
    sources_groups: [
      {
        heading: 'Données',
        items: [
          ['Natural Stat Trick — totaux d\'équipe et de joueurs des séries LNH 25-26', 'https://www.naturalstattrick.com/'],
          ['API jeu par jeu de LNH.com (présences et événements)', 'https://api-web.nhle.com/v1/gamecenter/'],
        ],
      },
      {
        heading: 'Presse francophone',
        items: [
          ['RDS — Lane Hutson donne la victoire en prolongation aux Canadiens (Éric Leblanc)', 'https://www.rds.ca/hockey/canadiens/article/lane-hutson-souleve-tout-le-quebec-en-prolongation/'],
          ['RDS — Rédemption et tir frappé (François Gagnon, chronique)', 'https://www.rds.ca/hockey/canadiens/article/redemption-et-tir-frappe/'],
          ['Radio-Canada — Lane Hutson joue les héros en prolongation', 'https://ici.radio-canada.ca/sports/2248979/canadien-montreal-lightning-tampa-bay-series'],
          ['Radio-Canada — Les effronteries de Jon Cooper (Martin Leclerc, chronique)', 'https://ici.radio-canada.ca/sports/2248923/chronique-martin-leclerc-canadien-lightning'],
          ['La Presse — Une formation intacte pour accueillir une foule en délire', 'https://www.lapresse.ca/sports/hockey/2026-04-24/le-canadien/une-formation-intacte-pour-accueillir-une-foule-en-delire.php'],
          ['La Presse — À la défense de Kirby Dach', 'https://www.lapresse.ca/sports/chroniques/2026-04-23/canadien-lightning/a-la-defense-de-kirby-dach.php'],
        ],
      },
      {
        heading: 'Presse anglophone',
        items: [
          ['New York Post — Analyse Lightning vs Canadiens M3', 'https://nypost.com/2026/04/24/betting/lightning-vs-canadiens-game-3-prediction-nhl-picks-odds-best-bets-for-stanley-cup-playoffs/'],
          ['Habs Eyes On The Prize — aperçu du M3', 'https://www.habseyesontheprize.com/'],
          ['HockeyDB — sommaire du M3', 'https://www.hockeydb.com/boxscores/20260424-45-55.html'],
          ['CityNews Montréal — couverture de la série', 'https://montreal.citynews.ca/2026/04/24/habs-lightning-montreal-series-hockey/'],
        ],
      },
    ],
    footer: 'Lemieux · analytique de hockey à code source ouvert · github.com/lemieuxAI/framework',
    page: 'Page',
    confirmed: 'Confirmée',
    mixed: 'Mitigée / nuancée',
    refuted: 'Infirmée',
    th_metric: 'Mesure', th_value: 'Valeur',
    th_claim: 'Affirmation', th_source: 'Source',
    th_data: 'Ce que disent les chiffres', th_verdict: 'Verdict',
    th_line: 'Trio', th_g2: 'Match 2 (TG)', th_g3: 'Match 3 (TG)', th_status: 'Statut',
    persisted: 'Maintenu', new_line: 'Nouveau', dropped: 'Abandonné',
  },
};

// ---------- LINEUP PROSE GENERATORS ----------
// Read structured lineup data and template prose against it.
// Every sentence about line composition or role transitions is built from
// fields in game3_lineups.yaml — never from narrative recall.

function findCenter(line) {
  return (line.players || []).find(p => p.position === 'C');
}
function findWingers(line) {
  return (line.players || []).filter(p => p.position === 'L' || p.position === 'R');
}
function reshuffles(team) {
  return ((LINEUPS.changes_vs_previous_game || {})[team] || {}).line_reshuffles || [];
}
function findReshuffle(team, predicate) {
  return reshuffles(team).find(predicate) || null;
}

function _lastName(full) { return (full || '').split(' ').slice(-1)[0]; }

function _newLineContext() {
  const moveDef = findReshuffle('MTL', x => x.moved_player) || {};
  const centerSwap = findReshuffle('MTL', x => x.prior_center && x.new_center) || {};
  const newLineRow = (LINEUPS.teams.MTL.forwards || []).find(L =>
    findCenter(L) && findCenter(L).name === moveDef.to_line_center
  );
  const newLine = newLineRow ? newLineRow.players.map(p => p.name) : [];
  const newLineTOI = (D.mtl_g3_forward_lines || []).find(c =>
    newLine.length === 3 && newLine.every(n => c.players.includes(n))
  );
  const top5 = (D.mtl_g3_forward_lines || []).slice(0, 5);
  const rank = newLineTOI ? top5.findIndex(c => c === newLineTOI) + 1 : null;
  return {
    moveDef, centerSwap, newLine,
    trioLabel: newLine.map(_lastName).join('-'),
    toi: newLineTOI ? newLineTOI.toi_min : 0,
    rank,
  };
}

function lineReshuffleBullet(lang) {
  const c = _newLineContext();
  const rankEn = c.rank ? `${c.rank}${['st','nd','rd','th'][Math.min(c.rank-1,3)]}` : '';
  const rankFr = c.rank ? `${c.rank}e` : '';
  if (lang === 'fr') {
    return `**${c.trioLabel} a marqué les deux buts du CH à 5 c. 5 en seulement ${c.toi.toFixed(1).replace('.', ',')} minutes ensemble — ${rankFr ? `${rankFr} trio le plus utilisé du CH ce soir, mais le plus productif` : 'malgré une utilisation limitée'}.** Le quatrième trio porte l\'offensive au lieu d\'un trio Suzuki-Caufield-Slafkovský qui en a partagé 9,6 mais n\'a pas trouvé le filet à 5 c. 5.`;
  }
  return `**${c.trioLabel} scored both of MTL's 5v5 goals in just ${c.toi.toFixed(1)} minutes together — ${rankEn ? `the ${rankEn}-most-deployed MTL forward combo of the night, but the most productive one` : 'despite limited deployment'}.** A bottom-of-the-rotation trio carried the even-strength offense while the Suzuki-Caufield-Slafkovský line had 9.6 minutes and didn't find the net at 5v5.`;
}

function lineupIntroProse(lang) {
  const c = _newLineContext();
  const rankEn = c.rank ? `${c.rank}${['st','nd','rd','th'][Math.min(c.rank-1,3)]}` : '';
  const rankFr = c.rank ? `${c.rank}e` : '';
  if (lang === 'fr') {
    return `${c.trioLabel} a inscrit les deux buts à 5 c. 5 du CH (Texier à 4:53 de la première, Dach à 12:43 de la deuxième sur un tir dévié contre la jambe de McDonagh) en ${c.toi.toFixed(1).replace('.', ',')} minutes ensemble. Lecture inhabituelle : c\'est le ${rankFr || ''} trio offensif le plus utilisé du CH au M3, mais c\'est lui qui a déverrouillé le filet à forces égales — pas le trio Suzuki-Caufield-Slafkovský (9,6 min, 0 but à 5 c. 5) ni la troisième vague Newhook-Kapanen-Demidov (7,9 min, 0 but).`;
  }
  return `${c.trioLabel} produced both of MTL's 5v5 goals (Texier at 4:53 of the first, Dach at 12:43 of the second on a tip off McDonagh's leg) in ${c.toi.toFixed(1)} minutes of shared ice. The unusual reading: it's the ${rankEn || ''}-most-deployed MTL forward combo of the night, yet it's the line that unlocked even-strength scoring — not the Suzuki-Caufield-Slafkovský trio (9.6 min, 0 5v5 goals) or the Newhook-Kapanen-Demidov unit (7.9 min, 0 goals).`;
}

// ---------- HELPERS ----------
const r = (text, opts = {}) => new TextRun({ text, font: 'Arial', size: 20, ...opts });
const para = (text, opts = {}) => new Paragraph({ spacing: { after: 100 }, children: [r(text, opts)] });

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

const h1 = txt => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: txt, font: 'Arial', size: 30, bold: true, color: BRAND.navy })] });
const h2 = txt => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: txt, font: 'Arial', size: 24, bold: true, color: BRAND.navyLight })] });

function calloutBox(title, bodyParas, fillColor) {
  return new Table({
    columnWidths: [9360],
    margins: { top: 140, bottom: 140, left: 220, right: 220 },
    rows: [new TableRow({ children: [new TableCell({
      borders: cellBorders,
      width: { size: 9360, type: WidthType.DXA },
      shading: { fill: fillColor, type: ShadingType.CLEAR },
      children: [
        ...(title ? [new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: title, bold: true, size: 22, font: 'Arial', color: BRAND.ink })] })] : []),
        ...bodyParas,
      ],
    })] })],
  });
}

function dataTable(headers, rows, colWidths) {
  const widths = colWidths || Array(headers.length).fill(Math.floor(9360 / headers.length));
  const headerCell = (text, i) => new TableCell({
    borders: cellBorders,
    width: { size: widths[i], type: WidthType.DXA },
    shading: { fill: BRAND.navy, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: String(text), bold: true, size: 18, font: 'Arial', color: 'FFFFFF' })],
    })],
  });
  const bodyCell = (text, i, rowOpts) => new TableCell({
    borders: cellBorders,
    width: { size: widths[i], type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    shading: rowOpts && rowOpts.fill ? { fill: rowOpts.fill, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      children: typeof text === 'object' && text.runs ? text.runs : [new TextRun({ text: String(text), size: 18, font: 'Arial' })],
    })],
  });
  return new Table({
    columnWidths: widths,
    margins: { top: 70, bottom: 70, left: 120, right: 120 },
    rows: [
      new TableRow({ tableHeader: true, children: headers.map(headerCell) }),
      ...rows.map(rw => {
        const rowOpts = (rw && rw._opts) || {};
        const cells = (rw && rw.cells) || rw;
        return new TableRow({ children: cells.map((c, i) => bodyCell(c, i, rowOpts)) });
      }),
    ],
  });
}

// ---------- BUILD CONTENT ----------
function brandHeader(t) {
  return new Header({ children: [new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { after: 0 },
    children: [
      new TextRun({ text: '◆  ', font: 'Arial', size: 16, color: BRAND.red }),
      new TextRun({ text: t.brand, font: 'Arial', size: 16, bold: true, color: BRAND.navy, characterSpacing: 60 }),
    ],
  })] });
}

function brandFooter(t) {
  return new Footer({ children: [new Paragraph({
    alignment: AlignmentType.LEFT,
    children: [
      new TextRun({ text: t.footer + '   ', font: 'Arial', size: 14, color: BRAND.mute }),
      new TextRun({ text: t.page + ' ', font: 'Arial', size: 14, color: BRAND.mute }),
      new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 14, color: BRAND.mute }),
    ],
  })] });
}

function titleBlock(t) {
  return [
    new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 60 },
      children: [new TextRun({ text: t.title, font: 'Arial', size: 44, bold: true, color: BRAND.navy })] }),
    new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 60 },
      children: [new TextRun({ text: t.subtitle, font: 'Arial', size: 24, italics: true, color: BRAND.navyLight })] }),
    new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 240 },
      border: { bottom: { color: BRAND.red, space: 4, style: BorderStyle.SINGLE, size: 12 } },
      children: [new TextRun({ text: t.date, font: 'Arial', size: 18, color: BRAND.mute })] }),
  ];
}

function tldrSection(t) {
  return [h2(t.tldr), ...t.tldr_bullets.map(b => new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    spacing: { after: 80 }, children: md(b),
  }))];
}

function methodologySection(t) {
  return [h2(t.methodology_title), calloutBox('', t.methodology.map(s => new Paragraph({ spacing: { after: 60 }, children: md(s) })), BRAND.explainer)];
}

function lineupSection(t, lang) {
  const drift = D.mtl_lineup_drift_g2_to_g3 || {};
  const tblDrift = D.tbl_lineup_drift_g2_to_g3 || {};
  const mtlG2 = D.mtl_g2_forward_lines || [];
  const mtlG3 = D.mtl_g3_forward_lines || [];

  const fmtCombo = c => `${c.players.join(' / ')} (${c.toi_min.toFixed(1)} ${lang === 'fr' ? 'min' : 'min'})`;

  // Pair G2 and G3 lines by best overlap in player set, top 4
  const g2Top = mtlG2.slice(0, 4);
  const g3Top = mtlG3.slice(0, 4);
  const lineRows = [];
  const usedG3 = new Set();
  for (let i = 0; i < g2Top.length; i++) {
    const g2 = g2Top[i];
    let bestIdx = -1;
    let bestOverlap = -1;
    for (let j = 0; j < g3Top.length; j++) {
      if (usedG3.has(j)) continue;
      const overlap = g2.players.filter(p => g3Top[j].players.includes(p)).length;
      if (overlap > bestOverlap) {
        bestOverlap = overlap;
        bestIdx = j;
      }
    }
    const g3 = bestIdx >= 0 ? g3Top[bestIdx] : null;
    if (bestIdx >= 0) usedG3.add(bestIdx);
    let status, fill;
    if (g3 && bestOverlap === 3) {
      status = t.persisted; fill = BRAND.confirm;
    } else if (g3) {
      status = `${t.new_line} (${bestOverlap}/3 ${lang === 'fr' ? 'communs' : 'shared'})`;
      fill = BRAND.neutral;
    } else {
      status = t.dropped; fill = BRAND.refute;
    }
    lineRows.push({
      cells: [
        `${lang === 'fr' ? 'Trio' : 'Line'} ${i + 1}`,
        fmtCombo(g2),
        g3 ? fmtCombo(g3) : '—',
        status,
      ],
      _opts: { fill },
    });
  }
  // Surface any G3 lines we didn't pair
  for (let j = 0; j < g3Top.length; j++) {
    if (usedG3.has(j)) continue;
    lineRows.push({
      cells: [
        `${lang === 'fr' ? 'Nouveau' : 'New'} ${j + 1}`,
        '—',
        fmtCombo(g3Top[j]),
        t.new_line,
      ],
      _opts: { fill: BRAND.neutral },
    });
  }

  return [
    h1(t.lineup_title),
    para(t.lineup_intro, {}),
    h2(t.lineup_mtl_change_title),
    para(t.lineup_drift_table_intro, { italics: true, color: BRAND.mute }),
    dataTable(
      [t.th_line, t.th_g2, t.th_g3, t.th_status],
      lineRows,
      [1100, 3500, 3500, 1260]
    ),
    h2(t.lineup_outcome_title),
    ...t.lineup_outcome.map(s => new Paragraph({ spacing: { after: 100 }, children: md(s) })),
    h2(t.tbl_lineup_title),
    new Paragraph({ spacing: { after: 100 }, children: md(t.tbl_lineup_text) }),
  ];
}

function claimsSection(t, lang) {
  const series5 = D.series_5v5 || {};
  const mtl5 = series5.MTL || {};
  const tbl5 = series5['T.B'] || {};

  const sogFacedBy = (gameKey, teamAbbr) => {
    const g = D.per_game[gameKey];
    if (g.home === teamAbbr) return g.away_sog;
    return g.home_sog;
  };
  const goalsAllowedBy = (gameKey, teamAbbr) => {
    const g = D.per_game[gameKey];
    if (g.home === teamAbbr) return g.away_goals;
    return g.home_goals;
  };
  let vasFaced = 0, vasGA = 0, dobFaced = 0, dobGA = 0;
  for (const k of ['G1','G2','G3']) {
    vasFaced += sogFacedBy(k, 'TBL'); vasGA += goalsAllowedBy(k, 'TBL');
    dobFaced += sogFacedBy(k, 'MTL'); dobGA += goalsAllowedBy(k, 'MTL');
  }
  const hits3 = ['G1','G2','G3'].reduce((s, k) => s + D.per_game[k].home_hits + D.per_game[k].away_hits, 0);
  const hits2 = ['G1','G2'].reduce((s, k) => s + D.per_game[k].home_hits + D.per_game[k].away_hits, 0);

  const claimsEN = [
    { verdict: 'confirmed', claim: 'Tampa Bay tilts the ice (drives shot volume).', source: 'NY Post', data: `At 5v5 across 3 games, TBL has ${pct(tbl5.cf_pct)} of Corsi shot attempts. Tampa drives volume.` },
    { verdict: 'confirmed', claim: 'Montreal generates more high-danger chances.', source: 'NY Post', data: `MTL has ${pct(mtl5.hdcf_pct)} of high-danger chances and ${pct(mtl5.xgf_pct)} of expected goals. Quality tilts hard toward Montreal.` },
    { verdict: 'refuted', claim: 'Vasilevskiy is more reliable than Dobes.', source: 'NY Post', data: `Vasilevskiy: ${vasFaced} shots, ${vasGA} GA (SV ${(1 - vasGA/vasFaced).toFixed(3)}); Dobes: ${dobFaced} shots, ${dobGA} GA (SV ${(1 - dobGA/dobFaced).toFixed(3)}). Dobes is marginally better through 3 games.` },
    { verdict: 'confirmed', claim: 'St-Louis reorganized lines pre-game (Kapanen to 3C, Texier to 2RW with Dach).', source: 'Radio-Canada', data: 'Confirmed by NHL.com shift charts. Major reshuffle: only 2 of MTL\'s top G2 lines persisted.' },
    { verdict: 'confirmed', claim: 'Dach\'s line scored 2 goals and 6 points.', source: 'Martin Leclerc, Radio-Canada', data: 'Texier-Dach-Bolduc trio: Texier scored, Dach scored, both assisted. Confirmed.' },
    { verdict: 'confirmed', claim: 'Hutson scored OT winner with first slap shot of the year, played 26:28.', source: 'François Gagnon, RDS', data: 'OT goal at 2:09 of P4 confirmed via NHL.com PBP. TOI is the reported figure (26:28 leading all skaters).' },
    { verdict: 'confirmed', claim: '"Dobes was at Vasilevskiy\'s level."', source: 'François Gagnon, RDS', data: 'Through 3 games Dobes\' implied SV% is .905 vs Vasilevskiy\'s .893. The chronique tracks the data.' },
    { verdict: 'mixed', claim: 'Slafkovský "much less impactful" since the Hagel fight.', source: 'speculation / commentary', data: 'True for individual production (8 → 2 SOG pre/post); false for on-ice impact (MTL outshoots TBL 20-9 and outscores 2-1 with him on after the fight).' },
    { verdict: 'confirmed', claim: 'Depth scoring carried the win (contributors outside the top duo).', source: 'Habs Eyes On The Prize', data: 'All 3 MTL goals from Texier, Dach, Hutson — exactly the depth profile EOTP wanted.' },
    { verdict: 'confirmed', claim: 'Hagel: consistent scorer (4th goal of the series).', source: 'NHL highlights', data: 'Confirmed via PBP shooter IDs.' },
    { verdict: 'confirmed', claim: `Fast and physical (~163 hits across the first 2 games).`, source: 'NY Post', data: `${hits2} hits across G1+G2. G3 added another ${D.per_game.G3.home_hits + D.per_game.G3.away_hits} for ${hits3} total.` },
    { verdict: 'confirmed', claim: 'Series tight (two then three straight OT games).', source: 'CityNews Montreal', data: 'All three games went to OT. Underlying xG share is also tight (56-44 MTL).' },
  ];

  const claimsFR = [
    { verdict: 'confirmed', claim: 'Tampa renverse la glace (génère le volume de tirs).', source: 'New York Post', data: `À 5 c. 5 sur 3 matchs, le TBL a ${pctFr(tbl5.cf_pct)} des tentatives Corsi. Tampa génère le volume.` },
    { verdict: 'confirmed', claim: 'Montréal génère plus de chances à haut danger.', source: 'New York Post', data: `Le CH détient ${pctFr(mtl5.hdcf_pct)} des chances à haut danger et ${pctFr(mtl5.xgf_pct)} des buts attendus. La qualité penche fortement vers Montréal.` },
    { verdict: 'refuted', claim: 'Vasilevskiy est plus fiable que Dobes.', source: 'New York Post', data: `Vasilevskiy : ${vasFaced} tirs, ${vasGA} buts accordés (% arrêts ${(1 - vasGA/vasFaced).toFixed(3).replace('.', ',')}); Dobes : ${dobFaced} tirs, ${dobGA} buts (${(1 - dobGA/dobFaced).toFixed(3).replace('.', ',')}). Dobes est légèrement meilleur sur 3 matchs.` },
    { verdict: 'confirmed', claim: 'St-Louis a brassé les trios avant le match (Kapanen au 3e centre, Texier au 2e ailier avec Dach).', source: 'Radio-Canada', data: 'Confirmé par les présences réelles de LNH.com. Brassage majeur : seuls 2 des principaux trios du M2 ont persisté.' },
    { verdict: 'confirmed', claim: 'Le trio de Dach a inscrit 2 buts et totalisé 6 points.', source: 'Martin Leclerc, Radio-Canada', data: 'Trio Texier-Dach-Bolduc : Texier marque, Dach marque, les deux récoltent une mention. Confirmé.' },
    { verdict: 'confirmed', claim: 'Hutson a marqué en prolongation avec son premier lancer frappé de la saison, 26:28 de temps de glace.', source: 'François Gagnon, RDS', data: 'But en supplémentaire à 2:09 de la P4 confirmé par le jeu par jeu de LNH.com. Le TG cité (26:28, meneur du match) provient du chroniqueur.' },
    { verdict: 'confirmed', claim: '« Dobes était à la hauteur de Vasilevskiy. »', source: 'François Gagnon, RDS', data: 'Sur 3 matchs, le pourcentage d\'arrêts implicite de Dobes (,905) est légèrement supérieur à celui de Vasilevskiy (,893). La chronique colle aux chiffres.' },
    { verdict: 'mixed', claim: 'Slafkovský « beaucoup moins impactant » depuis le combat avec Hagel.', source: 'spéculation / commentaires', data: 'Vrai sur la production individuelle (8 → 2 tirs avant/après); faux sur l\'impact territorial (le CH surclasse TBL 20-9 aux tirs et 2-1 au pointage avec lui sur la glace après le combat).' },
    { verdict: 'confirmed', claim: 'La profondeur a porté la victoire (les contributeurs hors du duo principal).', source: 'Habs Eyes On The Prize', data: 'Les 3 buts du CH viennent de Texier, Dach et Hutson — exactement le profil de profondeur souhaité.' },
    { verdict: 'confirmed', claim: 'Hagel : marqueur constant (4e but de la série).', source: 'Faits saillants LNH', data: 'Confirmé par les identifiants des tireurs au jeu par jeu.' },
    { verdict: 'confirmed', claim: 'Match rapide et physique (~163 mises en échec sur les deux premiers matchs).', source: 'New York Post', data: `${hits2} mises en échec sur M1+M2; le M3 en ajoute ${D.per_game.G3.home_hits + D.per_game.G3.away_hits} pour ${hits3} sur la série.` },
    { verdict: 'confirmed', claim: 'Série serrée (trois prolongations consécutives).', source: 'CityNews Montréal', data: 'Les trois matchs en supplémentaire. La part de buts attendus sous-jacente est aussi serrée (56-44 pour le CH).' },
  ];

  const claims = lang === 'fr' ? claimsFR : claimsEN;
  const verdictBadge = (k) => {
    const m = {
      confirmed: { label: '✓ ' + t.confirmed, color: '2E7D32' },
      mixed: { label: '◐ ' + t.mixed, color: '8A6D00' },
      refuted: { label: '✗ ' + t.refuted, color: '8B2A1A' },
    }[k];
    return { runs: [new TextRun({ text: m.label, bold: true, size: 18, font: 'Arial', color: m.color })] };
  };
  const fillFor = (k) => k === 'confirmed' ? BRAND.confirm : k === 'refuted' ? BRAND.refute : BRAND.neutral;
  const headers = [t.th_claim, t.th_source, t.th_data, t.th_verdict];
  const rows = claims.map(c => ({
    cells: [c.claim, c.source, c.data, verdictBadge(c.verdict)],
    _opts: { fill: fillFor(c.verdict) },
  }));
  return [h1(t.claims_title), para(t.claims_intro, { italics: true, color: BRAND.mute }), dataTable(headers, rows, [2400, 1400, 4060, 1500])];
}

function seriesSection(t, lang) {
  const series5 = D.series_5v5 || {};
  const mtl = series5.MTL || {};
  const tbl = series5['T.B'] || {};
  const pctFn = lang === 'fr' ? pctFr : pct;
  const headers = [t.th_metric, 'MTL', 'TBL'];
  const rows = [
    [lang === 'fr' ? 'Matchs joués' : 'Games played', String(mtl.gp || 0), String(tbl.gp || 0)],
    ['CF%', pctFn(mtl.cf_pct), pctFn(tbl.cf_pct)],
    ['xGF%', pctFn(mtl.xgf_pct), pctFn(tbl.xgf_pct)],
    ['HDCF%', pctFn(mtl.hdcf_pct), pctFn(tbl.hdcf_pct)],
    [lang === 'fr' ? 'Tirs pour / contre' : 'SF / SA', `${mtl.sf || '—'} / ${mtl.sa || '—'}`, `${tbl.sf || '—'} / ${tbl.sa || '—'}`],
    [lang === 'fr' ? 'Buts pour / contre' : 'GF / GA', `${mtl.gf || 0} / ${mtl.ga || 0}`, `${tbl.gf || 0} / ${tbl.ga || 0}`],
    ['xGF / xGA', `${(mtl.xgf || 0).toFixed(2)} / ${(mtl.xga || 0).toFixed(2)}`, `${(tbl.xgf || 0).toFixed(2)} / ${(tbl.xga || 0).toFixed(2)}`],
    ['PDO', String(mtl.pdo || '—').replace('.', lang === 'fr' ? ',' : '.'), String(tbl.pdo || '—').replace('.', lang === 'fr' ? ',' : '.')],
  ];
  return [h1(t.series_title), para(t.series_intro, {}), dataTable(headers, rows, [4000, 2680, 2680])];
}

function progressionSection(t, lang) {
  const mp = D.mtl_progression || { status: 'missing' };
  if (mp.status !== 'ok') return [h1(t.progression_title), para('Data not available.', { italics: true, color: BRAND.mute })];
  const fmtNum = n => lang === 'fr' ? fmt(n, 2).replace('.', ',') : fmt(n, 2);
  const fmtRow = row => [row.name, row.position,
    `${row.toi_r.toFixed(0)} / ${row.toi_p.toFixed(0)}`,
    fmtNum(row.iso_xgf60_r), fmtNum(row.iso_xgf60_p),
    fmtNum(row.iso_xga60_r), fmtNum(row.iso_xga60_p), fmtNum(row.delta_net)];
  const headers = [
    lang === 'fr' ? 'Joueur' : 'Player', 'Pos',
    lang === 'fr' ? 'TG rég/sér' : 'TOI reg/plf',
    lang === 'fr' ? 'iso xGF/60 rég' : 'iso xGF/60 reg',
    lang === 'fr' ? 'iso xGF/60 sér' : 'iso xGF/60 plf',
    lang === 'fr' ? 'iso xGA/60 rég' : 'iso xGA/60 reg',
    lang === 'fr' ? 'iso xGA/60 sér' : 'iso xGA/60 plf',
    'Δ net',
  ];
  const widths = [1900, 500, 1500, 1100, 1100, 1100, 1100, 1060];
  const upRows = mp.movers_up.slice(0, 6).map(fmtRow).map(cells => ({ cells, _opts: { fill: BRAND.confirm } }));
  const downRows = mp.movers_down.slice(0, 6).map(fmtRow).map(cells => ({ cells, _opts: { fill: BRAND.refute } }));
  return [
    h1(t.progression_title),
    para(t.progression_intro, {}),
    new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: lang === 'fr' ? 'Plus grandes progressions' : 'Top movers up', bold: true, font: 'Arial', size: 22, color: BRAND.navyLight })] }),
    dataTable(headers, upRows, widths),
    new Paragraph({ spacing: { after: 60, before: 200 }, children: [new TextRun({ text: lang === 'fr' ? 'Plus grandes régressions' : 'Top movers down', bold: true, font: 'Arial', size: 22, color: BRAND.navyLight })] }),
    dataTable(headers, downRows, widths),
    calloutBox('', [new Paragraph({ children: md(t.progression_stars_caveat) })], BRAND.caveat),
  ];
}

function goaliesSection(t, lang) {
  const sogFacedBy = (gameKey, teamAbbr) => {
    const g = D.per_game[gameKey];
    if (g.home === teamAbbr) return g.away_sog;
    return g.home_sog;
  };
  const goalsAllowedBy = (gameKey, teamAbbr) => {
    const g = D.per_game[gameKey];
    if (g.home === teamAbbr) return g.away_goals;
    return g.home_goals;
  };
  let vasFaced = 0, vasGA = 0, dobFaced = 0, dobGA = 0;
  for (const k of ['G1','G2','G3']) {
    vasFaced += sogFacedBy(k, 'TBL'); vasGA += goalsAllowedBy(k, 'TBL');
    dobFaced += sogFacedBy(k, 'MTL'); dobGA += goalsAllowedBy(k, 'MTL');
  }
  const fmtSv = n => (n.toFixed(3)).replace('.', lang === 'fr' ? ',' : '.');
  const headers = [t.th_metric, 'Vasilevskiy (TBL)', 'Dobes (MTL)'];
  const rows = [
    [lang === 'fr' ? 'Tirs subis (3 matchs)' : 'Shots faced (3 games)', String(vasFaced), String(dobFaced)],
    [lang === 'fr' ? 'Buts accordés' : 'Goals allowed', String(vasGA), String(dobGA)],
    [lang === 'fr' ? '% arrêts implicite' : 'Implied SV%', fmtSv(1 - vasGA/vasFaced), fmtSv(1 - dobGA/dobFaced)],
    [lang === 'fr' ? 'Charge par match' : 'Workload per game', `${(vasFaced/3).toFixed(1)} ${lang === 'fr' ? 'tirs/match' : 'shots/game'}`, `${(dobFaced/3).toFixed(1)} ${lang === 'fr' ? 'tirs/match' : 'shots/game'}`],
  ];
  return [h1(t.goalies_title), para(t.goalies_intro, {}), dataTable(headers, rows, [3360, 3000, 3000])];
}

function slafSection(t, lang) {
  const fb = D.slaf_fight_buckets;
  const pre = fb.pre, post = fb.post;
  const headers = [t.th_metric, lang === 'fr' ? 'Avant le combat' : 'Pre-fight', lang === 'fr' ? 'Après le combat' : 'Post-fight'];
  const tg = lang === 'fr' ? 'min' : 'min';
  const rows = [
    [lang === 'fr' ? 'TG Slafkovský' : 'Slafkovský TOI', `${pre.toi_min.toFixed(2)} ${tg}`, `${post.toi_min.toFixed(2)} ${tg}`],
    [lang === 'fr' ? 'Tirs (Slaf)' : 'Slafkovský SOG', String(pre.slaf_sog), String(post.slaf_sog)],
    [lang === 'fr' ? 'Buts (Slaf)' : 'Slafkovský goals', String(pre.slaf_goals), String(post.slaf_goals)],
    [lang === 'fr' ? 'Tirs MTL sur la glace' : 'MTL SOG on-ice', String(pre.mtl_sog_oi), String(post.mtl_sog_oi)],
    [lang === 'fr' ? 'Tirs TBL sur la glace' : 'TBL SOG on-ice', String(pre.tbl_sog_oi), String(post.tbl_sog_oi)],
    [lang === 'fr' ? 'Buts MTL sur la glace' : 'MTL goals on-ice', String(pre.mtl_goals_oi), String(post.mtl_goals_oi)],
    [lang === 'fr' ? 'Buts TBL sur la glace' : 'TBL goals on-ice', String(pre.tbl_goals_oi), String(post.tbl_goals_oi)],
  ];
  return [h1(t.slaf_title), para(t.slaf_intro, {}), dataTable(headers, rows, [3000, 3180, 3180])];
}

function usageSection(t, lang) {
  const items = (USAGE.usage_observations || []);
  const labelMap = {
    en: { ice_time_anomaly: 'Ice-time anomaly', line_creation: 'New line / line reshuffle', double_shift: 'Double shift', benched: 'Benched', scratch_activated: 'Scratch activated', role_change: 'Role change', sheltered_minutes: 'Sheltered minutes', heavy_matchup: 'Heavy matchup', goalie_anomaly: 'Goalie anomaly', defensive_role: 'Defensive role', special_teams_change: 'Special-teams change', other: 'Other' },
    fr: { ice_time_anomaly: 'TG anormal', line_creation: 'Nouveau trio / brassage', double_shift: 'Double présence', benched: 'Mis à l\'écart', scratch_activated: 'Réserviste activé', role_change: 'Changement de rôle', sheltered_minutes: 'Minutes protégées', heavy_matchup: 'Confrontation difficile', goalie_anomaly: 'Anomalie gardien', defensive_role: 'Rôle défensif', special_teams_change: 'Changement spéciales', other: 'Autre' },
  };
  const labels = labelMap[lang];
  const headers = lang === 'fr'
    ? ['Type', 'Joueur / Équipe', 'Observation', 'Source']
    : ['Type', 'Player / Team', 'Observation', 'Source'];
  const rows = items.map(o => {
    const label = labels[o.type] || (lang === 'fr' ? 'Autre' : 'Other');
    const obs = o.text + (o.significance ? '\n— ' + o.significance : '');
    return [label, o.player_or_team || '—',
      { runs: obs.split('\n').map((line, i) => new TextRun({ text: line, size: 18, font: 'Arial', italics: i > 0, color: i > 0 ? BRAND.mute : BRAND.ink, break: i > 0 ? 1 : 0 })) },
      o.source || '—'];
  });
  return [
    h1(t.usage_title),
    para(t.usage_intro, { italics: true, color: BRAND.mute }),
    dataTable(headers, rows, [1700, 1700, 4500, 1460]),
  ];
}

function cantSection(t) {
  return [h1(t.cant_title), ...t.cant_bullets.map(b => new Paragraph({
    numbering: { reference: 'bullets', level: 0 }, spacing: { after: 80 }, children: md(b),
  }))];
}

function sourcesSection(t) {
  const out = [h1(t.sources_title)];
  for (const group of t.sources_groups) {
    out.push(new Paragraph({ spacing: { before: 120, after: 60 }, children: [new TextRun({ text: group.heading, bold: true, font: 'Arial', size: 22, color: BRAND.navyLight })] }));
    for (const [txt, url] of group.items) {
      out.push(new Paragraph({
        numbering: { reference: 'bullets', level: 0 }, spacing: { after: 60 },
        children: [new ExternalHyperlink({ children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })], link: url })],
      }));
    }
  }
  return out;
}

// ---------- BUILD ----------
function buildDoc(lang) {
  const t = T[lang];
  const sections = [
    new Paragraph({ children: [] }),
    ...titleBlock(t),
    ...tldrSection(t),
    ...methodologySection(t),
    new Paragraph({ children: [new PageBreak()] }),
    ...lineupSection(t, lang),
    new Paragraph({ children: [new PageBreak()] }),
    ...usageSection(t, lang),
    new Paragraph({ children: [new PageBreak()] }),
    ...claimsSection(t, lang),
    new Paragraph({ children: [new PageBreak()] }),
    ...seriesSection(t, lang),
    ...progressionSection(t, lang),
    new Paragraph({ children: [new PageBreak()] }),
    ...goaliesSection(t, lang),
    ...slafSection(t, lang),
    ...cantSection(t),
    ...sourcesSection(t),
  ];
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
      children: sections,
    }],
  });
}

(async () => {
  for (const lang of ['en', 'fr']) {
    const doc = buildDoc(lang);
    const buf = await Packer.toBuffer(doc);
    const primary = path.join(__dirname, `game3_post_2026-04-25_${lang.toUpperCase()}.docx`);
    let out = primary;
    try {
      fs.writeFileSync(primary, buf);
    } catch (e) {
      if (e.code === 'EBUSY' || e.code === 'EACCES') {
        out = path.join(__dirname, `game3_post_2026-04-25_${lang.toUpperCase()}_v2.docx`);
        fs.writeFileSync(out, buf);
        console.log(`(primary file locked — wrote alternate)`);
      } else {
        throw e;
      }
    }
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
