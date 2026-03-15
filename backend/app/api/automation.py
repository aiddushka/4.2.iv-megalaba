from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.schemas.automation_schema import AutomationRuleCreate, AutomationRuleOut
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

