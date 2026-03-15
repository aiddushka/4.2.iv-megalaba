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
        sensors_out.append({
            "device_uid": s.device_uid,
            "sensor_type": s.sensor_type,
            "value": s.value,
            "created_at": s.created_at,
            "description": info["description"],
            "location": info["location"],
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
    }

