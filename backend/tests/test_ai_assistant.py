"""
Tests du module Nexus AI. Nécessitent : pip install -r requirements.txt
Lancer avec : pytest tests/ -v
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

TEST_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=TEST_ENGINE)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _register_and_login() -> str:
    user = {
        "email": "amina@example.com",
        "password": "MotDePasse123",
        "full_name": "Amina Diallo",
        "preferred_language": "fr",
    }
    client.post("/auth/register", json=user)
    response = client.post("/auth/login", json={"email": user["email"], "password": user["password"]})
    return response.json()["access_token"]


def test_send_message_requires_authentication():
    response = client.post("/ai/messages", json={"content": "Bonjour"})
    assert response.status_code == 401


def test_send_message_creates_conversation():
    token = _register_and_login()
    response = client.post(
        "/ai/messages",
        json={"content": "Bonjour Nexus"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_message"]["content"] == "Bonjour Nexus"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["conversation_id"]


def test_send_message_rejects_empty_content():
    token = _register_and_login()
    response = client.post(
        "/ai/messages", json={"content": "   "}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


def test_conversation_persists_across_messages():
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/ai/messages", json={"content": "Premier message"}, headers=headers)
    conversation_id = first.json()["conversation_id"]

    client.post(
        "/ai/messages",
        json={"content": "Deuxième message", "conversation_id": conversation_id},
        headers=headers,
    )

    detail = client.get(f"/ai/conversations/{conversation_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 4  # 2 messages utilisateur + 2 réponses assistant


def test_cannot_access_another_users_conversation():
    token_a = _register_and_login()
    first = client.post(
        "/ai/messages", json={"content": "Message privé"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    conversation_id = first.json()["conversation_id"]

    user_b = {
        "email": "youssef@example.com",
        "password": "AutreMotDePasse1",
        "full_name": "Youssef Alaoui",
    }
    client.post("/auth/register", json=user_b)
    login_b = client.post("/auth/login", json={"email": user_b["email"], "password": user_b["password"]})
    token_b = login_b.json()["access_token"]

    response = client.get(
        f"/ai/conversations/{conversation_id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404


# --- Tests du moteur d'IA réel (AnthropicProvider), ajoutés lors de son
# branchement en juillet 2026. Aucun appel réseau réel n'est fait ici :
# httpx.post est simulé (monkeypatch) pour rester rapide et déterministe.

class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("erreur simulée", request=None, response=self)

    def json(self):
        return self._json_data


def test_get_ai_provider_returns_echo_without_api_key(monkeypatch):
    from app.core.config import get_settings
    from app.modules.ai_assistant.provider import get_ai_provider, EchoProvider

    monkeypatch.delenv("AI_PROVIDER_API_KEY", raising=False)
    get_settings.cache_clear()
    assert isinstance(get_ai_provider(), EchoProvider)
    get_settings.cache_clear()


def test_get_ai_provider_returns_anthropic_with_api_key(monkeypatch):
    from app.core.config import get_settings
    from app.modules.ai_assistant.provider import get_ai_provider, AnthropicProvider

    monkeypatch.setenv("AI_PROVIDER_API_KEY", "sk-ant-test-fake-key")
    get_settings.cache_clear()
    provider = get_ai_provider()
    assert isinstance(provider, AnthropicProvider)
    get_settings.cache_clear()
    monkeypatch.delenv("AI_PROVIDER_API_KEY", raising=False)
    get_settings.cache_clear()


def test_anthropic_provider_parses_successful_reply(monkeypatch):
    import httpx as httpx_module
    from app.modules.ai_assistant.provider import AnthropicProvider

    def fake_post(url, headers, json, timeout):
        assert url == "https://api.anthropic.com/v1/messages"
        assert headers["x-api-key"] == "fake-key"
        assert json["messages"][-1] == {"role": "user", "content": "Bonjour"}
        return _FakeResponse({"content": [{"type": "text", "text": "Bonjour ! Comment puis-je vous aider ?"}]})

    monkeypatch.setattr(httpx_module, "post", fake_post)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", max_tokens=1000)
    reply = provider.generate_reply([{"role": "user", "content": "Bonjour"}], user_language="fr")
    assert reply == "Bonjour ! Comment puis-je vous aider ?"


def test_anthropic_provider_falls_back_on_network_error(monkeypatch):
    import httpx as httpx_module
    from app.modules.ai_assistant.provider import AnthropicProvider

    def fake_post(*args, **kwargs):
        raise httpx_module.RequestError("panne réseau simulée", request=None)

    monkeypatch.setattr(httpx_module, "post", fake_post)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", max_tokens=1000)
    reply = provider.generate_reply([{"role": "user", "content": "Bonjour"}], user_language="fr")
    assert "momentanément indisponible" in reply


def test_anthropic_provider_falls_back_on_timeout(monkeypatch):
    import httpx as httpx_module
    from app.modules.ai_assistant.provider import AnthropicProvider

    def fake_post(*args, **kwargs):
        raise httpx_module.TimeoutException("délai dépassé simulé", request=None)

    monkeypatch.setattr(httpx_module, "post", fake_post)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", max_tokens=1000)
    reply = provider.generate_reply([{"role": "user", "content": "Bonjour"}], user_language="en")
    assert "temporarily unavailable" in reply


def test_anthropic_provider_falls_back_on_http_error(monkeypatch):
    import httpx as httpx_module
    from app.modules.ai_assistant.provider import AnthropicProvider

    def fake_post(*args, **kwargs):
        return _FakeResponse({"error": {"message": "clé invalide simulée"}}, status_code=401)

    monkeypatch.setattr(httpx_module, "post", fake_post)
    provider = AnthropicProvider(api_key="mauvaise-cle", model="claude-sonnet-5", max_tokens=1000)
    reply = provider.generate_reply([{"role": "user", "content": "Bonjour"}], user_language="fr")
    assert "momentanément indisponible" in reply


# --- Tests de l'option gratuite OllamaProvider (modèle local, sans clé) ---

def test_ollama_provider_parses_successful_reply(monkeypatch):
    import httpx as httpx_module
    from app.modules.ai_assistant.provider import OllamaProvider

    def fake_post(url, json, timeout):
        assert url == "http://localhost:11434/api/chat"
        assert json["model"] == "llama3.2"
        assert json["messages"][0]["role"] == "system"  # instructions Nexus AI en premier
        assert json["messages"][-1] == {"role": "user", "content": "Bonjour"}
        return _FakeResponse({"message": {"role": "assistant", "content": "Bonjour depuis Ollama !"}})

    monkeypatch.setattr(httpx_module, "post", fake_post)
    provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2")
    reply = provider.generate_reply([{"role": "user", "content": "Bonjour"}], user_language="fr")
    assert reply == "Bonjour depuis Ollama !"


def test_ollama_provider_falls_back_when_not_running(monkeypatch):
    import httpx as httpx_module
    from app.modules.ai_assistant.provider import OllamaProvider

    def fake_post(*args, **kwargs):
        # Cas réel le plus fréquent : Ollama n'est pas démarré sur la machine.
        raise httpx_module.RequestError("connexion refusée simulée", request=None)

    monkeypatch.setattr(httpx_module, "post", fake_post)
    provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2")
    reply = provider.generate_reply([{"role": "user", "content": "Bonjour"}], user_language="fr")
    assert "momentanément indisponible" in reply


def test_get_ai_provider_engine_selection(monkeypatch):
    from app.core.config import get_settings
    from app.modules.ai_assistant.provider import get_ai_provider, EchoProvider, AnthropicProvider, OllamaProvider

    monkeypatch.setenv("AI_ENGINE", "ollama")
    get_settings.cache_clear()
    assert isinstance(get_ai_provider(), OllamaProvider)

    monkeypatch.setenv("AI_ENGINE", "echo")
    monkeypatch.setenv("AI_PROVIDER_API_KEY", "sk-ant-test-fake-key")
    get_settings.cache_clear()
    assert isinstance(get_ai_provider(), EchoProvider)  # "echo" force le mode démo même avec une clé

    monkeypatch.setenv("AI_ENGINE", "anthropic")
    get_settings.cache_clear()
    assert isinstance(get_ai_provider(), AnthropicProvider)

    monkeypatch.delenv("AI_ENGINE", raising=False)
    monkeypatch.delenv("AI_PROVIDER_API_KEY", raising=False)
    get_settings.cache_clear()
