"""
Limiteur de débit (rate limiting), commun à toute la plateforme.

Corrige API4:2023 "Unrestricted Resource Consumption" de l'OWASP API
Security Top 10 : sans limite, un attaquant peut spammer une route
(connexion, like, abonnement...) à volonté — brute-force, déni de
service, ou abus de logique métier (ex: script qui like massivement
pour manipuler un algorithme de recommandation).

Le compte super-administrateur (créateur de la plateforme, voir
`app/core/entitlements.py`) est exempté sur les routes authentifiées :
son jeton est vérifié directement ici, sans dépendre du reste de la
chaîne d'authentification, pour rester une vérification légère.

Implémentation "sliding window" en mémoire, suffisante pour un seul
processus / le développement. En production avec plusieurs instances
du serveur, remplacez le stockage interne par Redis (ex: bibliothèque
`slowapi` + backend Redis) pour que la limite soit partagée entre
toutes les instances.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        window = self._hits[key]

        while window and window[0] <= now - window_seconds:
            window.popleft()

        if len(window) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de requêtes. Veuillez réessayer dans quelques instants.",
            )
        window.append(now)


_limiter = InMemoryRateLimiter()


def _is_superuser_request(request: Request) -> bool:
    """
    Vérification légère et autonome (pas de Depends imbriqué) : décode le
    jeton s'il est présent et regarde si le compte est super-administrateur.
    Toute erreur (jeton absent, invalide, utilisateur introuvable) est
    traitée comme "non exempté" — jamais comme une erreur qui bloquerait
    la requête, le rate limiting doit rester silencieusement sûr par défaut.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    try:
        from app.core.security import decode_token
        from app.core.database import SessionLocal
        from app.modules.auth.models import User

        payload = decode_token(auth_header.removeprefix("Bearer "))
        if not payload or payload.get("type") != "access":
            return False

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == payload.get("sub")).first()
            return bool(user and user.is_superuser)
        finally:
            db.close()
    except Exception:
        return False


def rate_limit(max_requests: int, window_seconds: int):
    """
    Dépendance FastAPI à ajouter sur une route sensible :
        @router.post("/login", dependencies=[Depends(rate_limit(5, 60))])
    Limite par adresse IP + route. Le super-administrateur en est exempté.
    """

    def dependency(request: Request) -> None:
        if _is_superuser_request(request):
            return
        client_ip = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client_ip}"
        _limiter.check(key, max_requests, window_seconds)

    return dependency
