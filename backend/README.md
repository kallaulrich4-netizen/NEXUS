# Nexus Platform

Fondation technique de la plateforme Nexus, construite module par module.

## Modules livrés jusqu'ici

1. **Socle transversal** (`app/core`) : configuration, base de données, sécurité (JWT + hachage bcrypt). Utilisé par tous les modules futurs.
2. **Authentification** (`app/modules/auth`) : inscription, connexion, rafraîchissement de session, protection des routes. Un seul compte pour toute la plateforme.
3. **Nexus AI** (`app/modules/ai_assistant`) : conversations et messages, avec un moteur d'IA branché derrière une interface (`provider.py`) qui ne révèle jamais quel fournisseur est utilisé.
4. **Réseau social** (`app/modules/social`) : publications, likes, commentaires, abonnements, fil d'actualité, gestion de la visibilité (public / abonnés / privé).
5. **Marketplace** (`app/modules/marketplace`) : produits multi-vendeurs, commandes multi-articles, protection anti-survente (stock vérifié et décrémenté dans la même transaction), priorité aux produits du pays de l'utilisateur sans exclure l'international, workflow de statut de commande (pending → confirmed → shipped → delivered).
6. **Cartographie intelligente** (`app/modules/maps`) : fiches professionnelles géolocalisées (fermes, avocats, médecins, écoles, hôtels, restaurants...) créées par les professionnels eux-mêmes, recherche par proximité réelle (formule de Haversine), avis avec note moyenne, vérification manuelle des fiches distincte de l'auto-déclaration.
7. **Agriculture** (`app/modules/agriculture`) : parcelles, cycles de culture (semis → croissance → récolte), suivi des activités (irrigation, fertilisation, traitements...) avec coûts, statistiques de rendement par parcelle.
8. **Élevage** (`app/modules/livestock`) : troupeaux/cheptels toutes espèces (champ texte libre, non limité — bovins, ovins, caprins, porcins, volailles, poissons, abeilles, ou toute autre espèce), événements sanitaires ajustant automatiquement l'effectif, suivi de production (lait, œufs, laine, miel...), statistiques par troupeau.
9. **Droit** (`app/modules/legal`) : ressources juridiques par juridiction (jamais génériques — chaque contenu est rattaché à un pays précis), publication uniquement après validation (`is_reviewed` + `is_published`), mise en relation avec de vrais avocats référencés dans le module Cartographie, workflow de consultation avec permissions strictes (seul l'avocat accepte/refuse/termine, seul le client annule).
10. **Finance** (`app/modules/finance`) : comptes multi-devises, transactions revenus/dépenses, budgets par catégorie et période avec détection de dépassement, résumé de trésorerie (tableaux de bord) groupé par catégorie, **insights factuels** calculés sur les propres données de l'utilisateur (évolution des dépenses, taux d'épargne — jamais des recommandations d'investissement), et centre éducatif financier (épargne, fiscalité, dette, retraite...) avec le même processus de validation que le module Droit.
11. **Gestion d'entreprise** (`app/modules/business`) : entreprises tous secteurs (texte libre — commerce, agriculture, BTP, industrie, transport, santé, hôtellerie...), employés avec suivi de statut, clients, facturation complète avec calcul automatique des totaux, numéros de facture uniques par entreprise, workflow de statut contrôlé (brouillon → envoyée → payée), tableau de bord consolidé.
12. **Studio créatif** (`app/modules/studio`) : éditeur de design façon Canva (modèles, projets, calques en JSON) et montage vidéo façon CapCut (timeline, catalogue de filtres), avec **système premium/gratuit intégré** : chaque nouveau compte bénéficie de 24h d'accès complet, puis les modèles et filtres marqués premium nécessitent un abonnement actif. Le rendu vidéo réel (encodage .mp4) est isolé dans `render.py` comme point d'intégration futur — nécessite un pipeline FFmpeg en production, non simulable ici.
13. **Éducation** (`app/modules/education`) : cours toutes disciplines (texte libre — primaire, secondaire, université, informatique, médecine, droit, ingénierie, langues, IA, cybersécurité, ou toute autre discipline), leçons ordonnées, inscriptions, contenu réservé aux étudiants inscrits, suivi de progression automatique par complétion de leçon, cours premium/gratuits via le même système que le Studio créatif. **Évaluations obligatoires** : un cours peut exiger une évaluation à choix unique avec seuil de réussite configurable ; le cours n'est marqué terminé qu'après une tentative réussie, avec reprises illimitées en cas d'échec ; les bonnes réponses ne sont jamais exposées à l'étudiant avant correction.
14. **Développement logiciel** (`app/modules/devtools`) : projets tous types (texte libre — web, mobile, desktop, API, microservice, script...), gestion de tâches avec priorités et échéances, tableau de bord par statut, bibliothèque personnelle de snippets de code, documentation d'API par endpoint (méthode + chemin unique par projet). Ce module gère l'organisation du travail de développement ; la génération/débogage de code lui-même passe par le module Nexus AI, réutilisé plutôt que dupliqué.
15. **Cybersécurité** (`app/modules/cybersecurity`) : inventaire d'actifs, demandes d'audit **obligatoirement soumises à confirmation de propriété/autorisation** (rejetée automatiquement sinon), constats de vulnérabilité avec conseil de remédiation (jamais de code d'exploitation), tableau de bord de risque par sévérité, guides de sécurisation éducatifs avec validation avant publication. Volontairement un outil de gestion et de suivi, pas un outil offensif.
16. **DevOps/Cloud** (`app/modules/devops`) : ressources cloud tous types et tous fournisseurs (texte libre), déploiements avec workflow de statut contrôlé (impossible de sauter des étapes), **rollback** qui annule automatiquement le déploiement problématique, alertes de supervision par sévérité, tableau de bord infrastructure consolidé.

16. **Paiement** (`app/modules/payments`) : plans tarifaires configurables (journalier, hebdomadaire, mensuel...), abonnements qui restent **en attente jusqu'à confirmation réelle** du paiement (jamais de crédit avant encaissement effectif), webhook de confirmation protégé contre le double-crédit, prolongation automatique en cas de renouvellement. Abstraction MTN Mobile Money / Orange Money / Visa prête à recevoir de vraies clés d'API en production (voir `provider.py`). N'affecte jamais le Réseau social, qui reste gratuit pour tous.

**Les 15 modules de contenu et le système de paiement sont désormais tous livrés.**

## Export de documents (PDF / Word / Excel / PowerPoint)

Utilitaire partagé dans `app/core/exports.py` (reportlab, python-docx,
openpyxl, python-pptx), branché concrètement sur deux endpoints
démonstratifs : `GET /finance/cashflow/export` (PDF/Excel) et
`GET /business/invoices/{id}/export` (PDF/Word). N'importe quel autre
module peut réutiliser exactement le même utilitaire (`ExportDocument`,
`ExportSection`, `export_to_pdf/word/excel/powerpoint`) pour exposer ses
propres exports — c'est le patron à suivre pour l'étendre progressivement
à tous les modules restants.

## Génération vidéo par IA dans le Studio créatif (façon Veo3)

`app/modules/studio/ai_video_provider.py` définit l'abstraction d'appel à
un vrai service de génération vidéo par IA (Google Veo, Runway, Pika...).
Toujours premium. Sans clé d'API réelle branchée en production, un job
reste honnêtement à l'état "en_attente" plutôt que de simuler un faux
résultat — voir la docstring du fichier pour le point d'intégration exact.

## Système premium (fondation posée, paiement réel à venir)

`User.trial_ends_at` (24h à l'inscription) et `User.premium_until` (mis à
jour par le futur module de paiement) alimentent `has_premium_access()`
dans `app/core/entitlements.py` — un point de vérité unique réutilisé par
tous les modules payants. Grille tarifaire prévue pour le module de
paiement final : journalier dès 100 FCFA, hebdomadaire dès 500 FCFA,
mensuel dès 1350 FCFA. Le Réseau social n'utilise jamais cette
vérification : il reste entièrement gratuit.

### Votre accès créateur (super-administrateur)

Définissez `INITIAL_SUPERUSER_EMAIL` dans votre `.env` réel avec votre
propre adresse email **avant** de créer votre compte (ou reconnectez-vous
si vous l'ajoutez après coup). Ce compte, et uniquement celui-ci, obtient
automatiquement :
- un accès premium illimité et permanent à toutes les fonctionnalités payantes de la plateforme (Studio créatif, Éducation, génération vidéo IA...) ;
- une exemption des limites de débit (rate limiting) sur toutes les routes authentifiées.

Personne ne peut s'attribuer ce statut via l'inscription normale : c'est
une comparaison stricte avec une variable d'environnement que vous seul
contrôlez, jamais un champ de formulaire.

## Sécurité — failles corrigées proactivement

Plutôt que de découvrir ces problèmes après un incident (comme cela arrive
régulièrement à de grandes plateformes), Nexus corrige dès maintenant les
failles les plus fréquentes du classement OWASP API Security Top 10 :

| Faille (référence OWASP) | Correction appliquée |
|---|---|
| API1 — Broken Object Level Authorization | Vérification systématique du propriétaire à chaque accès (posts, conversations) |
| API2 — Broken Authentication | Hachage bcrypt + verrouillage de compte après 5 échecs de connexion (15 min) |
| API3 — Broken Object Property Level Authorization | Schémas de sortie stricts (le mot de passe haché n'est jamais exposé) |
| API4 — Unrestricted Resource Consumption | Limiteur de débit sur inscription, connexion, likes, abonnements |
| API8 — Security Misconfiguration | En-têtes de sécurité HTTP (X-Frame-Options, HSTS en production, etc.) |

**Note pour la mise en production** : le limiteur de débit actuel fonctionne
en mémoire, donc uniquement pour un seul serveur. Si vous déployez plusieurs
instances derrière un load balancer, remplacez-le par une solution
partagée (ex. Redis) — c'est indiqué dans `app/core/rate_limit.py`.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Éditez .env : générez une vraie SECRET_KEY avec :
#   python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Lancer le serveur

```bash
uvicorn app.main:app --reload
```

Documentation interactive : http://127.0.0.1:8000/docs

## Lancer les tests

```bash
pytest tests/ -v
```

## Important — limite de cet environnement de production du code

Ce code a été **écrit et vérifié syntaxiquement** (`py_compile` sur tous les
fichiers), mais **n'a pas pu être exécuté avec un vrai serveur** ici car cet
environnement n'a pas d'accès réseau pour installer FastAPI/SQLAlchemy/etc.
Avant de considérer ce module comme définitivement validé, lancez vous-même
`pytest tests/ -v` sur votre machine ou en CI — les tests sont écrits et
prêts, il ne manque que l'exécution réelle avec les dépendances installées.

## Prochaine étape

Tapez **"suite"** pour que je produise le module suivant (ex. : réseau
social, marketplace, finance...). Il s'enregistrera dans `app/main.py`
exactement comme le module `ai_assistant`, ce qui garantit l'interconnexion
de tous les modules dans une seule et même plateforme.


## Modèles prêts à l'emploi (cartes de visite, carte d'étudiant, logo, flyer...)

Le script `scripts/seed_templates.py` insère de vrais modèles directement
publiés (carte de visite x2, carte d'étudiant, logo, flyer, post réseau
social) : les utilisateurs n'ont qu'à modifier le texte plutôt que de
partir d'une page blanche. Lancez-le une fois votre compte
super-administrateur créé :

```bash
python3 -m scripts.seed_templates
```

Un nouveau modèle peut ensuite être publié via
`POST /studio/templates/{id}/publish`, réservé au super-administrateur.
