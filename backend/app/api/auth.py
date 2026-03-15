from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.auth_schema import (
    DashboardAccessUpdate,
    Token,
    UserCreate,
    UserOut,
    WorkerOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    is_first = db.query(User).count() == 0
    user = auth_service.create_user(
        db, user_in.username, user_in.password, is_admin=is_first
    )
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user


@router.get("/workers", response_model=list[WorkerOut])
def list_workers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Список всех пользователей-работников (не админов) для управления доступом к дашборду."""
    workers = db.query(User).filter(User.is_admin.is_(False)).all()
    return workers


@router.patch("/workers/{user_id}/dashboard-access", response_model=WorkerOut)
def set_worker_dashboard_access(
    user_id: int,
    payload: DashboardAccessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Включить или запретить работнику доступ на просмотр дашборда."""
    user = db.query(User).filter(User.id == user_id, User.is_admin.is_(False)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Worker not found")
    user.can_view_dashboard = payload.can_view_dashboard
    db.commit()
    db.refresh(user)
    return user

