from collections import defaultdict

from sqlalchemy.orm import Session

from app.modules.livestock.models import (
    Herd, HealthEvent, ProductionRecord,
    Animal, AnimalHealthRecord, WeightRecord, ReproductionRecord, FeedPlan,
)
from app.modules.livestock import feed_service


class HerdNotFoundError(Exception):
    """Levée quand un troupeau n'existe pas ou n'appartient pas à l'utilisateur."""


class AnimalNotFoundError(Exception):
    """Levée quand un animal n'existe pas ou n'appartient pas à l'utilisateur."""


def create_herd(db: Session, owner_id: str, data) -> Herd:
    herd = Herd(owner_id=owner_id, **data.model_dump())
    db.add(herd)
    db.commit()
    db.refresh(herd)
    return herd


def get_herd(db: Session, herd_id: str, owner_id: str) -> Herd:
    herd = db.query(Herd).filter(Herd.id == herd_id, Herd.owner_id == owner_id).first()
    if herd is None:
        raise HerdNotFoundError("Troupeau introuvable.")
    return herd


def list_herds(db: Session, owner_id: str) -> list[Herd]:
    return db.query(Herd).filter(Herd.owner_id == owner_id).order_by(Herd.created_at.desc()).all()


def update_herd(db: Session, herd_id: str, owner_id: str, data) -> Herd:
    herd = get_herd(db, herd_id, owner_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(herd, key, value)
    db.commit()
    db.refresh(herd)
    return herd


def delete_herd(db: Session, herd_id: str, owner_id: str) -> None:
    herd = get_herd(db, herd_id, owner_id)
    db.delete(herd)
    db.commit()


def add_health_event(db: Session, herd_id: str, owner_id: str, data) -> HealthEvent:
    """
    Ajoute un événement sanitaire et ajuste l'effectif du troupeau en
    conséquence (ex: +3 pour une naissance triple, -1 pour un décès).
    """
    herd = get_herd(db, herd_id, owner_id)

    event = HealthEvent(herd_id=herd_id, **data.model_dump())
    db.add(event)

    new_count = herd.current_count + data.count_change
    herd.current_count = max(new_count, 0)  # l'effectif ne peut jamais devenir négatif

    db.commit()
    db.refresh(event)
    return event


def list_health_events(db: Session, herd_id: str, owner_id: str) -> list[HealthEvent]:
    get_herd(db, herd_id, owner_id)
    return (
        db.query(HealthEvent)
        .filter(HealthEvent.herd_id == herd_id)
        .order_by(HealthEvent.event_date.desc())
        .all()
    )


def add_production_record(db: Session, herd_id: str, owner_id: str, data) -> ProductionRecord:
    get_herd(db, herd_id, owner_id)
    record = ProductionRecord(herd_id=herd_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_production_records(db: Session, herd_id: str, owner_id: str) -> list[ProductionRecord]:
    get_herd(db, herd_id, owner_id)
    return (
        db.query(ProductionRecord)
        .filter(ProductionRecord.herd_id == herd_id)
        .order_by(ProductionRecord.record_date.desc())
        .all()
    )


def get_herd_summary(db: Session, herd_id: str, owner_id: str) -> dict:
    herd = get_herd(db, herd_id, owner_id)

    health_events = db.query(HealthEvent).filter(HealthEvent.herd_id == herd_id).all()
    total_health_cost = sum(e.cost_amount for e in health_events if e.cost_amount is not None)

    production_records = db.query(ProductionRecord).filter(ProductionRecord.herd_id == herd_id).all()
    total_production_by_type: dict[str, float] = defaultdict(float)
    for record in production_records:
        total_production_by_type[record.product_type] += record.quantity

    return {
        "herd_id": herd.id,
        "herd_name": herd.name,
        "current_count": herd.current_count,
        "total_health_events": len(health_events),
        "total_health_cost": total_health_cost,
        "total_production_by_type": dict(total_production_by_type),
    }


# ============================================================================
# ÉLEVAGE V2 — Fiche individuelle
# ============================================================================

# --- Animaux ---

def create_animal(db: Session, herd_id: str, owner_id: str, data) -> Animal:
    get_herd(db, herd_id, owner_id)  # vérifie que le troupeau appartient bien à l'utilisateur
    if data.parent_id:
        _get_animal_for_owner(db, data.parent_id, owner_id)  # vérifie que le parent existe et appartient au même owner
    animal = Animal(herd_id=herd_id, **data.model_dump())
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return animal


def _get_animal_for_owner(db: Session, animal_id: str, owner_id: str) -> Animal:
    animal = (
        db.query(Animal)
        .join(Herd)
        .filter(Animal.id == animal_id, Herd.owner_id == owner_id)
        .first()
    )
    if animal is None:
        raise AnimalNotFoundError("Animal introuvable.")
    return animal


def get_animal(db: Session, animal_id: str, owner_id: str) -> Animal:
    return _get_animal_for_owner(db, animal_id, owner_id)


def list_animals(db: Session, herd_id: str, owner_id: str) -> list[Animal]:
    get_herd(db, herd_id, owner_id)
    return db.query(Animal).filter(Animal.herd_id == herd_id).order_by(Animal.created_at.desc()).all()


def update_animal(db: Session, animal_id: str, owner_id: str, data) -> Animal:
    animal = _get_animal_for_owner(db, animal_id, owner_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(animal, key, value)
    db.commit()
    db.refresh(animal)
    return animal


# --- Suivi sanitaire individuel ---

def add_animal_health_record(db: Session, animal_id: str, owner_id: str, data) -> AnimalHealthRecord:
    _get_animal_for_owner(db, animal_id, owner_id)
    record = AnimalHealthRecord(animal_id=animal_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_animal_health_records(db: Session, animal_id: str, owner_id: str) -> list[AnimalHealthRecord]:
    _get_animal_for_owner(db, animal_id, owner_id)
    return (
        db.query(AnimalHealthRecord)
        .filter(AnimalHealthRecord.animal_id == animal_id)
        .order_by(AnimalHealthRecord.record_date.desc())
        .all()
    )


# --- Suivi de croissance ---

def add_weight_record(db: Session, animal_id: str, owner_id: str, data) -> WeightRecord:
    animal = _get_animal_for_owner(db, animal_id, owner_id)
    record = WeightRecord(animal_id=animal_id, **data.model_dump())
    db.add(record)
    # Le poids courant de la fiche animal reflète toujours le dernier relevé.
    animal.current_weight_kg = data.weight_kg
    db.commit()
    db.refresh(record)
    return record


def get_growth_summary(db: Session, animal_id: str, owner_id: str) -> dict:
    animal = _get_animal_for_owner(db, animal_id, owner_id)
    records = (
        db.query(WeightRecord)
        .filter(WeightRecord.animal_id == animal_id)
        .order_by(WeightRecord.measured_at.asc())
        .all()
    )

    first_weight = records[0].weight_kg if records else None
    latest_weight = records[-1].weight_kg if records else None
    total_gain = (latest_weight - first_weight) if (first_weight is not None and latest_weight is not None) else None

    average_daily_gain = None
    if total_gain is not None and len(records) >= 2:
        days_elapsed = (records[-1].measured_at - records[0].measured_at).days
        if days_elapsed > 0:
            average_daily_gain = total_gain / days_elapsed

    return {
        "animal_id": animal.id,
        "animal_tag": animal.tag,
        "first_weight_kg": first_weight,
        "latest_weight_kg": latest_weight,
        "total_gain_kg": total_gain,
        "average_daily_gain_kg": average_daily_gain,
        "records": list(reversed(records)),  # plus récent en premier, cohérent avec le reste de l'API
    }


# --- Reproduction ---

def add_reproduction_record(db: Session, animal_id: str, owner_id: str, data) -> ReproductionRecord:
    _get_animal_for_owner(db, animal_id, owner_id)
    record = ReproductionRecord(animal_id=animal_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_reproduction_records(db: Session, animal_id: str, owner_id: str) -> list[ReproductionRecord]:
    _get_animal_for_owner(db, animal_id, owner_id)
    return (
        db.query(ReproductionRecord)
        .filter(ReproductionRecord.animal_id == animal_id)
        .order_by(ReproductionRecord.event_date.desc())
        .all()
    )


def declare_birth(db: Session, animal_id: str, owner_id: str, data) -> dict:
    """
    Déclare une mise bas : crée automatiquement une fiche par petit né,
    les rattache au parent, et incrémente l'effectif du troupeau — sur
    le même principe que add_health_event pour un événement de type
    naissance, afin que suivi individuel et effectif agrégé restent
    cohérents sans double saisie.
    """
    mother = _get_animal_for_owner(db, animal_id, owner_id)
    herd = mother.herd

    offspring = []
    for i in range(data.offspring_count):
        child = Animal(
            herd_id=herd.id,
            parent_id=mother.id,
            tag=f"{mother.tag}-petit-{i + 1}-{data.event_date.isoformat()}",
            sex=data.offspring_sex,
            birth_date=data.event_date,
            status="vivant",
        )
        db.add(child)
        offspring.append(child)

    herd.current_count = herd.current_count + data.offspring_count

    reproduction_record = ReproductionRecord(
        animal_id=mother.id,
        event_type="mise_bas",
        event_date=data.event_date,
        notes=data.notes,
    )
    db.add(reproduction_record)

    db.commit()
    for child in offspring:
        db.refresh(child)
    db.refresh(reproduction_record)

    return {"reproduction_record": reproduction_record, "offspring": offspring}


# --- Plan alimentaire ---

def generate_feed_plan(db: Session, herd_id: str, owner_id: str, data) -> FeedPlan:
    herd = get_herd(db, herd_id, owner_id)
    computed = feed_service.compute_feed_plan(herd.species, herd.current_count, data.feed_type)
    plan = FeedPlan(herd_id=herd_id, **computed)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_latest_feed_plan(db: Session, herd_id: str, owner_id: str) -> FeedPlan | None:
    get_herd(db, herd_id, owner_id)
    return (
        db.query(FeedPlan)
        .filter(FeedPlan.herd_id == herd_id)
        .order_by(FeedPlan.created_at.desc())
        .first()
    )


# --- Analyse économique ---

def get_herd_economics(db: Session, herd_id: str, owner_id: str) -> dict:
    herd = get_herd(db, herd_id, owner_id)

    herd_level_cost = sum(
        e.cost_amount or 0
        for e in db.query(HealthEvent).filter(HealthEvent.herd_id == herd_id).all()
    )
    animal_level_cost = sum(
        r.cost_amount or 0
        for r in (
            db.query(AnimalHealthRecord)
            .join(Animal)
            .filter(Animal.herd_id == herd_id)
            .all()
        )
    )
    total_cost = herd_level_cost + animal_level_cost

    # Estimation indicative de la valeur marchande par tête, servant à
    # chiffrer un troupeau sans transaction réelle : à ajuster selon le
    # marché local une fois cette valeur configurable côté produit.
    estimated_value_per_head = 150000.0 if herd.species.lower() == "bovins" else 25000.0

    sold_animals = (
        db.query(Animal)
        .filter(Animal.herd_id == herd_id, Animal.status == "vendu")
        .count()
    )
    total_revenue_from_sales = sold_animals * estimated_value_per_head

    production_records = db.query(ProductionRecord).filter(ProductionRecord.herd_id == herd_id).all()
    # Valorisation indicative de la production, faute de prix de vente déclaré par unité.
    total_revenue_from_production = sum(r.quantity for r in production_records) * 500.0

    estimated_herd_value = herd.current_count * estimated_value_per_head

    return {
        "herd_id": herd.id,
        "herd_name": herd.name,
        "total_cost": total_cost,
        "total_revenue_from_sales": total_revenue_from_sales,
        "total_revenue_from_production": total_revenue_from_production,
        "estimated_herd_value": estimated_herd_value,
        "net_profit": total_revenue_from_sales + total_revenue_from_production - total_cost,
        "currency": "XOF",
    }


# --- Génération de documents (réutilise le service partagé app.core.exports) ---

def build_animal_report(db: Session, animal_id: str, owner_id: str):
    """
    Construit un `ExportDocument` (voir app.core.exports) faisant office
    de carnet de suivi de l'animal : identité, suivi sanitaire (carnet de
    vaccination), croissance, reproduction. Comme pour l'agriculture, ce
    module ne génère aucun fichier lui-même — seul le contenu est décrit.
    """
    from app.core.exports import ExportDocument, ExportSection

    animal = _get_animal_for_owner(db, animal_id, owner_id)
    health_records = list_animal_health_records(db, animal_id, owner_id)
    growth = get_growth_summary(db, animal_id, owner_id)
    reproduction_records = list_reproduction_records(db, animal_id, owner_id)

    identity_section = ExportSection(
        heading="Identité",
        paragraphs=[
            f"Race : {animal.breed or 'non précisée'}.",
            f"Sexe : {animal.sex}.",
            f"Né(e) le : {animal.birth_date or 'inconnu'}.",
            f"Statut actuel : {animal.status}.",
        ],
    )

    health_section = ExportSection(
        heading="Carnet sanitaire (vaccinations, traitements)",
        table_headers=["Date", "Type", "Notes", "Coût"],
        table_rows=[
            [str(r.record_date), r.record_type, r.notes or "—", str(r.cost_amount or "—")]
            for r in health_records
        ],
    )

    growth_section = ExportSection(
        heading="Suivi de croissance",
        paragraphs=[
            f"Premier poids enregistré : {growth['first_weight_kg']} kg." if growth["first_weight_kg"] else "Aucun relevé de poids.",
            f"Dernier poids enregistré : {growth['latest_weight_kg']} kg." if growth["latest_weight_kg"] else "",
            f"Gain moyen par jour : {growth['average_daily_gain_kg']:.2f} kg." if growth["average_daily_gain_kg"] else "",
        ],
    )

    reproduction_section = ExportSection(
        heading="Historique de reproduction",
        table_headers=["Date", "Événement", "Notes"],
        table_rows=[
            [str(r.event_date), r.event_type.replace("_", " "), r.notes or "—"]
            for r in reproduction_records
        ],
    )

    return ExportDocument(
        title=f"Fiche animal — {animal.tag}",
        subtitle=f"Troupeau : {animal.herd.name}",
        sections=[identity_section, health_section, growth_section, reproduction_section],
    )
