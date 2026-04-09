from datetime import datetime

from pydantic import BaseModel


class AutomationRuleBase(BaseModel):
    name: str
    sensor_type: str
    condition: str
    threshold: str
    actuator_type: str
    action: str


class AutomationRuleCreate(AutomationRuleBase):
    ...


class AutomationRuleOut(AutomationRuleBase):
    id: int

    class Config:
        orm_mode = True


class DeviceLinkBase(BaseModel):
    source_device_uid: str
    target_device_uid: str
    controller: str | None = None
    description: str | None = None
    active: bool = True
    auto_control_enabled: bool = False
    min_value: float | None = None
    max_value: float | None = None


class DeviceLinkCreate(DeviceLinkBase):
    ...


class DeviceLinkUpdate(BaseModel):
    description: str | None = None
    auto_control_enabled: bool | None = None
    min_value: float | None = None
    max_value: float | None = None


class DeviceLinkOut(DeviceLinkBase):
    id: int
    created_at: datetime | None = None

    class Config:
        orm_mode = True

