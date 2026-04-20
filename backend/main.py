from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from pathlib import Path
import os


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]

from app.api import actuators, auth, automation, devices, sensors, dashboard
from app.database.base import Base
from app.database.session import engine
from app.services import mqtt_service
import app.models.device_link  # noqa: F401


def create_app() -> FastAPI:
    # СЃРѕР·РґР°РµРј С‚Р°Р±Р»РёС†С‹ РІ Р‘Р”
    Base.metadata.create_all(bind=engine)
    # РјРёРіСЂР°С†РёСЏ: РґРѕР±Р°РІРёС‚СЊ can_view_dashboard РґР»СЏ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёС… Р‘Р”
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_dashboard BOOLEAN DEFAULT false"
                )
            )
    except Exception:
        pass
    # РјРёРіСЂР°С†РёСЏ: РґРѕР±Р°РІРёС‚СЊ РЅРѕРІС‹Рµ РїРѕР»СЏ devices РґР»СЏ СЂР°СЃС€РёСЂРµРЅРЅРѕР№ РєРѕРЅС„РёРіСѓСЂР°С†РёРё
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
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS accepts_data BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_token_hash VARCHAR(128)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_token_version INTEGER NOT NULL DEFAULT 1"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_token_revoked_at TIMESTAMP"
                )
            )
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
            conn.execute(text("ALTER TABLE devices DROP COLUMN IF EXISTS device_token"))
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

    # Bootstrap admin account can be configured via env.
    try:
        from app.database.session import SessionLocal
        from app.models.user import User
        from app.services import auth_service

        db = SessionLocal()
        try:
            bootstrap_enabled = os.getenv("BOOTSTRAP_ADMIN_ENABLED", "false").lower() == "true"
            bootstrap_user = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "").strip()
            bootstrap_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
            if bootstrap_enabled:
                if not bootstrap_user or not bootstrap_password:
                    raise RuntimeError("BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD are required when BOOTSTRAP_ADMIN_ENABLED=true")
                if db.query(User).filter(User.username == bootstrap_user).first() is None:
                    auth_service.create_user(db, bootstrap_user, bootstrap_password, is_admin=True)
        finally:
            db.close()
    except Exception:
        pass

    app = FastAPI(title="IoT Greenhouse API")
    backend_root = Path(__file__).resolve().parent
    images_dir = backend_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="images")

    cors_origins = _parse_csv_env(
        "CORS_ALLOW_ORIGINS",
        "https://localhost:3000,https://localhost:3001",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Service-to-service key for sensor-emulator-manager internal calls (e.g. runtime secrets).
    app.state.manager_key = _require_env("MANAGER_KEY")
    app.state.device_token_pepper = _require_env("DEVICE_TOKEN_PEPPER")

    # РїРѕРґРєР»СЋС‡Р°РµРј РІСЃРµ СЂРѕСѓС‚РµСЂС‹
    app.include_router(auth.router)
    app.include_router(devices.router)
    app.include_router(sensors.router)
    app.include_router(actuators.router)
    app.include_router(automation.router)
    app.include_router(dashboard.router)

    @app.get("/")
    def root():
        return {"message": "IoT Greenhouse API running"}

    @app.on_event("startup")
    def startup_mqtt_listener():
        mqtt_service.start_mqtt_listener()

    @app.on_event("shutdown")
    def shutdown_mqtt_listener():
        mqtt_service.stop_mqtt_listener()

    return app


app = create_app()


