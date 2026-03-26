from typing import Any

from pydantic import BaseModel


class ThresholdConfig(BaseModel):
    min_value: float | None = None
    max_value: float | None = None
    calibration_offset: float | None = None
    frequency_seconds: float | None = None

    class Config:
        extra = "allow"


class ScheduleConfig(BaseModel):
    on_duration_seconds: float | None = None
    off_duration_seconds: float | None = None
    enabled: bool | None = None
    class Config:
        extra = "allow"


class DeviceConfigOut(BaseModel):
    device_uid: str
    config_type: str
    parameters: dict[str, Any]

