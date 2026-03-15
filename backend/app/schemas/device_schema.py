from pydantic import BaseModel


class DeviceBase(BaseModel):
    device_uid: str
    device_type: str
    description: str | None = None


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

from pydantic import BaseModel

class DeviceCreate(BaseModel):
    device_uid: str
    type: str
    name: str

class DeviceResponse(BaseModel):
    id: int
    device_uid: str
    type: str
    name: str
    status: str
    configured: bool

    class Config:
        orm_mode = True