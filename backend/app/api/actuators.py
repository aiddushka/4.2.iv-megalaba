from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.actuator_schema import ActuatorCommand, ActuatorStateOut
from app.services import actuator_service, mqtt_service

router = APIRouter(prefix="/actuators", tags=["Actuators"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/control", response_model=ActuatorStateOut)
def control_actuator(
    cmd: ActuatorCommand,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    try:
        mqtt_service.publish_actuator_command(
            device_uid=cmd.device_uid,
            action=cmd.action,
            actuator_type=cmd.actuator_type,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MQTT unavailable: {exc}",
        ) from exc
    actuator = actuator_service.set_actuator_state(
        db=db,
        device_uid=cmd.device_uid,
        action=cmd.action,
        actuator_type=cmd.actuator_type,
    )
    return ActuatorStateOut(
        device_uid=actuator.device_uid,
        actuator_type=actuator.actuator_type,
        state=actuator.state,
    )


@router.get("/status", response_model=list[ActuatorStateOut])
def get_actuators_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin and not current_user.can_view_dashboard:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к дашборду запрещён. Обратитесь к администратору.",
        )
    actuators = actuator_service.get_actuators(db)
    return [
        ActuatorStateOut(
            device_uid=a.device_uid,
            actuator_type=a.actuator_type,
            state=a.state,
        )
        for a in actuators
    ]