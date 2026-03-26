from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.device_schema import DeviceAssign, DeviceCreate, DeviceOut, DeviceUpdate
from app.services import device_service
from app.services.device_emulator_spawner import spawn_device_emulator

router = APIRouter(prefix="/devices", tags=["Devices"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=DeviceOut)
def register_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
):
    """Регистрация устройства без авторизации (сайт-конфигуратор с ноутбука/флешки у устройства)."""
    device = device_service.register_device(
        db=db,
        device_uid=payload.device_uid,
        device_type=payload.device_type,
        description=payload.description,
        location_hint=payload.location_hint,
    )

    # Запускаем эмулятор/скрипт устройства, чтобы оно сразу начало отправлять данные в сеть
    # (в рамках мегалабы устройство эмулируется Python-скриптом).
    spawn_device_emulator(device)

    return device


@router.get("/unassigned", response_model=list[DeviceOut])
def get_unassigned_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return device_service.get_unassigned_devices(db)


@router.get("/assigned", response_model=list[DeviceOut])
def get_assigned_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return device_service.get_assigned_devices(
        db=db, is_admin=current_user.is_admin, owner_id=current_user.id
    )


@router.post("/assign", response_model=DeviceOut)
def assign_device(
    payload: DeviceAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    device = device_service.assign_device(
        db=db, device_uid=payload.device_uid, location=payload.location
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.patch("/{device_uid}", response_model=DeviceOut)
def update_device_config(
    device_uid: str,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Изменение конфигурации устройства (описание, место) — только для админа."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    device = device_service.update_device(
        db=db,
        device_uid=device_uid,
        description=payload.description,
        location=payload.location,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device