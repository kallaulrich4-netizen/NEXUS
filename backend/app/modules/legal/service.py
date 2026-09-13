from duckduckgo_search import DDGS
from sqlalchemy.orm import Session

from app.modules.legal.models import LegalResource, ConsultationRequest
from app.modules.maps.models import Listing


class ResourceNotFoundError(Exception):
    """Levée quand une ressource juridique n'existe pas ou n'est pas publiée."""


class NotAuthorError(Exception):
    """Levée quand un utilisateur tente de modifier une ressource qui n'est pas la sienne."""


class LawyerListingNotFoundError(Exception):
    """Levée quand la fiche d'avocat référencée n'existe pas ou n'est pas de catégorie 'avocat'."""


class ConsultationNotFoundError(Exception):
    """Levée quand une demande de consultation n'existe pas ou n'est pas accessible à l'utilisateur."""


class InvalidConsultationTransitionError(Exception):
    """Levée quand un changement de statut de consultation n'est pas autorisé."""


class NotConsultationPartyError(Exception):
    """Levée quand un utilisateur n'est ni le client ni l'avocat concerné par la consultation."""


# --- Ressources juridiques ---

def submit_resource(db: Session, author_id: str, data) -> LegalResource:
    """
    Soumet une ressource. `is_reviewed` et `is_published` restent à False
    par défaut : AUCUN contenu juridique n'est visible publiquement sans
    validation, quel que soit son auteur.
    """
    resource = LegalResource(author_id=author_id, is_reviewed=False, is_published=False, **data.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def get_published_resource(db: Session, resource_id: str) -> LegalResource:
    resource = (
        db.query(LegalResource)
        .filter(LegalResource.id == resource_id, LegalResource.is_published.is_(True))
        .first()
    )
    if resource is None:
        raise ResourceNotFoundError("Ressource juridique introuvable ou non publiée.")
    return resource





def list_my_resources(db: Session, author_id: str) -> list[LegalResource]:
    """Un auteur voit toutes ses propres soumissions, publiées ou non."""
    return (
        db.query(LegalResource)
        .filter(LegalResource.author_id == author_id)
        .order_by(LegalResource.created_at.desc())
        .all()
    )


# --- Mises en relation avec un avocat ---def search_published_resources(db: Session, category: str = None, country: str = None, query_text: str = None, offset: int = 0, limit: int = 10):
    q = db.query(LegalResource).filter(LegalResource.is_published == True)
    if category:
        q = q.filter(LegalResource.category == category)
    if country:
        q = q.filter(LegalResource.jurisdiction_country == country)
    if query_text:
        like_pattern = f"%{query_text.strip()}%"
        q = q.filter(LegalResource.title.ilike(like_pattern) | LegalResource.summary.ilike(like_pattern))
    
    results = q.order_by(LegalResource.updated_at.desc()).offset(offset).limit(limit).all()
    
    # SI LA BASE DE DONNÉES EST VIDE : Fallback sur DuckDuckGo
    if not results:
        search_query = query_text or category or "droit civil"
        target_country = country or "Cameroun"
        return fetch_duckduckgo_legal_resources(query=search_query, country=target_country)
        
    return results

def create_consultation_request(db: Session, client_id: str, data) -> ConsultationRequest:
    lawyer_listing = (
        db.query(Listing)
        .filter(Listing.id == data.lawyer_listing_id, Listing.category == "avocat", Listing.is_active.is_(True))
        .first()
    )
    if lawyer_listing is None:
        raise LawyerListingNotFoundError(
            "Fiche d'avocat introuvable, inactive, ou n'appartenant pas à la catégorie 'avocat'."
        )

    request = ConsultationRequest(client_id=client_id, status="en_attente", **data.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def _get_consultation_for_party(db: Session, request_id: str, user_id: str) -> tuple[ConsultationRequest, bool]:
    """Retourne (demande, is_lawyer) si l'utilisateur est le client ou l'avocat concerné."""
    request = db.query(ConsultationRequest).filter(ConsultationRequest.id == request_id).first()
    if request is None:
        raise ConsultationNotFoundError("Demande de consultation introuvable.")

    if request.client_id == user_id:
        return request, False

    lawyer_listing = db.query(Listing).filter(Listing.id == request.lawyer_listing_id).first()
    if lawyer_listing is not None and lawyer_listing.owner_id == user_id:
        return request, True

    raise NotConsultationPartyError("Vous n'êtes pas partie à cette demande de consultation.")


def get_consultation_request(db: Session, request_id: str, user_id: str) -> ConsultationRequest:
    request, _ = _get_consultation_for_party(db, request_id, user_id)
    return request


def list_my_consultation_requests(db: Session, client_id: str) -> list[ConsultationRequest]:
    return (
        db.query(ConsultationRequest)
        .filter(ConsultationRequest.client_id == client_id)
        .order_by(ConsultationRequest.created_at.desc())
        .all()
    )


def list_incoming_consultation_requests(db: Session, lawyer_user_id: str) -> list[ConsultationRequest]:
    """Demandes reçues par un avocat, via ses fiches Cartographie de catégorie 'avocat'."""
    return (
        db.query(ConsultationRequest)
        .join(Listing, ConsultationRequest.lawyer_listing_id == Listing.id)
        .filter(Listing.owner_id == lawyer_user_id)
        .order_by(ConsultationRequest.created_at.desc())
        .all()
    )


_VALID_TRANSITIONS = {
    "en_attente": {"acceptee", "refusee", "annulee"},
    "acceptee": {"terminee", "annulee"},
    "refusee": set(),
    "terminee": set(),
    "annulee": set(),
}

# Seul l'avocat peut accepter/refuser/terminer ; seul le client peut annuler avant acceptation.
_LAWYER_ONLY_TRANSITIONS = {"acceptee", "refusee", "terminee"}
_CLIENT_ONLY_TRANSITIONS = {"annulee"}


def update_consultation_status(db: Session, request_id: str, user_id: str, new_status: str) -> ConsultationRequest:
    request, is_lawyer = _get_consultation_for_party(db, request_id, user_id)

    if new_status not in _VALID_TRANSITIONS.get(request.status, set()):
        raise InvalidConsultationTransitionError(
            f"Transition de statut invalide : « {request.status} » -> « {new_status} »."
        )

    if new_status in _LAWYER_ONLY_TRANSITIONS and not is_lawyer:
        raise NotConsultationPartyError("Seul l'avocat concerné peut effectuer cette action.")
    if new_status in _CLIENT_ONLY_TRANSITIONS and is_lawyer:
        raise NotConsultationPartyError("Seul le client peut annuler sa propre demande.")

    request.status = new_status
    db.commit()
    db.refresh(request)
    return request

def fetch_duckduckgo_legal_resources(query: str = "", country: str = "Cameroun"):
    search_term = f"{query} {country} droit loi".strip()
    results = []
    try:
        with DDGS() as ddgs:
            raw_results = ddgs.text(search_term, max_results=5)
            for item in raw_results:
                results.append(
                    {
                        "id": item.get("href"),
                        "title": item.get("title"),
                        "content": item.get("body"),
                        "summary": item.get("body"),
                        "source_url": item.get("href"),
                        "country": country,
                        "category": query or "Droit civil",
                        "is_published": True,
                    }
                )
    except Exception as e:
        print(f"Erreur DuckDuckGo: {e}")
    return results