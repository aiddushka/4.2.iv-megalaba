import secrets

from sqlalchemy.orm import Session

from app.models.device import Device


def register_device(
    db: Session,
    device_uid: str,
    device_type: str,
    description: str | None = None,
    catalog_info: str | None = None,
    model_name: str | None = None,
    manufacturer: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    config_settings: dict | None = None,
    is_configured: bool | None = None,
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
        model_name=model_name,
        manufacturer=manufacturer,
        min_value=min_value,
        max_value=max_value,
        config_settings=config_settings,
        is_configured=is_configured if is_configured is not None else False,
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


def assign_device(
    db: Session, device_uid: str, location: str, owner_id: int | None = None
) -> Device | None:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return None
    device.location = location
    device.status = "assigned"
    device.owner_id = owner_id
    db.commit()
    db.refresh(device)
    return device


def update_device(
    db: Session,
    device_uid: str,
    description: str | None = None,
    location: str | None = None,
    catalog_info: str | None = None,
    model_name: str | None = None,
    manufacturer: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    config_settings: dict[str, object] | None = None,
    is_configured: bool | None = None,
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
    if model_name is not None:
        device.model_name = model_name
    if manufacturer is not None:
        device.manufacturer = manufacturer
    if min_value is not None:
        device.min_value = min_value
    if max_value is not None:
        device.max_value = max_value
    if config_settings is not None:
        device.config_settings = config_settings
    if is_configured is not None:
        device.is_configured = is_configured
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, device_uid: str) -> bool:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return False
    # Мягкое удаление
    from datetime import datetime

    device.status = "deleted"
    device.deleted_at = datetime.utcnow()
    device.is_configured = False
    device.owner_id = None
    db.commit()
    return True


def restore_device(db: Session, device_uid: str) -> bool:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return False
    device.status = "assigned"
    device.deleted_at = None
    # При восстановлении сохраняем флаг настроенности.
    db.commit()
    db.refresh(device)
    return True


def get_deleted_devices(db: Session) -> list[Device]:
    return db.query(Device).filter(Device.status == "deleted").all()
