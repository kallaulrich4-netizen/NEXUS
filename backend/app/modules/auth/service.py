"""
Logique métier de l'authentification.

Séparer cette logique des routes (router.py) permet de la tester
directement, sans passer par HTTP, et de la réutiliser depuis d'autres
modules si besoin (ex: création d'un utilisateur système).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import UserRegister

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class EmailAlreadyExistsError(Exception):
    """Levée quand un email est déjà utilisé par un compte existant."""


class InvalidCredentialsError(Exception):
    """Levée quand l'email ou le mot de passe est incorrect."""


class AccountLockedError(Exception):
    """Levée quand un compte est temporairement verrouillé après trop d'échecs."""


class IncorrectPasswordError(Exception):
    """Levée quand le mot de passe actuel fourni pour un changement de mot de passe est incorrect."""


class UserNotFoundError(Exception):
    """Levée quand un utilisateur ciblé par une action d'administration n'existe pas."""


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def _promote_if_initial_superuser(user: User) -> None:
    """
    N'attribue le statut super-administrateur qu'à l'email exact défini
    dans la configuration serveur (`INITIAL_SUPERUSER_EMAIL`). Aucune
    requête utilisateur, aucun champ du formulaire d'inscription ne peut
    influencer ce statut : c'est uniquement une comparaison avec une
    variable d'environnement contrôlée par vous seul.

    Récupère les paramètres à chaque appel (plutôt qu'une variable liée
    à l'import du module) pour rester correct si la configuration est
    rechargée (tests automatisés, notamment).
    """
    current_settings = get_settings()
    if (
        current_settings.initial_superuser_email
        and user.email.lower() == current_settings.initial_superuser_email.lower()
        and not user.is_superuser
    ):
        user.is_superuser = True


def register_user(db: Session, data: UserRegister) -> User:
    """Crée un nouvel utilisateur. Lève EmailAlreadyExistsError si l'email existe déjà."""
    if get_user_by_email(db, data.email):
        raise EmailAlreadyExistsError(f"L'email {data.email} est déjà utilisé.")

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        preferred_language=data.preferred_language,
        country=data.country,
    )
    _promote_if_initial_superuser(user)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Vérifie les identifiants.

    Protection anti brute-force (OWASP API2:2023 - Broken Authentication) :
    après MAX_FAILED_ATTEMPTS échecs consécutifs, le compte est verrouillé
    pendant LOCKOUT_DURATION_MINUTES. C'est ce mécanisme qui manque dans
    beaucoup d'implémentations "maison" et qui permet les attaques par
    force brute ou credential stuffing sur les grandes plateformes.
    """
    user = get_user_by_email(db, email)
    if not user:
        raise InvalidCredentialsError("Email ou mot de passe incorrect.")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise AccountLockedError(
            f"Compte temporairement verrouillé suite à plusieurs échecs. "
            f"Réessayez après {user.locked_until.strftime('%H:%M UTC')}."
        )

    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            user.failed_login_attempts = 0
        db.commit()
        raise InvalidCredentialsError("Email ou mot de passe incorrect.")

    if not user.is_active:
        raise InvalidCredentialsError("Ce compte a été désactivé.")

    # Connexion réussie : on réinitialise le compteur d'échecs.
    if user.failed_login_attempts > 0 or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None

    _promote_if_initial_superuser(user)
    db.commit()

    return user


def update_profile(db: Session, user: User, data) -> User:
    """Met à jour les champs de profil modifiables — utilisé par la page Paramètres."""
    for key, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> User:
    """Change le mot de passe après vérification de l'ancien. Lève IncorrectPasswordError sinon."""
    if not verify_password(current_password, user.hashed_password):
        raise IncorrectPasswordError("Le mot de passe actuel est incorrect.")
    user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def deactivate_account(db: Session, user: User) -> None:
    """Désactive le compte de l'utilisateur (suppression douce, conservant l'historique des autres modules)."""
    user.is_active = False
    db.commit()


# --- Centre d'administration ---

def list_all_users(db: Session, limit: int = 200) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).limit(limit).all()


def admin_update_user(db: Session, target_user_id: str, data) -> User:
    user = get_user_by_id(db, target_user_id)
    if user is None:
        raise UserNotFoundError("Utilisateur introuvable.")
    for key, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def get_admin_stats(db: Session) -> dict:
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    superusers = db.query(User).filter(User.is_superuser.is_(True)).count()
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    new_users = db.query(User).filter(User.created_at >= thirty_days_ago).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "superusers": superusers,
        "new_users_last_30_days": new_users,
    }
