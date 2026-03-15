from sqlalchemy.orm import Session

from app.models.device import Device


def register_device(
    db: Session,
    device_uid: str,
    device_type: str,
    description: str | None = None,
    location_hint: str | None = None,
) -> Device:
    device = Device(
        device_uid=device_uid,
        device_type=device_type,
        description=description,
        location=location_hint,
        status="unassigned",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_unassigned_devices(db: Session) -> list[Device]:
    return db.query(Device).filter(Device.status == "unassigned").all()


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
) -> Device | None:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        return None
    if description is not None:
        device.description = description
    if location is not None:
        device.location = location
    db.commit()
    db.refresh(device)
    return device