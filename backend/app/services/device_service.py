from datetime import datetime

from sqlalchemy.orm import Session

from app.models.device import Device


def register_device(
    db: Session,
    device_uid: str,
    device_type: str,
    description: str | None = None,
    location_hint: str | None = None,
    controller: str | None = None,
    pin: int | None = None,
    bus: str | None = None,
    bus_address: str | None = None,
    components: list[str] | None = None,
) -> Device:
    device = Device(
        device_uid=device_uid,
        device_type=device_type,
        description=description,
        controller=controller,
        pin=pin,
        bus=bus,
        bus_address=bus_address,
        components=components,
        location=location_hint,
        # После регистрации устройство сразу считается установленным и видимым на Dashboard.
        # Контейнер/эмулятор поднимется менеджером через orchestration-state.
        status="active",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_unassigned_devices(db: Session) -> list[Device]:
    return db.query(Device).filter(Device.status == "unassigned").all()


def get_assigned_devices(db: Session) -> list[Device]:
    # Исторически существовал статус `unassigned` и отдельная страница установки.
    # Теперь устройства отображаются на Dashboard сразу после регистрации,
    # поэтому /devices/assigned фактически возвращает полный список.
    return get_all_devices(db)


def get_device_by_uid(db: Session, device_uid: str) -> Device | None:
    return db.query(Device).filter(Device.device_uid == device_uid).first()


def get_all_devices(db: Session) -> list[Device]:
    return db.query(Device).order_by(Device.id.asc()).all()


def log_change_history(
    device: Device,
    field: str,
    old_value,
    new_value,
    changed_by: str | None = None,
) -> None:
    if old_value == new_value:
        return
    history = list(device.change_history or [])
    history.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "changed_by": changed_by,
        }
    )
    device.change_history = history


def assign_device(db: Session, device_uid: str, location: str) -> Device | None:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return None
    log_change_history(device, "location", device.location, location, changed_by="admin")
    device.location = location
    log_change_history(device, "status", device.status, "active", changed_by="admin")
    device.status = "active"
    db.commit()
    db.refresh(device)
    return device


def disable_device(db: Session, device_uid: str, changed_by: str | None = None) -> Device | None:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return None
    if device.status != "disabled":
        log_change_history(device, "status", device.status, "disabled", changed_by)
        device.status = "disabled"
        db.commit()
        db.refresh(device)
    return device


def update_device(
    db: Session,
    device_uid: str,
    description: str | None = None,
    location: str | None = None,
    status: str | None = None,
    accepts_data: bool | None = None,
    last_maintenance: datetime | None = None,
    maintenance_notes: str | None = None,
    changed_by: str | None = None,
) -> Device | None:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return None
    if description is not None:
        log_change_history(device, "description", device.description, description, changed_by)
        device.description = description
    if location is not None:
        log_change_history(device, "location", device.location, location, changed_by)
        device.location = location
    if status is not None:
        log_change_history(device, "status", device.status, status, changed_by)
        device.status = status
    if accepts_data is not None:
        log_change_history(device, "accepts_data", bool(device.accepts_data), bool(accepts_data), changed_by)
        device.accepts_data = bool(accepts_data)
    if last_maintenance is not None:
        log_change_history(
            device,
            "last_maintenance",
            device.last_maintenance.isoformat() if device.last_maintenance else None,
            last_maintenance.isoformat(),
            changed_by,
        )
        device.last_maintenance = last_maintenance
    if maintenance_notes is not None:
        log_change_history(
            device, "maintenance_notes", device.maintenance_notes, maintenance_notes, changed_by
        )
        device.maintenance_notes = maintenance_notes
    db.commit()
    db.refresh(device)
    return device