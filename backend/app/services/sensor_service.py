import os

from sqlalchemy.orm import Session

from app.models.actuator import Actuator
from app.models.device import Device
from app.models.device_link import DeviceLink
from app.models.sensor_data import SensorData
from app.schemas.sensor_schema import SensorDataCreate
from app.services import actuator_service, automation_service, device_token_service

TEMPERATURE_CONTROL_STEP = 0.45
DEVICE_TOKEN_PEPPER = os.getenv("DEVICE_TOKEN_PEPPER", "").strip()
if not DEVICE_TOKEN_PEPPER:
    raise RuntimeError("Missing required environment variable: DEVICE_TOKEN_PEPPER")
RANDOM_BLEND_FACTOR = 0.2
VENTILATION_HUMIDITY_AIR_STEP_ON = -1.0
VENTILATION_HUMIDITY_AIR_STEP_OFF = 0.3
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


def create_sensor_data(
    db: Session, device_uid: str, value: float, sensor_type: str | None = None
) -> SensorData:
    data = SensorData(device_uid=device_uid, value=value, sensor_type=sensor_type)
    db.add(data)
    db.commit()
    db.refresh(data)
    return data


def get_all_sensor_data(db: Session) -> list[SensorData]:
    return db.query(SensorData).order_by(SensorData.created_at.desc()).all()


def ingest_sensor_data(db: Session, payload: SensorDataCreate) -> SensorData:
    if not payload.device_uid or payload.value is None:
        raise ValueError("device_uid and value required")

    device = db.query(Device).filter(Device.device_uid == payload.device_uid).first()
    if not device:
        raise LookupError("Device not found")
    if hasattr(device, "accepts_data") and not bool(device.accepts_data):
        raise RuntimeError("Device is not accepting data")
    # После регистрации (status=unassigned) контейнер уже может быть запущен и слать данные —
    # принимаем их так же, как для active. Останавливаем обработку только при disabled.
    if device.status == "disabled":
        raise RuntimeError("Device is disabled")
    if "SENSOR" not in (device.device_type or ""):
        raise ValueError("Device is not a sensor")

    if getattr(device, "device_token_hash", None):
        if not device_token_service.verify_device_token(
            device, payload.device_token, DEVICE_TOKEN_PEPPER
        ):
            raise PermissionError("Invalid or revoked device token")

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
        target_device = db.query(Device).filter(Device.device_uid == link.target_device_uid).first()
        if not target_device:
            continue
        if not automation_service.are_devices_compatible(
            device.device_type or "",
            target_device.device_type or "",
        ):
            continue
        sensor_kind = (payload.sensor_type or device.device_type or "").lower()
        actuator_kind = (actuator.actuator_type or "").lower()
        if not actuator_kind or actuator_kind == "unknown":
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
            elif "humidity_air" in sensor_kind and "vent" in actuator_kind:
                adjusted_value = max(0.0, working_value + VENTILATION_HUMIDITY_AIR_STEP_ON)
            elif "light" in sensor_kind and "light" in actuator_kind:
                adjusted_value = working_value + LIGHT_STEP_ON
        else:
            if "soil" in sensor_kind and "irrig" in actuator_kind:
                adjusted_value = max(0.0, working_value + IRRIGATION_STEP_OFF)
            elif "humidity_air" in sensor_kind and "vent" in actuator_kind:
                adjusted_value = min(100.0, working_value + VENTILATION_HUMIDITY_AIR_STEP_OFF)
            elif "light" in sensor_kind and "light" in actuator_kind:
                adjusted_value = max(0.0, working_value + LIGHT_STEP_OFF)

    adjusted_value = round(adjusted_value, 2)
    data = create_sensor_data(
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
        if not target_device:
            continue
        if not automation_service.are_devices_compatible(
            device.device_type or "",
            target_device.device_type or "",
        ):
            continue
        target_actuator_type = target_device.device_type if target_device else None
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

