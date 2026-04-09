from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from pathlib import Path

from app.api import actuators, auth, automation, devices, sensors, dashboard
from app.database.base import Base
from app.database.session import engine
import app.models.device_link  # noqa: F401


def create_app() -> FastAPI:
    # создаем таблицы в БД
    Base.metadata.create_all(bind=engine)
    # миграция: добавить can_view_dashboard для существующих БД
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_dashboard BOOLEAN DEFAULT false"
                )
            )
    except Exception:
        pass
    # миграция: добавить новые поля devices для расширенной конфигурации
    try:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS controller VARCHAR(100)")
            )
            conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS pin INTEGER"))
            conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS bus VARCHAR(50)"))
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS bus_address VARCHAR(100)")
            )
            conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS components JSON"))
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_maintenance TIMESTAMP"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS maintenance_notes VARCHAR(512)"
                )
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS change_history JSON")
            )
            conn.execute(
                text("ALTER TABLE devices ALTER COLUMN status SET DEFAULT 'active'")
            )
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS device_links ("
                    "id SERIAL PRIMARY KEY, "
                    "source_device_uid VARCHAR(100) NOT NULL, "
                    "target_device_uid VARCHAR(100) NOT NULL, "
                    "controller VARCHAR(100), "
                    "description VARCHAR(255), "
                    "active BOOLEAN NOT NULL DEFAULT TRUE, "
                    "auto_control_enabled BOOLEAN NOT NULL DEFAULT FALSE, "
                    "min_value DOUBLE PRECISION, "
                    "max_value DOUBLE PRECISION, "
                    "created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE device_links ADD COLUMN IF NOT EXISTS auto_control_enabled BOOLEAN DEFAULT FALSE"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE device_links ADD COLUMN IF NOT EXISTS min_value DOUBLE PRECISION"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE device_links ADD COLUMN IF NOT EXISTS max_value DOUBLE PRECISION"
                )
            )
    except Exception:
        pass

    # Учётная запись админа по умолчанию (admin / 123)
    try:
        from app.database.session import SessionLocal
        from app.models.user import User
        from app.services import auth_service

        db = SessionLocal()
        try:
            if db.query(User).filter(User.username == "admin").first() is None:
                auth_service.create_user(db, "admin", "123", is_admin=True)
        finally:
            db.close()
    except Exception:
        pass

    app = FastAPI(title="IoT Greenhouse API")
    project_root = Path(__file__).resolve().parent.parent
    images_dir = project_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="images")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # подключаем все роутеры
    app.include_router(auth.router)
    app.include_router(devices.router)
    app.include_router(sensors.router)
    app.include_router(actuators.router)
    app.include_router(automation.router)
    app.include_router(dashboard.router)

    @app.get("/")
    def root():
        return {"message": "IoT Greenhouse API running"}

    return app


app = create_app()
