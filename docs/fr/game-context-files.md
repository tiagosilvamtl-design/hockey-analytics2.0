# Fichiers de contexte par match

Chaque match qu'on analyse a son fichier `gameN_context.yaml`. C'est la
**base canonique des faits** pour ce match — la source unique de vérité
qu'un rapport futur consulte chaque fois qu'il y fait référence par
numéro, par événement ou par marque.

Sans cette convention, la mémoire en prose dérive. Le cadriciel a déjà
livré un rapport qui attribuait à tort le combat Hagel-Slafkovský au
Match 3 alors qu'il était au Match 2. Les fichiers de contexte
préviennent cette classe d'erreur *structurellement*, pas en espérant
qu'un humain attrape le coup.

## La règle

Si un document que tu rédiges fait référence à des événements d'un match
déjà analysé :

- « le combat de Hagel au Match 2 »
- « le CH a gagné le Match 1 en prolongation »
- « Crozier a frappé Slafkovský au Match 4 »

…alors **tu dois lire d'abord le `gameN_context.yaml` correspondant** et
vérifier l'affirmation contre lui. **La mémoire en prose n'est pas une
source.**

## Schéma

Voir [docs/en/game-context-files.md](../en/game-context-files.md) pour le
schéma complet (les noms de champs sont en anglais dans le YAML pour
correspondre aux conventions du code).

Sections :

1. Méta : `schema_version`, `game_id`, `date`, `season`, `series`, `series_game`
2. Marque + équipes : `home_team`, `away_team`, `final_score`, `result`,
   `regulation_or_overtime`
3. Gardiens et marqueurs
4. `goal_sequence` — séquence chronologique
5. `key_events` — combats, mises en échec marquantes, blessures, expulsions.
   Marquer les ancrages multimatchs avec `FRAMEWORK ANCHOR:` dans la
   ligne `significance`
6. `series_state_after_game` — par exemple « le CH mène 2-1 », « égal 2-2 »
7. `file_pointers` — URL et chemins relatifs
8. `related_briefs` — rapports qui ont consommé les données
9. `notes` — narratif libre que les données seules ne saisissent pas

## Champs auto vs manuels

**Auto** (rempli par `tools/build_game_context.py`) : marque finale,
gardiens, marqueurs, séquence des buts, événements bruts (pénalités /
combats / mises en échec sur Slafkovský), URL.

**Manuels** (à remplir à la main) : étiquette de série, index dans la
série, ligne `significance` de chaque événement clé,
`series_state_after_game`, `related_briefs`, `notes`. Le générateur
marque ces champs `TODO_MANUAL` pour qu'on les remplisse.

## Générer un fichier de départ

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python tools/build_game_context.py \
    2025030121 2025030122 2025030123 2025030124 \
    --series "Round 1, MTL vs TBL" \
    --series-start-game 1 \
    --output-dir examples/habs_round1_2026/
```

## Vérification mécanique (à utiliser dans les rendus)

`examples/habs_round1_2026/game_context_check.js` expose :

```javascript
const ctxCheck = require('./game_context_check');

ctxCheck.assertGameClaim({
  game: 2, kind: 'fight', period: 2, time: '05:14',
  contextDir: __dirname,
});
```

Chaque assertion **interrompt la construction avec le code de sortie 8**
si l'affirmation contredit le fichier de contexte ou si le fichier
n'existe pas. Ajouter ces appels en haut de tout rendu qui fait
référence à des matchs précédents — la construction elle-même devient
le vérificateur.

## Voir aussi

- `CLAUDE.md` §4 — schéma comme partie de l'invariant de flux de données
- `CLAUDE.md` §9 — « ne pas référencer un match déjà analysé de mémoire »
- `tools/build_game_context.py` — le générateur
- `examples/habs_round1_2026/game{1,2,3,4}_context.yaml` — exemples
