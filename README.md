# ⚽ FootySim — Simulation de championnat de football

FootySim est un projet Python utilisant **SQLAlchemy (async)** et **Alembic** pour simuler un championnat de football avec :
- Clubs, joueurs, transferts
- Fixtures (calendrier), matchs simulés, buteurs
- Classement dynamique
- CLI (Typer) pour jouer avec la base de données

Idéal pour apprendre SQLAlchemy **avec un projet complet et fun** 🎮.

---

## 🚀 Installation

### 1. Cloner le projet
```bash
git clone https://github.com/ton-compte/FootySim.git
cd FootySim
```

### 2. Créer et activer un venv
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer la base de données

Renommer `.env.example` → `.env` et modifier :
```env
DATABASE_URL=sqlite+aiosqlite:///footysim.db
# ou avec MySQL :
# DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/footysim
```

### 5. Initialiser la base
```bash
python -m footysim.cli initdb
```

### 6. Injecter des données de départ
```bash
python -m footysim.cli seed
```

---

## 🎮 Utilisation

Toutes les commandes passent par le CLI :

```bash
python -m footysim.cli [COMMANDE] [OPTIONS]
```

### 📅 Calendrier (fixtures)
Générer les journées :
```bash
python -m footysim.cli schedule
```

Lister les matchs programmés :
```bash
python -m footysim.cli fixtures 1   # 1 = season_id
```

### ⚽ Simulation de matchs
Simuler un seul match :
```bash
python -m footysim.cli simulate 3   # fixture_id = 3
```

Simuler **toute la saison** :
```bash
python -m footysim.cli simulate-season 1
```

Resimuler en réinitialisant les résultats :
```bash
python -m footysim.cli simulate-season 1 --reset
```

### 📊 Classement
Afficher la table actuelle :
```bash
python -m footysim.cli table 1
```

### 🏆 Meilleurs buteurs
Afficher les top scorers de la saison :
```bash
python -m footysim.cli topscorers 1
```

---

## ✅ Tests

Lancer la suite de tests unitaires :
```bash
pytest -v
```

---

## 📂 Structure du projet

```
src/footysim/
│── models/          # ORM SQLAlchemy (Club, Player, Fixture, Match, Goal, Transfer…)
│── services/        # Logique métier (schedule, match_engine, table_service…)
│── repositories/    # Accès DB
│── seeds/           # Données de départ
│── cli.py           # CLI Typer
│── core/            # config, logging, exceptions
alembic/             # migrations DB
tests/               # tests unitaires
```

---

## 🛠️ Roadmap (idées futures)

- 🔄 Mode "sauvegarde/chargement" de saison
- 💰 Gestion du mercato (budget, transferts)
- 🤕 Gestion blessures & suspensions
- 🏟️ Statistiques avancées (possession, tirs, etc.)
- 🌐 API FastAPI pour exposer les résultats

---

## 📜 Licence

Projet pédagogique — librement réutilisable et modifiable.
