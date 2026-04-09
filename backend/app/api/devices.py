from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.models.device import Device        
from app.models.device_link import DeviceLink 
from app.schemas.device_schema import DeviceAssign, DeviceCreate, DeviceOut, DeviceUpdate
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["Devices"])

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
        controller=payload.controller,
        pin=payload.pin,
        bus=payload.bus,
        bus_address=payload.bus_address,
        components=payload.components,
    )
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
    return device_service.get_assigned_devices(db)


@router.get("/{device_uid}", response_model=DeviceOut)
def get_device(
    device_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = device_service.get_device_by_uid(db=db, device_uid=device_uid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


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


@router.delete("/{device_uid}")
async def delete_device(
    device_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Только администратор может удалять устройства
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администратор может удалять устройства")
    
    # Найти устройство
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")
    
    # Удалить связанные device_links
    db.query(DeviceLink).filter(
        (DeviceLink.source_device_uid == device_uid) | 
        (DeviceLink.target_device_uid == device_uid)
    ).delete()
    
    # Удалить устройство
    db.delete(device)
    db.commit()
    
    return {"ok": True, "message": f"Устройство {device_uid} удалено"}

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
        status=payload.status,
        last_maintenance=payload.last_maintenance,
        maintenance_notes=payload.maintenance_notes,
        changed_by=current_user.username,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device