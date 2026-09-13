"""
Sécurité centrale de Nexus : hachage des mots de passe et jetons JWT.

C'est CE module que tous les autres modules (finance, droit, entreprise...)
utiliseront pour vérifier qu'un utilisateur est bien authentifié avant de
lui donner accès à leurs données. Un seul compte, un seul système de
sécurité pour toute la plateforme.
"""
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hache un mot de passe en clair. Ne jamais stocker un mot de passe en clair."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie qu'un mot de passe en clair correspond au hash stocké."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Crée un jeton JWT de courte durée (session active).
    `subject` est généralement l'identifiant unique de l'utilisateur.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    """Crée un jeton JWT de longue durée, utilisé pour renouveler la session."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    """Décode et valide un jeton. Retourne None si invalide ou expiré."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except PyJWTError:
        return None
