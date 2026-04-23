Montreal Canadiens --- 2026 Playoffs, Round 1

*A data-forward, intellectually-honest look at the MTL vs. TBL series*

Prepared 2026-04-22 · Series: 2026 NHL Stanley Cup Playoffs --- Round 1

Executive summary

Montreal opened its first-round series against Tampa Bay with a heroic
Game 1 (Slafkovský power-play hat trick, OT winner) and gave up a
late-game collapse in Game 2 (OT loss). This report digs into four
questions the friend group asked: (1) what would swapping Dach and
Texier out for Gallagher and Veleno do to the numbers, (2) what could
Laine add on PP2 if healthy, (3) who on MTL is actually moving the
needle in 25-26, and (4) what does a data-optimal lineup look like ---
plus a targeted look at Slafkovský\'s series by period.

**Four-bullet read:**

- The Dach→Gallagher / Texier→Veleno 2-for-2 at 5v5 projects a combined
  net of +0.051 xG per 60 --- a wash. CIs straddle zero; the data can\'t
  distinguish these lineups.

- On 5v4, the Texier→Veleno side of the swap is meaningfully negative
  --- Texier has been a real PP2 contributor this year and Veleno is a
  bottom-six 5v5 guy, not a PP option.

- Laine, if healthy, has enough pooled PP sample to show he\'s not a
  slam-dunk upgrade --- his on-ice 5v4 isolated rate is negative over
  the pooled window (small sample, post-injury context).

- Slafkovský per-period analysis confirms the eye test: 5 shots and 3
  goals in the \"hot\" bucket (G1 entire + G2 P1), zero shots in the
  \"cold\" bucket (G2 P3 + OT). He was not a driver of Game 2\'s
  collapse --- he was held off the puck.

How to read this report

+--------------------------------------------------------------------+
| **Key concepts at a glance**                                       |
|                                                                    |
| Expected goals (xG): each shot is assigned a probability of        |
| becoming a goal based on location, type, and context. xGF is       |
| expected goals for, xGA is expected goals against.                 |
|                                                                    |
| Rate per 60 (xGF/60, xGA/60): event count per 60 minutes of ice    |
| time --- the standard way to compare players and teams across      |
| different sample sizes.                                            |
|                                                                    |
| Isolated impact (iso_xgf60 / iso_xga60): player\'s on-ice rate     |
| minus the team\'s rate without the player. If positive on offense, |
| the team creates more xG with him on the ice. If negative on       |
| defense, the team gives up less xG with him on the ice (good).     |
|                                                                    |
| 80% confidence interval: we show the range of plausible values,    |
| not a single point. We use 80% rather than 95% because 95% on a    |
| 16-game playoff sample looks like \"we know nothing\" --- 80%      |
| shows signal when it exists without hiding it. CI spans zero =     |
| directionally ambiguous.                                           |
|                                                                    |
| Pooled baseline: for isolated impacts, we sum events and minutes   |
| across 2024-25 regular + playoffs and 2025-26 regular + playoffs   |
| so low-GP or traded players (Dach, Texier) get a more stable read. |
| For \"who\'s doing well\" and the optimal lineup, we use 2025-26   |
| only, as the user asked.                                           |
|                                                                    |
| *Directional, not predictive: this report never predicts series    |
| outcomes. It estimates what the numbers say about isolated player  |
| impact --- coaches see chemistry, matchups, and situational        |
| context this model cannot.*                                        |
+--------------------------------------------------------------------+

1\. Lineup swap analysis

The centerpiece. We project what each individual swap does to MTL\'s
per-60 team rates, then combine. All values use pooled baseline (2
seasons + both playoffs) unless noted; slot minutes are set to the OUT
player\'s usage in the context --- about 12 minutes per game at 5v5 for
these bottom/middle-six roles.

1.1 Dach → Gallagher

At 5v5, this swap is a coin flip. Dach\'s isolated impact is slightly
negative on offense (-0.128 iso xGF/60) and slightly positive on
defense; Gallagher is the mirror image. Over his pooled sample (+1878.4m
of 5v5 TOI across 2 seasons), Gallagher has been a genuine
possession-driving veteran --- better than his 25-26-only numbers
suggest.

  -----------------------------------------------------------------------
  **Metric**       **OUT: Dach**         **IN:    **Δ (per     **80% CI**
                                   Gallagher**       60)** 
  ---------------- ------------- ------------- ----------- --------------
  5v5 iso xGF/60          -0.128        +0.350      +0.095       (-0.036,
                                                                  +0.226)

  5v5 iso xGA/60          +0.053        -0.023      -0.015       (-0.152,
                                                                  +0.122)

  5v4 iso xGF/60          -1.676        -1.319      +0.009            ---

  Pooled TOI 5v5 /    +1171.8m /    +1878.4m /         ---            ---
  5v4                    +183.3m       +236.6m             
  -----------------------------------------------------------------------

+--------------------------------------------------------------------+
| **Plain-language verdict**                                         |
|                                                                    |
| Net team impact of Dach → Gallagher ≈ +0.110 xG per 60 at 5v5, CIs |
| straddling zero. A wash in the data. On PP2, Dach is the incumbent |
| and has meaningful PP TOI; Gallagher is not a PP option. This      |
| decision is driven by injury status and chemistry, not numbers.    |
+--------------------------------------------------------------------+

1.2 Texier → Veleno

Texier\'s pooled 5v5 impact across STL and MTL minutes (+1025.5m total)
is near-neutral. Veleno is notably worse on offense (-0.557 iso xGF/60)
but also suppresses xG against slightly better. At 5v4, Texier is the
real loss: his pooled 5v4 iso xGF/60 is +0.589, well ahead of Veleno,
who has essentially no PP role. If PP2 minutes are at stake, the swap is
clearly negative.

  -----------------------------------------------------------------------
  **Metric**              **OUT:         **IN:    **Δ (per     **80% CI**
                        Texier**      Veleno**       60)** 
  ---------------- ------------- ------------- ----------- --------------
  5v5 iso xGF/60          -0.120        -0.557      -0.091       (-0.233,
                                                                  +0.051)

  5v5 iso xGA/60          -0.216        -0.370      -0.032       (-0.181,
                                                                  +0.117)

  5v4 iso xGF/60          +0.589        -6.610      -0.180            ---

  Pooled TOI 5v5 /    +1025.5m /    +1453.8m /         ---            ---
  5v4                     +80.5m         +6.3m             
  -----------------------------------------------------------------------

+--------------------------------------------------------------------+
| **Traded-player caveat**                                           |
|                                                                    |
| Texier\'s pooled sample includes his 2025-26 split between STL and |
| MTL and his 2024-25 STL minutes. Our isolated-impact math compares |
| his total on-ice events against MTL\'s team totals, which is a     |
| mild approximation. The directional read (Texier ≥ Veleno on       |
| offense) is robust; the magnitude is noisier than usual.           |
+--------------------------------------------------------------------+

1.3 Combined 2-for-2

Adding the two independent swaps (variances add in quadrature), the
combined projected team impact at 5v5 is mildly positive on net but both
confidence intervals cross zero.

  ---------------------------------------------------------------------
  **Metric**                 **Point estimate**              **80% CI**
  --------------------- ----------------------- -----------------------
  Δ team xGF/60                          +0.004        (-0.190, +0.197)

  Δ team xGA/60                          -0.047        (-0.249, +0.155)

  Net (xGF − xGA)                        +0.051                     ---
  ---------------------------------------------------------------------

+--------------------------------------------------------------------+
| **What this actually means in hockey terms**                       |
|                                                                    |
| Net shift: +0.051 xG per 60 of team play (80% CI straddles zero).  |
|                                                                    |
| Translated: in a typical 5v5 game (\~50 min), that\'s roughly      |
| +0.042 xG per game. Over a 7-game series, \~+0.296 xG total ---    |
| you\'d need to play roughly 24 games before the model would expect |
| a single-goal swing.                                               |
|                                                                    |
| The 5v5 data does not distinguish these lineups. The 5v4 picture   |
| favors keeping Texier on PP2. Net-net: if you\'re making this      |
| swap, you\'re doing it for reasons the model doesn\'t see          |
| (matchups, chemistry, discipline, coach\'s read on effort).        |
+--------------------------------------------------------------------+

2\. Patrik Laine --- what if he were healthy?

Laine had core-muscle surgery October 16, 2025, and was publicly ruled
out for Round 1 by Martin St-Louis. This is a counterfactual: IF he were
activated, how would his PP2 profile compare to the players MTL is
actually using?

The pooled 5v4 numbers across 2024-25 + 2025-26 show Laine with +162.8
minutes of 5v4 on-ice time --- a meaningful sample, though
injury-shortened. His on-ice 5v4 isolated rate (-0.824 iso xGF/60) is
not as strong as his reputation suggests --- partly because the
comparison team (MTL without him) already has Caufield, Suzuki,
Slafkovský on PP1, and partly because his post-injury usage in 25-26 was
tiny.

  ---------------------------------------------------------------------
  **Candidate (5v4)**       **Pooled TOI**               **iso xGF/60**
  ------------------------- -------------- ----------------------------
  Patrik Laine                     +162.8m                       -0.824

  Alexandre Texier                  +80.5m                       +0.589

  Kirby Dach                       +183.3m                       -1.676

  Alex Newhook                     +182.5m                       -1.762

  Zachary Bolduc                   +126.1m                       -0.096
  ---------------------------------------------------------------------

+--------------------------------------------------------------------+
| **The honest read on Laine**                                       |
|                                                                    |
| Career PP shooting profile: elite. Recent pooled sample: too       |
| damaged by surgery and limited 25-26 minutes to cleanly say \"drop |
| him in and it\'s better.\" On pure 5v4 iso xGF/60, Texier          |
| currently outperforms the other PP2 options, including pooled      |
| Laine.                                                             |
|                                                                    |
| If St-Louis could activate him, the bet is that his shot and       |
| right-handed release elevates PP2 beyond what these small-sample   |
| numbers capture --- coaches see that, the isolated-impact model    |
| cannot. This report will not claim the activation is worth +X      |
| wins.                                                              |
+--------------------------------------------------------------------+

3\. Who\'s moving the needle

Ranking MTL skaters by their isolated impact at 5v5, pooled across the
2025-26 regular season and the playoffs so far. Minimum 200 minutes
pooled TOI to exclude tiny samples. \"Net\" is iso xGF/60 minus iso
xGA/60 --- higher is better. Remember: these are isolated rates, meaning
player rate minus team-without-player rate, not raw shot-share numbers.

Doing well (top 8 by net)

  ----------------------------------------------------------------------------------------
  **Player**        **Pos**   **GP**   **TOI**      **iso      **iso   **Net**   **GF-GA**
                                                 xGF/60**   xGA/60**           
  --------------- --------- -------- --------- ---------- ---------- --------- -----------
  Lane Hutson             D       84   +1543.6      +0.70      -0.39     +1.09       93-58

  Cole Caufield           R       83   +1116.9      +0.68      -0.27     +0.95       67-41

  Nick Suzuki             C       84   +1235.4      +0.52      -0.22     +0.74       72-42

  Zachary Bolduc          R       80    +937.9      +0.18      -0.25     +0.43       37-37

  Alexandre               L       53    +641.0      +0.20      -0.10     +0.29       26-18
  Texier                                                                       

  Jayden Struble          D       61    +825.7      -0.07      -0.13     +0.06       36-31

  Alexandre               D       75   +1154.4      +0.03      +0.00     +0.03       55-53
  Carrier                                                                      

  Juraj                   L       84   +1170.1      +0.26      +0.23     +0.03       62-45
  Slafkovský                                                                   
  ----------------------------------------------------------------------------------------

Doing poorly (bottom 5 by net)

  ----------------------------------------------------------------------------------------
  **Player**        **Pos**   **GP**   **TOI**      **iso      **iso   **Net**   **GF-GA**
                                                 xGF/60**   xGA/60**           
  --------------- --------- -------- --------- ---------- ---------- --------- -----------
  Oliver Kapanen          C       84    +950.9      -0.24      +0.68     -0.92       51-48

  Alex Newhook            C       44    +519.3      -0.56      +0.17     -0.73       29-23

  Mike Matheson           D       80   +1474.5      -0.15      +0.45     -0.59       64-61

  Josh Anderson           R       74    +833.6      -0.36      +0.15     -0.52       31-38

  Arber Xhekaj            D       67    +735.4      -0.71      -0.20     -0.51       23-31
  ----------------------------------------------------------------------------------------

+--------------------------------------------------------------------+
| **How to interpret these numbers**                                 |
|                                                                    |
| A net of +0.5 xG per 60 is strong; +1.0 is elite. A net of −0.5 is |
| meaningfully weighing the team down. For context, the gap between  |
| Hutson (top) and Kapanen (bottom) in this sample is \~2 xG/60 ---  |
| a massive isolated-impact spread.                                  |
|                                                                    |
| Negatives need context: Newhook and Kapanen are matchup/deployment |
| bottom-six forwards; Matheson is often paired with Hutson or       |
| Xhekaj in heavy-usage spots and gets caved on defense as a result. |
| These numbers are not verdicts on \"good\" or \"bad\" players ---  |
| they\'re diagnostic.                                               |
+--------------------------------------------------------------------+

4\. A data-optimal lineup

A lineup built mechanically from 2025-26 regular-season + 2026 playoff
iso net impact, with constraints: Suzuki stays at 1C, Ds pair best +
worst across the top 6 for balance, and PP units are seeded by 5v4 iso
xGF/60. This is what the data says --- not what the coach\'s eye
necessarily sees.

Forwards

*The center slot is always column 2; the two wings fill columns 3-4
without handedness preference. Minimum 300 pooled minutes so fringe
trade-deadline pickups (e.g., Sammy Blais) are excluded.*

  ----------------------------------------------------------------------
  **Line**            **Center**            **Wing**            **Wing**
  ---------- ------------------- ------------------- -------------------
  Line 1             Nick Suzuki       Cole Caufield      Zachary Bolduc

  Line 2              Kirby Dach    Alexandre Texier    Juraj Slafkovský

  Line 3              Joe Veleno   Brendan Gallagher        Ivan Demidov

  Line 4              Jake Evans       Josh Anderson 
  ----------------------------------------------------------------------

Defense

  ----------------------------------------------------------------------
  **Pair**                          **LD**                        **RD**
  ---------- ----------------------------- -----------------------------
  Pair 1                       Lane Hutson                  Arber Xhekaj

  Pair 2                    Jayden Struble                   Noah Dobson

  Pair 3                 Alexandre Carrier                  Kaiden Guhle
  ----------------------------------------------------------------------

Power play

  ---------------------------------------------------------------------------
  **Unit**          **F1**        **F2**        **F3**        **F4**    **D**
  ---------- ------------- ------------- ------------- ------------- --------
  PP1          Nick Suzuki         Juraj Cole Caufield  Ivan Demidov     Lane
                              Slafkovský                               Hutson

  PP2              Zachary       Phillip       Brendan     Alexandre     Noah
                    Bolduc       Danault     Gallagher        Texier   Dobson
  ---------------------------------------------------------------------------

+--------------------------------------------------------------------+
| **Where the model and St-Louis will disagree**                     |
|                                                                    |
| Chemistry is invisible to the model. A line that looks             |
| statistically sub-optimal can outperform its parts if the players  |
| read each other; conversely, stacking the three highest-net        |
| forwards on Line 1 can leave Lines 2-4 thin and get your stars     |
| out-matched.                                                       |
|                                                                    |
| The PP1 composition here (Suzuki, Slafkovský, Caufield, Demidov,   |
| Hutson) aligns with the real deployment and looks correct. PP2     |
| composition depends heavily on what St-Louis wants the unit to do  |
| (grind / cycle / shoot-first) --- the model only sees \"who has    |
| generated xG on 5v4 so far this season\".                          |
|                                                                    |
| *Goalie: data on GSAx (goals saved above expected) was not         |
| ingested in our goalie layer for this report. Dobes is the assumed |
| starter based on public usage; verify before citing in chat.*      |
+--------------------------------------------------------------------+

5\. Slafkovský --- hot bucket vs. cold bucket

A targeted look at the question \"was Slafkovský part of MTL\'s Game 2
collapse?\" Bucket A covers the hot stretch (all of Game 1 plus the 1st
period of Game 2). Bucket B covers the cold stretch (3rd period of Game
2 plus OT). The 2nd period of Game 2 is excluded intentionally --- this
is not a full-game comparison, it\'s the \"when Slafkovský was flying\"
vs. \"when the team collapsed\" split.

+--------------------------------------------------------------------+
| **Data source for this section**                                   |
|                                                                    |
| NST game reports do not expose per-period player splits. We built  |
| this from the NHL.com public endpoints: shift charts (per-player,  |
| per-period shift times) joined to play-by-play (every shot /       |
| missed shot / goal with an event time and period). Events are      |
| counted as \"on-ice\" if the event time falls inside a Slafkovský  |
| shift in the same period.                                          |
+--------------------------------------------------------------------+

  --------------------------------------------------------------------
  **Metric**               **A: G1 all + G2 P1**  **B: G2 P3 + G2 OT**
  ------------------------ --------------------- ---------------------
  Slafkovský shifts                           33                    12

  Slafkovský TOI (min)                    +28.03                +12.55

  Slafkovský SOG                               5                     0

  Slafkovský goals                             3                     0

  MTL SOG on-ice                              10                     5

  MTL goals on-ice                             5                     0

  MTL missed shots on-ice                      7                     2

  TBL SOG on-ice                               5                     5

  TBL goals on-ice                             4                     1
  --------------------------------------------------------------------

+--------------------------------------------------------------------+
| **The story in one read**                                          |
|                                                                    |
| Bucket A (+28.03 min, 33 shifts): Slafkovský generated 5 shots on  |
| goal and scored 3. MTL outshot TBL 10-5 with him on the ice. This  |
| is a player driving play.                                          |
|                                                                    |
| Bucket B (+12.55 min, 12 shifts): zero shots on goal, zero goals.  |
| MTL and TBL broke even on shots with him on the ice (5-5), but TBL |
| scored 1 to MTL\'s 0.                                              |
|                                                                    |
| Verdict: Slafkovský was neutralized in the cold stretch --- not    |
| caved in defensively, but unable to generate offense. \"Held off   |
| the puck\" rather than \"bled chances\". That aligns with          |
| St-Louis\' post-Game 2 read that MTL lost possession and couldn\'t |
| forecheck.                                                         |
+--------------------------------------------------------------------+

6\. Data sources & methodology notes

Primary data

- [Natural Stat Trick --- NHL advanced stats (team, skater, 5v5 / 5v4 /
  playoff splits)](https://www.naturalstattrick.com/)

- [NHL.com public shift chart API (per-player shifts with
  period)](https://api.nhle.com/stats/rest/en/shiftcharts)

- [NHL.com public play-by-play API (events with period + timestamp +
  shooter)](https://api-web.nhle.com/v1/gamecenter/{gameId}/play-by-play)

Pooled windows used

• Swap analyses (pooled baseline): 2024-25 regular + playoff, 2025-26
regular + playoff.

• \"Who\'s moving the needle\" + optimal lineup: 2025-26 regular + 2026
playoff only (per user ask).

• Slafkovský per-period: NHL.com shift+play-by-play for games 2025030121
(G1) and 2025030122 (G2). Bucket A = G1 all periods + G2 P1. Bucket B =
G2 P3 + G2 OT. G2 P2 explicitly excluded.

Known caveats

• Playoff samples are tiny (1--2 games per team at time of writing). The
model uses regular-season impacts for the swap math to avoid overfitting
playoff noise; see each section for the specific window used.

• Traded players (Texier: STL → MTL mid-season) have NST team_id stored
as \"MTL, STL\". Isolated impact pools all their minutes against the
receiving team\'s totals --- a mild approximation for traded players,
robust for everyone else.

• Goalie GSAx was not ingested in the \"optimal lineup\" section --- the
starter is a placeholder; verify before citing.

• Beat-reporter \"narrative\" about specific games is NOT cited in this
report because agent-assisted web research produced some unverifiable
material. Where we describe events (e.g., Slafkovský\'s Game 1 hat
trick), the claim is backed by NHL.com play-by-play directly --- not a
press recap.

Reproducibility

Every number in this report is computed by analytics/habs_round1.py and
dumped to reports/output/habs_round1_2026.numbers.json alongside this
.docx file. The docx is rendered by reports/build_habs_round1_2026.js.
