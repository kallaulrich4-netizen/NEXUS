"""
Schémas Pydantic : définissent précisément ce que l'API accepte en entrée
et renvoie en sortie. Ils empêchent, entre autres, qu'un mot de passe
haché soit un jour accidentellement renvoyé au client.
"""
import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    preferred_language: str = "fr"
    country: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("Le mot de passe doit contenir au moins 10 caractères.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule.")
        if not re.search(r"[0-9]", value):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
        return value

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le nom complet ne peut pas être vide.")
        return value.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    preferred_language: str
    country: str | None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileUpdate(BaseModel):
    """Mise à jour du profil utilisateur — utilisée par la page Paramètres."""
    full_name: str | None = None
    preferred_language: str | None = None
    country: str | None = None

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le nom complet ne peut pas être vide.")
        return cleaned


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 10 caractères.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Le nouveau mot de passe doit contenir au moins une majuscule.")
        if not re.search(r"[0-9]", value):
            raise ValueError("Le nouveau mot de passe doit contenir au moins un chiffre.")
        return value


class AdminUserUpdate(BaseModel):
    """Utilisé par le Centre d'administration pour activer/désactiver un compte ou changer son rôle."""
    is_active: bool | None = None
    is_superuser: bool | None = None


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    superusers: int
    new_users_last_30_days: int
