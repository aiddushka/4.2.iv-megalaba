import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.device import Device
from app.models.user import User
from app.models.device_link import DeviceLink
from app.schemas.device_schema import (
    DeviceAssign,
    DeviceCreate,
    DeviceOut,
    DeviceRegisteredOut,
    DeviceUpdate,
)
from app.services import device_service, device_token_service, mqtt_service

router = APIRouter(prefix="/devices", tags=["Devices"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=DeviceRegisteredOut)
def register_device(
    payload: DeviceCreate,
    request: Request,
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
    pepper = request.app.state.device_token_pepper
    token = device_token_service.generate_device_token()
    device_token_service.set_device_token(db=db, device=device, token=token, pepper=pepper)
    # Return token only once (registration response).
    return {**DeviceOut.from_orm(device).dict(), "device_token": token}


def _require_manager_key(request: Request) -> None:
    expected = getattr(request.app.state, "manager_key", "") or ""
    provided = (request.headers.get("x-manager-key") or "").strip()
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=403, detail="Manager key required")


@router.get("/internal/orchestration-state")
def get_orchestration_state_internal(request: Request, db: Session = Depends(get_db)):
    """
    INTERNAL endpoint for sensor-emulator-manager.
    Same as /devices/orchestration-state, plus token version metadata for runtime sync.
    Protected by X-Manager-Key header.
    """
    _require_manager_key(request)
    devices = device_service.get_all_devices(db)
    # Internal state intentionally does not expose raw device token.
    rows: list[dict] = []
    for d in devices:
        rows.append(
            {
                "device_uid": d.device_uid,
                "device_type": d.device_type,
                "status": d.status,
                "desired_runtime_state": "stopped" if d.status == "disabled" else "running",
                "device_token_version": int(getattr(d, "device_token_version", 1) or 1),
            }
        )
    return rows


@router.get("/internal/runtime-token/{device_uid}")
def get_runtime_token_internal(
    device_uid: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    INTERNAL endpoint for sensor-emulator-manager.
    Returns token for exactly one device (least-privilege alternative to bulk state endpoint).
    Protected by X-Manager-Key header.
    """
    _require_manager_key(request)
    device = device_service.get_device_by_uid(db=db, device_uid=device_uid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {
        "device_uid": device.device_uid,
        "device_token": getattr(device, "device_token", None),
        "device_token_version": int(getattr(device, "device_token_version", 1) or 1),
    }


@router.get("/internal/metrics")
def get_internal_metrics(request: Request):
    """
    INTERNAL endpoint for quick runtime observability.
    Protected by X-Manager-Key header.
    """
    _require_manager_key(request)
    stale_seconds = int(os.getenv("HEARTBEAT_STALE_SECONDS", "30"))
    runtime = mqtt_service.get_runtime_stats()
    heartbeat_ages = mqtt_service.get_heartbeat_ages_seconds()
    stale_devices = sorted([uid for uid, age in heartbeat_ages.items() if age > stale_seconds])
    max_age = max(heartbeat_ages.values()) if heartbeat_ages else None
    return {
        "mqtt": runtime,
        "heartbeat_stale_seconds": stale_seconds,
        "heartbeat_ages_seconds": heartbeat_ages,
        "stale_devices": stale_devices,
        "max_heartbeat_age_seconds": max_age,
    }


@router.post("/token/rotate/{device_uid}")
def rotate_device_token(
    device_uid: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    device = device_service.get_device_by_uid(db=db, device_uid=device_uid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    pepper = request.app.state.device_token_pepper
    token = device_token_service.generate_device_token()
    device_token_service.set_device_token(db=db, device=device, token=token, pepper=pepper)
    return {"ok": True, "device_uid": device_uid, "device_token": token, "version": device.device_token_version}


@router.post("/token/revoke/{device_uid}")
def revoke_device_token(
    device_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    device = device_service.get_device_by_uid(db=db, device_uid=device_uid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device_token_service.revoke_device_token(db=db, device=device)
    return {"ok": True, "device_uid": device_uid}


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
            # Контейнеры поднимаются сразу после регистрации устройства,
            # и останавливаются только при явном выключении (status=disabled).
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

    # Registration on 3001 creates device with status=unassigned. Enabling should not move it to active
    # (otherwise it disappears from /unassigned dashboard page).
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