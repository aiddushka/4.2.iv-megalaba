import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

SECRET_KEY = _require_env("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt принимает не более 72 байт
BCRYPT_MAX_BYTES = 72


def _truncate_password_for_bcrypt(password: str) -> str:
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) <= BCRYPT_MAX_BYTES:
        return password
    return pw_bytes[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_password = _truncate_password_for_bcrypt(plain_password)
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    password = _truncate_password_for_bcrypt(password)
    return pwd_context.hash(password)


def create_user(db: Session, username: str, password: str, is_admin: bool = False) -> User:
    user = User(
        username=username,
        hashed_password=get_password_hash(password),
        is_admin=is_admin,
        can_view_dashboard=is_admin,  # админ всегда может; работник — по умолчанию нет
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
