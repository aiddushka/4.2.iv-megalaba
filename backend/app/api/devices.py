from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.device import Device
from app.models.user import User
from app.models.device_link import DeviceLink
from app.schemas.device_schema import DeviceAssign, DeviceCreate, DeviceOut, DeviceUpdate
from app.services import device_service, mqtt_service

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


@router.get("/status/{device_uid}")
def get_device_status_public(
    device_uid: str,
    db: Session = Depends(get_db),
):
    """Публичный статус устройства для эмуляторов/устройств без авторизации."""
    device = device_service.get_device_by_uid(db=db, device_uid=device_uid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {
        "device_uid": device.device_uid,
        "device_type": device.device_type,
        "status": device.status,
    }


@router.get("/active-sensors")
def get_active_sensors_public(db: Session = Depends(get_db)):
    """Публичный список активных датчиков для менеджера эмуляторов."""
    devices = (
        db.query(Device)
        .filter(Device.status == "active", Device.device_type.like("%SENSOR%"))
        .all()
    )
    return [
        {"device_uid": d.device_uid, "device_type": d.device_type, "status": d.status}
        for d in devices
    ]


@router.get("/heartbeats")
def get_device_heartbeats():
    return mqtt_service.get_all_heartbeats()


@router.get("/orchestration-state")
def get_orchestration_state(db: Session = Depends(get_db)):
    """
    Публичный endpoint для менеджера контейнеров.
    Возвращает желаемое состояние жизненного цикла для каждого устройства.
    """
    devices = device_service.get_all_devices(db)
    return [
        {
            "device_uid": d.device_uid,
            "device_type": d.device_type,
            "status": d.status,
            # Контейнеры должны подниматься сразу после регистрации устройства (status=unassigned),
            # и останавливаться только при явном выключении (status=disabled).
            "desired_runtime_state": "stopped" if d.status == "disabled" else "running",
        }
        for d in devices
    ]


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
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администратор может удалять устройства")

    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")

    # Удалить из actuator (если есть)
    from app.models.actuator import Actuator

    db.query(Actuator).filter(Actuator.device_uid == device_uid).delete()

    # Удалить из sensor_data (если есть)
    from app.models.sensor_data import SensorData

    db.query(SensorData).filter(SensorData.device_uid == device_uid).delete()

    # Удалить связанные device_links
    db.query(DeviceLink).filter(
        (DeviceLink.source_device_uid == device_uid)
        |
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
        accepts_data=payload.accepts_data,
        last_maintenance=payload.last_maintenance,
        maintenance_notes=payload.maintenance_notes,
        changed_by=current_user.username,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/public/list")
def list_devices_public(db: Session = Depends(get_db)):
    """
    Публичный список устройств для конфигуратора (порт 3001).
    Возвращает базовую информацию + "с кем связь".
    """
    devices = device_service.get_all_devices(db)
    links = db.query(DeviceLink).filter(DeviceLink.active == True).all()
    linked_by_uid: dict[str, set[str]] = {}
    for link in links:
        linked_by_uid.setdefault(link.source_device_uid, set()).add(link.target_device_uid)
        linked_by_uid.setdefault(link.target_device_uid, set()).add(link.source_device_uid)

    def _linked(u: str) -> list[str]:
        return sorted(list(linked_by_uid.get(u, set())))

    return [
        {
            "device_uid": d.device_uid,
            "device_type": d.device_type,
            "location": d.location,
            "status": d.status,
            "accepts_data": bool(getattr(d, "accepts_data", True)),
            "linked_device_uids": _linked(d.device_uid),
        }
        for d in devices
    ]


@router.patch("/public/{device_uid}/runtime")
def set_device_runtime_public(
    device_uid: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Публичное включение/выключение устройства для конфигуратора (порт 3001).
    Меняет Device.status между 'active' и 'disabled' (контейнер старт/стоп делается sensor-emulator-manager).
    """
    status_value = payload.get("status")
    if status_value not in {"active", "disabled"}:
        raise HTTPException(status_code=400, detail="status must be 'active' or 'disabled'")
    existing = device_service.get_device_by_uid(db=db, device_uid=device_uid)
    if not existing:
        raise HTTPException(status_code=404, detail="Device not found")

    # Важно: регистрация на 3001 создаёт устройство как unassigned.
    # Кнопка "Включить" должна запускать контейнер, не переводя устройство в active
    # (иначе оно пропадёт со страницы /unassigned на дашборде).
    next_status = status_value
    if status_value == "active" and existing.status == "disabled":
        next_status = "unassigned"

    device = device_service.update_device(
        db=db,
        device_uid=device_uid,
        status=next_status,
        changed_by="public-configurator",
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"ok": True, "device_uid": device_uid, "status": device.status}


@router.delete("/public/{device_uid}")
def delete_device_public(device_uid: str, db: Session = Depends(get_db)):
    """
    Публичное удаление устройства для конфигуратора (порт 3001).
    Удаляет запись из БД; контейнер будет удалён менеджером, когда устройство исчезнет из orchestration-state.
    """
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Устройство не найдено")

    from app.models.actuator import Actuator
    from app.models.sensor_data import SensorData

    db.query(Actuator).filter(Actuator.device_uid == device_uid).delete()
    db.query(SensorData).filter(SensorData.device_uid == device_uid).delete()
    db.query(DeviceLink).filter(
        (DeviceLink.source_device_uid == device_uid) | (DeviceLink.target_device_uid == device_uid)
    ).delete()
    db.delete(device)
    db.commit()

    return {"ok": True, "message": f"Устройство {device_uid} удалено"}