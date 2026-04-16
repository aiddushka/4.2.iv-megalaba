from datetime import datetime

from pydantic import BaseModel


class DeviceHistoryEntry(BaseModel):
    timestamp: str
    field: str
    old_value: str | int | float | bool | None = None
    new_value: str | int | float | bool | None = None
    changed_by: str | None = None


class DeviceBase(BaseModel):
    device_uid: str
    device_type: str
    description: str | None = None
    controller: str | None = None
    pin: int | None = None
    bus: str | None = None
    bus_address: str | None = None
    components: list[str] | None = None


class DeviceCreate(DeviceBase):
    location_hint: str | None = None


class DeviceOut(DeviceBase):
    id: int
    status: str
    accepts_data: bool
    location: str | None = None
    last_maintenance: datetime | None = None
    maintenance_notes: str | None = None
    change_history: list[DeviceHistoryEntry] | None = None

    class Config:
        orm_mode = True


class DeviceAssign(BaseModel):
    device_uid: str
    location: str


class DeviceUpdate(BaseModel):
    description: str | None = None
    location: str | None = None
    status: str | None = None
    accepts_data: bool | None = None
    last_maintenance: datetime | None = None
    maintenance_notes: str | None = None


class DeviceAdminUpdate(BaseModel):
    status: str | None = None
    last_maintenance: datetime | None = None
    maintenance_notes: str | None = None