from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.device_schema import (
    DeviceAssign,
    DeviceCreate,
    DeviceOut,
    DeviceUpdate,
)
from app.services import device_service
from app.services.device_emulator_spawner import spawn_device_emulator
from app.services.device_emulator_spawner import stop_device_emulator

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
        catalog_info=payload.catalog_info,
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
        db=db,
        device_uid=payload.device_uid,
        location=payload.location,
        owner_id=current_user.id,
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
        catalog_info=payload.catalog_info,
        model_name=payload.model_name,
        manufacturer=payload.manufacturer,
        min_value=payload.min_value,
        max_value=payload.max_value,
        config_settings=payload.config_settings,
        is_configured=payload.is_configured,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/{device_uid}", status_code=200)
def delete_device(
    device_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Мягкое удаление устройства: останавливаем эмулятор и переводим в status='deleted'."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    # Сначала останавливаем запущенный эмулятор
    stop_device_emulator(device_uid)

    ok = device_service.delete_device(db=db, device_uid=device_uid)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"status": "ok"}


@router.post("/{device_uid}/restore", response_model=DeviceOut)
def restore_device(
    device_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Восстановление удаленного устройства (status='assigned') + запуск эмулятора."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    ok = device_service.restore_device(db=db, device_uid=device_uid)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found")

    # Получаем устройство и запускаем эмулятор.
    from app.models.device import Device

    d = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    if d.status != "deleted":
        spawn_device_emulator(d)
    return d


@router.get("/deleted", response_model=list[DeviceOut])
def get_deleted_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return device_service.get_deleted_devices(db)


@router.patch("/{device_uid}/configure", response_model=DeviceOut)
def configure_device(
    device_uid: str,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Настройка параметров устройства (только админ)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    device = device_service.update_device(
        db=db,
        device_uid=device_uid,
        description=payload.description,
        location=payload.location,
        catalog_info=payload.catalog_info,
        model_name=payload.model_name,
        manufacturer=payload.manufacturer,
        min_value=payload.min_value,
        max_value=payload.max_value,
        config_settings=payload.config_settings,
        is_configured=payload.is_configured,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/{device_uid}/config", response_model=DeviceOut)
def get_device_config(
    device_uid: str,
    db: Session = Depends(get_db),
):
    """Получение текущих настроек устройства.
    Доступ разрешён, если устройство не удалено (для эмуляторов устройств).
    """
    from app.models.device import Device

    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device or device.status == "deleted":
        raise HTTPException(status_code=404, detail="Device not found")
    return device