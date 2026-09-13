"""
Couche d'accès à la base de données, commune à TOUS les modules de Nexus.

Chaque module (auth, ai_assistant, finance, agriculture, ...) importera
`Base` pour définir ses tables, et `get_db` pour obtenir une session.
C'est ce fichier qui garantit que les 15 modules parlent à la même base
de données et peuvent donc être interconnectés.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe de base commune à tous les modèles de tous les modules."""
    pass


def get_db():
    """
    Dépendance FastAPI : fournit une session DB à une requête,
    puis la ferme systématiquement, même en cas d'erreur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
