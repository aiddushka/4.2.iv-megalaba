from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.schemas.actuator_schema import ActuatorCommand, ActuatorStateOut
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
    )


@router.get("/status", response_model=list[ActuatorStateOut])
def get_actuators_status(db: Session = Depends(get_db)):
    actuators = actuator_service.get_actuators(db)
    return [
        ActuatorStateOut(
            device_uid=a.device_uid,
            actuator_type=a.actuator_type,
            state=a.state,
        )
        for a in actuators
    ]

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import SessionLocal

router = APIRouter(prefix="/actuators", tags=["Actuators"])

actuator_states = {}  # хранение текущего состояния актуаторов в памяти

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/control")
def control_actuator(payload: dict):
    device_uid = payload.get("device_uid")
    action = payload.get("action")  # ON / OFF
    if not device_uid or action not in ["ON", "OFF"]:
        return {"error": "device_uid and valid action required"}

    actuator_states[device_uid] = action
    return {"status": "ok", "device_uid": device_uid, "action": action}

@router.get("/status")
def get_actuator_status():
    return actuator_states