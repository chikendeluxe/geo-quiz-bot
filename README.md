# 🌍 Bot Discord – Quiz de Géographie

Un bot Discord de quiz géographique avec trois types de questions, plusieurs niveaux de difficulté et un système de scores multijoueur.

---

## ✨ Fonctionnalités

| Type de question | Description |
|---|---|
| 🚩 Drapeau | Un emoji drapeau est affiché — il faut identifier le pays |
| 🏛️ Capitale | « Quelle est la capitale de X ? » ou « Y est la capitale de quel pays ? » |
| 🗺️ Carte | Une carte s'affiche avec un pays coloré en rouge — il faut le nommer |

- **4 niveaux de difficulté** : Facile / Moyen / Difficile / Tous mélangés
- **7 combinaisons de types** : un seul type, ou plusieurs en même temps
- **5 à 20 questions** configurables
- **Multijoueur** : tous les joueurs répondent simultanément via des boutons
- **Scores en temps réel** avec `/scores`
- **90 pays** dans la base de données

---

## 🛠️ Installation

### Prérequis
- Python **3.10+**
- Un compte développeur Discord

### 1. Créer le bot Discord

1. Rendez-vous sur [discord.com/developers/applications](https://discord.com/developers/applications)
2. Cliquez sur **New Application**, donnez-lui un nom
3. Onglet **Bot** → **Add Bot**
4. Copiez le **Token** (vous en aurez besoin)
5. Activez **"Message Content Intent"** (Privileged Gateway Intents)
6. Onglet **OAuth2 → URL Generator** :
   - Scopes : `bot` + `applications.commands`
   - Permissions : `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`
7. Copiez l'URL générée et invitez le bot sur votre serveur

### 2. Installer les dépendances

```bash
git clone <votre-repo>
cd geo-quiz-bot

# Environnement virtuel (recommandé)
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configurer le token

```bash
cp .env.example .env
# Éditez .env et collez votre token Discord
```

### 4. Lancer le bot

```bash
python bot.py
```

Vous devriez voir :
```
✅  Connecté en tant que VotreBot#1234  (ID : ...)
✅  Commandes slash synchronisées
```

> **Note :** La synchronisation des commandes slash peut prendre jusqu'à 1 heure pour apparaître globalement. Pour les tests, elle est quasi instantanée sur le serveur où le bot est invité.

---

## 🎮 Utilisation

### Commandes disponibles

| Commande | Description |
|---|---|
| `/quiz` | Lance un quiz (paramètres : type, difficulté, nombre de questions) |
| `/stopquiz` | Arrête le quiz en cours |
| `/scores` | Affiche les scores actuels (visible uniquement par vous) |
| `/aide` | Affiche l'aide |

### Exemple de partie

```
/quiz type:🚩🏛️ Drapeaux + Capitales  difficulty:🟡 Moyen  questions:10
```

Chaque question affiche un embed avec **4 boutons** (A / B / C / D).
Les joueurs cliquent — la réponse est **éphémère** (invisible des autres) pour que tout le monde joue équitablement.
Après 15 secondes, la bonne réponse est révélée et les scores mis à jour.

---

## 📁 Structure du projet

```
geo-quiz-bot/
├── bot.py              # Point d'entrée – commandes slash Discord
├── quiz_manager.py     # Gestionnaire des sessions actives (une par salon)
├── quiz_session.py     # Logique d'une session + UI Discord (boutons)
├── questions.py        # Génération des questions et des distracteurs
├── map_generator.py    # Génération d'images de carte (geopandas/matplotlib)
├── countries_data.py   # Base de données des 90 pays
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🗺️ Questions de type Carte

Les cartes sont générées à la volée avec **geopandas** et **matplotlib** à partir des données [Natural Earth](https://www.naturalearthdata.com/) (incluses dans `geodatasets`). Le pays cible est coloré en **rouge** sur un fond sombre.

Si les cartes ne s'affichent pas, vérifiez que `geodatasets` est bien installé :
```bash
pip install geodatasets
```

---

## ➕ Ajouter des pays

Ouvrez `countries_data.py` et ajoutez une entrée dans `COUNTRIES` :

```python
{
    "fr":         "Finlande",         # Nom français (affiché dans le quiz)
    "en":         "Finland",          # Nom dans geopandas (pour les cartes)
    "capital_fr": "Helsinki",         # Capitale (en français)
    "iso2":       "FI",               # Code ISO 3166-1 alpha-2 (pour le drapeau)
    "difficulty": "medium",           # "easy" | "medium" | "hard"
    "continent":  "Europe",           # Pour grouper les distracteurs
},
```

---

## 📝 Licence

MIT — libre d'utilisation et de modification.
