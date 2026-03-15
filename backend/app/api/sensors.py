from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.schemas.sensor_schema import SensorDataCreate, SensorDataOut
from app.services import sensor_service

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
    data = sensor_service.create_sensor_data(
        db=db,
        device_uid=payload.device_uid,
        value=payload.value,
        sensor_type=payload.sensor_type,
    )
    return data


@router.get("/", response_model=list[SensorDataOut])
def get_sensor_data(db: Session = Depends(get_db)):
    return sensor_service.get_all_sensor_data(db)
