"""
Abstraction du fournisseur de génération vidéo par IA.

Même principe que `app/modules/ai_assistant/provider.py` : le reste de
l'application ne parle jamais directement à un fournisseur externe. En
production, `RealAiVideoProvider.submit` enverrait le prompt à un vrai
service (Google Veo, Runway, Pika, etc.) via son API, avec la clé stockée
uniquement dans les variables d'environnement, puis interrogerait le
statut du job jusqu'à obtenir l'URL de la vidéo finale.

Aucun service de ce type n'étant accessible depuis cet environnement de
développement (pas d'accès réseau, pas de clé d'API), l'implémentation
par défaut place honnêtement le job en attente plutôt que de simuler un
faux résultat qui induirait l'utilisateur en erreur.
"""
from abc import ABC, abstractmethod


class AiVideoProvider(ABC):
    @abstractmethod
    def submit(self, prompt: str, style: str, duration_seconds: int, resolution: str) -> dict:
        """
        Soumet une demande de génération. Retourne un dict avec au moins
        {"status": ..., "result_url": ... | None, "error_message": ... | None}.
        """
        raise NotImplementedError


class PendingAiVideoProvider(AiVideoProvider):
    """
    Provider par défaut : place la demande en attente. Ne prétend jamais
    avoir généré une vidéo qui n'existe pas.
    """

    def submit(self, prompt: str, style: str, duration_seconds: int, resolution: str) -> dict:
        return {
            "status": "en_attente",
            "result_url": None,
            "error_message": (
                "Aucun fournisseur de génération vidéo par IA n'est configuré en production. "
                "Branchez une implémentation réelle (Veo, Runway, Pika...) dans ce fichier."
            ),
        }


def get_ai_video_provider() -> AiVideoProvider:
    return PendingAiVideoProvider()
