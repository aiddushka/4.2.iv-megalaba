from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.actuator import Actuator
from app.models.device import Device
from app.models.device_link import DeviceLink
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


def _sensor_indicator(value: float, min_value: float | None, max_value: float | None) -> str:
    if min_value is None and max_value is None:
        return "unknown"
    if min_value is not None and max_value is not None:
        band = max((max_value - min_value) * 0.1, 1e-6)
        if min_value <= value <= max_value:
            return "green"
        if (min_value - band) <= value <= (max_value + band):
            return "yellow"
        return "red"
    if min_value is not None:
        if value >= min_value:
            return "green"
        if value >= min_value * 0.9:
            return "yellow"
        return "red"
    if value <= max_value:
        return "green"
    if value <= max_value * 1.1:
        return "yellow"
    return "red"


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
    latest_sensors = (
        db.query(SensorData)
        .order_by(SensorData.device_uid, SensorData.created_at.desc())
        .all()
    )
    actuators = db.query(Actuator).all()
    # Уникальные device_uid для датчиков (последнее значение по каждому)
    seen_sensor_uids = set()
    sensors_out = []
    for s in latest_sensors:
        if s.device_uid in seen_sensor_uids:
            continue
        seen_sensor_uids.add(s.device_uid)
        info = _device_info(db, s.device_uid)
        link = (
            db.query(DeviceLink)
            .filter(
                DeviceLink.source_device_uid == s.device_uid,
                DeviceLink.active == True,
            )
            .order_by(DeviceLink.id.desc())
            .first()
        )
        min_value = link.min_value if link else None
        max_value = link.max_value if link else None
        sensors_out.append({
            "device_uid": s.device_uid,
            "sensor_type": s.sensor_type,
            "value": s.value,
            "created_at": s.created_at,
            "description": info["description"],
            "location": info["location"],
            "min_value": min_value,
            "max_value": max_value,
            "indicator": _sensor_indicator(s.value, min_value, max_value),
        })
    return {
        "sensors": sensors_out,
        "actuators": [
            {
                "device_uid": a.device_uid,
                "actuator_type": a.actuator_type,
                "state": a.state,
                **(_device_info(db, a.device_uid)),
            }
            for a in actuators
        ],
        "links": [
            {
                "id": link.id,
                "source_device_uid": link.source_device_uid,
                "target_device_uid": link.target_device_uid,
                "controller": link.controller,
                "description": link.description,
                "active": link.active,
                "auto_control_enabled": link.auto_control_enabled,
                "min_value": link.min_value,
                "max_value": link.max_value,
            }
            for link in db.query(DeviceLink).order_by(DeviceLink.id.desc()).all()
        ],
    }

