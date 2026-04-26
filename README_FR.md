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

| Paquet | Rôle |
|---|---|
| [`lemieux-core`](./packages/lemieux-core) | Primitives analytiques : moteur d'échange, impact isolé, bases pondérées, projections avec variance |
| [`lemieux-connectors`](./packages/lemieux-connectors) | Connecteurs enfichables vers les sources de données (API publique LNH, Natural Stat Trick, autres à venir) |
| [`lemieux-mcp`](./packages/lemieux-mcp) | Serveur FastMCP qui expose les outils et ressources analytiques à tout client MCP |
| [`lemieux-glossary`](./packages/lemieux-glossary) | Définitions bilingues (FR/EN) de toutes les métriques utilisées, avec formules et mises en garde |
| [`.claude/skills/`](./.claude/skills) | Flux de travail Claude — `research-game`, `translate-to-quebec-fr`, `draft-game-post`, `propose-swap-scenario`, `validate-analysis`, `review-pr-lemieux` |
| [`examples/`](./examples) | Trois analyses complètes dans `examples/habs_round1_2026/` : rapport autonome du premier tour, analyse par match (M3), classement des joueurs en séries |
| [`tools/push_to_drive.py`](./tools) | Téléversement portable vers Google Drive (OAuth personnel, `--public --folder-public` pour des liens partageables) |
| [`CLAUDE.md`](./CLAUDE.md) | Guide d'utilisation canonique pour travailler dans ce dépôt avec Claude Code — règles d'écriture, flux de données, invariants structurels |

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

- **API publique de LNH.com** — jeu par jeu, présences, formations, classements (pas de clé requise)
- **Natural Stat Trick** — statistiques avancées (clé d'accès personnelle requise, gratuite)
- **MoneyPuck, PWHL** — prévus pour v0.2 (voir [ROADMAP.md](./ROADMAP.md))

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
