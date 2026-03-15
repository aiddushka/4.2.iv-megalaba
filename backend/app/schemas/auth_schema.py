from pydantic import BaseModel


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_admin: bool
    can_view_dashboard: bool = False

    class Config:
        orm_mode = True


class WorkerOut(UserBase):
    id: int
    is_admin: bool
    can_view_dashboard: bool

    class Config:
        orm_mode = True


class DashboardAccessUpdate(BaseModel):
    can_view_dashboard: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None

