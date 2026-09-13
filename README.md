# Nexus — Plateforme complète (backend + frontend + paiement + modèles)

## Démarrage rapide

**Terminal 1 — backend :**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # configurez SECRET_KEY et INITIAL_SUPERUSER_EMAIL
uvicorn app.main:app --reload
```

**Terminal 2 — frontend :**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Ouvrez `http://localhost:5173`, inscrivez-vous avec l'email défini dans
`INITIAL_SUPERUSER_EMAIL`, puis lancez le script de modèles :
```bash
cd backend && python3 -m scripts.seed_templates
```

## Fonctionne sur mobile ET ordinateur

L'interface s'adapte automatiquement : sidebar fixe + panneaux côte à
côte sur ordinateur, barre de navigation en bas + panneaux empilés
verticalement sur mobile (vérifié explicitement sur l'éditeur de
calques, le plus complexe de la plateforme). Aucune installation
supplémentaire n'est nécessaire : c'est une application web responsive,
accessible depuis n'importe quel navigateur, téléphone ou ordinateur.

## État du projet

- **Backend** : 15/15 modules de contenu + paiement, tous testés
- **Frontend** : 15/15 modules connectés, éditeur de calques complet (glisser-déposer)
- **Modèles graphiques** : carte de visite, carte d'étudiant, logo, flyer, post réseau social — prêts à l'emploi via le script de seed
- **Paiement** : plans, abonnements, webhook anti double-crédit

## Reste à faire avant un vrai lancement

1. Brancher un vrai fournisseur de paiement (MTN MoMo, Orange Money, processeur carte)
2. Sécuriser le webhook de paiement par signature
3. Restreindre la création de plans tarifaires au super-administrateur
4. Ajouter davantage de modèles graphiques
5. Déployer avec PostgreSQL plutôt que SQLite

## Branche de test
Ceci est un test pour apprendre la gestion des branches dans Nexus.