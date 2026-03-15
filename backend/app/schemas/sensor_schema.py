from datetime import datetime

from pydantic import BaseModel


class SensorDataCreate(BaseModel):
    device_uid: str
    value: float
    sensor_type: str | None = None


class SensorDataOut(BaseModel):
    id: int
    device_uid: str
    value: float
    sensor_type: str | None = None
    created_at: datetime

    class Config:
        orm_mode = True

