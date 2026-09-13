"""
Environnement Alembic pour Nexus.

Point important : Nexus a UNE seule base de données partagée par les 15
modules (voir app/core/database.py). Ce fichier importe donc les modèles
de TOUS les modules pour que `Base.metadata` — utilisée par la génération
automatique de migrations — les connaisse tous. Sans ces imports,
`alembic revision --autogenerate` ne verrait que les tables déjà
importées ailleurs et manquerait des tables entières.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base

# Modèles de chaque module — l'import seul suffit à les enregistrer
# dans Base.metadata, même si `*` n'est pas utilisé directement ici.
from app.modules.agriculture import models as agriculture_models  # noqa: F401
from app.modules.ai_assistant import models as ai_assistant_models  # noqa: F401
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.business import models as business_models  # noqa: F401
from app.modules.cybersecurity import models as cybersecurity_models  # noqa: F401
from app.modules.devops import models as devops_models  # noqa: F401
from app.modules.devtools import models as devtools_models  # noqa: F401
from app.modules.education import models as education_models  # noqa: F401
from app.modules.finance import models as finance_models  # noqa: F401
from app.modules.legal import models as legal_models  # noqa: F401
from app.modules.livestock import models as livestock_models  # noqa: F401
from app.modules.maps import models as maps_models  # noqa: F401
from app.modules.marketplace import models as marketplace_models  # noqa: F401
from app.modules.payments import models as payments_models  # noqa: F401
from app.modules.social import models as social_models  # noqa: F401
from app.modules.studio import models as studio_models  # noqa: F401

# Briques transversales (pas des modules métier, mais elles ont des tables).
from app.core import notification_models  # noqa: F401
from app.core import audit_models  # noqa: F401

config = context.config

# La véritable URL de connexion vient TOUJOURS de DATABASE_URL (.env),
# jamais du fichier alembic.ini — même principe que le reste de Nexus :
# rien de sensible ou d'environnement-spécifique en dur dans un fichier versionné.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
