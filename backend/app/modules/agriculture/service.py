from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.agriculture.models import (
    Field, CropCycle, Activity,
    CropRecommendation, CalendarTask, DiseaseDiagnosis, FinancialProjection,
)
from app.modules.agriculture import calendar_service, ai_service
from app.modules.ai_assistant.provider import AIProvider


class FieldNotFoundError(Exception):
    """Levée quand une parcelle n'existe pas ou n'appartient pas à l'utilisateur."""


class CropCycleNotFoundError(Exception):
    """Levée quand un cycle de culture n'existe pas ou n'appartient pas à l'utilisateur."""


class NotOwnerError(Exception):
    """Levée quand un utilisateur tente d'accéder à une ressource qui n'est pas la sienne."""


class InvalidCycleStateError(Exception):
    """Levée quand une opération n'est pas cohérente avec l'état actuel du cycle de culture."""


class CalendarTaskNotFoundError(Exception):
    """Levée quand une tâche de calendrier n'existe pas ou n'appartient pas à l'utilisateur."""


class DiagnosisNotFoundError(Exception):
    """Levée quand un diagnostic n'existe pas ou n'appartient pas à l'utilisateur."""


# --- Parcelles ---

def create_field(db: Session, owner_id: str, data) -> Field:
    field = Field(owner_id=owner_id, **data.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


def get_field(db: Session, field_id: str, owner_id: str) -> Field:
    field = db.query(Field).filter(Field.id == field_id, Field.owner_id == owner_id).first()
    if field is None:
        raise FieldNotFoundError("Parcelle introuvable.")
    return field


def list_fields(db: Session, owner_id: str) -> list[Field]:
    return db.query(Field).filter(Field.owner_id == owner_id).order_by(Field.created_at.desc()).all()


def update_field(db: Session, field_id: str, owner_id: str, data) -> Field:
    field = get_field(db, field_id, owner_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return field


def delete_field(db: Session, field_id: str, owner_id: str) -> None:
    field = get_field(db, field_id, owner_id)
    db.delete(field)
    db.commit()


# --- Cycles de culture ---

def create_crop_cycle(db: Session, field_id: str, owner_id: str, data) -> CropCycle:
    get_field(db, field_id, owner_id)  # vérifie que la parcelle appartient bien à l'utilisateur
    cycle = CropCycle(field_id=field_id, status="planifie", **data.model_dump())
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


def _get_cycle_for_owner(db: Session, cycle_id: str, owner_id: str) -> CropCycle:
    cycle = (
        db.query(CropCycle)
        .join(Field)
        .filter(CropCycle.id == cycle_id, Field.owner_id == owner_id)
        .first()
    )
    if cycle is None:
        raise CropCycleNotFoundError("Cycle de culture introuvable.")
    return cycle


def get_crop_cycle(db: Session, cycle_id: str, owner_id: str) -> CropCycle:
    return _get_cycle_for_owner(db, cycle_id, owner_id)


def list_crop_cycles(db: Session, field_id: str, owner_id: str) -> list[CropCycle]:
    get_field(db, field_id, owner_id)
    return (
        db.query(CropCycle)
        .filter(CropCycle.field_id == field_id)
        .order_by(CropCycle.planting_date.desc())
        .all()
    )


def mark_growing(db: Session, cycle_id: str, owner_id: str) -> CropCycle:
    cycle = _get_cycle_for_owner(db, cycle_id, owner_id)
    if cycle.status != "planifie":
        raise InvalidCycleStateError("Seul un cycle « planifié » peut passer à « en croissance ».")
    cycle.status = "en_croissance"
    db.commit()
    db.refresh(cycle)
    return cycle


def record_harvest(db: Session, cycle_id: str, owner_id: str, data) -> CropCycle:
    """Enregistre la récolte : c'est ce qui alimente les statistiques de rendement."""
    cycle = _get_cycle_for_owner(db, cycle_id, owner_id)
    if cycle.status not in {"planifie", "en_croissance"}:
        raise InvalidCycleStateError("Ce cycle a déjà été récolté ou marqué comme échoué.")
    if data.actual_harvest_date < cycle.planting_date:
        raise InvalidCycleStateError("La date de récolte ne peut pas précéder la date de semis.")

    cycle.status = "recolte"
    cycle.actual_harvest_date = data.actual_harvest_date
    cycle.yield_amount = data.yield_amount
    cycle.yield_unit = data.yield_unit
    db.commit()
    db.refresh(cycle)
    return cycle


def mark_failed(db: Session, cycle_id: str, owner_id: str, notes: str | None) -> CropCycle:
    cycle = _get_cycle_for_owner(db, cycle_id, owner_id)
    if cycle.status == "recolte":
        raise InvalidCycleStateError("Un cycle déjà récolté ne peut pas être marqué comme échoué.")
    cycle.status = "echoue"
    if notes:
        cycle.notes = notes
    db.commit()
    db.refresh(cycle)
    return cycle


# --- Activités ---

def add_activity(db: Session, cycle_id: str, owner_id: str, data) -> Activity:
    _get_cycle_for_owner(db, cycle_id, owner_id)
    activity = Activity(crop_cycle_id=cycle_id, **data.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def list_activities(db: Session, cycle_id: str, owner_id: str) -> list[Activity]:
    _get_cycle_for_owner(db, cycle_id, owner_id)
    return (
        db.query(Activity)
        .filter(Activity.crop_cycle_id == cycle_id)
        .order_by(Activity.activity_date.desc())
        .all()
    )


# --- Analyses ---

def get_field_yield_summary(db: Session, field_id: str, owner_id: str) -> dict:
    field = get_field(db, field_id, owner_id)
    cycles = db.query(CropCycle).filter(CropCycle.field_id == field_id).all()

    total_yield_by_unit: dict[str, float] = defaultdict(float)
    harvested_count = 0
    for cycle in cycles:
        if cycle.status == "recolte" and cycle.yield_amount is not None and cycle.yield_unit:
            total_yield_by_unit[cycle.yield_unit] += cycle.yield_amount
            harvested_count += 1

    total_cost = (
        db.query(Activity)
        .join(CropCycle)
        .filter(CropCycle.field_id == field_id, Activity.cost_amount.isnot(None))
        .all()
    )
    total_cost_amount = sum(a.cost_amount for a in total_cost)

    return {
        "field_id": field.id,
        "field_name": field.name,
        "total_cycles": len(cycles),
        "harvested_cycles": harvested_count,
        "total_yield_by_unit": dict(total_yield_by_unit),
        "total_cost": total_cost_amount,
    }


# ============================================================================
# AGRICULTURE V2
# ============================================================================

# --- Recommandations de culture ---

def generate_crop_recommendations(
    db: Session, field_id: str, owner_id: str, data, provider: AIProvider, user_language: str = "fr"
) -> list[CropRecommendation]:
    field = get_field(db, field_id, owner_id)

    raw_recommendations = ai_service.generate_crop_recommendations(
        provider,
        soil_type=field.soil_type,
        country=field.country,
        region=field.region,
        season=data.season,
        budget_amount=data.budget_amount,
        user_language=user_language,
    )

    created = []
    for item in raw_recommendations:
        recommendation = CropRecommendation(
            field_id=field_id,
            crop_name=item["crop_name"],
            score=item["score"],
            rationale=item["rationale"],
            season=data.season,
            budget_amount=data.budget_amount,
            budget_currency=data.budget_currency,
        )
        db.add(recommendation)
        created.append(recommendation)

    db.commit()
    for recommendation in created:
        db.refresh(recommendation)
    return created


def list_crop_recommendations(db: Session, field_id: str, owner_id: str) -> list[CropRecommendation]:
    get_field(db, field_id, owner_id)
    return (
        db.query(CropRecommendation)
        .filter(CropRecommendation.field_id == field_id)
        .order_by(CropRecommendation.created_at.desc())
        .all()
    )


# --- Calendrier automatique ---

def generate_calendar(db: Session, cycle_id: str, owner_id: str) -> list[CalendarTask]:
    """
    Génère les tâches du calendrier pour un cycle de culture. Appel
    idempotent côté utilisateur : les tâches encore "prevue" sont
    remplacées à chaque nouvel appel, les tâches déjà traitées
    ("faite", "reportee", "annulee") sont conservées telles quelles.
    """
    cycle = _get_cycle_for_owner(db, cycle_id, owner_id)

    db.query(CalendarTask).filter(
        CalendarTask.crop_cycle_id == cycle_id, CalendarTask.status == "prevue"
    ).delete()

    raw_tasks = calendar_service.build_calendar_tasks(cycle.crop_name, cycle.planting_date, cycle.expected_harvest_date)
    tasks = []
    for item in raw_tasks:
        task = CalendarTask(crop_cycle_id=cycle_id, status="prevue", **item)
        db.add(task)
        tasks.append(task)

    db.commit()
    for task in tasks:
        db.refresh(task)
    return list_calendar_tasks(db, cycle_id, owner_id)


def list_calendar_tasks(db: Session, cycle_id: str, owner_id: str) -> list[CalendarTask]:
    _get_cycle_for_owner(db, cycle_id, owner_id)
    return (
        db.query(CalendarTask)
        .filter(CalendarTask.crop_cycle_id == cycle_id)
        .order_by(CalendarTask.due_date.asc())
        .all()
    )


def _get_calendar_task_for_owner(db: Session, task_id: str, owner_id: str) -> CalendarTask:
    task = (
        db.query(CalendarTask)
        .join(CropCycle)
        .join(Field)
        .filter(CalendarTask.id == task_id, Field.owner_id == owner_id)
        .first()
    )
    if task is None:
        raise CalendarTaskNotFoundError("Tâche de calendrier introuvable.")
    return task


def update_calendar_task(db: Session, task_id: str, owner_id: str, data) -> CalendarTask:
    task = _get_calendar_task_for_owner(db, task_id, owner_id)
    task.status = data.status
    if data.notes is not None:
        task.notes = data.notes
    db.commit()
    db.refresh(task)
    return task


# --- Diagnostic des maladies ---

def create_disease_diagnosis(
    db: Session, cycle_id: str, owner_id: str, data, provider: AIProvider, user_language: str = "fr"
) -> DiseaseDiagnosis:
    cycle = _get_cycle_for_owner(db, cycle_id, owner_id)

    result = ai_service.diagnose_disease(
        provider,
        crop_name=cycle.crop_name,
        symptoms_description=data.symptoms_description,
        photo_reference=data.photo_reference,
        user_language=user_language,
    )

    diagnosis = DiseaseDiagnosis(
        crop_cycle_id=cycle_id,
        symptoms_description=data.symptoms_description,
        photo_reference=data.photo_reference,
        diagnosis_text=result["diagnosis_text"],
        recommended_actions=result["recommended_actions"],
        confidence=result["confidence"],
        status="en_analyse",
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


def list_disease_diagnoses(db: Session, cycle_id: str, owner_id: str) -> list[DiseaseDiagnosis]:
    _get_cycle_for_owner(db, cycle_id, owner_id)
    return (
        db.query(DiseaseDiagnosis)
        .filter(DiseaseDiagnosis.crop_cycle_id == cycle_id)
        .order_by(DiseaseDiagnosis.created_at.desc())
        .all()
    )


# --- Projection économique ---

def generate_financial_projection(db: Session, field_id: str, owner_id: str, data) -> FinancialProjection:
    field = get_field(db, field_id, owner_id)

    cycles_query = db.query(CropCycle).filter(CropCycle.field_id == field_id)
    if data.crop_cycle_id:
        cycles_query = cycles_query.filter(CropCycle.id == data.crop_cycle_id)
    cycles = cycles_query.all()

    cost_to_date = (
        db.query(Activity)
        .join(CropCycle)
        .filter(CropCycle.field_id == field_id, Activity.cost_amount.isnot(None))
    )
    if data.crop_cycle_id:
        cost_to_date = cost_to_date.filter(CropCycle.id == data.crop_cycle_id)
    estimated_cost_total = sum(a.cost_amount for a in cost_to_date.all())

    remaining_tasks = (
        db.query(CalendarTask)
        .join(CropCycle)
        .filter(CropCycle.field_id == field_id, CalendarTask.status == "prevue")
    )
    if data.crop_cycle_id:
        remaining_tasks = remaining_tasks.filter(CropCycle.id == data.crop_cycle_id)
    # Estimation simple : coût moyen forfaitaire par tâche restante non chiffrée,
    # cohérente avec la nature volontairement indicative de cette projection.
    estimated_cost_total += remaining_tasks.count() * 5000.0

    expected_yield = sum(c.yield_amount or 0 for c in cycles if c.status in {"planifie", "en_croissance", "recolte"})
    market_price = data.market_price_per_unit or 0.0
    estimated_revenue_total = expected_yield * market_price

    projection = FinancialProjection(
        field_id=field_id,
        crop_cycle_id=data.crop_cycle_id,
        estimated_cost_total=estimated_cost_total,
        estimated_revenue_total=estimated_revenue_total,
        estimated_profit=estimated_revenue_total - estimated_cost_total,
        currency=data.currency,
        assumptions=(
            f"Coût forfaitaire de 5000 {data.currency} par tâche de calendrier restante ; "
            f"prix de marché utilisé : {market_price} {data.currency} par unité de rendement."
        ),
    )
    db.add(projection)
    db.commit()
    db.refresh(projection)
    return projection


def get_latest_financial_projection(db: Session, field_id: str, owner_id: str) -> FinancialProjection | None:
    get_field(db, field_id, owner_id)
    return (
        db.query(FinancialProjection)
        .filter(FinancialProjection.field_id == field_id)
        .order_by(FinancialProjection.created_at.desc())
        .first()
    )


# --- Tableau de bord consolidé ---

def get_farm_dashboard(db: Session, owner_id: str) -> dict:
    fields = list_fields(db, owner_id)
    now = datetime.now(timezone.utc).date()

    field_summaries = []
    total_active_cycles = 0
    total_upcoming = 0
    total_overdue = 0

    for field in fields:
        active_cycles = (
            db.query(CropCycle)
            .filter(CropCycle.field_id == field.id, CropCycle.status.in_(["planifie", "en_croissance"]))
            .count()
        )
        tasks = (
            db.query(CalendarTask)
            .join(CropCycle)
            .filter(CropCycle.field_id == field.id, CalendarTask.status == "prevue")
            .all()
        )
        upcoming = sum(1 for t in tasks if t.due_date >= now)
        overdue = sum(1 for t in tasks if t.due_date < now)

        cost_query = (
            db.query(Activity)
            .join(CropCycle)
            .filter(CropCycle.field_id == field.id, Activity.cost_amount.isnot(None))
            .all()
        )
        total_cost = sum(a.cost_amount for a in cost_query)

        field_summaries.append({
            "field_id": field.id,
            "field_name": field.name,
            "active_cycles": active_cycles,
            "upcoming_tasks": upcoming,
            "overdue_tasks": overdue,
            "total_cost_to_date": total_cost,
        })

        total_active_cycles += active_cycles
        total_upcoming += upcoming
        total_overdue += overdue

    return {
        "total_fields": len(fields),
        "total_active_cycles": total_active_cycles,
        "total_upcoming_tasks": total_upcoming,
        "total_overdue_tasks": total_overdue,
        "fields": field_summaries,
    }


# --- Génération de documents (réutilise le service partagé app.core.exports) ---

def build_field_report(db: Session, field_id: str, owner_id: str):
    """
    Construit un `ExportDocument` (voir app.core.exports) résumant une
    parcelle : cycles de culture, activités, rendement, projection
    économique. Le module ne génère aucun fichier lui-même : il ne fait
    que décrire son contenu, la mise en forme PDF/Word/Excel/CSV reste
    entièrement gérée par le service partagé.
    """
    from app.core.exports import ExportDocument, ExportSection

    field = get_field(db, field_id, owner_id)
    cycles = list_crop_cycles(db, field_id, owner_id)
    yield_summary = get_field_yield_summary(db, field_id, owner_id)
    projection = get_latest_financial_projection(db, field_id, owner_id)

    cycles_section = ExportSection(
        heading="Cycles de culture",
        table_headers=["Culture", "Semis", "Récolte prévue", "Statut", "Rendement"],
        table_rows=[
            [
                c.crop_name, str(c.planting_date), str(c.expected_harvest_date or "—"),
                c.status.replace("_", " "),
                f"{c.yield_amount} {c.yield_unit}" if c.yield_amount else "—",
            ]
            for c in cycles
        ],
    )

    summary_section = ExportSection(
        heading="Synthèse",
        paragraphs=[
            f"Cycles au total : {yield_summary['total_cycles']} (dont {yield_summary['harvested_cycles']} récoltés).",
            f"Coût cumulé des activités : {yield_summary['total_cost']:.0f}.",
        ],
    )

    sections = [summary_section, cycles_section]

    if projection:
        sections.append(ExportSection(
            heading="Projection économique",
            paragraphs=[
                f"Coûts estimés : {projection.estimated_cost_total:.0f} {projection.currency}.",
                f"Revenus estimés : {projection.estimated_revenue_total:.0f} {projection.currency}.",
                f"Bénéfice estimé : {projection.estimated_profit:.0f} {projection.currency}.",
            ],
        ))

    return ExportDocument(
        title=f"Rapport de culture — {field.name}",
        subtitle=f"{field.country}{f', ' + field.region if field.region else ''} — {field.area_hectares} ha",
        sections=sections,
    )
