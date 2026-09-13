"""
Point d'entrée de Nexus.

Chaque nouveau module produit dans les prochaines étapes devra
simplement s'enregistrer ici avec `app.include_router(...)` pour
rejoindre la plateforme 15-en-1. C'est ce fichier qui, à terme,
matérialise l'interconnexion de tous les modules.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine

# Modules actifs de la plateforme
from app.modules.auth.router import router as auth_router
from app.modules.ai_assistant.router import router as ai_router
from app.modules.social.router import router as social_router
from app.modules.marketplace.router import router as marketplace_router
from app.modules.maps.router import router as maps_router
from app.modules.agriculture.router import router as agriculture_router
from app.modules.livestock.router import router as livestock_router
from app.modules.legal.router import router as legal_router
from app.modules.finance.router import router as finance_router
from app.modules.business.router import router as business_router
from app.modules.studio.router import router as studio_router
from app.modules.education.router import router as education_router
from app.modules.devtools.router import router as devtools_router
from app.modules.cybersecurity.router import router as cybersecurity_router
from app.modules.devops.router import router as devops_router
from app.modules.payments.router import router as payments_router

# Briques transversales (pas des modules métier — au même titre que
# rate_limit/entitlements/security) : notifications et journal d'activité.
from app.core.notifications_router import router as notifications_router
from app.core.audit_router import router as audit_router

settings = get_settings()

# La doc interactive (/docs, /redoc) expose le schéma complet de l'API :
# utile en développement, mais à ne pas laisser accessible publiquement en
# production sans restriction (reverse proxy, IP allowlist, etc.).
_is_prod = settings.environment == "production"

app = FastAPI(
    title=settings.app_name,
    description="Plateforme unifiée Nexus — un seul compte, un seul écosystème.",
    version="0.1.0",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

# En développement : tout est autorisé pour ne pas bloquer le travail local.
# En production : uniquement les domaines listés dans CORS_ALLOWED_ORIGINS
# (variable d'environnement). Si elle est vide, aucune origine n'est
# autorisée (fail-safe fermé) plutôt que d'ouvrir l'API par erreur.
_prod_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else _prod_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    """
    Ajoute des en-têtes de sécurité HTTP standards, absents par défaut
    dans la plupart des frameworks. Corrige API8:2023 "Security
    Misconfiguration" de l'OWASP API Security Top 10.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.on_event("startup")
def on_startup():
    # En développement uniquement : crée les tables si elles n'existent pas.
    # En production, utilisez Alembic (migrations) plutôt que create_all().
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["Système"])
def health_check():
    return {"status": "ok", "platform": settings.app_name}


# --- Enregistrement des modules de la plateforme Nexus ---
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(social_router)
app.include_router(marketplace_router)
app.include_router(maps_router)
app.include_router(agriculture_router)
app.include_router(livestock_router)
app.include_router(legal_router)
app.include_router(finance_router)
app.include_router(business_router)
app.include_router(studio_router)
app.include_router(education_router)
app.include_router(devtools_router)
app.include_router(cybersecurity_router)
app.include_router(devops_router)
app.include_router(payments_router)
app.include_router(notifications_router)
app.include_router(audit_router)
# Les 15 modules de contenu et le système de paiement transversal sont
# désormais tous enregistrés. Le module Réseau social n'utilise jamais
# ce système : il reste entièrement gratuit pour tous.
