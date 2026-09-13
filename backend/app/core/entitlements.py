"""
Vérification centrale de l'accès premium.

Un seul point de vérité pour savoir si un utilisateur a accès aux
fonctionnalités payantes (essai gratuit de 24h à l'inscription, puis
abonnement actif). Tous les modules payants (Studio créatif, et
d'autres à venir) importent `has_premium_access` plutôt que de
réimplémenter cette logique — évite les incohérences entre modules.

Le Réseau social n'utilise JAMAIS cette fonction : il reste
entièrement gratuit, conformément à la vision du projet.
"""
from datetime import datetime, timezone

from app.modules.auth.models import User


def has_premium_access(user: User) -> bool:
    if user.is_superuser:
        return True  # Accès premium illimité et permanent pour le(s) créateur(s) de la plateforme.

    now = datetime.now(timezone.utc)
    if user.trial_ends_at and user.trial_ends_at > now:
        return True
    if user.premium_until and user.premium_until > now:
        return True
    return False
