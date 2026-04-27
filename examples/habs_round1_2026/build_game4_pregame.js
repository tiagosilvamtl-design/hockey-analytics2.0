// Pre-game brief for Game 4 (TBL @ MTL, 2026-04-26).
// Inputs:
//   - game4_pregame_lineups.yaml — announced lineup changes (canonical fact base)
//   - playoff_rankings.numbers.json — MTL series-to-date 5v5 iso impacts (for matchup math)
//
// This is forward-looking, not a post-game report. No predictions of outcome.
// Lead with what the announced TBL change opens up tactically; what MTL could do
// to exploit it; what to watch.
//
// Run:
//   node examples/habs_round1_2026/build_game4_pregame.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');
const yaml = require('yaml');

const LINEUPS = yaml.parse(fs.readFileSync(path.join(__dirname, 'game4_pregame_lineups.yaml'), 'utf8'));
const RANK = JSON.parse(fs.readFileSync(path.join(__dirname, 'playoff_rankings.numbers.json'), 'utf8'));
const SWAP = JSON.parse(fs.readFileSync(path.join(__dirname, 'game4_pregame_swap.numbers.json'), 'utf8'));

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

const fmt = (n, p = 2) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  const s = Number(n).toFixed(p);
  return (Number(n) > 0 ? '+' : '') + s;
};
const fmtFr = (n, p = 2) => fmt(n, p).replace('.', ',');

const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: BRAND.rule };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

// ---------- helpers ----------
function findRank(name) {
  return (RANK.rank_5v5 || []).find(r => r.name === name) || null;
}

const dachLine = ['Alexandre Texier', 'Kirby Dach', 'Zachary Bolduc'].map(findRank).filter(Boolean);
const suzukiLine = ['Juraj Slafkovský', 'Nick Suzuki', 'Cole Caufield'].map(findRank).filter(Boolean);

const dachLineNet = dachLine.length
  ? dachLine.reduce((s, r) => s + r.net, 0) / dachLine.length
  : null;
const suzukiLineNet = suzukiLine.length
  ? suzukiLine.reduce((s, r) => s + r.net, 0) / suzukiLine.length
  : null;
const dachLineHdcf = dachLine.length
  ? dachLine.reduce((s, r) => s + r.hdcf_pct, 0) / dachLine.length
  : null;

// ---------- I18N ----------
const T = {
  en: {
    title: 'Pre-game brief — Habs vs Lightning, Game 4 (Apr 26, 2026)',
    subtitle: 'Bell Centre · 7:00 p.m. ET · MTL leads series 2–1',
    tldr_title: 'Three things',
    tldr: [
      `Pooled-iso swap math (24-25 reg+playoff + 25-26 reg+playoff, 5v5): Crozier-for-Carlile projects to **${fmt(SWAP.swap.delta_xgf_per_game, 2)} xGF and ${fmt(SWAP.swap.delta_xga_per_game, 2)} xGA per game** for Tampa over a ${SWAP.swap.slot_minutes.toFixed(0)}-minute 3rd-pair slot. Net **${fmt(SWAP.swap.delta_net_per_game, 2)} xG/game** to TBL. Both 80% CIs straddle zero — directionally a small upgrade, statistically a wash.`,
      'Montreal has not announced any changes. Same 18 skaters from Game 3, same forward lines (including Texier–Dach–Bolduc, who produced both 5v5 goals plus the OT setup in Game 3), same defense pairs, Dobeš in net. **Projected MTL impact from announced changes: zero.**',
      'The matchup lever sits with St-Louis. With last change at the Bell Centre, the Habs can choose to feed the Dach line minutes against Lilleberg–Crozier (Tampa\'s least-settled pair, with a Lilleberg pooled iso of ' + fmt(SWAP.impacts['Emil Lilleberg'].iso_net60, 2) + ' xG/60 net) rather than against Cernák / Sergachev.',
    ],
    lineups_title: 'Announced lineup status',
    lineups_intro: 'TBL data here is from morning-skate reports (Dose.ca, Montreal Hockey Fanatics, NHL.com) — not yet shift-confirmed. MTL is unchanged from Game 3 per St-Louis\'s morning skate.',
    th_team: 'Team',
    th_change: 'Reported change',
    th_who_in: 'In',
    th_who_out: 'Out',
    th_position: 'Position / role',
    tbl_d_section_title: 'Tampa\'s blue-line rotation through four games',
    tbl_d_intro: 'Cooper has used three different right-side defensemen across the first four games. The cause is structural — Hedman is out, D\'Astous (third straight) is day-to-day after the Anderson hit in Game 1 — and the carousel has now reached the third option.',
    tbl_d_table_intro: 'Series rotation on Tampa\'s third pair:',
    th_game: 'Game',
    th_third_pair: 'Third pair (announced / deployed)',
    th_note: 'Note',
    rotation_rows: [
      ['1', 'D\'Astous (R) — partner', 'D\'Astous hit by Anderson; injured.'],
      ['2', 'Carlile activated', 'Carlile NHL playoff debut.'],
      ['3', 'Carlile remains', '−3 / 11:20 TOI; sheltered minutes.'],
      ['4 (announced)', 'Crozier (R) — Lilleberg slides to L', 'Third different right-side D in four games.'],
    ],
    swap_title: 'Projected impact of the announced change (swap engine)',
    swap_intro: 'Pooled NST 5v5 on/off splits across 24-25 reg + 24-25 playoffs + 25-26 reg + 25-26 playoffs (current). Iso impact = on-ice rate − team-without-player rate. Slot = 12 min/game (3rd-pair 5v5).',
    swap_table_intro: 'Pooled iso impacts at 5v5:',
    th_player: 'Player',
    th_pool_toi: 'Pooled TOI (min)',
    th_iso_xgf: 'iso xGF/60',
    th_iso_xga: 'iso xGA/60',
    th_iso_net: 'Net',
    swap_result_title: 'Projected swap delta (TBL perspective)',
    swap_result_intro: 'Δ = (in_player iso − out_player iso) × slot_share. Variance: Poisson approximation on event counts.',
    th_metric: 'Metric',
    th_value: 'Δ per game',
    th_ci: '80% CI',
    swap_interpretation_title: 'What this means',
    swap_interpretation: [
      `**The headline number is +${SWAP.swap.delta_net_per_game.toFixed(2)} xG/game to Tampa, but neither leg is significant at 80% confidence.** The xGF leg moves +${SWAP.swap.delta_xgf_per_game.toFixed(2)} (CI [${SWAP.swap.delta_xgf_ci80[0].toFixed(2)}, ${SWAP.swap.delta_xgf_ci80[1].toFixed(2)}]) and the xGA leg moves +${SWAP.swap.delta_xga_per_game.toFixed(2)} (CI [${SWAP.swap.delta_xga_ci80[0].toFixed(2)}, ${SWAP.swap.delta_xga_ci80[1].toFixed(2)}]). Both bands cross zero — the swap could plausibly hurt Tampa as well as help.`,
      `**The driver is Carlile's pooled iso, not Crozier's gain.** Carlile sits at ${fmt(SWAP.impacts['Declan Carlile'].iso_net60, 2)} net xG/60 across 627 pooled minutes (24-25 + 25-26 reg + 25-26 playoff). Crozier sits at ${fmt(SWAP.impacts['Max Crozier'].iso_net60, 2)} across 501 minutes — close to team-baseline. Cooper is removing a clearly-below-baseline minute-eater rather than upgrading to a plus driver.`,
      `**Cumulative ceiling over a worst-case 4 remaining games is ~${(SWAP.swap.delta_net_per_game * 4).toFixed(1)} xG of net effect for Tampa, which translates to roughly half a goal of expected impact.** Below the noise floor of a single goalie-night swing. The lineup change is real; its expected magnitude on the scoreboard is small.`,
      `**Lilleberg's side flip is unmeasurable here.** His pooled iso net is ${fmt(SWAP.impacts['Emil Lilleberg'].iso_net60, 2)} xG/60 — also below baseline. Whether the L-side reads improve his pucks-out rate is a Game-4 watch item, not a number the framework projects.`,
    ],
    matchup_title: 'What it opens up — the matchup lever',
    matchup_intro: 'Last change at the Bell Centre + a freshly-reshuffled third pair = the cleanest matchup window of the series for whichever MTL line St-Louis wants to feed. The candidate is the Texier–Dach–Bolduc line, whose iso impacts at 5v5 through three games are the strongest among MTL forward groups.',
    matchup_table_intro: 'MTL forward-line iso impacts at 5v5 (avg of three players, three games):',
    th_line: 'Line',
    th_avg_net: 'Avg net iso (xGF/60 − xGA/60)',
    th_hdcf: 'Avg HDCF%',
    th_g3_outcomes: 'G3 outcomes',
    matchup_lines: [
      ['Texier–Dach–Bolduc',  fmt(dachLineNet, 2), (dachLineHdcf ?? 0).toFixed(1) + '%', 'Both MTL 5v5 goals; OT goal assist (Bolduc).'],
      ['Suzuki–Caufield–Slafkovský', fmt(suzukiLineNet, 2), '—', 'No 5v5 goals; PP-driven contribution.'],
    ],
    matchup_takeaways_title: 'How MTL could play it',
    matchup_takeaways: [
      'Hard-match the Dach line against the Lilleberg–Crozier pair. Crozier has played sparingly since February; Lilleberg is shifting sides mid-series. The combination is the least settled defensive unit Tampa has put on the ice in this series.',
      'Keep the Suzuki line away from the Cernák / Sergachev pair where possible. Through three games, the top line has carried negative 5v5 net iso and lives off the power play. A worse 5v5 matchup compresses that even further.',
      'Don\'t blender what worked. The Game 3 trio assignments held for the full game and produced both 5v5 goals — there is no analytical case for shaking forward lines on the back of a one-goal OT win.',
      'Watch Tampa\'s response: Cooper can hide the new pair with Cirelli on the ice (defensive matchup) or expose it with Kucherov (offensive zone start). Either tells you how confident the bench is in Crozier\'s reads.',
    ],
    watch_title: 'What to watch',
    watch: [
      '**Lilleberg\'s left-side reads** — first time on his natural side this series. Pucks held in vs. exited; first-pass success vs. forecheck.',
      '**Dach line\'s zone-entry rate** — if MTL is matching as suggested, the entries-against-3rd-pair rate should be visibly higher than in Games 1–3.',
      '**Hutson\'s ice time** — 26:28 in Game 3, OT goal. If the score is close he\'ll be over 25 again; if the model says any defender is overworked the iso impact narrows.',
      '**Slafkovský\'s shot diet** — 8 → 2 SOG pre/post the Game-2 Hagel fight (bucket: G1 + G2-pre vs G2-post + G3). Game 4 is the cleanest test of whether the drop persists.',
      '**Dobeš vs. Vasilevskiy** — through three games, the implied SV% read is .892 vs .880 (PBP-direct count). One bad night flips that read; one strong night locks the series goalie story.',
    ],
    caveats_title: 'Caveats',
    caveats: [
      'All TBL change reporting is morning-skate-derived. Final lineup is confirmed at puck drop.',
      'MTL line iso impacts are from a 3-game playoff sample. Confidence intervals are wide; treat magnitudes as directional.',
      'No predictions of game or series outcomes. The framework grades claims, not forecasts.',
    ],
    sources_title: 'Sources',
    sources: [
      ['Game #4: Here\'s the change the Lightning will make to their lineup — Dose.ca', 'https://dose.ca/2026/04/26/game-4-heres-the-change-the-lightning-will-make-to-their-lineup/'],
      ['Lightning replace defenseman for Game 4 vs Canadiens — Montreal Hockey Fanatics', 'https://www.montrealhockeyfanatics.com/nhl-team/tampa-bay-lightning/lightning-replace-defenseman-for-game-4-vs-canadiens-as-cooper-makes-third-blue-line-change'],
      ['Updates from optional morning skate – Apr. 26 — NHL.com Canadiens', 'https://www.nhl.com/canadiens/news/updates-from-optional-morning-skate-apr-26-2026'],
      ['TBL@MTL: What you need to know | Game 4 — NHL.com Canadiens', 'https://www.nhl.com/canadiens/news/tbl-mtl-what-you-need-to-know-game-4-apr-26-2026'],
      ['3 Things to Watch: Lightning at Canadiens, Game 4 — NHL.com', 'https://www.nhl.com/news/topic/playoffs/tampa-bay-lightning-montreal-canadiens-game-4-preview-april-26-2026'],
      ['Game 4 Preview — Habs Eyes on the Prize', 'https://www.habseyesontheprize.com/canadiens-lightning-2026-04-26-stanley-cup-playoffs-round-1-game-4-preview-start-time-tale-of-the-tape-and-how-to-watch-tv-listings/'],
    ],
    footer_left: 'Lemieux · pre-game brief · MTL @ TBL Game 4',
    footer_right: 'Page',
  },
  fr: {
    title: 'Survol d\'avant-match — Canadien c. Lightning, Match 4 (26 avril 2026)',
    subtitle: 'Centre Bell · 19 h · le CH mène la série 2–1',
    tldr_title: 'Trois constats',
    tldr: [
      `Math du moteur d'échange (poolé : sais. rég. + séries 24-25 et 25-26, 5 c. 5) : Crozier-pour-Carlile projette **${fmtFr(SWAP.swap.delta_xgf_per_game, 2)} BAF et ${fmtFr(SWAP.swap.delta_xga_per_game, 2)} BAC par match** pour Tampa sur une fenêtre de ${SWAP.swap.slot_minutes.toFixed(0)} minutes au 3ᵉ duo. Net : **${fmtFr(SWAP.swap.delta_net_per_game, 2)} BA/match** pour le TBL. Les deux IC à 80 % chevauchent zéro — direction haussière, ampleur statistiquement nulle.`,
      'Le CH n\'annonce aucun changement. Mêmes 18 patineurs qu\'au M3, mêmes trios à l\'avant (incluant Texier–Dach–Bolduc, qui a produit les deux buts à 5 c. 5 et la mise en place de la prolongation), mêmes paires défensives, Dobeš devant le filet. **Impact projeté côté CH des changements annoncés : zéro.**',
      'Le levier d\'appariement appartient à St-Louis. Avec le dernier changement au Centre Bell, le CH peut servir au trio de Dach ses minutes les plus propres face à Lilleberg–Crozier (le duo le moins stable de Tampa; Lilleberg affiche un net iso poolé de ' + fmtFr(SWAP.impacts['Emil Lilleberg'].iso_net60, 2) + ' BA/60) plutôt que face à Cernák ou Sergachev.',
    ],
    lineups_title: 'Alignements annoncés',
    lineups_intro: 'Les données du TBL viennent des comptes-rendus du patinage matinal (Dose.ca, Montreal Hockey Fanatics, NHL.com) — non confirmées par les présences réelles. Le CH est inchangé depuis le M3 selon St-Louis.',
    th_team: 'Équipe',
    th_change: 'Changement rapporté',
    th_who_in: 'Entre',
    th_who_out: 'Sort',
    th_position: 'Position / rôle',
    tbl_d_section_title: 'La rotation à la ligne bleue de Tampa sur 4 matchs',
    tbl_d_intro: 'Cooper a employé trois défenseurs différents du côté droit en quatre matchs. La cause est structurelle — Hedman absent, D\'Astous (3ᵉ match consécutif) jour-à-jour après la mise en échec d\'Anderson au M1 — et le carrousel atteint maintenant la troisième option.',
    tbl_d_table_intro: 'Rotation au 3ᵉ duo de Tampa, par match :',
    th_game: 'Match',
    th_third_pair: '3ᵉ duo (annoncé / déployé)',
    th_note: 'Note',
    rotation_rows: [
      ['1', 'D\'Astous (D) — partenaire', 'D\'Astous frappé par Anderson; blessé.'],
      ['2', 'Carlile activé', 'Premiers minutes en séries pour Carlile.'],
      ['3', 'Carlile demeure', '−3 / 11:20 de TG; minutes protégées.'],
      ['4 (annoncé)', 'Crozier (D) — Lilleberg passe à G', '3ᵉ défenseur droitier différent en 4 matchs.'],
    ],
    swap_title: 'Impact projeté du changement annoncé (moteur d\'échange)',
    swap_intro: 'Splits NST 5 c. 5 sur la glace / hors glace, poolés sur saison rég. + séries 24-25 et 25-26 (actuelle). Iso = taux sur la glace − taux équipe-sans-joueur. Fenêtre = 12 min/match (3ᵉ duo 5 c. 5).',
    swap_table_intro: 'Impacts isolés poolés à 5 c. 5 :',
    th_player: 'Joueur',
    th_pool_toi: 'TG poolé (min)',
    th_iso_xgf: 'iso BAF/60',
    th_iso_xga: 'iso BAC/60',
    th_iso_net: 'Net',
    swap_result_title: 'Delta projeté du changement (perspective TBL)',
    swap_result_intro: 'Δ = (iso joueur entrant − iso joueur sortant) × part de la fenêtre. Variance : approximation Poisson sur le nombre d\'événements.',
    th_metric: 'Mesure',
    th_value: 'Δ par match',
    th_ci: 'IC 80 %',
    swap_interpretation_title: 'Ce que ça veut dire',
    swap_interpretation: [
      `**Le chiffre vedette est +${SWAP.swap.delta_net_per_game.toFixed(2).replace('.', ',')} BA/match en faveur de Tampa, mais ni la jambe BAF ni la BAC n\'est significative à 80 %.** Δ BAF : +${SWAP.swap.delta_xgf_per_game.toFixed(2).replace('.', ',')} (IC [${SWAP.swap.delta_xgf_ci80[0].toFixed(2).replace('.', ',')}, ${SWAP.swap.delta_xgf_ci80[1].toFixed(2).replace('.', ',')}]). Δ BAC : +${SWAP.swap.delta_xga_per_game.toFixed(2).replace('.', ',')} (IC [${SWAP.swap.delta_xga_ci80[0].toFixed(2).replace('.', ',')}, ${SWAP.swap.delta_xga_ci80[1].toFixed(2).replace('.', ',')}]). Les deux bandes traversent zéro — le changement pourrait nuire à Tampa autant qu\'aider.`,
      `**Le moteur du gain, c\'est l\'iso poolé de Carlile, pas l\'apport de Crozier.** Carlile est à ${fmtFr(SWAP.impacts['Declan Carlile'].iso_net60, 2)} BA/60 net sur 627 minutes poolées (rég. 24-25 + 25-26 + séries 25-26). Crozier : ${fmtFr(SWAP.impacts['Max Crozier'].iso_net60, 2)} sur 501 minutes — proche de la base d\'équipe. Cooper retire un mangeur de minutes clairement sous la base, plus qu\'il ne fait monter un défenseur positif.`,
      `**Le plafond cumulatif sur 4 matchs restants au pire est d\'environ ${(SWAP.swap.delta_net_per_game * 4).toFixed(1).replace('.', ',')} BA d\'effet net pour Tampa, soit grosso modo un demi-but d\'impact attendu.** Sous le seuil de bruit d\'une seule sortie de gardien. Le changement est réel; son ampleur attendue au tableau indicateur est petite.`,
      `**Le changement de côté de Lilleberg n\'est pas mesurable ici.** Son net iso poolé est de ${fmtFr(SWAP.impacts['Emil Lilleberg'].iso_net60, 2)} BA/60 — aussi sous la base. Si jouer à gauche améliore ses sorties de zone, c\'est un item à surveiller au M4, pas un chiffre que le cadriciel projette.`,
    ],
    matchup_title: 'Ce que ça ouvre — le levier d\'appariement',
    matchup_intro: 'Dernier changement au Centre Bell + 3ᵉ duo refait à neuf = la fenêtre d\'appariement la plus nette de la série pour le trio que St-Louis voudra servir. Le candidat évident : Texier–Dach–Bolduc, dont les impacts isolés à 5 c. 5 sur 3 matchs dominent les groupes d\'attaquants du CH.',
    matchup_table_intro: 'Impacts isolés des trios du CH à 5 c. 5 (moyenne de 3 joueurs, 3 matchs) :',
    th_line: 'Trio',
    th_avg_net: 'Net iso moyen (BAF/60 − BAC/60)',
    th_hdcf: 'CHD% moyen',
    th_g3_outcomes: 'Résultats au M3',
    matchup_lines: [
      ['Texier–Dach–Bolduc', fmtFr(dachLineNet, 2), (dachLineHdcf ?? 0).toFixed(1).replace('.', ',') + ' %', 'Les 2 buts à 5 c. 5; mention sur le but en prolongation (Bolduc).'],
      ['Suzuki–Caufield–Slafkovský', fmtFr(suzukiLineNet, 2), '—', 'Aucun but à 5 c. 5; production via l\'avantage numérique.'],
    ],
    matchup_takeaways_title: 'Comment le CH peut jouer ça',
    matchup_takeaways: [
      'Cibler le trio de Dach contre le duo Lilleberg–Crozier. Crozier joue peu depuis février; Lilleberg change de côté en pleine série. C\'est l\'unité défensive la moins stable que Tampa a alignée jusqu\'ici.',
      'Tenir le trio de Suzuki loin du duo Cernák / Sergachev quand possible. Sur 3 matchs, le premier trio affiche un net iso négatif à 5 c. 5 et vit sur l\'avantage numérique. Un appariement défavorable à 5 c. 5 comprime encore davantage.',
      'Ne rien brasser de ce qui a fonctionné. Les trios du M3 ont tenu tout le match et produit les deux buts à 5 c. 5 — aucun argument analytique pour brasser à l\'avant après une victoire d\'un but en supplémentaire.',
      'Surveiller la réplique de Tampa : Cooper peut cacher le nouveau duo avec Cirelli sur la glace (matchup défensif) ou l\'exposer avec Kucherov (mise en jeu offensive). Le choix dévoilera la confiance du banc envers les lectures de Crozier.',
    ],
    watch_title: 'À surveiller',
    watch: [
      '**Lectures de Lilleberg du côté gauche** — premier match cette série sur son côté naturel. Rondelles tenues en zone c. sorties; passes sous pression de l\'échec-avant.',
      '**Taux d\'entrée de zone du trio de Dach** — si le CH appariement comme suggéré, le taux d\'entrées contre le 3ᵉ duo devrait être visiblement plus élevé qu\'aux M1–M3.',
      '**Le temps de glace de Hutson** — 26:28 au M3, but en prolongation. Si la marque reste serrée, il dépassera encore 25 minutes; si un défenseur est trop sollicité, l\'impact isolé se rétrécit.',
      '**Le diète de tirs de Slafkovský** — 8 → 2 tirs au but avant/après le combat avec Hagel au M2 (tranches : M1 + M2-avant c. M2-après + M3). Le M4 est le test le plus net pour voir si la baisse persiste.',
      '**Dobeš c. Vasilevskiy** — sur 3 matchs, le % d\'arrêts implicite (compté direct du jeu par jeu) est de ,892 c. ,880. Une mauvaise soirée renverse la lecture; une grosse soirée verrouille le récit du gardien.',
    ],
    caveats_title: 'Mises en garde',
    caveats: [
      'Les rapports sur les changements du TBL viennent du patinage matinal. La composition finale est confirmée à la mise au jeu.',
      'Les impacts isolés des trios du CH proviennent d\'un échantillon de 3 matchs en séries. Les intervalles de confiance sont larges; traiter les amplitudes comme directionnelles.',
      'Aucune prédiction de match ou de série. Le cadriciel évalue des prétentions, il ne fait pas de pronostics.',
    ],
    sources_title: 'Sources',
    sources: [
      ['Game #4: Here\'s the change the Lightning will make to their lineup — Dose.ca', 'https://dose.ca/2026/04/26/game-4-heres-the-change-the-lightning-will-make-to-their-lineup/'],
      ['Lightning replace defenseman for Game 4 vs Canadiens — Montreal Hockey Fanatics', 'https://www.montrealhockeyfanatics.com/nhl-team/tampa-bay-lightning/lightning-replace-defenseman-for-game-4-vs-canadiens-as-cooper-makes-third-blue-line-change'],
      ['Mise à jour de l\'entraînement matinal optionnel — 26 avril (LNH.com Canadien)', 'https://www.nhl.com/canadiens/news/updates-from-optional-morning-skate-apr-26-2026'],
      ['TBL@MTL : ce qu\'il faut savoir | Match 4 (LNH.com Canadien)', 'https://www.nhl.com/canadiens/news/tbl-mtl-what-you-need-to-know-game-4-apr-26-2026'],
      ['3 Things to Watch: Lightning at Canadiens, Game 4 — NHL.com', 'https://www.nhl.com/news/topic/playoffs/tampa-bay-lightning-montreal-canadiens-game-4-preview-april-26-2026'],
      ['Aperçu du Match 4 — Habs Eyes on the Prize', 'https://www.habseyesontheprize.com/canadiens-lightning-2026-04-26-stanley-cup-playoffs-round-1-game-4-preview-start-time-tale-of-the-tape-and-how-to-watch-tv-listings/'],
    ],
    footer_left: 'Lemieux · survol d\'avant-match · M4 CH c. TBL',
    footer_right: 'Page',
  },
};

// ---------- docx primitives ----------
function md(s) {
  // simple **bold** parsing
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
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 280, after: 140 },
    children: [new TextRun({ text, bold: true, size: 30, color: BRAND.navy, font: 'Arial' })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, bold: true, size: 24, color: BRAND.navyLight, font: 'Arial' })],
  });
}

function bulletList(items) {
  return items.map(s => new Paragraph({
    numbering: { reference: 'bullets', level: 0 },
    spacing: { after: 80 },
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
      children: cells.map(c => {
        const children = (c && c.runs)
          ? [new Paragraph({ spacing: { before: 40, after: 40 }, children: c.runs })]
          : [new Paragraph({ spacing: { before: 40, after: 40 }, children: [new TextRun({ text: String(c ?? '—'), font: 'Arial', size: 18, color: BRAND.ink })] })];
        return new TableCell({
          borders: cellBorders,
          shading: opts.fill ? { type: ShadingType.CLEAR, color: 'auto', fill: opts.fill } : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children,
        });
      }),
    });
  });
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: widths,
    rows: [headerRow, ...bodyRows],
  });
}

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
  ];
}

function tldrSection(t) {
  return [h1(t.tldr_title), ...bulletList(t.tldr)];
}

function lineupsSection(t, lang) {
  const tblIn = LINEUPS.teams.TBL.defense_changes[0].in.name;
  const tblOut = LINEUPS.teams.TBL.defense_changes[0].out.name;
  const lillebergShift = LINEUPS.teams.TBL.defense_changes[1].shift;
  const rows = [
    ['MTL', lang === 'fr' ? 'Aucun' : 'None', '—', '—', lang === 'fr' ? 'Mêmes 18 qu\'au M3' : 'Same 18 as Game 3'],
    ['TBL', lang === 'fr' ? 'Échange à la défense' : 'Defenseman swap', tblIn, tblOut, lang === 'fr' ? 'Défenseur droitier (3ᵉ duo)' : 'RHD (third pair)'],
    ['TBL', lang === 'fr' ? 'Changement de côté' : 'Side flip', `${lillebergShift.player} → ${lang === 'fr' ? 'gauche' : 'left'}`, '—', lang === 'fr' ? 'Pour faire de la place à Crozier (D)' : 'To accommodate Crozier (RHD)'],
  ];
  return [
    h1(t.lineups_title),
    para(t.lineups_intro, { italics: true }),
    dataTable(
      [t.th_team, t.th_change, t.th_who_in, t.th_who_out, t.th_position],
      rows,
      [800, 2700, 2200, 2200, 2160]
    ),
  ];
}

function tblDSection(t) {
  return [
    h1(t.tbl_d_section_title),
    para(t.tbl_d_intro),
    para(t.tbl_d_table_intro, { italics: true }),
    dataTable(
      [t.th_game, t.th_third_pair, t.th_note],
      t.rotation_rows,
      [1200, 4400, 4460]
    ),
  ];
}

function swapSection(t, lang) {
  const fmtN = lang === 'fr' ? fmtFr : fmt;
  const i = SWAP.impacts;
  const s = SWAP.swap;
  const playerRows = [
    [`${i['Declan Carlile'].name}  ${lang === 'fr' ? '(sortant)' : '(out)'}`, i['Declan Carlile'].toi_on_min.toFixed(0), fmtN(i['Declan Carlile'].iso_xgf60, 3), fmtN(i['Declan Carlile'].iso_xga60, 3), fmtN(i['Declan Carlile'].iso_net60, 3)],
    [`${i['Max Crozier'].name}  ${lang === 'fr' ? '(entrant)' : '(in)'}`,    i['Max Crozier'].toi_on_min.toFixed(0),    fmtN(i['Max Crozier'].iso_xgf60, 3),    fmtN(i['Max Crozier'].iso_xga60, 3),    fmtN(i['Max Crozier'].iso_net60, 3)],
    [`${i['Emil Lilleberg'].name}  ${lang === 'fr' ? '(côté G nouveau)' : '(side flip → L)'}`, i['Emil Lilleberg'].toi_on_min.toFixed(0), fmtN(i['Emil Lilleberg'].iso_xgf60, 3), fmtN(i['Emil Lilleberg'].iso_xga60, 3), fmtN(i['Emil Lilleberg'].iso_net60, 3)],
  ];
  const resultRows = [
    [lang === 'fr' ? 'Δ BAF/match' : 'Δ xGF/game', fmtN(s.delta_xgf_per_game, 3), `[${fmtN(s.delta_xgf_ci80[0], 3)}, ${fmtN(s.delta_xgf_ci80[1], 3)}]`],
    [lang === 'fr' ? 'Δ BAC/match' : 'Δ xGA/game', fmtN(s.delta_xga_per_game, 3), `[${fmtN(s.delta_xga_ci80[0], 3)}, ${fmtN(s.delta_xga_ci80[1], 3)}]`],
    [lang === 'fr' ? 'Δ Net/match' : 'Δ Net/game', fmtN(s.delta_net_per_game, 3), '—'],
  ];
  return [
    h1(t.swap_title),
    para(t.swap_intro, { italics: true }),
    h2(lang === 'fr' ? 'Impacts isolés poolés' : 'Pooled iso impacts'),
    para(t.swap_table_intro, { italics: true }),
    dataTable(
      [t.th_player, t.th_pool_toi, t.th_iso_xgf, t.th_iso_xga, t.th_iso_net],
      playerRows,
      [3700, 1700, 1700, 1700, 1260]
    ),
    h2(t.swap_result_title),
    para(t.swap_result_intro, { italics: true }),
    dataTable(
      [t.th_metric, t.th_value, t.th_ci],
      resultRows,
      [3000, 2200, 4860]
    ),
    h2(t.swap_interpretation_title),
    ...bulletList(t.swap_interpretation),
  ];
}

function matchupSection(t) {
  return [
    h1(t.matchup_title),
    para(t.matchup_intro),
    para(t.matchup_table_intro, { italics: true }),
    dataTable(
      [t.th_line, t.th_avg_net, t.th_hdcf, t.th_g3_outcomes],
      t.matchup_lines,
      [3000, 2600, 1800, 2660]
    ),
    h2(t.matchup_takeaways_title),
    ...bulletList(t.matchup_takeaways),
  ];
}

function watchSection(t) {
  return [h1(t.watch_title), ...bulletList(t.watch)];
}

function caveatsSection(t) {
  return [h1(t.caveats_title), ...bulletList(t.caveats)];
}

function sourcesSection(t) {
  const out = [h1(t.sources_title)];
  for (const [txt, url] of t.sources) {
    out.push(new Paragraph({
      numbering: { reference: 'bullets', level: 0 },
      spacing: { after: 60 },
      children: [new ExternalHyperlink({
        children: [new TextRun({ text: txt, style: 'Hyperlink', font: 'Arial', size: 18 })],
        link: url,
      })],
    }));
  }
  return out;
}

function brandHeader(t) {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      spacing: { after: 80 },
      children: [
        new TextRun({ text: 'LEMIEUX  ', bold: true, color: BRAND.red, font: 'Arial', size: 18 }),
        new TextRun({ text: '· hockey analytics', color: BRAND.mute, font: 'Arial', size: 16 }),
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

// ---------- prose fact-check guard (light version for pre-game) ----------
// Pre-game piece has no scoring claims. The guard below catches accidental
// future-tense scoring assertions (e.g. "X will score") which violate the
// "no predictions" rail, and any "scored" claim about a non-scorer just in case.
function runProseFactCheck() {
  const corpus = [];
  for (const lang of ['en', 'fr']) {
    const t = T[lang];
    corpus.push(...t.tldr, ...t.matchup_takeaways, ...t.watch, ...t.caveats);
    corpus.push(t.tldr_title, t.matchup_title, t.matchup_intro, t.tbl_d_intro);
  }
  const text = corpus.join(' \n ');
  const banned = [
    /\bwill\s+score\b/i,
    /\bva\s+marquer\b/i,
    /\bMTL\s+wins\s+in\b/i,
    /\bvictoire\s+du\s+CH\s+en\b/i,
    /predict(?:s|ed|ion)\b/i,
  ];
  const violations = [];
  for (const re of banned) {
    const m = text.match(re);
    if (m) violations.push(`Banned pattern matched: "${m[0]}" (regex ${re.source})`);
  }
  if (violations.length) {
    console.error('\nProse fact-check guard: pre-game brief violates "no predictions" rail.');
    for (const v of violations) console.error('  ✗ ' + v);
    process.exit(7);
  }
}

// ---------- BUILD ----------
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
      headers: { default: brandHeader(t) },
      footers: { default: brandFooter(t) },
      children: [
        new Paragraph({ children: [] }),
        ...titleBlock(t),
        ...tldrSection(t),
        ...lineupsSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...tblDSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...swapSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...matchupSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...watchSection(t),
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
    const primary = path.join(__dirname, `game4_pregame_2026-04-26_${lang.toUpperCase()}.docx`);
    let out = primary;
    try {
      fs.writeFileSync(primary, buf);
    } catch (e) {
      if (e.code === 'EBUSY' || e.code === 'EACCES') {
        out = path.join(__dirname, `game4_pregame_2026-04-26_${lang.toUpperCase()}_v2.docx`);
        fs.writeFileSync(out, buf);
        console.log('(primary file locked — wrote alternate)');
      } else throw e;
    }
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
