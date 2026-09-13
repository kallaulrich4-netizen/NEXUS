"""
Configuration centrale de Nexus.

Toute la configuration passe par des variables d'environnement (12-factor app).
Rien n'est codé en dur : ni secrets, ni URLs, ni clés.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Identité de la plateforme
    app_name: str = "Nexus Platform"
    environment: str = "development"  # development | staging | production
    debug: bool = False

    # Base de données
    database_url: str = "sqlite:///./nexus.db"

    # Sécurité / Authentification
    secret_key: str  # OBLIGATOIRE : doit venir de l'environnement, jamais d'une valeur par défaut
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # Module IA (Nexus AI)
    ai_provider_api_key: str | None = None
    ai_model: str = "claude-sonnet-5"
    ai_max_tokens_per_request: int = 4000
    ai_rate_limit_per_minute: int = 20
    # Option gratuite pour tester Nexus AI sans clé payante : Ollama fait
    # tourner un modèle directement sur votre ordinateur (aucun coût,
    # aucune donnée envoyée à l'extérieur). Mettez AI_ENGINE=ollama pour
    # l'utiliser à la place d'Anthropic, même si AI_PROVIDER_API_KEY est
    # aussi renseigné. Voir chapitre 12 du manuel.
    ai_engine: str = "auto"  # "auto" | "anthropic" | "ollama" | "echo"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Stockage local des fichiers médias du Studio (images/vidéos importées
    # par l'utilisateur, et vidéos rendues). En production, un dossier sur
    # un disque persistant (ou monté depuis un stockage réseau) ; voir
    # chapitre 12 du manuel pour l'option d'un vrai stockage objet (S3/GCS).
    media_storage_path: str = "./media"
    media_max_upload_mb: int = 100

    # Domaines autorisés à appeler l'API depuis un navigateur (CORS), séparés
    # par des virgules, ex: "https://nexus-platform.com,https://app.nexus-platform.com"
    # Obligatoire en production : sans valeur, aucune origine n'est autorisée
    # (fail-safe fermé) plutôt que d'autoriser tout le monde par erreur.
    cors_allowed_origins: str = ""

    # Compte créateur : l'email défini ici (et UNIQUEMENT celui-ci)
    # obtient automatiquement le statut super-administrateur (accès
    # premium illimité à vie) lors de son inscription ou de sa
    # prochaine connexion. Configurez-le dans votre .env réel avant le
    # déploiement, jamais dans le code source.
    initial_superuser_email: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """
    Retourne une instance unique (singleton) des paramètres.
    Le cache évite de relire le fichier .env à chaque appel.
    """
    return Settings()
