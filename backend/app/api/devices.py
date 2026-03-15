from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.schemas.device_schema import DeviceAssign, DeviceCreate, DeviceOut
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["Devices"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=DeviceOut)
def register_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    device = device_service.register_device(
        db=db,
        device_uid=payload.device_uid,
        device_type=payload.device_type,
        description=payload.description,
        location_hint=payload.location_hint,
    )
    return device


@router.get("/unassigned", response_model=list[DeviceOut])
def get_unassigned_devices(db: Session = Depends(get_db)):
    return device_service.get_unassigned_devices(db)


@router.post("/assign", response_model=DeviceOut)
def assign_device(payload: DeviceAssign, db: Session = Depends(get_db)):
    device = device_service.assign_device(
        db=db, device_uid=payload.device_uid, location=payload.location
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.schemas.device_schema import DeviceCreate, DeviceResponse
from app.services.device_service import create_device, get_devices

router = APIRouter(prefix="/devices", tags=["Devices"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=DeviceResponse)
def register_device(device: DeviceCreate, db: Session = Depends(get_db)):
    return create_device(db, device)

@router.get("/", response_model=list[DeviceResponse])
def list_devices(db: Session = Depends(get_db)):
    return get_devices(db)