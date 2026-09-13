"""
Script de départ (seed) : crée de vrais modèles prêts à l'emploi dans le
Studio créatif — carte de visite, carte d'étudiant, logo, flyer, post
réseau social — directement publiés, pour que les utilisateurs n'aient
qu'à modifier le texte plutôt que de partir d'une page blanche.

Usage :
    cd backend
    python3 -m scripts.seed_templates

Nécessite que INITIAL_SUPERUSER_EMAIL soit configuré et que ce compte
existe déjà (inscrivez-vous une première fois avec cet email avant de
lancer ce script) — c'est cet utilisateur qui devient l'auteur des modèles.
"""
import json
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.auth.models import User
from app.modules.studio.models import Template


def _text(x, y, width, height, content, font_size, color="#1a1a2e"):
    return {
        "type": "text", "x": x, "y": y, "width": width, "height": height,
        "content": content, "color": color, "fontSize": font_size, "rotation": 0,
    }


def _rect(x, y, width, height, color, rotation=0):
    return {
        "type": "rectangle", "x": x, "y": y, "width": width, "height": height,
        "backgroundColor": color, "rotation": rotation,
    }


TEMPLATES = [
    {
        "name": "Carte de visite — Classique bleu",
        "category": "carte_visite",
        "width": 1050, "height": 600,
        "is_premium": False,
        "elements": [
            _rect(0, 0, 1050, 600, "#0a0e1a"),
            _rect(0, 0, 16, 600, "#3b82f6"),
            _text(60, 80, 600, 60, "Votre Nom Complet", 36, "#ffffff"),
            _text(60, 150, 600, 40, "Votre Fonction / Métier", 20, "#8b93b0"),
            _text(60, 420, 500, 30, "+225 00 00 00 00", 18, "#e8ecf7"),
            _text(60, 460, 500, 30, "vous@exemple.com", 18, "#e8ecf7"),
            _text(60, 500, 500, 30, "www.votresite.com", 18, "#e8ecf7"),
        ],
    },
    {
        "name": "Carte de visite — Minimaliste clair",
        "category": "carte_visite",
        "width": 1050, "height": 600,
        "is_premium": False,
        "elements": [
            _rect(0, 0, 1050, 600, "#f5f5f5"),
            _text(60, 220, 700, 60, "Votre Nom Complet", 38, "#0a0e1a"),
            _text(60, 290, 700, 40, "Votre Fonction", 20, "#4b5563"),
            _rect(60, 350, 120, 4, "#3b82f6"),
            _text(60, 400, 500, 30, "contact@exemple.com  •  +225 00 00 00 00", 16, "#4b5563"),
        ],
    },
    {
        "name": "Carte d'étudiant — Standard",
        "category": "carte_etudiant",
        "width": 1013, "height": 638,
        "is_premium": False,
        "elements": [
            _rect(0, 0, 1013, 638, "#1e3a5c"),
            _rect(0, 0, 1013, 110, "#0a0e1a"),
            _text(40, 30, 500, 50, "NOM DE L'ÉTABLISSEMENT", 26, "#ffffff"),
            _rect(40, 150, 220, 280, "#ffffff"),
            _text(90, 260, 120, 30, "PHOTO", 16, "#94a3b8"),
            _text(300, 160, 600, 40, "Nom de l'étudiant", 28, "#ffffff"),
            _text(300, 210, 600, 35, "Prénom de l'étudiant", 24, "#e8ecf7"),
            _text(300, 280, 500, 30, "N° étudiant : 000000", 18, "#e8ecf7"),
            _text(300, 320, 500, 30, "Filière : ______________", 18, "#e8ecf7"),
            _text(300, 360, 500, 30, "Année académique : 2026-2027", 18, "#e8ecf7"),
            _text(40, 560, 500, 30, "Valable jusqu'au 31/08/2027", 14, "#94a3b8"),
        ],
    },
    {
        "name": "Logo — Monogramme dégradé",
        "category": "logo",
        "width": 500, "height": 500,
        "is_premium": True,
        "elements": [
            _rect(150, 150, 200, 200, "#3b82f6", 45),
            _text(150, 210, 200, 80, "AB", 64, "#ffffff"),
        ],
    },
    {
        "name": "Flyer — Événement",
        "category": "flyer",
        "width": 1080, "height": 1350,
        "is_premium": False,
        "elements": [
            _rect(0, 0, 1080, 1350, "#10152a"),
            _text(80, 120, 900, 100, "TITRE DE VOTRE ÉVÉNEMENT", 56, "#ffffff"),
            _text(80, 260, 900, 60, "Sous-titre ou accroche", 28, "#8b5cf6"),
            _rect(80, 900, 400, 4, "#3b82f6"),
            _text(80, 950, 800, 50, "Date : __ / __ / ____", 26, "#e8ecf7"),
            _text(80, 1010, 800, 50, "Lieu : ________________", 26, "#e8ecf7"),
        ],
    },
    {
        "name": "Post réseau social — Citation",
        "category": "post_reseau_social",
        "width": 1080, "height": 1080,
        "is_premium": False,
        "elements": [
            _rect(0, 0, 1080, 1080, "#0a0e1a"),
            _text(100, 400, 880, 300, "« Votre citation inspirante ici »", 44, "#ffffff"),
            _text(100, 750, 600, 40, "— Auteur de la citation", 22, "#8b93b0"),
        ],
    },
]


def main():
    settings = get_settings()
    if not settings.initial_superuser_email:
        print("ERREUR : INITIAL_SUPERUSER_EMAIL n'est pas configuré dans votre .env.")
        sys.exit(1)

    db = SessionLocal()
    try:
        author = db.query(User).filter(User.email == settings.initial_superuser_email.lower()).first()
        if author is None:
            print(
                f"ERREUR : aucun compte trouvé pour {settings.initial_superuser_email}. "
                "Inscrivez-vous une première fois avec cet email avant de lancer ce script."
            )
            sys.exit(1)

        created_count = 0
        for tpl in TEMPLATES:
            existing = db.query(Template).filter(Template.name == tpl["name"]).first()
            if existing:
                print(f"Déjà présent, ignoré : {tpl['name']}")
                continue

            template = Template(
                author_id=author.id,
                name=tpl["name"],
                category=tpl["category"],
                width=tpl["width"],
                height=tpl["height"],
                canvas_data=json.dumps({"elements": tpl["elements"]}),
                is_premium=tpl["is_premium"],
                is_published=True,
            )
            db.add(template)
            created_count += 1
            print(f"Créé : {tpl['name']}")

        db.commit()
        print(f"\n{created_count} modèle(s) créé(s) avec succès.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
