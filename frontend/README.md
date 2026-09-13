# Nexus Frontend

Interface web de la plateforme Nexus, fidèle à la maquette validée : thème
sombre, dégradés bleu-violet, sidebar fixe, grille de modules, widget IA.

## Installation

```bash
npm install
cp .env.example .env
npm run dev
```

Assurez-vous que le backend Nexus tourne sur `http://127.0.0.1:8000`
(voir le README du backend) — Vite proxifie automatiquement `/api` vers
cette adresse en développement (voir `vite.config.js`).

## État actuel : les 15 modules sont connectés au backend

- **Authentification** : inscription, connexion, session persistante, déconnexion
- **Tableau de bord d'accueil** : reproduction fidèle de la maquette
- **IA Nexus** : conversations, historique, envoi de messages
- **Réseau Social** : fil d'actualité, publication, likes
- **Marketplace** : recherche et publication de produits
- **Finance** : comptes, solde en direct, transactions, résumé de trésorerie
- **Cartographie (Maps)** : recherche par proximité géographique, création de fiches
- **Agriculture** : parcelles, cycles de culture
- **Élevage** : troupeaux, événements sanitaires avec effectif en temps réel
- **Droit** : recherche de ressources juridiques par pays et catégorie
- **Gestion d'entreprise** : entreprises, tableau de bord (employés, clients, facturation)
- **Éducation** : recherche de cours, inscription (avec gestion premium)
- **Studio créatif** : statut premium, génération vidéo par IA
- **Développement logiciel** : projets, tâches avec statuts
- **Cybersécurité** : actifs, demande d'audit avec confirmation obligatoire, tableau de bord de risque
- **DevOps/Cloud** : ressources cloud, tableau de bord infrastructure

Navigation desktop (sidebar) et mobile (barre du bas) fonctionnelles partout.

## Note sur la profondeur fonctionnelle

Chaque module couvre son **flux principal** (créer/consulter/lister
l'essentiel) plutôt que 100% des routes backend disponibles — par
exemple, Éducation ne couvre pas encore l'interface des évaluations
obligatoires, Studio ne couvre pas encore l'éditeur de calques complet.
Le backend, lui, expose déjà TOUTES ces routes (voir son README) : il
suffit de suivre le même patron (`apiRequest` + composants `nexus-*`)
pour étoffer chaque page.

## Design system

Toutes les couleurs sont centralisées dans `tailwind.config.js` (palette
`nexus.*` pour le thème général, `module.*` pour les couleurs de chaque
carte de module). Ne codez jamais une couleur en dur dans un composant.

## Limite connue de cet environnement de développement

Cet environnement n'a pas d'accès réseau pour exécuter `npm install` et
lancer un vrai serveur de développement. Tous les fichiers ont été
**vérifiés syntaxiquement** avec esbuild (28 fichiers, tous valides),
mais n'ont pas pu être exécutés dans un navigateur ici. Lancez
`npm run dev` sur votre machine pour la validation visuelle finale.
