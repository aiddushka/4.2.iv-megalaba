from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.actuator import Actuator
from app.models.device_link import DeviceLink
from app.schemas.sensor_schema import SensorDataCreate, SensorDataOut
from app.services import actuator_service, sensor_service

router = APIRouter(prefix="/sensor-data", tags=["Sensors"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=SensorDataOut)
def create_sensor_data(payload: SensorDataCreate, db: Session = Depends(get_db)):
    if not payload.device_uid or payload.value is None:
        raise HTTPException(status_code=400, detail="device_uid and value required")
    adjusted_value = payload.value
    links = (
        db.query(DeviceLink)
        .filter(DeviceLink.source_device_uid == payload.device_uid, DeviceLink.active == True)
        .all()
    )
    for link in links:
        actuator = db.query(Actuator).filter(Actuator.device_uid == link.target_device_uid).first()
        if not actuator:
            continue
        sensor_kind = (payload.sensor_type or "").lower()
        actuator_kind = (actuator.actuator_type or "").lower()
        if actuator.state == "ON":
            if "soil" in sensor_kind and "irrig" in actuator_kind:
                adjusted_value = min(100.0, adjusted_value + 2.0)
            elif "temp" in sensor_kind and "heater" in actuator_kind:
                adjusted_value = adjusted_value + 0.8
            elif "temp" in sensor_kind and "vent" in actuator_kind:
                adjusted_value = adjusted_value - 0.8
            elif "light" in sensor_kind and "light" in actuator_kind:
                adjusted_value = adjusted_value + 12.0
        else:
            if "soil" in sensor_kind and "irrig" in actuator_kind:
                adjusted_value = max(0.0, adjusted_value - 0.6)
            elif "temp" in sensor_kind and "heater" in actuator_kind:
                adjusted_value = adjusted_value - 0.2
            elif "light" in sensor_kind and "light" in actuator_kind:
                adjusted_value = max(0.0, adjusted_value - 3.0)

    data = sensor_service.create_sensor_data(
        db=db,
        device_uid=payload.device_uid,
        value=adjusted_value,
        sensor_type=payload.sensor_type,
    )
    for link in links:
        if not link.auto_control_enabled:
            continue
        should_turn_on = False
        if link.min_value is not None and adjusted_value < link.min_value:
            should_turn_on = True
        if link.max_value is not None and adjusted_value > link.max_value:
            should_turn_on = False
        actuator_service.set_actuator_state(
            db=db,
            device_uid=link.target_device_uid,
            action="ON" if should_turn_on else "OFF",
        )
    return data


@router.get("/", response_model=list[SensorDataOut])
def get_sensor_data(db: Session = Depends(get_db)):
    return sensor_service.get_all_sensor_data(db)
