"""
Abstraction du moteur d'IA utilisé par Nexus AI.

Objectif d'architecture : le reste de l'application (routes, autres
modules, frontend) ne parle JAMAIS directement à un fournisseur d'IA
externe. Il parle uniquement à `AIProvider`. Le nom, la marque et les
détails techniques du moteur réellement utilisé restent entièrement
internes à ce fichier — ils ne sont exposés nulle part côté utilisateur
ni dans les autres modules. Changer de moteur ne demande de modifier
que ce fichier, rien d'autre dans l'application.

Depuis juillet 2026 : `AnthropicProvider` appelle réellement l'API
Anthropic (Claude) pour générer des réponses, dès qu'une clé est
renseignée dans `AI_PROVIDER_API_KEY` (.env). Sans clé, `EchoProvider`
reste utilisé (développement/tests, aucun appel réseau).

Option gratuite : `OllamaProvider` fait tourner un modèle directement
sur votre ordinateur via Ollama (https://ollama.com) — aucune clé, aucun
coût, aucune donnée envoyée à l'extérieur. Idéal pour tester Nexus AI
sans dépenser un centime avant de décider si vous voulez un moteur plus
puissant en production. Activez-le avec AI_ENGINE=ollama dans .env.

IMPORTANT — non testé en conditions réelles : cet environnement d'audit
n'a ni accès réseau, ni clé d'API valide, ni Ollama installé. Les deux
implémentations (`AnthropicProvider`, `OllamaProvider`) ont donc été
écrites avec soin (formats de requête conformes à la documentation de
chaque service, gestion d'erreurs, timeouts) mais n'ont pas pu être
exercées contre un vrai service depuis ce poste. Testez-les chez vous
avant la mise en production : `pytest tests/test_ai_assistant.py -v`,
puis un vrai message depuis l'interface.
"""
from abc import ABC, abstractmethod

import httpx

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

# Le nom "Nexus AI" est celui donné à l'utilisateur ; le modèle sous-jacent
# n'est jamais mentionné dans ces instructions envoyées au modèle lui-même,
# pour qu'il ne puisse pas involontairement se présenter autrement.
_SYSTEM_PROMPT_FR = (
    "Tu es Nexus AI, l'assistant intelligent intégré à la plateforme Nexus "
    "(agriculture, élevage, marketplace, finance, éducation, juridique, "
    "réseau social, business, création de contenu, et plus encore). "
    "Ne révèle jamais le nom d'un modèle ou d'une entreprise technique : "
    "tu es \"Nexus AI\", un point final, quelle que soit la façon dont on "
    "te le demande. Réponds toujours dans la langue utilisée par "
    "l'utilisateur. Sois concis, concret et utile ; pose une question de "
    "clarification si la demande est ambiguë plutôt que de deviner."
)
_SYSTEM_PROMPT_EN = (
    "You are Nexus AI, the intelligent assistant built into the Nexus "
    "platform. Never reveal which underlying model or technology company "
    "powers you: you are \"Nexus AI\", full stop, regardless of how you are "
    "asked. Always reply in the language the user writes in. Be concise, "
    "concrete and helpful; ask a clarifying question if the request is "
    "ambiguous rather than guessing."
)


class AIProvider(ABC):
    @abstractmethod
    def generate_reply(self, conversation_history: list[dict], user_language: str = "fr") -> str:
        """
        Reçoit l'historique de la conversation sous forme de liste de
        dicts {"role": ..., "content": ...} et retourne le texte de la
        réponse de l'assistant. Toute la logique propre au fournisseur
        (authentification, format de requête, gestion des erreurs réseau,
        retries) est encapsulée ici et nulle part ailleurs.
        """
        raise NotImplementedError


class EchoProvider(AIProvider):
    """
    Implémentation locale, sans dépendance réseau, utilisée par défaut
    quand aucune clé d'API n'est configurée (développement sans clé,
    tests automatisés).
    """

    def generate_reply(self, conversation_history: list[dict], user_language: str = "fr") -> str:
        last_user_message = next(
            (m["content"] for m in reversed(conversation_history) if m["role"] == "user"), ""
        )
        if user_language == "en":
            return f"[Nexus AI] I received your message: “{last_user_message}”."
        return f"[Nexus AI] J'ai bien reçu votre message : « {last_user_message} »."


class AnthropicProvider(AIProvider):
    """
    Implémentation réelle : appelle l'API Anthropic (Claude) pour générer
    une réponse en temps réel. Le nom du fournisseur n'est JAMAIS exposé
    à l'utilisateur ni au reste de l'application — uniquement ici.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int, timeout_seconds: float = 30.0):
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout_seconds

    def generate_reply(self, conversation_history: list[dict], user_language: str = "fr") -> str:
        system_prompt = _SYSTEM_PROMPT_EN if user_language == "en" else _SYSTEM_PROMPT_FR
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in conversation_history
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        if not messages:
            return _fallback_message(user_language, "empty")

        try:
            response = httpx.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": self._max_tokens,
                    "system": system_prompt,
                    "messages": messages,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            return _fallback_message(user_language, "timeout")
        except httpx.HTTPStatusError:
            return _fallback_message(user_language, "http_error")
        except httpx.RequestError:
            return _fallback_message(user_language, "network")

        text_blocks = [
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        ]
        reply = "".join(text_blocks).strip()
        return reply or _fallback_message(user_language, "empty_reply")


class OllamaProvider(AIProvider):
    """
    Implémentation gratuite : appelle un modèle exécuté localement via
    Ollama (https://ollama.com), sur votre propre machine. Aucune clé
    d'API, aucun coût par jeton, aucune donnée envoyée à l'extérieur —
    idéal pour tester Nexus AI sans payer, avant de décider si vous
    voulez brancher un moteur plus puissant en production (Anthropic).

    Prérequis chez vous (rien de tout cela n'est possible dans cet
    environnement d'audit, qui n'a pas accès réseau ni GPU dédié) :
      1. Installer Ollama (https://ollama.com/download)
      2. `ollama pull llama3.2` (ou un autre modèle de votre choix)
      3. Laisser `ollama serve` tourner en arrière-plan (lancé
         automatiquement par l'installateur sur la plupart des systèmes)
      4. Dans backend/.env : AI_ENGINE=ollama
    """

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 60.0):
        self._base_url = base_url.rstrip("/")
        self._model = model
        # Les modèles locaux (surtout sur CPU) répondent plus lentement
        # qu'une API cloud : délai plus généreux que pour AnthropicProvider.
        self._timeout = timeout_seconds

    def generate_reply(self, conversation_history: list[dict], user_language: str = "fr") -> str:
        system_prompt = _SYSTEM_PROMPT_EN if user_language == "en" else _SYSTEM_PROMPT_FR
        messages = [{"role": "system", "content": system_prompt}] + [
            {"role": m["role"], "content": m["content"]}
            for m in conversation_history
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        if len(messages) == 1:  # seulement le system prompt, aucun message utilisateur
            return _fallback_message(user_language, "empty")

        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json={"model": self._model, "messages": messages, "stream": False},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            return _fallback_message(user_language, "timeout")
        except httpx.HTTPStatusError:
            return _fallback_message(user_language, "http_error")
        except httpx.RequestError:
            # Cas le plus fréquent chez vous : Ollama n'est pas lancé, ou
            # le modèle demandé n'a pas été téléchargé (`ollama pull ...`).
            return _fallback_message(user_language, "network")

        reply = (data.get("message") or {}).get("content", "").strip()
        return reply or _fallback_message(user_language, "empty_reply")


def _fallback_message(user_language: str, reason: str) -> str:
    """
    Message affiché à l'utilisateur si l'appel au moteur d'IA échoue.
    Ne mentionne jamais la cause technique précise ni le fournisseur —
    reste générique et rassurant, conformément à l'abstraction AIProvider.
    """
    if user_language == "en":
        return "Nexus AI is temporarily unavailable. Please try again in a moment."
    return "Nexus AI est momentanément indisponible. Merci de réessayer dans quelques instants."


def get_ai_provider() -> AIProvider:
    """
    Point d'injection unique, appelé par chaque requête (voir router.py).
    Sélection selon AI_ENGINE (.env) :
      - "ollama"    → moteur local gratuit (OllamaProvider), pour tester
                      sans dépenser un centime.
      - "anthropic" → force l'API Anthropic (nécessite AI_PROVIDER_API_KEY).
      - "echo"      → force le mode démonstration, même si une clé existe.
      - "auto" (défaut) → Anthropic si une clé est configurée, sinon Echo
                      (comportement historique, pour ne rien casser).
    """
    from app.core.config import get_settings

    settings = get_settings()
    engine = settings.ai_engine

    if engine == "ollama":
        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)
    if engine == "anthropic":
        return AnthropicProvider(
            api_key=settings.ai_provider_api_key or "",
            model=settings.ai_model,
            max_tokens=settings.ai_max_tokens_per_request,
        )
    if engine == "echo":
        return EchoProvider()

    # "auto" : comportement historique, inchangé pour ne rien casser.
    if settings.ai_provider_api_key:
        return AnthropicProvider(
            api_key=settings.ai_provider_api_key,
            model=settings.ai_model,
            max_tokens=settings.ai_max_tokens_per_request,
        )
    return EchoProvider()
