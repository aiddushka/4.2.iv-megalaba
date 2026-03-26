from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.actuator_schema import (
    ActuatorCommand,
    ActuatorModeUpdate,
    ActuatorStateOut,
)
from app.schemas.device_config_schema import DeviceConfigOut, ScheduleConfig
from app.services import device_config_service, device_service
from app.services import actuator_service

router = APIRouter(prefix="/actuators", tags=["Actuators"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/control", response_model=ActuatorStateOut)
def control_actuator(cmd: ActuatorCommand, request: Request, db: Session = Depends(get_db)):
    actuator = actuator_service.set_actuator_state(
        db=db,
        device_uid=cmd.device_uid,
        action=cmd.action,
        actuator_type=cmd.actuator_type,
    )

    # Отправляем команду устройству через MQTT, чтобы эмулятор/реальное устройство
    # подтвердило состояние (и могло быть показано на дашборде).
    mqtt_manager = getattr(request.app.state, "mqtt_manager", None)
    if mqtt_manager is not None:
        mqtt_manager.publish_actuator_command(
            device_uid=actuator.device_uid,
            actuator_type=actuator.actuator_type,
            action=actuator.state,
        )

    return ActuatorStateOut(
        device_uid=actuator.device_uid,
        actuator_type=actuator.actuator_type,
        state=actuator.state,
        control_mode=actuator.control_mode,
    )


@router.patch("/{device_uid}/mode", response_model=ActuatorStateOut)
def update_actuator_mode(
    device_uid: str,
    payload: ActuatorModeUpdate,
    db: Session = Depends(get_db),
):
    if payload.control_mode not in {"AUTO", "MANUAL"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="control_mode must be AUTO or MANUAL",
        )
    actuator = actuator_service.set_actuator_mode(
        db=db, device_uid=device_uid, control_mode=payload.control_mode
    )
    if not actuator:
        raise HTTPException(status_code=404, detail="Actuator not found")
    return ActuatorStateOut(
        device_uid=actuator.device_uid,
        actuator_type=actuator.actuator_type,
        state=actuator.state,
        control_mode=actuator.control_mode,
    )


@router.get("/status", response_model=list[ActuatorStateOut])
def get_actuators_status(db: Session = Depends(get_db)):
    actuators = actuator_service.get_actuators(db)
    return [
        ActuatorStateOut(
            device_uid=a.device_uid,
            actuator_type=a.actuator_type,
            state=a.state,
            control_mode=a.control_mode,
        )
        for a in actuators
    ]


@router.post("/{device_uid}/toggle", response_model=ActuatorStateOut)
def toggle_actuator(
    device_uid: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Включить/выключить актуатор (ON/OFF)."""
    # Получаем текущий статус актуатора
    # Проще: читаем напрямую из модели
    from app.models.actuator import Actuator

    act = db.query(Actuator).filter(Actuator.device_uid == device_uid).first()
    new_action = "OFF"
    if act and act.state == "OFF":
        new_action = "ON"
    elif act and act.state == "ON":
        new_action = "OFF"
    elif not act:
        new_action = "ON"

    # Обновляем состояние и публикуем команду
    actuator_type = act.actuator_type if act else None
    actuator_out = actuator_service.set_actuator_state(
        db=db, device_uid=device_uid, action=new_action, actuator_type=actuator_type
    )

    mqtt_manager = getattr(request.app.state, "mqtt_manager", None)
    if mqtt_manager is not None:
        mqtt_manager.publish_actuator_command(
            device_uid=actuator_out.device_uid,
            actuator_type=actuator_out.actuator_type,
            action=actuator_out.state,
        )

    return ActuatorStateOut(
        device_uid=actuator_out.device_uid,
        actuator_type=actuator_out.actuator_type,
        state=actuator_out.state,
        control_mode=actuator_out.control_mode,
    )


@router.get("/{device_uid}/status", response_model=ActuatorStateOut)
def get_actuator_status(device_uid: str, db: Session = Depends(get_db)):
    from app.models.actuator import Actuator

    act = db.query(Actuator).filter(Actuator.device_uid == device_uid).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actuator not found")
    return ActuatorStateOut(
        device_uid=act.device_uid,
        actuator_type=act.actuator_type,
        state=act.state,
        control_mode=act.control_mode,
    )


@router.post("/{device_uid}/schedule", response_model=DeviceConfigOut)
def set_actuator_schedule(
    device_uid: str,
    payload: ScheduleConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Установить расписание работы (только админ)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    params = payload.dict(exclude_none=True)
    cfg = device_config_service.upsert_config(
        db=db,
        device_uid=device_uid,
        config_type="schedule",
        parameters=params,
        created_by=current_user.id,
    )

    device_service.update_device(
        db=db,
        device_uid=device_uid,
        config_settings=params,
        is_configured=True,
    )

    return DeviceConfigOut(
        device_uid=cfg.device_uid,
        config_type=cfg.config_type,
        parameters=cfg.parameters,
    )
