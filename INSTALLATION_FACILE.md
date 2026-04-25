# Installer Lemieux sans être techno — guide pour les amis

Ce guide suppose **zéro** connaissance technique. Tu vas faire deux choses :

1. **Installer Claude Code** (un assistant IA qui exécute des commandes pour toi).
2. **Demander à Claude Code d'installer Lemieux** à ta place.

C'est tout. Compte 15 à 20 minutes la première fois.

---

## Avant de commencer : ce qu'il te faut

- Un ordinateur **Windows**, **Mac** ou **Linux**.
- Un **abonnement Claude** (Claude Pro ou Claude Max — environ 20 $/mois) **ou** un compte API Anthropic avec un peu de crédit. Sans ça, Claude Code ne fonctionnera pas.
  - Inscription : https://claude.ai
- Une connexion Internet.

Pas besoin d'installer Python, Git ou autre chose à la main. Claude Code va s'en occuper.

---

## Étape 1 — Installer Claude Code

### Sur Windows

1. Clique sur le bouton **Démarrer** de Windows, tape `powershell`, puis clique sur **Windows PowerShell**.
2. Une fenêtre noire s'ouvre. Copie la ligne suivante, colle-la dedans (clic droit pour coller), puis appuie sur **Entrée** :

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

3. Attends que l'installation se termine. Ça peut prendre 1-2 minutes.
4. **Ferme complètement** la fenêtre PowerShell, puis **rouvre-la** (étape 1 à nouveau). C'est important — sinon la commande `claude` ne sera pas reconnue.

### Sur Mac ou Linux

1. Ouvre l'application **Terminal** (sur Mac : `Cmd + Espace`, tape « terminal », appuie sur Entrée).
2. Copie-colle ceci, puis appuie sur **Entrée** :

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

3. Attends la fin. Ferme et rouvre le Terminal.

### Vérifier que ça marche

Dans ta fenêtre Terminal/PowerShell, tape :

```
claude --version
```

Tu devrais voir un numéro de version (par ex. `2.x.x`). Si oui, bravo. Sinon, ferme tout et recommence l'étape 1.

---

## Étape 2 — Se connecter à son compte Claude

1. Dans la même fenêtre, tape simplement :

   ```
   claude
   ```

2. La première fois, Claude Code va te demander de te connecter. Suis les instructions à l'écran — ça va ouvrir ton navigateur, tu te connectes avec ton compte Claude, et tu reviens dans la fenêtre.

3. Quand tu vois une invite qui ressemble à ça :

   ```
   > 
   ```

   …c'est que Claude Code est prêt à recevoir tes instructions.

---

## Étape 3 — Créer un dossier pour Lemieux

Avant de demander à Claude Code d'installer Lemieux, on va lui donner un endroit propre où travailler.

### Sur Windows

1. Dans PowerShell, **quitte Claude Code** s'il est ouvert (tape `/exit` ou ferme la fenêtre et rouvre-la).
2. Tape ceci, ligne par ligne :

   ```powershell
   cd $HOME
   mkdir lemieux
   cd lemieux
   claude
   ```

### Sur Mac/Linux

```bash
cd ~
mkdir lemieux
cd lemieux
claude
```

Tu es maintenant dans un dossier nommé `lemieux` dans ton répertoire personnel, et Claude Code est ouvert dedans.

---

## Étape 4 — Demander à Claude Code d'installer Lemieux

C'est ici que la magie opère. Tu n'as **rien d'autre à taper toi-même** — tu écris simplement à Claude Code ce que tu veux. Copie-colle le bloc suivant dans Claude Code et appuie sur Entrée :

```
Salut. J'aimerais installer le cadriciel Lemieux AI pour analyser le hockey.
Voici ce que je veux que tu fasses pour moi, étape par étape :

1. Vérifie si Git et Python 3.11+ sont installés sur ma machine. Si non,
   installe-les (sur Windows utilise winget, sur Mac utilise Homebrew, sur
   Linux utilise le gestionnaire de paquets approprié). Demande-moi
   confirmation avant chaque installation.

2. Clone le dépôt depuis https://github.com/lemieuxAI/framework.git dans
   le dossier courant.

3. Crée un environnement virtuel Python (.venv) et installe les quatre
   paquets locaux en mode editable :
     - packages/lemieux-core
     - packages/lemieux-glossary
     - packages/lemieux-connectors
     - packages/lemieux-mcp

4. Copie .env.example vers .env. NE remplis PAS la clé NST_ACCESS_KEY —
   on s'en occupe à la prochaine étape ensemble.

5. Lance la suite de tests pour confirmer que tout fonctionne.

6. Quand c'est fait, dis-moi exactement où aller chercher une clé d'accès
   Natural Stat Trick et où la coller.

Si une étape échoue, arrête-toi et explique-moi le problème en français
simple — je ne suis pas technique. Ne devine pas.
```

Claude Code va exécuter chaque étape une par une. Il va te demander la permission à chaque commande importante (par exemple `Allow this command? (y/n)`). Réponds **`y`** (yes/oui) si la commande te semble raisonnable. Si tu n'es pas sûr, demande-lui en français : « C'est quoi cette commande, en mots simples ? »

---

## Étape 5 — Obtenir une clé Natural Stat Trick

La plupart des analyses avancées de Lemieux s'appuient sur **Natural Stat Trick** (NST), un site gratuit. Il faut une clé personnelle d'accès.

1. Va sur https://www.naturalstattrick.com et crée un compte (gratuit).
2. Demande à NST une clé API personnelle (voir leur page « contact » ou « API access »).
3. Quand tu l'as, retourne dans Claude Code et tape :

   ```
   J'ai reçu ma clé NST. Elle est : XXXXXXXX
   Peux-tu la coller au bon endroit dans le fichier .env, et confirmer
   qu'elle fonctionne en faisant un appel test à NST ?
   ```

   (Remplace `XXXXXXXX` par ta vraie clé.)

Claude Code va modifier le fichier `.env` pour toi et faire un test.

---

## Étape 6 — Premier essai

Tu peux maintenant demander une analyse en langage naturel. Exemple :

```
Rédige un billet de 800 mots sur le dernier match du Canadien.
Concentre-toi sur la structure défensive à 5 contre 5. Inclus les
intervalles de confiance à 80 % et lie chaque métrique à sa définition
dans le lexique.
```

Claude Code va activer l'habileté `draft-game-post`, aller chercher les données du match, faire les calculs, et te livrer un texte en Markdown. Tu peux le copier-coller dans n'importe quel éditeur de texte ou plateforme de blogue.

---

## Si quelque chose plante

Tape simplement à Claude Code :

```
Cette étape ne fonctionne pas. Voici l'erreur que je vois : [colle l'erreur].
Diagnostique le vrai problème — ne contourne pas. Explique-moi en français
simple.
```

Claude Code est plutôt bon pour déboguer ses propres installations. Donne-lui le message d'erreur tel quel.

---

## Résumé en cinq lignes

1. Installe Claude Code (une commande dans PowerShell ou Terminal).
2. Connecte-toi à ton compte Claude.
3. Crée un dossier `lemieux` et lance `claude` dedans.
4. Copie-colle le gros bloc de l'**Étape 4** dans Claude Code.
5. Va chercher ta clé NST, donne-la à Claude Code, et amuse-toi.

Bonne analyse — et souviens-toi : un seul match ne prouve à peu près rien. C'est exactement pour ça que Lemieux affiche les intervalles de confiance.
