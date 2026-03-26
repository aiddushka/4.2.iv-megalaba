from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.actuator import Actuator
from app.models.device import Device
from app.models.sensor_data import SensorData
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _device_info(db: Session, device_uid: str) -> dict:
    d = db.query(Device).filter(Device.device_uid == device_uid).first()
    return {"description": d.description if d else None, "location": d.location if d else None}

def _is_sensor(device_type: str) -> bool:
    return device_type.upper().endswith("_SENSOR")


def _is_actuator(device_type: str) -> bool:
    return device_type.upper().endswith("_ACTUATOR")


@router.get("/state")
def get_dashboard_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Работник может смотреть дашборд только если у него есть право
    if not current_user.is_admin and not current_user.can_view_dashboard:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к дашборду запрещён. Обратитесь к администратору.",
        )

    # Показываем на дашборде "установленные" устройства.
    # Для изоляции данных: работник видит только свои (owner_id == current_user.id)
    # и общие (owner_id IS NULL) устройства.
    q = db.query(Device).filter(Device.status == "assigned")
    if not current_user.is_admin:
        q = q.filter((Device.owner_id.is_(None)) | (Device.owner_id == current_user.id))
    assigned_devices = q.all()
    sensors_by_uid: dict[str, dict] = {}
    actuators_by_uid: dict[str, dict] = {}

    for d in assigned_devices:
        if _is_sensor(d.device_type):
            sensors_by_uid[d.device_uid] = {
                "device_uid": d.device_uid,
                "sensor_type": d.device_type,
                "value": None,
                "created_at": None,
                "description": d.description,
                "location": d.location,
            }
        elif _is_actuator(d.device_type):
            actuators_by_uid[d.device_uid] = {
                "device_uid": d.device_uid,
                "actuator_type": d.device_type,
                "state": None,
                "control_mode": None,
                "description": d.description,
                "location": d.location,
            }

    latest_sensors = (
        db.query(SensorData)
        .order_by(SensorData.device_uid, SensorData.created_at.desc())
        .all()
    )
    actuators = db.query(Actuator).all()
    # Уникальные device_uid для датчиков (последнее значение по каждому)
    seen_sensor_uids = set()
    sensors_out: list[dict] = list(sensors_by_uid.values())
    for s in latest_sensors:
        if s.device_uid in seen_sensor_uids:
            continue
        # На дашборде показываем только те сенсоры, которые входят в список видимых assigned устройств
        if s.device_uid not in sensors_by_uid:
            continue
        seen_sensor_uids.add(s.device_uid)
        info = _device_info(db, s.device_uid)
        existing = sensors_by_uid.get(s.device_uid)
        item = existing
        if item is None:
            continue
        item["sensor_type"] = s.sensor_type or item.get("sensor_type")
        item["value"] = s.value
        item["created_at"] = s.created_at
        item["description"] = info["description"]
        item["location"] = info["location"]

    actuators_out_by_uid: dict[str, dict] = dict(actuators_by_uid)
    for a in actuators:
        if a.device_uid not in actuators_by_uid:
            continue
        info = _device_info(db, a.device_uid)
        item = actuators_out_by_uid.get(a.device_uid)
        if item is None:
            continue
        item["actuator_type"] = a.actuator_type or item.get("actuator_type")
        item["state"] = a.state
        item["control_mode"] = a.control_mode
        item["description"] = info["description"]
        item["location"] = info["location"]
        actuators_out_by_uid[a.device_uid] = item

    return {
        "sensors": sensors_out,
        "actuators": list(actuators_out_by_uid.values()),
    }

