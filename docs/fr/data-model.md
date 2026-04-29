# Modèle de données Lemieux

Voici le guide canonique de ce que Lemieux sait des joueurs de la LNH, et de
comment ce savoir est structuré. À lire une fois avant d'écrire un analyseur,
une habileté ou un nouveau connecteur.

Le flux de données comporte **cinq couches**, chacune apportant un signal que
la précédente ne peut produire seule :

```
[1] Statistiques de comptage  ←  splits NST sur la glace + individuels
       ↓                          skater_stats, skater_individual_stats, goalie_stats
[2] Bio + biométrie           ←  vitesses de patinage / tir NHL Edge,
       ↓                          taille / poids / repêchage
                                  edge_player_bio, edge_player_features
[3] Comparables intégrés      ←  ACP + kNN style Mahalanobis sur
       ↓                          caractéristiques standardisées
                                  comparable_index.json, goalie_comparable_index.json
[4] Profil scouting           ←  extraction LLM sur texte scouting public
       ↓                          scouting_profiles, scouting_attributes,
                                  scouting_tags
[5] Contexte par match        ←  faits dérivés du jeu par jeu + notes
                                  manuelles de signification
                                  examples/<scope>/gameN_context.yaml
```

**L'invariant prose-contre-données** (`runProseFactCheck()`, voir CLAUDE.md
§5) s'applique à toutes les couches : toute phrase d'une sortie doit pouvoir
être tracée à une requête contre l'un de ces magasins. La mémoire-prose ne
constitue pas une source.

---

## Couche 1 — Statistiques de comptage (NST)

### `skater_stats` — splits sur la glace
Regroupé par `(player_id, season, stype, sit, split)`. `split='oi'` contient
les xGF / xGA / CF / CA / HDCF, etc. sur la glace. Alimenté par
`legacy/data/ingest.py` pour les patineurs.

- Couverture : 5 saisons (`20212022` → `20252026`), `stype` ∈ {2 (régulière),
  3 (séries)}, `sit` ∈ {`5v5`, `5v4`, `all`}
- Univers : ~1 300 patineurs distincts par saison avec ≥ 1 minute à 5 c. 5
- Source : NST `playerteams.php?stdoi=oi`

### `skater_individual_stats` — stats de comptage par joueur
Par `(player_id, season, stype, sit)`. Buts, passes (1ère/2e/total), tirs,
ixG, iCF, iSCF, iHDCF, tentatives en surnombre, retours créés, MP, pénalités
provoquées, revirements, vols, mises en échec, mises en échec subies, tirs
bloqués, mises au jeu.

- **Remplace l'ancien chemin `split='bio'`** — qui tirait `stdoi=bio`
  (informations biographiques : taille / poids / repêchage) et les mappait à
  travers le schéma sur la glace, laissant chaque colonne de stat
  individuelle à NULL. Voir le commit `dbf467a` pour le correctif.
- Couverture : mêmes 5 saisons × 3 sits que `skater_stats`. ~18 500 lignes
  au total.
- Source : NST `playerteams.php?stdoi=std`
- Rafraîchissement : `tools/refresh_skater_individual_stats.py`

### `goalie_stats` — splits des gardiens
Par `(player_id, season, stype, sit)`. Inclut les colonnes brutes de
comptage (ga, sa, xga, hdga, hdca) et les % d'arrêts, % d'arrêts à haut
danger et gsax calculés.

- Couverture : 5 saisons, `sit` ∈ {`5v5`, `all`}, ~135 gardiens distincts
- Source : NST `playerteams.php?pos=G`
- Rafraîchissement : `tools/refresh_goalie_stats.py`

### `team_stats` / `team_stats_raw`
xG / CF / HDCF d'équipe regroupés — le dénominateur du calcul d'« impact
isolé » (voir `lemieux.core.swap_engine`).

---

## Couche 2 — Bio + biométrie (NHL Edge)

### `edge_player_bio` — bio statique
Par `player_id`. Taille (po), poids (lb), date et pays de naissance, année /
ronde / rang général de repêchage, position, tire / attrape.

- Couverture : **1 322 joueurs LNH** (patineurs + gardiens), 100 % pour la
  taille et le poids, ~1 113 avec rang de repêchage consigné
- Source : endpoint « player landing » de LNH.com
- Résolution : `tools/refresh_edge_biometrics.py` avec **appariement de
  noms en espace ASCII-folded** (gère Dobeš, Slafkovský, etc. — voir
  `_ascii_fold()` dans `packages/lemieux-connectors/.../nhl_edge/client.py`)

### `edge_player_features` — pistage biométrique
Par `(player_id, season, game_type)`. Vitesse maximale de patinage,
décomptes d'accélérations (20-22 mi/h, 22+ mi/h), vitesse maximale de tir,
décomptes de tirs forts (80-90 mi/h, 90+ mi/h).

- Couverture : **1 122 patineurs distincts avec mesures biométriques
  remplies**
- NHL Edge est **réservé aux patineurs** ; les gardiens ont des lignes
  fantômes mais aucun champ mesuré n'est rempli.

---

## Couche 3 — Index de comparables intégrés

### `legacy/data/comparable_index.json` — kNN patineurs
Construit par `tools/build_comparable_index.py`. ACP sur caractéristiques
standardisées, distance euclidienne (équivalente à Mahalanobis) dans
l'espace intégré.

- 1 257 patineurs indexés
- 24 caractéristiques : iso NST 5 c. 5 + 5 c. 4 (xGF/60, xGA/60, net), taux
  de comptage, position (encodage one-hot), biométrie, bio
- La sortie comprend l'ACP ajustée et l'embedding pour les requêtes kNN
- Utilisé par `lemieux.core.comparable.ComparableIndex.find_comparables()`

### `legacy/data/goalie_comparable_index.json` — kNN gardiens (v1)
Construit par `tools/build_goalie_comparable_index.py`. Même code
d'embedding (le module est agnostique aux caractéristiques), 10
caractéristiques propres aux gardiens :

- Performance : sv_pct, hd_sv_pct, gsax_per60, workload_share, hd_share, gp_growth
- Bio : taille, poids, âge, rang de repêchage

- 136 gardiens indexés (≥ 200 minutes regroupées en saison régulière)
- **Mise en garde v1** : ne capture pas les différences stylistiques
  (positionnel vs « scrambly », côté mitaine vs côté bouclier) — celles-ci
  exigent un taux de retour, une vitesse de relevé et un temps de
  récupération dérivés du jeu par jeu. Capture la bio + la forme de la
  performance, rien de plus.

---

## Couche 4 — Scouting (extraction GenAI)

Quatre tables, toutes indexées sur le `name` du joueur. Construites par
Claude Sonnet 4.5 qui extrait du JSON structuré à partir d'extraits de
recherche DDG sur des textes scouting publics.

### `scouting_profiles`
Par joueur : `extracted_at`, liste des URL sources consultées.

- **1 393 profils au total** (1 257 patineurs + 136 gardiens)
- **1 023 patineurs et 135 gardiens ont du contenu significatif** (au moins
  un attribut ou une étiquette) ; le reste a été cherché mais a produit des
  résultats minces.

### `scouting_attributes`
Attributs continus sur une échelle de 1 à 5 avec confiance. **1 719 lignes.**
- Vocabulaire patineur : skating, hands, hockey_iq, compete, size, speed,
  shot, vision, defense
- Vocabulaire gardien : positioning, athleticism, glove, blocker,
  rebound_control, puck_handling, mental, size

### `scouting_tags` — étiquettes d'archétype à vocabulaire contrôlé
**2 501 lignes.** Chaque étiquette transporte sa `confidence`, son
`source_quote` (citation textuelle du texte source) et son `source_url`.

Étiquettes patineurs : `warrior`, `playmaker`, `sniper`, `two_way`,
`shutdown`, `agitator`, `enforcer`, `power_forward`, `puck_mover`,
`stay_at_home`, `offensive_d`, `fast`, `slow_start`, `streaky`,
`consistent`, `top_six`, `bottom_six`, `bottom_pair`, `rover`,
`specialist_pp`, `specialist_pk`, `clutch`, `volume_shooter`.

Étiquettes gardiens : `positional`, `athletic`, `hybrid`, `butterfly`,
`scrambly`, `calm`, `fiery`, `prospect`, `veteran`, `big_frame`,
`undersized_quick`, `starter`, `backup`, `tandem`, `puck_mover_g`,
`big_game`, `streaky`, `consistent`.

**La règle de provenance :** une étiquette sans son `source_quote` et son
`source_url` est interne au cadriciel et ne peut pas figurer dans la prose
destinée au lecteur. Si un docx cite l'étiquette, il doit citer le texte
source aux côtés.

### `scouting_comparable_mentions`
Mentions explicites « X me rappelle Y » / « le prochain Y », avec
citation + URL. **125 lignes.** Servent de supervision faible pour
l'embedding contrastif v3 (pas encore livré) et pour les légendes
narratives de comparables.

### Outils de rafraîchissement
- `tools/build_scouting_corpus.py` — corpus complet patineurs, requête DDG
  unique par joueur, idempotent (saute les profils déjà constitués)
- `tools/build_goalie_scouting_corpus.py` — même structure, vocabulaire
  gardien
- `tools/refresh_scouting_empties.py` — deuxième passe avec **recherche
  enrichie à 3 requêtes** sur les profils revenus vides au premier coup
  (récupère ~38 % des vides)

---

## Couche 5 — Contexte par match

`examples/<scope>/<gameN>_context.yaml` — base canonique des faits pour
chaque match analysé. **Lecture obligatoire avant toute affirmation
inter-matchs en prose.**

Schéma documenté dans CLAUDE.md §4. Généré par `tools/build_game_context.py`
(champs dérivables des données) plus une rédaction manuelle des champs
`significance` et `notes` pour les évènements marquants.

---

## Comment interroger : l'outil snapshot

`tools/player_snapshot.py <nom>` (également exposé comme l'habileté Claude
`player-snapshot`) rend les cinq couches pour un joueur dans un format
fixe :

```
$ python tools/player_snapshot.py "Cole Caufield"

[1] BIO STATIQUE            — taille / poids / naissance / repêchage
[2] NST SUR LA GLACE        — arc de carrière par (saison, stype, sit)
[3] BIOMÉTRIE EDGE          — vitesses patin + tir, décomptes d'accélérations
[4] NST INDIVIDUEL          — B/A/Tirs/ixG/iCF/iHDCF/etc.
[5] SCOUTING                — attributs + étiquettes + mentions de comparables
[6] COMPARABLES kNN         — top 5-7 comparables LNH avec contributeurs par
                              caractéristique
[7] ANCRAGES PAR MATCH      — apparitions dans les contextes de match indexés
[8] STATS SÉRIE EN COURS    — stats directes du jeu par jeu de l'analyseur JSON
```

Détecte automatiquement patineur ou gardien. Appariement partiel sur le nom
en espace ASCII-folded.

---

## Instantané de couverture (au 2026-04-29)

| Couche | Couverture |
|---|---|
| Sur la glace patineurs (NST) | 5 saisons × 3 sits × 2 stypes |
| Individuel patineurs (NST) | 5 saisons × 3 sits × 2 stypes, 18 500 lignes |
| Stats gardiens (NST) | 5 saisons × 2 sits × 2 stypes, ~135 gardiens |
| Bio joueurs | **1 322** (taille / poids 100 %) |
| Biométrie patineurs | **1 122** patineurs distincts avec mesures |
| Scouting patineurs | **1 023** avec contenu significatif (sur 1 257 profils) |
| Scouting gardiens | **135** avec contenu significatif (sur 136 profils) |
| Index kNN patineurs | **1 257** lignes, 24 caractéristiques |
| Index kNN gardiens | **136** lignes, 10 caractéristiques |

---

## Ce qui peut être redistribué

**On ne peut pas pousser** la base SQLite elle-même : `skater_stats`,
`skater_individual_stats`, `goalie_stats`, `team_stats` contiennent des
tables brutes de Natural Stat Trick. Selon [SOURCES.md](../../SOURCES.md) :
*« Do NOT redistribute raw tables. »*

**On peut pousser** (ce sont des artefacts dérivés que Lemieux possède) :

- `legacy/data/comparable_index.json` — embeddings blanchis par ACP (pas
  des stats NST brutes, mais les paramètres ajustés de notre modèle)
- `legacy/data/goalie_comparable_index.json` — même structure
- Tables scouting extraites par LLM (`scouting_*`) — il s'agit
  d'extractions sur du *texte web public* via nos propres invites et notre
  propre code
- `edge_player_bio` et `edge_player_features` — LNH.com permet la mise en
  cache « personnelle / analytique » ; la redistribution est en zone grise
  (citer la source)

Utilisez `tools/export_derived_artifacts.py` pour produire un zip de la
sous-section publiable accompagné d'un README pointeur pour les
utilisateurs en aval.
