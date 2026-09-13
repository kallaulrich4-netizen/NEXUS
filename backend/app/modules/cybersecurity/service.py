from collections import defaultdict

from sqlalchemy.orm import Session

from app.modules.cybersecurity.models import SecurityAsset, SecurityAudit, Finding, SecurityGuide


class AssetNotFoundError(Exception):
    """Levée quand un actif n'existe pas ou n'appartient pas à l'utilisateur."""


class AuditNotFoundError(Exception):
    """Levée quand un audit n'existe pas ou n'appartient pas à un actif de l'utilisateur."""


class FindingNotFoundError(Exception):
    """Levée quand un constat n'existe pas pour cet audit."""


class GuideNotFoundError(Exception):
    """Levée quand un guide n'existe pas ou n'est pas publié."""


# --- Actifs ---

def create_asset(db: Session, owner_id: str, data) -> SecurityAsset:
    asset = SecurityAsset(owner_id=owner_id, **data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_asset(db: Session, asset_id: str, owner_id: str) -> SecurityAsset:
    asset = db.query(SecurityAsset).filter(SecurityAsset.id == asset_id, SecurityAsset.owner_id == owner_id).first()
    if asset is None:
        raise AssetNotFoundError("Actif introuvable.")
    return asset


def list_assets(db: Session, owner_id: str) -> list[SecurityAsset]:
    return db.query(SecurityAsset).filter(SecurityAsset.owner_id == owner_id).order_by(SecurityAsset.created_at.desc()).all()


def delete_asset(db: Session, asset_id: str, owner_id: str) -> None:
    asset = get_asset(db, asset_id, owner_id)
    db.delete(asset)
    db.commit()


# --- Audits ---

def request_audit(db: Session, asset_id: str, owner_id: str, data) -> SecurityAudit:
    """
    `data.ownership_confirmed` est déjà validé à True par le schéma
    (impossible de soumettre False) — double sécurité : on revérifie ici.
    """
    get_asset(db, asset_id, owner_id)
    if not data.ownership_confirmed:
        raise ValueError("La confirmation de propriété est obligatoire.")

    audit = SecurityAudit(
        asset_id=asset_id,
        requested_by=owner_id,
        ownership_confirmed=data.ownership_confirmed,
        scheduled_date=data.scheduled_date,
        status="demande",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def _get_audit_for_owner(db: Session, audit_id: str, owner_id: str) -> SecurityAudit:
    audit = (
        db.query(SecurityAudit)
        .join(SecurityAsset)
        .filter(SecurityAudit.id == audit_id, SecurityAsset.owner_id == owner_id)
        .first()
    )
    if audit is None:
        raise AuditNotFoundError("Audit introuvable.")
    return audit


def get_audit(db: Session, audit_id: str, owner_id: str) -> SecurityAudit:
    return _get_audit_for_owner(db, audit_id, owner_id)


def list_audits(db: Session, asset_id: str, owner_id: str) -> list[SecurityAudit]:
    get_asset(db, asset_id, owner_id)
    return (
        db.query(SecurityAudit)
        .filter(SecurityAudit.asset_id == asset_id)
        .order_by(SecurityAudit.created_at.desc())
        .all()
    )


def update_audit_status(db: Session, audit_id: str, owner_id: str, new_status: str, summary: str | None) -> SecurityAudit:
    audit = _get_audit_for_owner(db, audit_id, owner_id)
    audit.status = new_status
    if summary is not None:
        audit.summary = summary
    db.commit()
    db.refresh(audit)
    return audit


# --- Constats ---

def add_finding(db: Session, audit_id: str, owner_id: str, data) -> Finding:
    _get_audit_for_owner(db, audit_id, owner_id)
    finding = Finding(audit_id=audit_id, status="ouvert", **data.model_dump())
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def list_findings(db: Session, audit_id: str, owner_id: str) -> list[Finding]:
    _get_audit_for_owner(db, audit_id, owner_id)
    return db.query(Finding).filter(Finding.audit_id == audit_id).order_by(Finding.created_at.desc()).all()


def _get_finding_for_owner(db: Session, finding_id: str, owner_id: str) -> Finding:
    finding = (
        db.query(Finding)
        .join(SecurityAudit)
        .join(SecurityAsset)
        .filter(Finding.id == finding_id, SecurityAsset.owner_id == owner_id)
        .first()
    )
    if finding is None:
        raise FindingNotFoundError("Constat introuvable.")
    return finding


def update_finding_status(db: Session, finding_id: str, owner_id: str, new_status: str) -> Finding:
    finding = _get_finding_for_owner(db, finding_id, owner_id)
    finding.status = new_status
    db.commit()
    db.refresh(finding)
    return finding


def get_risk_dashboard(db: Session, asset_id: str, owner_id: str) -> dict:
    asset = get_asset(db, asset_id, owner_id)
    findings = (
        db.query(Finding)
        .join(SecurityAudit)
        .filter(SecurityAudit.asset_id == asset_id)
        .all()
    )

    open_by_severity: dict[str, int] = defaultdict(int)
    for finding in findings:
        if finding.status in {"ouvert", "en_correction"}:
            open_by_severity[finding.severity] += 1

    return {
        "asset_id": asset.id,
        "asset_name": asset.name,
        "total_findings": len(findings),
        "open_findings_by_severity": dict(open_by_severity),
        "critical_open_count": open_by_severity.get("critique", 0),
    }


# --- Guides de sécurisation (contenu éducatif) ---

def submit_guide(db: Session, author_id: str, data) -> SecurityGuide:
    guide = SecurityGuide(author_id=author_id, is_reviewed=False, is_published=False, **data.model_dump())
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide


def get_published_guide(db: Session, guide_id: str) -> SecurityGuide:
    guide = db.query(SecurityGuide).filter(SecurityGuide.id == guide_id, SecurityGuide.is_published.is_(True)).first()
    if guide is None:
        raise GuideNotFoundError("Guide introuvable ou non publié.")
    return guide


def search_published_guides(db: Session, category: str | None = None, limit: int = 20, offset: int = 0) -> list[SecurityGuide]:
    q = db.query(SecurityGuide).filter(SecurityGuide.is_published.is_(True))
    if category:
        q = q.filter(SecurityGuide.category == category)
    return q.order_by(SecurityGuide.updated_at.desc()).offset(offset).limit(limit).all()
