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

