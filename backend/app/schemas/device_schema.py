from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DeviceBase(BaseModel):
    device_uid: str
    device_type: str
    description: str | None = None
    catalog_info: str | None = None
    model_name: str | None = None
    manufacturer: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    config_settings: dict[str, Any] | None = None
    is_configured: bool | None = None


class DeviceCreate(DeviceBase):
    location_hint: str | None = None


class DeviceOut(DeviceBase):
    id: int
    status: str
    location: str | None = None
    deleted_at: datetime | None = None

    class Config:
        orm_mode = True


class DeviceAssign(BaseModel):
    device_uid: str
    location: str


class DeviceUpdate(BaseModel):
    description: str | None = None
    location: str | None = None
    catalog_info: str | None = None
    model_name: str | None = None
    manufacturer: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    config_settings: dict[str, Any] | None = None
    is_configured: bool | None = None