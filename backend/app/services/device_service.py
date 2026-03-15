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

from sqlalchemy.orm import Session
from app.models.device import Device
from app.schemas.device_schema import DeviceCreate

def create_device(db: Session, device: DeviceCreate):
    db_device = Device(
        device_uid=device.device_uid,
        type=device.type,
        name=device.name
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def get_devices(db: Session):
    return db.query(Device).all()