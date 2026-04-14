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
    try:
        return sensor_service.ingest_sensor_data(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/", response_model=list[SensorDataOut])
def get_sensor_data(db: Session = Depends(get_db)):
    return sensor_service.get_all_sensor_data(db)


