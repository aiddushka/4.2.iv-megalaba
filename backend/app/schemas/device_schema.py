from pydantic import BaseModel


class DeviceBase(BaseModel):
    device_uid: str
    device_type: str
    description: str | None = None
    catalog_info: str | None = None


class DeviceCreate(DeviceBase):
    location_hint: str | None = None


class DeviceOut(DeviceBase):
    id: int
    status: str
    location: str | None = None

    class Config:
        orm_mode = True


class DeviceAssign(BaseModel):
    device_uid: str
    location: str


class DeviceUpdate(BaseModel):
    description: str | None = None
    location: str | None = None
    catalog_info: str | None = None