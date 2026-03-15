from pydantic import BaseModel


class ActuatorCommand(BaseModel):
    device_uid: str
    action: str  # ON | OFF
    actuator_type: str | None = None


class ActuatorStateOut(BaseModel):
    device_uid: str
    actuator_type: str
    state: str

    class Config:
        orm_mode = True

