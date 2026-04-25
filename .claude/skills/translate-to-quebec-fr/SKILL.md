---
name: translate-to-quebec-fr
description: Translate hockey-analytics English text into idiomatic Québec hockey-press French — the register La Presse / RDS / Radio-Canada chroniqueurs use, not literal word-for-word. Use this for ALL French versions of Lemieux output (analysis posts, READMEs, skills, glossary entries). Call it BEFORE finalizing FR copy, never to "tweak" English-translated text after the fact.
triggers:
  - "translate to french"
  - "translate to quebec french"
  - "fr version"
  - "passe ça en français"
  - "version française"
---

# translate-to-quebec-fr

You are translating hockey-analytics writing into Québec hockey-press French. The target register is **La Presse columnist / RDS chroniqueur** — analytical, grounded, idiomatic — not formal European French, not casual social-media French, and absolutely not literal word-for-word translation.

## The standard you're hitting

Imagine a François Gagnon RDS column or a Mathias Brunet La Presse piece. That's the register: data-aware, opinionated when warranted, sentence rhythm that reads aloud well. If a sentence sounds like a textbook (or worse, like a Google Translate output), rewrite it.

## Hard rules

1. **Never translate literally.** If the English sentence has a structure that sounds clunky in French, rewrite the sentence. Preserve meaning, not word order.
2. **Use Québec hockey vocabulary.** See the term map below.
3. **Vary references to teams.** "Le Canadien" / "Le CH" / "Le Tricolore" / "La Sainte-Flanelle" — but not all in one paragraph. Default to "Le Canadien" or "Le Tricolore"; use the others sparingly for color.
4. **No false-friend Anglicisms.** "Performance" is fine; "delivrer" (for "deliver") is not — say "produire" or "livrer". "Réaliser" doesn't mean "to achieve" in French — use "accomplir" or restructure.
5. **Sentence rhythm.** Mix short and long. Québec sports prose is rarely a wall of long sentences.
6. **Keep diacritics.** é, è, ç, à, ô, etc. — never strip.
7. **Numbers and stats**: French uses comma decimal separators (`56,1 %`) and thin space before `%` and units. `5 c. 5` for "5-on-5" (not "5v5" except in technical contexts). `xGF/60` and `iso_xgf60` are technical and stay as-is.
8. **Avoid filler clichés.** Skip "compete level" → don't translate it as "niveau de compétition"; just say what you actually mean (effort, intensité, ardeur, hargne, etc.).

## Term map (most-used)

| English | Québec hockey French (preferred) | Notes |
|---|---|---|
| game | match | "partie" is also OK but "match" is the press standard |
| period | période | |
| overtime / OT | prolongation | |
| shootout | tirs de barrage | |
| shot on goal (SOG) | tir au but / lancer | "lancer" for a single attempt; "tirs au but" for the count |
| shot attempt | tentative de tir | |
| missed shot | tir raté | |
| blocked shot | tir bloqué | |
| slap shot | lancer frappé | |
| wrist shot | tir du poignet | |
| backhand | revers | |
| one-timer | retour de palette / une-passe | |
| scoring chance | chance de marquer | |
| high-danger chance | chance à haut danger | |
| breakaway | échappée | |
| odd-man rush | surnombre | |
| zone entry | entrée de zone | |
| dump-in | dégagement (controlled vs forced) | |
| forecheck | échec avant | |
| backcheck | repli défensif | |
| power play | avantage numérique / attaque massive | "attaque massive" is press-y; "avantage numérique" is neutral |
| penalty kill | désavantage numérique | |
| 5-on-5 | 5 c. 5 (or à forces égales) | |
| 5-on-4 / PP | 5 c. 4 | |
| 4-on-5 / PK | 4 c. 5 | |
| line / forward line | trio | |
| defensive pair | duo défensif | |
| linemate | compagnon de trio / coéquipier de trio | |
| ice time / TOI | temps de glace / TG | "minutes utilisées" also fine |
| even-strength | à forces égales | |
| net front | devant le filet | |
| short-handed | en désavantage / en infériorité | |
| save percentage / SV% | pourcentage d'arrêts / % d'arrêts | |
| goals against / GA | buts accordés | |
| goals for / GF | buts inscrits / buts marqués | |
| shutout | blanchissage / jeu blanc | |
| expected goals (xG) | buts attendus | "buts prévus" also acceptable |
| Corsi (CF/CA/CF%) | Corsi (left in English; technical term) | The metric name stays English |
| Fenwick | Fenwick | same |
| isolated impact | impact isolé | |
| confidence interval | intervalle de confiance | |
| pooled baseline | base regroupée / référence sur plusieurs saisons | |
| sample size | taille d'échantillon | |
| outshoot | surclasser aux tirs / dominer aux tirs | |
| outscore | dominer au pointage | |
| outchance | dominer aux chances | |
| overperform | surpasser ses attentes / surperformer | "surperformer" is now standard sports-press |
| regress (statistical) | régresser vers la moyenne | the technical sense |
| drive play | piloter le jeu / dicter le rythme | |
| drive possession | mener la possession | |
| tilting the ice | renverser la glace / dominer territorialement | |
| momentum | élan / momentum | "momentum" is acceptable in QC sports French |
| heavy minutes | minutes corsées | |
| sheltered minutes | minutes protégées | |
| matchup | confrontation / vis-à-vis | |
| coach | entraîneur (formal) / coach (broadcast/casual) | "entraîneur" preferred in print |
| head coach | entraîneur-chef | |
| general manager | directeur général | |
| stretch run | dernier droit | |
| sweep | balayage | |
| Game 1 / Match 1 | Match no 1 / Match 1 / Premier match | "no 1" with thin space is press style |
| series | série | |
| roster | formation / alignement | |
| lineup | formation (the 18-skater group) / trios (the line combinations) | |
| call-up | rappel | |
| healthy scratch | retrait santé / réserviste en santé | |
| trade | échange | |
| traded player | joueur échangé | |
| draft pick | choix au repêchage | |
| rookie | recrue | |
| veteran | vétéran | |
| rebuild | reconstruction | |
| contender | aspirant (au championnat) | |

## Sentence-level patterns

### Replace literal calques

| Don't write | Write instead |
|---|---|
| « basé sur les données » | « selon les chiffres » / « les données indiquent » |
| « il a fait un bon travail » (literal "good job") | « il a livré une solide performance » / « il a été à la hauteur » |
| « les chiffres ne mentent pas » | (avoid — cliché in both languages; just present the numbers) |
| « cela soulève des questions » | « cela laisse songeur » / « les questions s'imposent » |
| « il joue avec confiance » | « il joue avec aplomb » / « il a retrouvé son aplomb » |
| « performance impressionnante » | « performance soutenue » / « performance dominante » / specify *what* impressed |
| « game-winning goal » → « but gagnant le match » | « le but vainqueur » / « le but de la victoire » |
| « OT winner » → « gagnant de la prolongation » | « le but de la prolongation » / « le but de la victoire en supplémentaire » |
| « in the third period » → « dans la troisième période » | « en troisième » / « lors du troisième vingt » (broadcast) |
| « MTL outshot TBL 20-9 » → « MTL surclassait TBL 20-9 aux tirs » | (this one is fine — "surclasser" is the right verb) |

### Verb economy

Québec sports prose tends to drop weak verbs. Instead of "il a marqué un but", it's often just "il a marqué" or "il a inscrit son deuxième." Trust context.

### Voice

Active over passive. "Hutson a lancé une fusée" beats "une fusée a été lancée par Hutson."

### Number formatting

- Decimals: `56,1 %` (comma decimal, thin space before %)
- Times: `26:28` for ice time stays as-is
- Scores: `3-2` stays as-is
- Don't translate "5v5" if it's used in a technical/data context with table headers; in prose, prefer "à 5 c. 5" or "à forces égales"

## Workflow

1. **Read the English source.** Don't start typing FR yet.
2. **Identify the meaning per paragraph**, not per sentence. What is this paragraph *doing*?
3. **Rewrite in French**, paragraph-level, in the register described above.
4. **Re-read aloud** (mentally). If a sentence stumbles, restructure.
5. **Term-map check**: any term in the table above used wrong? Fix.
6. **Anglicism scan**: any false friends? Fix.

## Worked example

### English
> Slafkovský's individual offense **fell off a cliff after the Hagel fight at G2 P2 5:14** — 8 shots / 3 goals before, 2 shots / 0 goals after — but **his line is still winning the on-ice battle (20-9 SOG, 2-1 goals after the fight)**. "Less impactful" is the wrong frame; "playing differently" is right.

### Literal (BAD) French
> L'offensive individuelle de Slafkovský **est tombée d'une falaise après le combat avec Hagel au M2 P2 5:14** — 8 tirs / 3 buts avant, 2 tirs / 0 buts après — mais **son trio gagne encore la bataille sur la glace (20-9 tirs, 2-1 buts après le combat)**. « Moins impactant » est le mauvais cadre; « joue différemment » est bon.

### Idiomatic Québec French (GOOD)
> La production individuelle de Slafkovský **s'est tarie après son combat avec Hagel** (M2, deuxième période, 5:14) : 8 tirs et 3 buts avant, 2 tirs et 0 but après. Mais **son trio continue de dominer le territoire avec lui sur la glace** : MTL surclasse TBL 20-9 aux tirs et 2-1 au pointage depuis le combat. Le narratif du « joueur diminué » rate la cible. Le bon cadrage : Slafkovský a changé de rôle, pas d'efficacité.

Notice what changed:
- "fell off a cliff" → "s'est tarie" (idiom-for-idiom, not word-for-word)
- "his line is still winning the on-ice battle" → "son trio continue de dominer le territoire" (ditched "battle" calque, used "dominer le territoire" which is RDS broadcaster register)
- "playing differently is right" → "Slafkovský a changé de rôle, pas d'efficacité" (rewrote for clarity in FR; the parallel is sharper)
- Sentence rhythm broken into three short statements at the end. Québec prose pattern.

## When this skill is invoked from inside another skill

If `draft-game-post` is producing the FR version of a post, it should call this skill *paragraph-by-paragraph*, not "translate the whole thing then come back." That keeps the register consistent and prevents falling back into literal mode.

## Self-check before delivery

- [ ] No literal calque sentence structures remain
- [ ] Every term from the term map used in its preferred form
- [ ] Decimals use comma, thin space before %
- [ ] Diacritics intact
- [ ] Sentence rhythm varies (short + long)
- [ ] Active voice preferred
- [ ] If the text was supposed to be analytical, the register matches La Presse columnist or RDS chronique — not formal European French and not casual social media
