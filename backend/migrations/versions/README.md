# Migrations

Ce dossier est vide intentionnellement : l'échafaudage Alembic est prêt
(`alembic.ini`, `migrations/env.py`), mais la **révision initiale** doit être
générée chez vous, avec vos dépendances installées (`pip install -r
requirements.txt`), car elle a besoin d'introspecter la vraie base :

```bash
cd backend
alembic revision --autogenerate -m "schema initial (15 modules)"
alembic upgrade head
```

Ensuite, à chaque modification d'un `models.py` (nouveau champ, nouvelle
table...), générez une nouvelle révision de la même façon plutôt que de
modifier la base à la main.

En développement, `Base.metadata.create_all()` (dans `app/main.py`)
continue de fonctionner sans Alembic pour aller vite. En production,
utilisez uniquement Alembic — c'est déjà branché dans `Dockerfile` et
`deployment/deploy.sh`.
