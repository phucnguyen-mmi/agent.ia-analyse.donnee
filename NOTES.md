# Notes de session - Agent IA Analyse Données

## Ce qu'on a construit

Application Flask d'analyse de données marketing avec Claude IA.

URL Render : à compléter (ton URL Render)

## Fonctionnalités

- Upload d'un fichier CSV
- Analyse automatique par Claude (claude-opus-4-6)
- Génération de graphiques (bar chart + histogramme)
- Téléchargement du rapport en PDF (reportlab)
- Système de login avec mot de passe (variable APP_PASSWORD)
- Historique des analyses sauvegardé en base de données PostgreSQL
- Page /historique avec filtre par date
- Page /historique/<id> pour revoir une analyse passée

## Variables d'environnement Render

| Variable | Description |
|---|---|
| ANTHROPIC_API_KEY | Clé API Claude |
| APP_PASSWORD | Mot de passe de connexion à l'app |
| SECRET_KEY | Clé secrète Flask (optionnel) |
| DATABASE_URL | URL interne PostgreSQL Render |

## Routes

| Route | Description |
|---|---|
| / | Page principale, upload CSV |
| /login | Page de connexion |
| /logout | Déconnexion |
| /telecharger-pdf | Télécharge le rapport PDF |
| /historique | Liste des analyses avec filtre par date |
| /historique/<id> | Détail d'une analyse |

## Déploiement

- GitHub : https://github.com/phucnguyen-mmi/agent.ia-analyse.donnee
- Render deploy hook : https://api.render.com/deploy/srv-d8eqhqegvqtc73doa8hg?key=q-HpujUlGSo
- Base PostgreSQL : agent-ia-db (créée sur Render)

## Stack technique

- Flask + Flask-SQLAlchemy
- Claude API (anthropic)
- Pandas + Matplotlib
- ReportLab (PDF)
- PostgreSQL (Render) / SQLite (local)
- Gunicorn (production)
