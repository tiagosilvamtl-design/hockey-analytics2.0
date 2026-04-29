# Démarrer avec Lemieux

> **Langue** : Français · [English](../en/getting-started.md)

## Ce qu'est Lemieux

Lemieux est un cadriciel à code source ouvert qui combine Claude (ou tout autre client IA compatible MCP) avec des connecteurs de données de hockey soigneusement sélectionnés, des primitives analytiques et des habiletés agentiques. Objectif : produire une couverture de hockey rigoureusement analytique et consciente de ses limites, sans tout reconstruire à partir de zéro.

## Installation en 5 minutes

```bash
git clone https://github.com/<votre-fork>/lemieux.git
cd lemieux

python -m venv .venv
source .venv/bin/activate       # Windows Git Bash : . .venv/Scripts/activate

# Installer tous les paquets Lemieux en mode éditable
pip install -e packages/lemieux-core
pip install -e packages/lemieux-glossary
pip install -e packages/lemieux-connectors
pip install -e packages/lemieux-mcp
pip install -e packages/lemieux-app

# Ajouter votre clé d'accès NST (obtenue depuis votre profil NST — gratuit mais approbation requise)
cp .env.example .env
# Modifier .env, définir NST_ACCESS_KEY=...
```

## Lancer le serveur MCP

```bash
lemieux-mcp --store ~/.lemieux/store.sqlite
```

Puis pointez votre `mcp.json` de Claude Desktop vers ce serveur. Voir le [README de lemieux-mcp](../../packages/lemieux-mcp/README.md) pour la configuration.

## Utiliser dans Claude Code

Ouvrez le dépôt Lemieux dans Claude Code. Le dossier `.claude/skills/` est automatiquement découvert. Demandez à Claude :

```
« Rédige un billet de 1000 mots sur le match du Canadien d'hier. Concentre-toi
sur la seconde unité d'avantage numérique. Inclus une analyse de substitution. »
```

Claude invoque `draft-game-post`, appelle les outils MCP, consulte le lexique pour les définitions des métriques, exécute `validate-analysis` pour vérifier la rigueur et produit une ébauche en Markdown.

## Prochaines étapes

- Lire le [lexique](../../packages/lemieux-glossary/src/lemieux/glossary/terms.yaml) pour comprendre ce que Lemieux connaît.
- Explorer `examples/habs_round1_2026/` pour un exemple d'analyse complète.
- Ajouter un connecteur : voir `templates/connector-template/`.

## Philosophie

Lemieux ne cherche pas à remplacer Natural Stat Trick, Evolving-Hockey ou HockeyViz. C'est une couche d'agrégation et d'orchestration qui permet à un client IA d'opérer honnêtement sur leurs sorties — avec taille d'échantillon, intervalles de confiance, mises en garde et liens vers le lexique toujours visibles.

Si votre ébauche ressemble à un résumé de match rempli de clichés, quelque chose ne va pas. Ouvrez un ticket.
