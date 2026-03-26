from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.schemas.actuator_schema import (
    ActuatorCommand,
    ActuatorModeUpdate,
    ActuatorStateOut,
)
from app.services import actuator_service

router = APIRouter(prefix="/actuators", tags=["Actuators"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/control", response_model=ActuatorStateOut)
def control_actuator(cmd: ActuatorCommand, db: Session = Depends(get_db)):
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
        control_mode=actuator.control_mode,
    )


@router.patch("/{device_uid}/mode", response_model=ActuatorStateOut)
def update_actuator_mode(
    device_uid: str,
    payload: ActuatorModeUpdate,
    db: Session = Depends(get_db),
):
    if payload.control_mode not in {"AUTO", "MANUAL"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="control_mode must be AUTO or MANUAL",
        )
    actuator = actuator_service.set_actuator_mode(
        db=db, device_uid=device_uid, control_mode=payload.control_mode
    )
    if not actuator:
        raise HTTPException(status_code=404, detail="Actuator not found")
    return ActuatorStateOut(
        device_uid=actuator.device_uid,
        actuator_type=actuator.actuator_type,
        state=actuator.state,
        control_mode=actuator.control_mode,
    )


@router.get("/status", response_model=list[ActuatorStateOut])
def get_actuators_status(db: Session = Depends(get_db)):
    actuators = actuator_service.get_actuators(db)
    return [
        ActuatorStateOut(
            device_uid=a.device_uid,
            actuator_type=a.actuator_type,
            state=a.state,
            control_mode=a.control_mode,
        )
        for a in actuators
    ]
