from sqlalchemy.orm import Session

from app.models.actuator import Actuator


def set_actuator_state(
    db: Session, device_uid: str, action: str, actuator_type: str | None = None
) -> Actuator:
    actuator = db.query(Actuator).filter(Actuator.device_uid == device_uid).first()
    if not actuator:
        actuator = Actuator(
            device_uid=device_uid,
            actuator_type=actuator_type or "unknown",
            state=action,
        )
        db.add(actuator)
    else:
        actuator.state = action
        if actuator_type:
            actuator.actuator_type = actuator_type
    db.commit()
    db.refresh(actuator)
    return actuator


def set_actuator_mode(
    db: Session, device_uid: str, control_mode: str
) -> Actuator | None:
    actuator = db.query(Actuator).filter(Actuator.device_uid == device_uid).first()
    if not actuator:
        return None
    actuator.control_mode = control_mode
    db.commit()
    db.refresh(actuator)
    return actuator


def get_actuators(db: Session) -> list[Actuator]:
    return db.query(Actuator).all()

