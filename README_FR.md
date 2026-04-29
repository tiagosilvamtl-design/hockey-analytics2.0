# Lemieux — cadriciel d'analyse avancée de hockey par IA

[![tests](https://github.com/lemieuxAI/framework/actions/workflows/tests.yml/badge.svg)](https://github.com/lemieuxAI/framework/actions/workflows/tests.yml)
[![license](https://img.shields.io/badge/licence-MIT-blue)](./LICENSE)
[![python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](./pyproject.toml)
[![mcp](https://img.shields.io/badge/MCP-serveur-8A2BE2)](./packages/lemieux-mcp)
[![docs](https://img.shields.io/badge/docs-EN%20%7C%20FR-green)](./docs)

[🇬🇧 English](./README.md) · 🇫🇷 **Français**

> *Rédigez l'analyse sportive que vous auriez aimé lire.*

**Lemieux** est un cadriciel à code source ouvert qui combine Claude (ou tout autre client IA compatible MCP) avec des connecteurs de données de hockey soigneusement sélectionnés, des primitives analytiques et des habiletés agentiques, afin de produire une couverture analytiquement rigoureuse et consciente de ses limites — le genre que la plupart des médias sportifs ne produisent pas.

Le flux de travail principal n'est pas une application autonome — c'est un dépôt que vous clonez et une session Claude que vous ouvrez dedans :

```
cloner le dépôt  →  ouvrir Claude Code  →  poser une question sur le match d'hier
                 →  Claude utilise les outils MCP + habiletés + connecteurs
                 →  ébauche avec tableaux, IC à 80 %, sources, liens vers le lexique
```

## Pourquoi ce projet existe

En 2026, la couverture médiatique du hockey demeure majoritairement innumérique : conclusions profondes tirées d'un seul match, narratifs recyclés depuis les années 90, aucun véritable engagement avec vingt ans de statistiques avancées pourtant publiques. Lemieux est d'abord un outil qui **gratte notre propre démangeaison**, et ensuite un cadriciel communautaire. C'est ce que l'un d'entre nous aurait aimé avoir hier; nous l'ouvrons parce que d'autres veulent probablement la même chose.

## Ce que Lemieux vous permet de faire

Voici des cas d'usage concrets que vous pouvez piloter à partir d'une session Claude Code dans ce dépôt. Chaque capacité repose sur les données — pas de mémoire-prose, aucune citation fabriquée, aucune prédiction de série.

### Demander un portrait de joueur

> *« Dis-moi tout ce qu'on sait sur Cole Caufield. »*

Déclenche `player-snapshot`. Renvoie d'un seul coup le modèle de données complet en 5 couches : bio, arc de carrière sur la glace, biométrie NHL Edge, production individuelle NST, profil scouting (avec citations textuelles des sources), top 7 des comparables kNN avec contributeurs par caractéristique, ancrages dans les contextes de match indexés, stats série en cours dérivées du jeu par jeu. Détecte automatiquement patineur ou gardien.

### Rédiger un compte-rendu post-match

> *« Rédige un post-match du Canadien de ce soir. Inclus une analyse de substitution pour le troisième trio. »*

Déclenche le pipeline `research-game` → analyseur → générateur. Produit un docx FR + EN aux couleurs du cadriciel : registre des prétentions, analyse de la dérive des trios par rapport au match précédent, projections d'échanges avec IC à 80 %, liens vers le lexique, et garde-fou de cohérence prose-données à la construction (impossible de prétendre qu'un joueur sans but a marqué — code de sortie 7 si la règle est violée). Téléversement Drive en une commande.

### Évaluer un changement de formation

> *« Si Slafkovský ne peut pas jouer le Match 5, qui est le meilleur remplaçant et combien ça coûte en buts attendus par match? »*

Utilise le moteur d'échange et le moteur de comparables. Chaque candidat reçoit une projection sur base regroupée avec IC à 80 %; les permutations multi-segments propagent l'incertitude; si une étude par étiquette d'archétype soutient la lecture, une couche ajustée par archétype vient s'y ajouter. Le dossier de contingence M5 dans `examples/habs_round1_2026/` est un exemple complet.

### Trouver des joueurs comparables

> *« Trouve-moi les patineurs LNH les plus similaires à Brendan Gallagher. »*

L'index kNN patineurs renvoie les meilleurs comparables avec **les contributeurs par caractéristique** (quelles caractéristiques ont gagné l'appariement). 1 257 patineurs indexés sur 24 caractéristiques (iso NST 5 c. 5 / 5 c. 4, biométrie, bio statique). Les gardiens ont leur propre index v1 sur 10 caractéristiques (performance + bio).

### Lancer une étude par étiquette d'archétype

> *« Les joueurs étiquetés `warrior` surperforment-ils leur iso de saison régulière en séries? »*

La couche scouting expose 23 étiquettes d'archétype avec citations textuelles et URL. Le module cohort-effects roule des études de relèvement saison régulière → séries pour n'importe quelle étiquette, avec IC obtenus par bootstrap. Exemple complet livré aujourd'hui (les comparables de Gallagher) : les comparables étiquetés warrior relèvent leur iso de **+0,49 but attendu / 60** de plus que les non-warriors, IC à 80 % qui exclut zéro sur n=4 — résultat suggestif, pas porteur. Le cadrage prudent est intégré.

### Valider la rigueur d'une ébauche avant publication

> *« Valide cette analyse avant publication. »*

Déclenche `validate-analysis`. Repère les surinterprétations, les IC manquants, les prédictions déguisées en analyse, les erreurs de position, les redites du narratif d'avant-match, les prétentions de pointage fabriquées. Exécution automatique sur chaque PR via le workflow GitHub Actions `claude-pr-review.yml`.

### Traduire en français de presse hockey québécois

> *« Traduis cette ébauche post-match en français. »*

Déclenche `translate-to-quebec-fr`. Glossaire de termes (50+ entrées), patrons de phrases du registre des chroniqueurs La Presse / RDS. Aucun calque littéral. Décimales avec virgule, espace fine avant %, `5 c. 5` dans la prose, `5v5` réservé aux contextes techniques.

## Architecture en un coup d'œil

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code / Claude Desktop / tout client MCP                 │
│        ▲                                   ▲                    │
│        │ habiletés (flux)                  │ outils MCP          │
│        │                                   │ + ressources        │
└────────┼───────────────────────────────────┼────────────────────┘
         │                                   │
    .claude/skills/                   packages/lemieux-mcp
    ├── draft-game-post                      │
    ├── propose-swap-scenario                ▼
    └── validate-analysis           ┌──────────────────┐
                                    │  lemieux-core    │  moteur d'échange,
                                    │                  │  IC, bases pondérées
                                    └─────────┬────────┘
                                              │
                                    ┌─────────▼────────┐
                                    │ lemieux-glossary │  défs bilingues
                                    │                  │  (EN + FR)
                                    └──────────────────┘
                                              │
                                    ┌─────────▼────────────┐
                                    │  lemieux-connectors  │  sources de données
                                    │                      │  (API LNH, NST, ...)
                                    └──────────────────────┘
```

## Ce qu'on y trouve

| Paquet / dossier | Rôle |
|---|---|
| [`lemieux-core`](./packages/lemieux-core) | Primitives analytiques : **moteur d'échange** (bases regroupées + IC à 80 %), **moteur de comparables** (kNN sur caractéristiques standardisées et blanchies par ACP), **scouting** + **étiquettes** + **cohort_effects** (études par étiquette d'archétype) |
| [`lemieux-connectors`](./packages/lemieux-connectors) | Connecteurs enfichables : API publique LNH.com, Natural Stat Trick, NHL Edge (biométrie) |
| [`lemieux-mcp`](./packages/lemieux-mcp) | Serveur FastMCP qui expose les outils et ressources analytiques à tout client MCP |
| [`lemieux-glossary`](./packages/lemieux-glossary) | Définitions bilingues (FR/EN) de toutes les métriques utilisées, avec formules et mises en garde |
| [`.claude/skills/`](./.claude/skills) | Flux de travail Claude — `research-game`, `translate-to-quebec-fr`, `draft-game-post`, `propose-swap-scenario`, `validate-analysis`, `review-pr-lemieux`, `player-snapshot` |
| [`tools/`](./tools) | Scripts autonomes : constructeur de corpus scouting, constructeur d'index kNN, rafraîchissement biométrique, instantané de joueur, téléversement Drive, exporteur d'artefacts dérivés |
| [`examples/habs_round1_2026/`](./examples/habs_round1_2026) | Plusieurs analyses bout-à-bout : survol d'avant-match, post-match (M3, M4), classement des séries, **dossier de contingence M5**, analyse par période avec compartimentage du combat de Slafkovský |
| [`docs/en/data-model.md`](./docs/en/data-model.md) | Guide canonique du modèle de données en 5 couches (comptage → bio → kNN → scouting → contexte par match) |
| [`CLAUDE.md`](./CLAUDE.md) | Guide d'utilisation canonique pour travailler dans ce dépôt avec Claude Code — règles d'écriture, flux de données, invariants structurels |

## Couverture des données (au 2026-04-29)

La base de données de Lemieux dispose des couches suivantes pour chaque joueur de la LNH :

| Couche | Couverture |
|---|---|
| **Statistiques de comptage NST** (patineurs + gardiens) | 5 saisons × {5 c. 5, 5 c. 4, toutes situations} × {saison régulière, séries}, ~18 500 lignes de stats individuelles |
| **Bio du joueur** (taille / poids / repêchage) | **1 322** joueurs, 100 % pour la taille et le poids |
| **Données biométriques NHL Edge** (patinage, tir, accélérations) | **1 122** patineurs distincts avec mesures |
| **Étiquettes et attributs scouting (GenAI)** | **1 023 patineurs + 135 gardiens** avec contenu extrait (1 393 profils au total) |
| **Index de comparables kNN** | **1 257 patineurs** (espace de 24 caractéristiques) + **136 gardiens** (v1, 10 caractéristiques) |
| **Yamls de contexte par match** | Série Canadien — Lightning, premier tour 2026 (M1 à M4 indexés) |

Lancez `python tools/player_snapshot.py "<nom>"` (ou utilisez l'habileté Claude `player-snapshot`) pour obtenir d'un seul coup les cinq couches pour n'importe quel joueur.

## Démarrage rapide

```bash
git clone https://github.com/lemieuxAI/framework.git lemieux
cd lemieux

python -m venv .venv
source .venv/bin/activate     # Windows Git Bash : . .venv/Scripts/activate

pip install -e packages/lemieux-core
pip install -e packages/lemieux-glossary
pip install -e packages/lemieux-connectors
pip install -e packages/lemieux-mcp

cp .env.example .env          # ajoutez votre clé d'accès NST (voir SOURCES.md)
```

### Utiliser depuis Claude Code

Ouvrez le dépôt dans Claude Code. Le dossier `.claude/skills/` est découvert automatiquement. Demandez :

> *« Rédige un billet de 1000 mots sur le match du Canadien d'hier. Concentre-toi sur la structure défensive à 5 contre 5. Inclus une analyse de substitution. »*

Claude invoque `draft-game-post`, appelle les outils MCP, consulte le lexique pour les définitions des métriques, exécute `validate-analysis` pour vérifier la rigueur et produit une ébauche en Markdown.

### Utiliser depuis Claude Desktop

Ajouter à votre `mcp.json` :

```json
{
  "mcpServers": {
    "lemieux": {
      "command": "lemieux-mcp",
      "args": ["--store", "/chemin/vers/.lemieux/store.sqlite"],
      "env": { "NST_ACCESS_KEY": "votre-clé-ici" }
    }
  }
}
```

## Sources de données

Voir [SOURCES.md](./SOURCES.md) pour la liste complète avec les termes d'utilisation. Connecteurs livrés en v0.1 :

- **API publique de LNH.com** — jeu par jeu, présences, formations, classements, biométrie NHL Edge (pas de clé requise)
- **Natural Stat Trick** — statistiques avancées sur la glace, individuelles et de gardiens (clé d'accès personnelle requise, gratuite)
- **Extraction DDG + Sonnet 4.5** — texte scouting public → étiquettes et attributs structurés avec citation textuelle de la source
- **MoneyPuck, PWHL, EliteProspects** — prévus pour v0.2 (voir [ROADMAP.md](./ROADMAP.md))

### Peut-on redistribuer la base de données elle-même?

**Non.** Le fichier `legacy/data/store.sqlite` renferme des tableaux bruts de Natural Stat Trick, et la position de SOURCES.md ne souffre aucune ambiguïté : *« Do NOT redistribute raw tables. »* Chaque utilisateur fournit sa propre clé d'accès NST (gratuite, à demander via un profil NST), et les scripts de rafraîchissement dans `tools/` reconstruisent la DB localement.

**En revanche, les artefacts dérivés peuvent l'être :**

- Index de comparables (`comparable_index.json`, `goalie_comparable_index.json`) — ce sont des plongements blanchis par ACP et les paramètres ajustés de notre modèle, pas des statistiques brutes.
- Tables scouting (`scouting_*`) — extraites par LLM à partir de textes publics du web avec nos propres invites; le travail d'extraction nous appartient.

Lancez `python tools/export_derived_artifacts.py` pour produire un zip redistribuable accompagné d'un fichier README pointeur.

## Principes de conception

1. **Honnêteté intellectuelle plutôt que confiance excessive.** Chaque sortie affiche la taille des échantillons et les intervalles de confiance.
2. **Directionnel, pas prédictif.** Aucune prédiction de série, aucune note globale pour les joueurs.
3. **Lié au lexique.** Chaque métrique dans une sortie est liée à sa définition.
4. **Bilingue dès le premier jour.** Documentation, lexique, habiletés — tout est livré en FR + EN. L'analyse avancée de hockey en français est essentiellement un territoire inoccupé; Lemieux s'y installe.
5. **Architecture enfichable.** Ajouter un connecteur ou une habileté, c'est 3 fichiers + des tests. Voir [`templates/`](./templates).
6. **Respectueux des fournisseurs.** Mise en cache agressive, limitation de débit polie, documentation des termes, aucune redistribution de données non produites par nous.
7. **Les données sont la source; la prose est templatée à partir d'elles.** Les fichiers d'entrée structurés (`<gameN>_lineups.yaml`, `<task>.numbers.json`) sont la base canonique des faits. L'invariant de construction garantit qu'aucune prose ne peut contredire les données — `runProseFactCheck()` interrompt la production du docx (code de sortie 7) si un patineur sans but apparaît comme sujet d'un verbe de marquage. Le même patron s'applique à la composition des trios, le temps de glace, les passes, etc. La composition des trios est une ENTRÉE de l'analyse, jamais inférée d'extraits de presse.
8. **Mener par les résultats, pas par les annonces.** Le public a regardé le match — le rôle du rapport post-match est de faire surface ce que seuls les chiffres révèlent (amplitudes inattendues, paradoxes que l'œil ne voit pas, contradictions avec le narratif d'avant-série). Le pipeline de révision automatique des PR attrape les manquements.

## Contribuer

Voir [CONTRIBUTING.md](./CONTRIBUTING.md) (bilingue). La contribution la plus facile : un connecteur — copier `templates/connector-template`, implémenter `refresh()`, écrire trois tests.

**Révision automatique de chaque PR.** Lorsqu'une PR est ouverte, un workflow GitHub lance Claude Code avec l'habileté [`review-pr-lemieux`](./.claude/skills/review-pr-lemieux) et publie un commentaire de révision structuré en quelques minutes — verdict (MERGE / DEMANDER DES CHANGEMENTS / FERMER), ce que fait la PR, ce qui est bien, ce qui inquiète, une grille des règles du projet, et la prochaine étape recommandée. Le mainteneur lit la révision et accepte ou refuse; Claude ne fusionne ni ne ferme jamais automatiquement.

## Feuille de route

Voir [ROADMAP.md](./ROADMAP.md). Axes v0.2 : connecteur MoneyPuck, connecteur PWHL (un auditoire réellement sous-servi), publication sur PyPI, migration de l'application Streamlit complémentaire.

## Licence

- **Code** : MIT. Voir [LICENSE](./LICENSE).
- **Documentation** : CC BY 4.0.
- **Données** : varient selon la source. Voir [SOURCES.md](./SOURCES.md). Nous ne re-licensions pas les données que nous ne possédons pas.

## Remerciements

Repose sur la communauté analytique qui a rendu ce projet pensable : [Natural Stat Trick](https://www.naturalstattrick.com/), [MoneyPuck](https://moneypuck.com/), les API publiques de LNH.com, [Evolving-Hockey](https://evolving-hockey.com/), [HockeyViz](https://hockeyviz.com/), [All Three Zones](https://www.allthreezones.com/) (Corey Sznajder), et la longue liste de blogueurs, mainteneurs de paquets R et auteurs Substack référencés dans le lexique et la documentation.

## Le nom

*Lemieux* est un hommage à **Claude Lemieux** — l'ailier québécois qui s'est bâti une carrière décorée de Coupes Stanley dans des séries éliminatoires longues et rugueuses — et donc un clin d'œil implicite à un certain outil de codage préféré et aux modèles qui l'animent. On ne s'étend pas là-dessus.
