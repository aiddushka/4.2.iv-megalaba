from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.schemas.device_config_schema import DeviceConfigOut, ThresholdConfig
from app.schemas.sensor_schema import SensorDataCreate, SensorDataOut
from app.services import device_config_service, device_service, sensor_service

from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(tags=["Sensors"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/sensor-data/", response_model=SensorDataOut)
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


@router.get("/sensor-data/", response_model=list[SensorDataOut])
def get_sensor_data(db: Session = Depends(get_db)):
    return sensor_service.get_all_sensor_data(db)


@router.post("/sensors/{device_uid}/threshold", response_model=DeviceConfigOut)
def set_sensor_threshold(
    device_uid: str,
    payload: ThresholdConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    params = payload.dict(exclude_none=True)
    cfg = device_config_service.upsert_config(
        db=db,
        device_uid=device_uid,
        config_type="threshold",
        parameters=params,
        created_by=current_user.id,
    )

    # Обновляем поля устройства, чтобы в UI были диапазоны и статус "настроено".
    device_service.update_device(
        db=db,
        device_uid=device_uid,
        min_value=params.get("min_value"),
        max_value=params.get("max_value"),
        config_settings=params,
        is_configured=True,
    )

    return DeviceConfigOut(
        device_uid=cfg.device_uid,
        config_type=cfg.config_type,
        parameters=cfg.parameters,
    )


@router.get("/sensors/{device_uid}/threshold", response_model=DeviceConfigOut)
def get_sensor_threshold(
    device_uid: str,
    db: Session = Depends(get_db),
    # Эмулятору устройства не нужен JWT, поэтому GET доступен без авторизации.
):
    cfg = device_config_service.get_config(db=db, device_uid=device_uid, config_type="threshold")
    if not cfg:
        raise HTTPException(status_code=404, detail="Threshold not found")
    return DeviceConfigOut(
        device_uid=cfg.device_uid,
        config_type=cfg.config_type,
        parameters=cfg.parameters,
    )
