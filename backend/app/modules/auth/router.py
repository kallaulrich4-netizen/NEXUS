"""
Routes HTTP de l'authentification, et surtout : `get_current_user`.

`get_current_user` est la dépendance que TOUS les autres modules (IA,
finance, marketplace, droit...) importeront pour protéger leurs propres
routes. C'est le point d'entrée unique de sécurité de toute la plateforme.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core import notifications, audit
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    UserRegister, UserLogin, UserOut, TokenPair, RefreshRequest,
    UserProfileUpdate, PasswordChangeRequest, AdminUserUpdate, AdminStats,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dépendance de sécurité réutilisable partout dans Nexus.
    Exemple d'usage dans un autre module :
        @router.get("/mes-donnees")
        def route(user: User = Depends(get_current_user)): ...
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Dépendance de sécurité pour le Centre d'administration. Réutilisable
    par n'importe quel module qui a besoin de restreindre une route aux
    seuls administrateurs (ex: `Depends(require_superuser)`).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return current_user


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
def register(data: UserRegister, db: Session = Depends(get_db)):
    try:
        user = service.register_user(db, data)
    except service.EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    audit.log_action(
        db, user_id=user.id, action="creation", module="auth",
        description="Création du compte.", resource_type="user", resource_id=user.id,
    )
    notifications.notify(
        db, user_id=user.id, category="confirmation", module="auth",
        title="Bienvenue sur Nexus", link="/settings",
        message=f"Bonjour {user.full_name}, votre compte est prêt. Explorez les modules depuis le tableau de bord.",
    )
    return user


@router.post(
    "/login",
    response_model=TokenPair,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = service.authenticate_user(db, data.email, data.password)
    except service.AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc))
    except service.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    audit.log_action(db, user_id=user.id, action="connexion", module="auth", description="Connexion réussie.")

    return TokenPair(
        access_token=create_access_token(subject=user.id),
        refresh_token=create_refresh_token(subject=user.id),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton de rafraîchissement invalide.")

    user = service.get_user_by_id(db, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable ou inactif.")

    return TokenPair(
        access_token=create_access_token(subject=user.id),
        refresh_token=create_refresh_token(subject=user.id),
    )


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met à jour le profil de l'utilisateur connecté (nom, langue, pays) — utilisé par la page Paramètres."""
    return service.update_profile(db, current_user, data)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.change_password(db, current_user, data.current_password, data.new_password)
    except service.IncorrectPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    audit.log_action(db, user_id=current_user.id, action="modification", module="auth", description="Changement de mot de passe.")


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Désactive le compte (suppression douce) : l'utilisateur ne peut plus se
    connecter, mais l'historique dans les autres modules (agriculture,
    élevage, finance...) est conservé, conformément aux obligations légales
    de conservation de certaines données commerciales/financières.
    """
    service.deactivate_account(db, current_user)
    audit.log_action(db, user_id=current_user.id, action="suppression", module="auth", description="Désactivation du compte.")


# --- Centre d'administration (réservé aux superutilisateurs) ---

@router.get("/admin/users", response_model=list[UserOut])
def admin_list_users(
    admin: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    return service.list_all_users(db)


@router.patch("/admin/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: str,
    data: AdminUserUpdate,
    admin: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    try:
        return service.admin_update_user(db, user_id, data)
    except service.UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/admin/stats", response_model=AdminStats)
def admin_get_stats(
    admin: User = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    return service.get_admin_stats(db)
