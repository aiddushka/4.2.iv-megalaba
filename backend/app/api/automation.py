from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.automation_schema import (
    AutomationRuleCreate,
    AutomationRuleOut,
    DeviceLinkCreate,
    DeviceLinkUpdate,
    DeviceLinkOut,
)
from app.services import automation_service

router = APIRouter(prefix="/automation", tags=["Automation"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/rules", response_model=AutomationRuleOut)
def create_rule(payload: AutomationRuleCreate, db: Session = Depends(get_db)):
    rule = automation_service.create_rule(
        db=db,
        name=payload.name,
        sensor_type=payload.sensor_type,
        condition=payload.condition,
        threshold=payload.threshold,
        actuator_type=payload.actuator_type,
        action=payload.action,
    )
    return rule


@router.get("/rules", response_model=list[AutomationRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return automation_service.get_rules(db)


@router.post("/links", response_model=DeviceLinkOut)
def create_link(payload: DeviceLinkCreate, db: Session = Depends(get_db)):
    return automation_service.create_device_link(
        db=db,
        source_device_uid=payload.source_device_uid,
        target_device_uid=payload.target_device_uid,
        controller=payload.controller,
        description=payload.description,
        active=payload.active,
        auto_control_enabled=payload.auto_control_enabled,
        min_value=payload.min_value,
        max_value=payload.max_value,
    )


@router.get("/links", response_model=list[DeviceLinkOut])
def list_links(device_uid: str | None = None, db: Session = Depends(get_db)):
    return automation_service.get_device_links(db, device_uid=device_uid)


@router.patch("/links/{link_id}", response_model=DeviceLinkOut)
def update_link(
    link_id: int,
    payload: DeviceLinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    link = automation_service.update_device_link(
        db=db,
        link_id=link_id,
        auto_control_enabled=payload.auto_control_enabled,
        min_value=payload.min_value,
        max_value=payload.max_value,
        description=payload.description,
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return link


@router.delete("/links/{link_id}")
def delete_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    deleted = automation_service.delete_device_link(db, link_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return {"ok": True}

