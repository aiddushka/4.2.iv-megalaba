import secrets

from sqlalchemy.orm import Session

from app.models.device import Device


def register_device(
    db: Session,
    device_uid: str,
    device_type: str,
    description: str | None = None,
    catalog_info: str | None = None,
    location_hint: str | None = None,
) -> Device:
    existing = db.query(Device).filter(Device.device_uid == device_uid).first()
    if existing:
        # Устройство уже зарегистрировано. Секрет остаётся прежним.
        return existing

    device_secret = secrets.token_urlsafe(32)
    device = Device(
        device_uid=device_uid,
        device_type=device_type,
        description=description,
        catalog_info=catalog_info,
        location=location_hint,
        status="unassigned",
        device_secret=device_secret,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_unassigned_devices(db: Session) -> list[Device]:
    return db.query(Device).filter(Device.status == "unassigned").all()


def get_assigned_devices(db: Session, is_admin: bool, owner_id: int) -> list[Device]:
    """
    Изоляция данных:
    - админ видит все assigned
    - работник видит либо свои (owner_id == current_user.id), либо "общие" устройства (owner_id IS NULL)
    """
    q = db.query(Device).filter(Device.status == "assigned")
    if is_admin:
        return q.all()
    return q.filter((Device.owner_id.is_(None)) | (Device.owner_id == owner_id)).all()


def assign_device(db: Session, device_uid: str, location: str) -> Device | None:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return None
    device.location = location
    device.status = "assigned"
    db.commit()
    db.refresh(device)
    return device


def update_device(
    db: Session,
    device_uid: str,
    description: str | None = None,
    location: str | None = None,
    catalog_info: str | None = None,
) -> Device | None:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return None
    if description is not None:
        device.description = description
    if location is not None:
        device.location = location
    if catalog_info is not None:
        device.catalog_info = catalog_info
    db.commit()
    db.refresh(device)
    return device