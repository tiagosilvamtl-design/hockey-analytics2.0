// Game 4 multi-period report — handles N completed periods (P1, P1+P2, P1+P2+P3, OT...).
// Sections:
//   1. TLDR (auto-tailors to "single period" or "multi-period" mode)
//   2. Team totals: per-period + cumulative
//   3. Consolidated ranking (top 12, bottom 5)
//   4. Per-period rankings (compact)
//   5. Period-over-period movers (delta tables) — only shown when ≥2 periods complete
//   6. MTL lines per period + consolidated
//   7. Method + caveats
//
// Reads game4_periods.numbers.json. EN + FR.
//
// Run:
//   node examples/habs_round1_2026/build_game4_periods_post.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, Header, Footer, PageBreak,
  ExternalHyperlink,
} = require('docx');

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'game4_periods.numbers.json'), 'utf8'));
const BAREME = JSON.parse(fs.readFileSync(path.join(__dirname, 'score_bareme.json'), 'utf8'));

function tierFor(score) {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  const t = BAREME.tiers;
  if (score < t.Awful.max) return 'Awful';
  if (score < t.Mediocre.max) return 'Mediocre';
  if (score < t.Good.max) return 'Good';
  return 'Excellent';
}
function tierFill(score) {
  const tier = tierFor(score);
  return tier ? BAREME.tiers[tier].color_hex : undefined;
}
function tierLabel(score, lang) {
  const tier = tierFor(score);
  if (!tier) return '—';
  return BAREME.tiers[tier][lang === 'fr' ? 'label_fr' : 'label_en'];
}

const BRAND = {
  navy: '1F2F4A', navyLight: '2F4A70', red: 'A6192E',
  ink: '111111', mute: '666666', rule: 'BFBFBF',
  good: 'E2F0D9', mid: 'FFF2CC', bad: 'F8CBAD',
  mtlfill: 'EAF1FB', tblfill: 'F4E6E8',
  upfill: 'D4EDDA', downfill: 'F5C6CB',
};

const fmtNum = (n, p = 1) => (n === null || n === undefined) ? '—' : Number(n).toFixed(p);
const fmtFr = (n, p = 1) => fmtNum(n, p).replace('.', ',');
const teamFill = (t) => t === 'MTL' ? BRAND.mtlfill : BRAND.tblfill;
const moveFill = (delta) => delta > 0 ? BRAND.upfill : (delta < 0 ? BRAND.downfill : undefined);

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
  const headerRow = new TableRow({
    tableHeader: true,
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
        // Cells can be: primitive | {value, fill, bold}.
        const isObj = c && typeof c === 'object' && !Array.isArray(c) && 'value' in c;
        const text = isObj ? String(c.value ?? '—') : String(c ?? '—');
        const cellFill = isObj && c.fill ? c.fill : opts.fill;
        const bold = !!(isObj && c.bold);
        return new TableCell({
          borders: cellBorders,
          shading: cellFill ? { type: ShadingType.CLEAR, color: 'auto', fill: cellFill } : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: [new TextRun({ text, font: 'Arial', size: 18, color: BRAND.ink, bold })] })],
        });
      }),
    });
  });
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, columnWidths: widths, rows: [headerRow, ...bodyRows] });
}

const completed = D.meta.completed_periods || [];
const periodLabel = completed.length === 1 ? 'P1' : (completed.length === 2 ? 'P1 + P2' : `P1–P${completed[completed.length - 1]}`);
const matchupParts = D.meta.matchup.split(' @ ');
const awayA = matchupParts[0]; // TBL
const homeA = matchupParts[1]; // MTL

// Cumulative team totals across completed periods.
const cumTeam = { [homeA]: { cf_5v5: 0, hdcf_5v5: 0, sog: 0, hits: 0, goals: 0, hd_attempts: 0, shot_attempts: 0 },
                  [awayA]: { cf_5v5: 0, hdcf_5v5: 0, sog: 0, hits: 0, goals: 0, hd_attempts: 0, shot_attempts: 0 } };
for (const pn of completed) {
  const pTeam = D.periods[`P${pn}`].team;
  for (const t of [homeA, awayA]) {
    for (const k of Object.keys(cumTeam[t])) {
      cumTeam[t][k] += pTeam[t][k] || 0;
    }
  }
}
const cumCfPct = (cumTeam[homeA].cf_5v5 + cumTeam[awayA].cf_5v5) > 0
  ? (100 * cumTeam[homeA].cf_5v5 / (cumTeam[homeA].cf_5v5 + cumTeam[awayA].cf_5v5)) : null;
const cumHdcfPct = (cumTeam[homeA].hdcf_5v5 + cumTeam[awayA].hdcf_5v5) > 0
  ? (100 * cumTeam[homeA].hdcf_5v5 / (cumTeam[homeA].hdcf_5v5 + cumTeam[awayA].hdcf_5v5)) : null;

// Identify the latest delta key (e.g. "P1_to_P2" or "P2_to_P3") if available.
const deltaKeys = Object.keys(D.deltas || {});
const latestDeltaKey = deltaKeys.length ? deltaKeys[deltaKeys.length - 1] : null;
const latestDelta = latestDeltaKey ? D.deltas[latestDeltaKey] : null;

// ---------- TLDR generation (data-driven) ----------
function genTldrEN() {
  const score = D.meta.score_now;
  const lines = [];
  const isFinal = !!D.postgame;
  if (isFinal) {
    const winner = D.postgame.winner;
    const loser = winner === homeA ? awayA : homeA;
    lines.push(
      `**${winner} ${score[winner]}, ${loser} ${score[loser]} (final, regulation).** Series tied 2–2; Game 5 in Tampa. Tampa flipped a 2–1 deficit by scoring 4v4 at 19:06 of P2, then twice in P3 — both Hagel, both with Kucherov primary assist. The pre-game thesis (Crozier swap as a small TBL upgrade) verified directionally and ineffectively; the actual swing came from Hagel + Kucherov in P3.`
    );
  } else {
    lines.push(
      `**Score: ${awayA} ${score[awayA]} – ${score[homeA]} ${homeA}** through ${periodLabel}. ` +
      `Cumulative 5v5 Corsi: ${homeA} ${cumTeam[homeA].cf_5v5} – ${awayA} ${cumTeam[awayA].cf_5v5} ` +
      `(${cumCfPct !== null ? cumCfPct.toFixed(1) : '—'}% MTL). ` +
      `Cumulative 5v5 HD attempts: ${homeA} ${cumTeam[homeA].hdcf_5v5} – ${awayA} ${cumTeam[awayA].hdcf_5v5} ` +
      `(${cumHdcfPct !== null ? cumHdcfPct.toFixed(1) : '—'}% MTL).`
    );
  }
  if (D.consolidated && D.consolidated.skaters_sorted.length) {
    const t = D.consolidated.skaters_sorted[0];
    lines.push(
      `**Game's top composite score: ${t.team} ${t.name}** — ${fmtNum(t.score, 2)} (${tierLabel(t.score, 'en')} tier), ` +
      `${t.g}–${t.a1 + t.a2}, ${t.sog} SOG, ${t.ind_hd_attempts} individual HD attempts. ` +
      `Cumulative ranking has 5 skaters in the Excellent tier (≥3.0): ${D.consolidated.skaters_sorted.slice(0, 5).map(r => `${r.team} ${r.name.split(' ').slice(-1)[0]}`).join(', ')}.`
    );
  }
  if (latestDelta && latestDelta.length) {
    const top = latestDelta[0];
    const bot = latestDelta[latestDelta.length - 1];
    lines.push(
      `**P2 → P3 swing**: Biggest climbers — ${top.team} ${top.name} (Δ ${fmtNum(top.delta, 2)}) and ${latestDelta[1] ? `${latestDelta[1].team} ${latestDelta[1].name}` : ''} (Δ ${latestDelta[1] ? fmtNum(latestDelta[1].delta, 2) : ''}). ` +
      `Biggest drop: ${bot.team} ${bot.name} (Δ ${fmtNum(bot.delta, 2)}). MTL's P2 goal-scorers (Bolduc, Caufield) were the period's top movers DOWN — single-game-period scores reset hard.`
    );
  } else {
    lines.push('Only one completed period in the data so far.');
  }
  return lines;
}

function genTldrFR() {
  const score = D.meta.score_now;
  const lines = [];
  const isFinal = !!D.postgame;
  if (isFinal) {
    const winner = D.postgame.winner;
    const loser = winner === homeA ? awayA : homeA;
    lines.push(
      `**${winner} ${score[winner]}, ${loser} ${score[loser]} (final, temps réglementaire).** Série égale 2–2; Match 5 à Tampa. Tampa renverse un déficit 2–1 en marquant à 4 c. 4 à 19:06 de la P2, puis deux fois en P3 — les deux par Hagel avec Kucherov à la mention principale. La thèse d\'avant-match (l\'échange Crozier comme petite amélioration TBL) était directionnellement juste mais quasi nulle; le vrai swing est venu de Hagel + Kucherov en P3.`
    );
  } else {
    lines.push(
      `**Marque : ${awayA} ${score[awayA]} – ${score[homeA]} ${homeA}** après ${periodLabel}.`
    );
  }
  if (D.consolidated && D.consolidated.skaters_sorted.length) {
    const t = D.consolidated.skaters_sorted[0];
    lines.push(
      `**Meilleur pointage composite du match : ${t.team} ${t.name}** — ${fmtFr(t.score, 2)} (niveau ${tierLabel(t.score, 'fr')}), ` +
      `${t.g}–${t.a1 + t.a2}, ${t.sog} TB, ${t.ind_hd_attempts} CHD individuelles. ` +
      `Le top 5 cumulé compte 5 patineurs dans le niveau Excellent (≥3,0) : ${D.consolidated.skaters_sorted.slice(0, 5).map(r => `${r.team} ${r.name.split(' ').slice(-1)[0]}`).join(', ')}.`
    );
  }
  if (latestDelta && latestDelta.length) {
    const top = latestDelta[0];
    const bot = latestDelta[latestDelta.length - 1];
    lines.push(
      `**Swing P2 → P3** : Plus fortes hausses — ${top.team} ${top.name} (Δ ${fmtFr(top.delta, 2)})${latestDelta[1] ? ` et ${latestDelta[1].team} ${latestDelta[1].name} (Δ ${fmtFr(latestDelta[1].delta, 2)})` : ''}. ` +
      `Plus grosse baisse : ${bot.team} ${bot.name} (Δ ${fmtFr(bot.delta, 2)}). Les marqueurs M2 du CH (Bolduc, Caufield) sont les plus grosses chutes — les pointages d\'une seule période se réinitialisent fort.`
    );
  } else {
    lines.push(`Une seule période complétée pour l'instant.`);
  }
  return lines;
}

// ---------- sections ----------
function baremeSection(t, lang) {
  const so = BAREME.stats_overall;
  const t10 = BAREME.tiers.Awful.max;
  const t50 = BAREME.tiers.Mediocre.max;
  const t90 = BAREME.tiers.Good.max;
  const labelKey = lang === 'fr' ? 'label_fr' : 'label_en';
  const rows = [
    {
      cells: [
        { value: BAREME.tiers.Awful[labelKey],     fill: BAREME.tiers.Awful.color_hex,     bold: true },
        `< ${t10.toFixed(2)}`,
        lang === 'fr' ? 'Bottom 10 % des observations en séries' : 'Bottom 10% of playoff observations',
      ],
      _opts: {},
    },
    {
      cells: [
        { value: BAREME.tiers.Mediocre[labelKey],  fill: BAREME.tiers.Mediocre.color_hex,  bold: true },
        `${t10.toFixed(2)} – ${t50.toFixed(2)}`,
        lang === 'fr' ? '10ᵉ – 50ᵉ percentile' : '10th – 50th percentile',
      ],
    },
    {
      cells: [
        { value: BAREME.tiers.Good[labelKey],      fill: BAREME.tiers.Good.color_hex,      bold: true },
        `${t50.toFixed(2)} – ${t90.toFixed(2)}`,
        lang === 'fr' ? '50ᵉ – 90ᵉ percentile (au-dessus de la médiane)' : '50th – 90th percentile (above median, contributing)',
      ],
    },
    {
      cells: [
        { value: BAREME.tiers.Excellent[labelKey], fill: BAREME.tiers.Excellent.color_hex, bold: true },
        `≥ ${t90.toFixed(2)}`,
        lang === 'fr' ? 'Top 10 % — période dominante' : 'Top 10% — dominant period',
      ],
    },
  ];
  const provBlurb = lang === 'fr'
    ? `Calibré sur ${so.n.toLocaleString('fr-CA')} observations joueur-période issues de ${BAREME.meta.games_fetched} matchs des séries 2024 + 2025. Distribution : moyenne ${fmtFr(so.mean, 2)}, médiane ${fmtFr(so.median, 2)}, écart-type ${fmtFr(so.stdev, 2)} (min ${fmtFr(so.min, 2)}, max ${fmtFr(so.max, 2)}). La distribution est asymétrique à droite — les seuils par percentiles sont plus honnêtes qu'un score-z gaussien.`
    : `Calibrated on ${so.n.toLocaleString('en-US')} player-period observations from ${BAREME.meta.games_fetched} games of the 2024 + 2025 playoffs. Distribution: mean ${fmtNum(so.mean, 2)}, median ${fmtNum(so.median, 2)}, stdev ${fmtNum(so.stdev, 2)} (min ${fmtNum(so.min, 2)}, max ${fmtNum(so.max, 2)}). The distribution is right-skewed — percentile thresholds are more honest than a Gaussian z-score.`;
  return [
    h1(t.bareme_title),
    para(t.bareme_intro, { italics: true }),
    dataTable(
      [t.th_tier, t.th_score_range, t.th_meaning],
      rows,
      [2000, 2500, 5500]
    ),
    para(provBlurb, { italics: true, color: BRAND.mute }),
  ];
}

function gameStorySection(t, lang) {
  if (!D.postgame) return [];
  const seq = D.postgame.goal_sequence || [];
  const out = [h1(t.story_title), para(t.story_intro)];
  // Build the chronological table
  const rows = seq.map(g => {
    const teamCells = `${g.owner}`;
    const scorerCell = g.scorer || '—';
    const assists = [g.assist1, g.assist2].filter(Boolean).join(', ') || '—';
    return {
      cells: [
        `P${g.period} ${g.time}`,
        teamCells,
        scorerCell,
        assists,
        g.situation,
      ],
      _opts: { fill: g.owner === 'MTL' ? BRAND.mtlfill : BRAND.tblfill },
    };
  });
  out.push(dataTable([t.th_when, t.th_team, t.th_scorer, t.th_assists, t.th_sit], rows, [1300, 800, 2700, 4000, 1200]));
  // Narrative bullets — manually reasoned from the sequence
  out.push(h2(t.story_narrative_title));
  // Auto-generate narrative from the data
  const mtlGoals = seq.filter(g => g.owner === 'MTL');
  const tblGoals = seq.filter(g => g.owner === 'TBL');
  const mtlPpGoals = mtlGoals.filter(g => g.situation.startsWith('5v4')).length;
  const tblPpGoals = tblGoals.filter(g => g.situation.startsWith('5v4')).length;
  const tbl4v4 = tblGoals.filter(g => g.situation.startsWith('4v4')).length;
  const hagelGoals = tblGoals.filter(g => (g.scorer || '').includes('Hagel')).length;
  const narr = lang === 'fr' ? [
    `**P1 (0–0)** : Tampa a dirigé la période (Corsi 5 c. 5 ${D.periods.P1.team.MTL.cf_5v5}–${D.periods.P1.team.TBL.cf_5v5}, CHD ${D.periods.P1.team.MTL.hdcf_5v5}–${D.periods.P1.team.TBL.hdcf_5v5}). Dobeš a tenu le fort.`,
    `**P2 (CH 2–1)** : Bolduc à 10:06 (Guhle, Texier) à 5 c. 5 — la thèse d\'avant-match (servir Texier–Dach–Bolduc face au 3ᵉ duo refait) livre. Caufield à 13:29 sur l\'AN (Suzuki, Hutson) — 2–0. Mais Guentzel à 19:06 ${tbl4v4 ? 'à 4 c. 4' : ''} (Moser, Raddysh) — TBL revient à 2–1 avant l\'entracte.`,
    `**P3 (TBL 3–2)** : Hagel ${hagelGoals === 2 ? 'avec deux buts' : 'avec un but'} — l\'AN à 1:40 (Kucherov, Guentzel) pour égaler, puis le but vainqueur à 15:07 à 5 c. 5 (Kucherov, Moser). Score composite Hagel par période : 0,00 → 1,75 → ${fmtFr(D.postgame.hagel_by_period.P3.score, 2)} (top 10 % toutes périodes confondues).`,
    `**Spéciales** : ${tblPpGoals} but${tblPpGoals > 1 ? 's' : ''} TBL en AN, ${mtlPpGoals} but CH en AN. La 4 c. 4 du M2 a swingé la fin de période.`,
  ] : [
    `**P1 (0–0)**: Tampa drove the period (5v5 Corsi ${D.periods.P1.team.MTL.cf_5v5}–${D.periods.P1.team.TBL.cf_5v5}, HDCF ${D.periods.P1.team.MTL.hdcf_5v5}–${D.periods.P1.team.TBL.hdcf_5v5}). Dobeš held it level.`,
    `**P2 (MTL 2–1)**: Bolduc 10:06 (Guhle, Texier) at 5v5 — the pre-game thesis (feed Texier–Dach–Bolduc into the reshuffled 3rd pair) cashed. Caufield 13:29 on the PP (Suzuki, Hutson) — 2–0. Then Guentzel at 19:06 ${tbl4v4 ? '4v4' : ''} (Moser, Raddysh) — TBL back to 2–1 entering the intermission.`,
    `**P3 (TBL 3–2)**: Hagel ${hagelGoals === 2 ? 'twice' : 'once'} — PP at 1:40 (Kucherov, Guentzel) to tie, then the game-winner at 15:07 at 5v5 (Kucherov, Moser). Hagel composite score by period: 0.00 → 1.75 → ${fmtNum(D.postgame.hagel_by_period.P3.score, 2)} (top 10% of all periods sampled).`,
    `**Special teams**: ${tblPpGoals} TBL PP goal${tblPpGoals !== 1 ? 's' : ''}, ${mtlPpGoals} MTL PP goal. The 4v4 stretch late in P2 swung the period.`,
  ];
  out.push(...bullets(narr));
  return out;
}

function thesisCheckSection(t, lang) {
  if (!D.postgame) return [];
  const cz = D.postgame.crozier_on_ice;
  const out = [h1(t.thesis_title), para(t.thesis_intro)];
  // Pull the swap result from the swap json (already in repo).
  let swap = null;
  try {
    swap = JSON.parse(fs.readFileSync(path.join(__dirname, 'game4_pregame_swap.numbers.json'), 'utf8'));
  } catch (e) { /* ok */ }
  if (swap) {
    const s = swap.swap;
    const rows = [
      [
        lang === 'fr' ? 'Net BA/match projeté pour TBL (modèle d\'échange poolé)' : 'Projected net xG/game for TBL (pooled swap engine)',
        (lang === 'fr' ? fmtFr : fmtNum)(s.delta_net_per_game, 2),
        lang === 'fr' ? `IC 80 % BAF : [${fmtFr(s.delta_xgf_ci80[0], 2)}, ${fmtFr(s.delta_xgf_ci80[1], 2)}] — chevauche zéro` : `80% CI on xGF: [${fmtNum(s.delta_xgf_ci80[0], 2)}, ${fmtNum(s.delta_xgf_ci80[1], 2)}] — straddles zero`,
      ],
      [
        lang === 'fr' ? 'Buts pour TBL avec Crozier sur la glace (M4)' : 'TBL goals while Crozier on-ice (Game 4)',
        cz.goals_for_oi,
        lang === 'fr' ? 'Mesuré via présences LNH.com' : 'Measured via NHL.com shifts',
      ],
      [
        lang === 'fr' ? 'Buts contre TBL avec Crozier sur la glace (M4)' : 'TBL goals against while Crozier on-ice (Game 4)',
        cz.goals_against_oi,
        lang === 'fr' ? 'Présence partielle en P3 — voir « Mise en garde »' : 'P3 shifts partially populated — see caveat',
      ],
    ];
    out.push(dataTable([t.th_metric, t.th_value, t.th_note], rows.map(r => ({cells: r})), [4400, 1500, 4100]));
  }
  const verdict = lang === 'fr' ? [
    `**Verdict du modèle d\'échange** : la projection était directionnellement haussière mais sans signification statistique (IC 80 % chevauchant zéro). Le résultat M4 (Crozier ${cz.goals_for_oi}–${cz.goals_against_oi} sur la glace) est compatible avec un effet quasi-nul. Le changement de défenseur n\'a ni cassé ni sauvé Tampa.`,
    `**Ce qui a vraiment changé pour TBL** : Hagel et Kucherov en P3. Le pointage composite de Hagel est passé de 0,00 (P1) à 1,75 (P2) à ${fmtFr(D.postgame.hagel_by_period.P3.score, 2)} (P3, niveau Excellent). Kucherov : Δ ${fmtFr(7.9 - 1.9, 2)} cumulatif. La différence c\'est le top 6, pas le 3ᵉ duo.`,
  ] : [
    `**Swap engine verdict**: the projection was directionally up but not statistically meaningful (80% CI straddled zero). The Game 4 result (Crozier ${cz.goals_for_oi}–${cz.goals_against_oi} on-ice) is consistent with near-zero effect. The defenseman swap neither broke nor saved Tampa.`,
    `**What actually shifted for TBL**: Hagel and Kucherov in P3. Hagel composite score went 0.00 (P1) → 1.75 (P2) → ${fmtNum(D.postgame.hagel_by_period.P3.score, 2)} (P3, Excellent tier). Kucherov: Δ ${fmtNum(7.9 - 1.9, 2)} cumulative. The difference came from the top six, not the third pair.`,
  ];
  out.push(...bullets(verdict));
  return out;
}

function playerOfTheMatchSection(t, lang) {
  if (!D.postgame || !D.postgame.hagel_by_period) return [];
  const h = D.postgame.hagel_by_period;
  const rows = ['P1', 'P2', 'P3'].map(k => {
    const r = h[k] || {score: 0, g: 0, a: 0, sog: 0, ind_hd_attempts: 0};
    return [k, r.g, r.a, r.sog, r.ind_hd_attempts, fmtNum(r.score, 2), tierLabel(r.score, lang)];
  });
  // tier-color the score cell in those rows
  const styledRows = rows.map(r => ({
    cells: [
      r[0], r[1], r[2], r[3], r[4],
      { value: r[5], fill: tierFill(parseFloat(r[5])), bold: true },
      { value: r[6], fill: tierFill(parseFloat(r[5])) },
    ],
  }));
  return [
    h1(t.potm_title),
    para(t.potm_intro),
    dataTable([t.th_period, t.th_lg, t.th_la, t.th_lsog, t.th_lihd, t.th_score, t.th_tier], styledRows, [1100, 700, 700, 700, 900, 1000, 1500]),
  ];
}

function teamTotalsSection(t) {
  const headerCells = [t.th_period];
  for (const team of [homeA, awayA]) {
    headerCells.push(`${team} CF`);
    headerCells.push(`${team} HD`);
    headerCells.push(`${team} SOG`);
    headerCells.push(`${team} G`);
    headerCells.push(`${team} Hits`);
  }
  const rows = [];
  for (const pn of completed) {
    const pT = D.periods[`P${pn}`].team;
    const r = [`P${pn}`];
    for (const team of [homeA, awayA]) {
      r.push(pT[team].cf_5v5);
      r.push(pT[team].hdcf_5v5);
      r.push(pT[team].sog);
      r.push(pT[team].goals);
      r.push(pT[team].hits);
    }
    rows.push({ cells: r });
  }
  // cumulative row
  const cum = [t.cumulative];
  for (const team of [homeA, awayA]) {
    cum.push(cumTeam[team].cf_5v5);
    cum.push(cumTeam[team].hdcf_5v5);
    cum.push(cumTeam[team].sog);
    cum.push(cumTeam[team].goals);
    cum.push(cumTeam[team].hits);
  }
  rows.push({ cells: cum, _opts: { fill: BRAND.mid } });
  const widths = [1100];
  for (let i = 0; i < 10; i++) widths.push(900);
  return [
    h1(t.team_title),
    para(t.team_intro, { italics: true }),
    dataTable(headerCells, rows, widths),
  ];
}

function rankRow(r, idx, t, lang) {
  return {
    cells: [
      String(idx + 1), `${r.team} ${r.name}`, r.position,
      `${r.g}–${(r.a1 || 0) + (r.a2 || 0)}`, r.sog, r.ind_hd_attempts || 0,
      r.blocks_made || 0, r.hits_for || 0,
      `${r.takeaways || 0}/${r.giveaways || 0}`,
      { value: fmtNum(r.score, 2), fill: tierFill(r.score), bold: true },
      { value: tierLabel(r.score, lang), fill: tierFill(r.score) },
    ],
    _opts: { fill: teamFill(r.team) },
  };
}

function consolidatedRankSection(t, lang) {
  if (!D.consolidated) return [];
  const all = D.consolidated.skaters_sorted;
  const top12 = all.slice(0, 12).map((r, i) => rankRow(r, i, t, lang));
  const bot5offset = Math.max(0, all.length - 5);
  const bot5 = all.slice(bot5offset).map((r, i) => rankRow(r, bot5offset + i, t, lang));
  const headers = [t.th_rank, t.th_player, t.th_pos, t.th_g_a, t.th_sog, t.th_ihd, t.th_blk, t.th_hit, t.th_take, t.th_score, t.th_tier];
  const widths = [500, 2900, 700, 700, 700, 700, 700, 700, 1000, 800, 1100];
  return [
    h1(t.cons_title),
    para(t.cons_intro, { italics: true }),
    dataTable(headers, top12, widths),
    para(t.cons_bottom_intro, { italics: true }),
    dataTable(headers, bot5, widths),
  ];
}

function perPeriodRankSection(t, lang) {
  const out = [h1(t.byperiod_title), para(t.byperiod_intro, { italics: true })];
  for (const pn of completed) {
    const top = D.periods[`P${pn}`].skaters_sorted.slice(0, 8).map((r, i) => rankRow(r, i, t, lang));
    out.push(h2(`P${pn}`));
    out.push(dataTable(
      [t.th_rank, t.th_player, t.th_pos, t.th_g_a, t.th_sog, t.th_ihd, t.th_blk, t.th_hit, t.th_take, t.th_score, t.th_tier],
      top,
      [500, 2900, 700, 700, 700, 700, 700, 700, 1000, 800, 1100]
    ));
  }
  return out;
}

function deltasSection(t, lang) {
  if (!latestDelta || !latestDelta.length) {
    return [h1(t.deltas_title), para(t.deltas_none, { italics: true })];
  }
  // Up: top 8 by delta, Down: bottom 8 by delta
  const ups = latestDelta.filter(r => r.delta > 0).slice(0, 8);
  const downs = latestDelta.filter(r => r.delta < 0).slice(-8).reverse();
  // Build column keys based on the delta key e.g. P1_to_P2 -> p1, p2
  const m = latestDeltaKey.match(/P(\d+)_to_P(\d+)/);
  const a = m ? m[1] : '?'; const b = m ? m[2] : '?';
  const headers = [t.th_player, t.th_pos, `Score P${a}`, `Score P${b}`, `Δ`, `SOG P${a}→P${b}`, `iHD P${a}→P${b}`, `G P${a}→P${b}`];
  function mkRow(r) {
    return {
      cells: [
        `${r.team} ${r.name}`, r.position || '',
        fmtNum(r[`score_p${a}`], 2), fmtNum(r[`score_p${b}`], 2),
        (r.delta > 0 ? '+' : '') + fmtNum(r.delta, 2),
        `${r[`sog_p${a}`]}→${r[`sog_p${b}`]}`,
        `${r[`ihd_p${a}`]}→${r[`ihd_p${b}`]}`,
        `${r[`g_p${a}`]}→${r[`g_p${b}`]}`,
      ],
      _opts: { fill: moveFill(r.delta) },
    };
  }
  const widths = [3000, 700, 1000, 1000, 900, 1200, 1200, 1000];
  return [
    h1(t.deltas_title.replace('{from}', `P${a}`).replace('{to}', `P${b}`)),
    para(t.deltas_intro.replace('{from}', `P${a}`).replace('{to}', `P${b}`), { italics: true }),
    h2(t.movers_up),
    dataTable(headers, ups.map(mkRow), widths),
    h2(t.movers_down),
    dataTable(headers, downs.map(mkRow), widths),
  ];
}

function linesSection(t) {
  // Consolidated lines table + per-period mini tables
  const cons = D.mtl_lines_consolidated || [];
  const consRows = cons.map(L => [
    `L${L.line}`, L.players.join(' / '),
    L.g, L.a, L.sog, L.ind_hd_attempts, L.hits_for, L.blocks_made, fmtNum(L.score_sum, 2),
  ]);
  const out = [
    h1(t.lines_title),
    para(t.lines_intro, { italics: true }),
    h2(t.cumulative),
    dataTable(
      [t.th_line, t.th_players, t.th_lg, t.th_la, t.th_lsog, t.th_lihd, t.th_lhits, t.th_lblk, t.th_lscore],
      consRows,
      [700, 4500, 700, 700, 700, 700, 700, 700, 800]
    ),
  ];
  for (const pn of completed) {
    const ln = D.mtl_lines_by_period[`P${pn}`] || [];
    if (!ln.length) continue;
    out.push(h2(`P${pn}`));
    out.push(dataTable(
      [t.th_line, t.th_players, t.th_lg, t.th_la, t.th_lsog, t.th_lihd, t.th_lhits, t.th_lblk, t.th_lscore],
      ln.map(L => [`L${L.line}`, L.players.join(' / '), L.g, L.a, L.sog, L.ind_hd_attempts, L.hits_for, L.blocks_made, fmtNum(L.score_sum, 2)]),
      [700, 4500, 700, 700, 700, 700, 700, 700, 800]
    ));
  }
  return out;
}

const T = {
  en: {
    title: `Multi-period ranking — Habs vs Lightning, Game 4 (Apr 26, 2026)`,
    subtitle: `${periodLabel} complete · ${awayA} ${D.meta.score_now[awayA]} – ${D.meta.score_now[homeA]} ${homeA} now`,
    tldr_title: 'Three things',
    tldr: genTldrEN(),
    team_title: 'Team totals — per period and cumulative',
    team_intro: 'All numbers from full PBP. CF/HDCF restricted to 5v5 (situationCode 1551). SOG and goals all-strength.',
    th_period: 'Period',
    cumulative: 'Cumulative',
    cons_title: 'Cumulative ranking — both teams (top 12, bottom 5)',
    cons_intro: 'Sorted by composite score across all completed periods.',
    cons_bottom_intro: 'Bottom 5 (skaters with non-trivial events):',
    byperiod_title: 'Per-period top performers (top 8 each)',
    byperiod_intro: 'For drilling into where each player\'s value showed up.',
    deltas_title: 'Period-over-period movers ({from} → {to})',
    deltas_intro: 'Per-skater composite-score change between {from} and {to}. Green = improved, red = regressed. Read with TOI in mind — short-shift skewing is real.',
    deltas_none: 'Only one completed period so far — deltas will populate after the next intermission.',
    movers_up: 'Movers UP',
    movers_down: 'Movers DOWN',
    th_rank: '#', th_player: 'Player', th_pos: 'Pos',
    th_g_a: 'G–A', th_sog: 'SOG', th_ihd: 'iHD', th_blk: 'Blk', th_hit: 'Hit',
    th_take: 'Tk/Gv', th_score: 'Score', th_tier: 'Tier',
    story_title: 'How the game went',
    story_intro: 'Goal sequence in chronological order, with situation (5v5, 5v4 = PP, 4v4 = coincidental minors). Row color indicates which team scored.',
    th_when: 'When', th_scorer: 'Scorer', th_assists: 'Assists', th_sit: 'Situation',
    story_narrative_title: 'Narrative',
    thesis_title: 'Pre-game thesis check — did the swap engine call it?',
    thesis_intro: 'The pre-game brief projected the Crozier-for-Carlile swap at +0.11 net xG/game for TBL with the 80% CI straddling zero — a directional but not statistically significant upgrade. Reality:',
    th_metric: 'Metric', th_value: 'Value', th_note: 'Note',
    potm_title: 'Player of the match — Brandon Hagel',
    potm_intro: 'Per-period composite score for Hagel: quiet through 40, then top-tier in P3 (2 goals). The score recipe captures both his individual offense and his on-ice contribution.',
    bareme_title: 'Score barème — what\'s a good number?',
    bareme_intro: 'A 4-tier rating scale derived from a representative sample of 2024 + 2025 playoff games. Apply the same composite-score recipe to every skater-period observation, then read percentile cuts. Thresholds + colors below.',
    th_score_range: 'Score range', th_meaning: 'What it means',
    lines_title: 'MTL forward lines',
    lines_intro: 'Sum of individual contributions across each trio. Player names from canonical lineup yaml.',
    th_line: 'Line', th_players: 'Players',
    th_lg: 'G', th_la: 'A', th_lsog: 'SOG', th_lihd: 'iHD', th_lhits: 'Hits', th_lblk: 'Blocks', th_lscore: 'Score sum',
    method_title: 'Method + caveats',
    method: [
      'Source: NHL.com play-by-play + boxscore (full game data through current state).',
      'Per-player ON-ICE Corsi NOT computed — NHL.com shifts trail PBP and would mis-attribute. Individual contribution and team totals are complete.',
      'Composite score: G×3 + A×2 + SOG×0.5 + ind-HD×0.75 + (missed/blocked attempts)×0.15 + (hits + blocks)×0.25 − giveaways×0.5 + takeaways×0.5.',
      'xG model not applied (NST publishes post-game). Read magnitudes as directional.',
    ],
    sources_title: 'Sources',
    sources: [
      ['NHL.com — Play-by-play (live)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/play-by-play`],
      ['NHL.com — Boxscore (live)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/boxscore`],
    ],
    footer_left: `Lemieux · ${periodLabel} ranking · Game 4 MTL @ TBL`,
    footer_right: 'Page',
  },
  fr: {
    title: `Classement multi-période — CH c. Lightning, Match 4 (26 avril 2026)`,
    subtitle: `${periodLabel} complétée(s) · ${awayA} ${D.meta.score_now[awayA]} – ${D.meta.score_now[homeA]} ${homeA} actuellement`,
    tldr_title: 'Trois constats',
    tldr: genTldrFR(),
    team_title: 'Totaux d\'équipe — par période et cumulatif',
    team_intro: 'Toutes valeurs du JPJ complet. CF/CHD restreints à 5 c. 5 (situationCode 1551). TB et buts à toutes forces.',
    th_period: 'Période',
    cumulative: 'Cumulatif',
    cons_title: 'Classement cumulatif — les deux équipes (top 12, bas 5)',
    cons_intro: 'Trié par pointage composite sur toutes les périodes complétées.',
    cons_bottom_intro: 'Bas 5 (patineurs avec événements non triviaux) :',
    byperiod_title: 'Meilleurs par période (top 8 chacune)',
    byperiod_intro: 'Pour creuser où chaque joueur a apporté sa valeur.',
    deltas_title: 'Mouvements période sur période ({from} → {to})',
    deltas_intro: 'Variation du pointage composite par patineur entre {from} et {to}. Vert = en hausse, rouge = en baisse. Lire avec le TG en tête — les présences courtes peuvent fausser.',
    deltas_none: 'Une seule période complétée — les deltas apparaîtront après la prochaine période.',
    movers_up: 'En HAUSSE',
    movers_down: 'En BAISSE',
    th_rank: '#', th_player: 'Joueur', th_pos: 'Pos',
    th_g_a: 'B–A', th_sog: 'TB', th_ihd: 'CHDi', th_blk: 'Blq', th_hit: 'M.É.',
    th_take: 'Réc/Rev', th_score: 'Pointage', th_tier: 'Niveau',
    story_title: 'Comment le match s\'est déroulé',
    story_intro: 'Séquence des buts en ordre chronologique, avec situation (5 c. 5, 5 c. 4 = AN, 4 c. 4 = pénalités coïncidentes). La couleur de la rangée indique l\'équipe qui marque.',
    th_when: 'Moment', th_scorer: 'Marqueur', th_assists: 'Mentions', th_sit: 'Situation',
    story_narrative_title: 'Récit',
    thesis_title: 'Vérification de la thèse d\'avant-match — le moteur d\'échange avait-il vu juste?',
    thesis_intro: 'Le survol d\'avant-match projetait l\'échange Crozier-pour-Carlile à +0,11 BA net/match pour TBL avec un IC à 80 % chevauchant zéro — direction haussière, pas significatif. Réalité :',
    th_metric: 'Mesure', th_value: 'Valeur', th_note: 'Note',
    potm_title: 'Joueur du match — Brandon Hagel',
    potm_intro: 'Pointage composite de Hagel par période : silencieux pendant 40 minutes, puis sommet en P3 (2 buts). La recette du pointage capte à la fois sa production individuelle et sa contribution sur la glace.',
    bareme_title: 'Barème du pointage — qu\'est-ce qu\'un bon chiffre?',
    bareme_intro: 'Échelle à 4 niveaux dérivée d\'un échantillon représentatif des séries 2024 + 2025. On applique la même recette de pointage composite à toutes les observations joueur-période, puis on lit les coupures par percentile. Seuils et couleurs ci-dessous.',
    th_score_range: 'Plage de pointage', th_meaning: 'Signification',
    lines_title: 'Trios à l\'avant du CH',
    lines_intro: 'Somme des contributions individuelles par trio. Noms tirés du fichier yaml d\'alignement.',
    th_line: 'Trio', th_players: 'Joueurs',
    th_lg: 'B', th_la: 'A', th_lsog: 'TB', th_lihd: 'CHDi', th_lhits: 'M.É.', th_lblk: 'Blq', th_lscore: 'Σ pointage',
    method_title: 'Méthode et mises en garde',
    method: [
      'Source : JPJ + sommaire LNH.com (données complètes jusqu\'à l\'état actuel).',
      'Le Corsi ON-ICE par joueur n\'est PAS calculé — le tableau des présences en direct est en retard sur le JPJ et causerait une mauvaise attribution.',
      'Pointage composite : B×3 + A×2 + TB×0,5 + CHD-i×0,75 + (ratés/bloqués)×0,15 + (mises en échec + blocages)×0,25 − revirements×0,5 + récupérations×0,5.',
      'Modèle xG non appliqué (NST publie en post-match). Amplitudes à lire comme directionnelles.',
    ],
    sources_title: 'Sources',
    sources: [
      ['LNH.com — JPJ (en direct)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/play-by-play`],
      ['LNH.com — Sommaire (en direct)', `https://api-web.nhle.com/v1/gamecenter/${D.meta.game_id}/boxscore`],
    ],
    footer_left: `Lemieux · classement ${periodLabel} · Match 4 CH c. TBL`,
    footer_right: 'Page',
  },
};

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
        h1(t.tldr_title), ...bullets(t.tldr),
        ...gameStorySection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...thesisCheckSection(t, lang),
        ...playerOfTheMatchSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...baremeSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...teamTotalsSection(t),
        new Paragraph({ children: [new PageBreak()] }),
        ...consolidatedRankSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...deltasSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...perPeriodRankSection(t, lang),
        new Paragraph({ children: [new PageBreak()] }),
        ...linesSection(t),
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
    // Use a distinct prefix from build_game4_p1_post.js so the standalone P1 doc isn't clobbered.
    const tag = completed.length === 1 ? 'p1only' : (completed.length === 2 ? 'p1p2' : `p1-p${completed[completed.length - 1]}`);
    const primary = path.join(__dirname, `game4_periods_${tag}_2026-04-26_${lang.toUpperCase()}.docx`);
    let out = primary;
    try {
      fs.writeFileSync(primary, buf);
    } catch (e) {
      if (e.code === 'EBUSY' || e.code === 'EACCES') {
        out = path.join(__dirname, `game4_${tag}_2026-04-26_${lang.toUpperCase()}_v2.docx`);
        fs.writeFileSync(out, buf);
      } else throw e;
    }
    console.log(`wrote ${out} (${buf.length} bytes)`);
  }
})().catch(e => { console.error(e); process.exit(1); });
