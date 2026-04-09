from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.actuator import Actuator
from app.models.device import Device
from app.models.device_link import DeviceLink
from app.models.sensor_data import SensorData
from app.schemas.sensor_schema import SensorDataCreate, SensorDataOut
from app.services import actuator_service, sensor_service

router = APIRouter(prefix="/sensor-data", tags=["Sensors"])

TEMPERATURE_CONTROL_STEP = 0.45
RANDOM_BLEND_FACTOR = 0.2
VENTILATION_STEP_ON = -0.7
IRRIGATION_STEP_ON = 1.2
IRRIGATION_STEP_OFF = -0.35
LIGHT_STEP_ON = 8.0
LIGHT_STEP_OFF = -2.0


def _should_turn_on(link: DeviceLink, value: float) -> bool:
    if link.min_value is not None and value < link.min_value:
        return True
    if link.max_value is not None and value > link.max_value:
        return True
    return False


def _should_turn_off(link: DeviceLink, value: float) -> bool:
    if link.min_value is not None and link.max_value is not None:
        span = max(link.max_value - link.min_value, 0.0)
        lower = link.min_value + (0.3 * span)
        upper = link.max_value - (0.3 * span)
        return lower <= value <= upper
    if link.min_value is not None:
        return value >= link.min_value
    if link.max_value is not None:
        return value <= link.max_value
    return False


def _is_temperature_control(sensor_kind: str, actuator_kind: str) -> bool:
    return ("temp" in sensor_kind) and (("heater" in actuator_kind) or ("temp" in actuator_kind))


def _temperature_target(link: DeviceLink, value: float) -> float | None:
    if link.min_value is not None and link.max_value is not None:
        span = max(link.max_value - link.min_value, 0.0)
        lower = link.min_value + (0.3 * span)
        upper = link.max_value - (0.3 * span)
        if value < link.min_value:
            return lower
        if value > link.max_value:
            return upper
        if value < lower:
            return lower
        if value > upper:
            return upper
        return None
    if link.min_value is not None and value < link.min_value:
        return link.min_value
    if link.max_value is not None and value > link.max_value:
        return link.max_value
    return None


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
    device = db.query(Device).filter(Device.device_uid == payload.device_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device.status != "active":
        raise HTTPException(status_code=409, detail="Device is not active yet")
    if "SENSOR" not in (device.device_type or ""):
        raise HTTPException(status_code=400, detail="Device is not a sensor")
    latest_sensor = (
        db.query(SensorData)
        .filter(SensorData.device_uid == payload.device_uid)
        .order_by(SensorData.created_at.desc())
        .first()
    )
    previous_value = latest_sensor.value if latest_sensor else payload.value
    adjusted_value = previous_value + ((payload.value - previous_value) * RANDOM_BLEND_FACTOR)
    links = (
        db.query(DeviceLink)
        .filter(DeviceLink.source_device_uid == payload.device_uid, DeviceLink.active == True)
        .all()
    )
    for link in links:
        actuator = db.query(Actuator).filter(Actuator.device_uid == link.target_device_uid).first()
        if not actuator:
            continue
        sensor_kind = (payload.sensor_type or device.device_type or "").lower()
        actuator_kind = (actuator.actuator_type or "").lower()
        if not actuator_kind or actuator_kind == "unknown":
            target_device = (
                db.query(Device).filter(Device.device_uid == link.target_device_uid).first()
            )
            actuator_kind = (target_device.device_type or "").lower() if target_device else ""
        working_value = previous_value if actuator.state == "ON" else adjusted_value
        if actuator.state == "ON":
            if "soil" in sensor_kind and "irrig" in actuator_kind:
                adjusted_value = min(100.0, working_value + IRRIGATION_STEP_ON)
            elif _is_temperature_control(sensor_kind, actuator_kind):
                target = _temperature_target(link, working_value)
                if target is not None:
                    delta = target - working_value
                    if delta > 0:
                        adjusted_value = working_value + min(delta, TEMPERATURE_CONTROL_STEP)
                    else:
                        adjusted_value = working_value + max(delta, -TEMPERATURE_CONTROL_STEP)
                else:
                    adjusted_value = working_value
            elif "temp" in sensor_kind and "vent" in actuator_kind:
                adjusted_value = working_value + VENTILATION_STEP_ON
            elif "light" in sensor_kind and "light" in actuator_kind:
                adjusted_value = working_value + LIGHT_STEP_ON
        else:
            if "soil" in sensor_kind and "irrig" in actuator_kind:
                adjusted_value = max(0.0, working_value + IRRIGATION_STEP_OFF)
            elif "light" in sensor_kind and "light" in actuator_kind:
                adjusted_value = max(0.0, working_value + LIGHT_STEP_OFF)

    adjusted_value = round(adjusted_value, 2)

    data = sensor_service.create_sensor_data(
        db=db,
        device_uid=payload.device_uid,
        value=adjusted_value,
        sensor_type=payload.sensor_type,
    )
    for link in links:
        if not link.auto_control_enabled:
            continue
        actuator = db.query(Actuator).filter(Actuator.device_uid == link.target_device_uid).first()
        target_device = db.query(Device).filter(Device.device_uid == link.target_device_uid).first()
        target_actuator_type = (target_device.device_type if target_device else None)
        is_on = bool(actuator and actuator.state == "ON")
        should_turn_on = _should_turn_on(link, adjusted_value)
        should_turn_off = _should_turn_off(link, adjusted_value)
        next_action = "ON" if should_turn_on else "OFF"
        if is_on and not should_turn_off:
            next_action = "ON"
        actuator_service.set_actuator_state(
            db=db,
            device_uid=link.target_device_uid,
            action=next_action,
            actuator_type=target_actuator_type,
        )
    return data


@router.get("/", response_model=list[SensorDataOut])
def get_sensor_data(db: Session = Depends(get_db)):
    return sensor_service.get_all_sensor_data(db)
