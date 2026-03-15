from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.actuator import Actuator
from app.models.sensor_data import SensorData

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/state")
def get_dashboard_state(db: Session = Depends(get_db)):
    latest_sensors = (
        db.query(SensorData)
        .order_by(SensorData.device_uid, SensorData.created_at.desc())
        .all()
    )
    actuators = db.query(Actuator).all()

    return {
        "sensors": [
            {
                "device_uid": s.device_uid,
                "sensor_type": s.sensor_type,
                "value": s.value,
                "created_at": s.created_at,
            }
            for s in latest_sensors
        ],
        "actuators": [
            {
                "device_uid": a.device_uid,
                "actuator_type": a.actuator_type,
                "state": a.state,
            }
            for a in actuators
        ],
    }

