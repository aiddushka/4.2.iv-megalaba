import os
import subprocess
import sys
from typing import Callable

from app.models.device import Device


# Глобальный реестр процессов для защиты от повторного запуска на одном экземпляре backend.
# В проде нужно распределённое состояние, но для мегалабы хватает.
_running: dict[str, subprocess.Popen] = {}


def _mqtt_env() -> tuple[str, int]:
    host = os.getenv("MQTT_HOST", "mqtt")
    port = int(os.getenv("MQTT_PORT", "1883"))
    return host, port


def _script_for_device_type(device_type: str) -> str | None:
    device_type_u = device_type.upper()

    # Важно: пути относительны рабочей директории контейнера.
    # В docker-compose мы монтируем repo-папку в /app, поэтому скрипты лежат в /app/device-emulator/...
    sensors = {
        "TEMP_SENSOR": "device-emulator/sensors/temperature_sensor.py",
        "HUMIDITY_AIR_SENSOR": "device-emulator/sensors/humidity_air_sensor.py",
        "HUMIDITY_SOIL_SENSOR": "device-emulator/sensors/humidity_soil_sensor.py",
        "LIGHT_SENSOR": "device-emulator/sensors/light_sensor.py",
    }
    actuators = {
        "IRRIGATION_ACTUATOR": "device-emulator/actuators/irrigation.py",
        "HEATER_ACTUATOR": "device-emulator/actuators/heater.py",
        "VENTILATION_ACTUATOR": "device-emulator/actuators/ventilation.py",
        "LIGHT_ACTUATOR": "device-emulator/actuators/light.py",
    }

    return sensors.get(device_type_u) or actuators.get(device_type_u)


def spawn_device_emulator(device: Device) -> None:
    # Если процесс уже запущен и не завершился — не запускаем второй раз.
    running = _running.get(device.device_uid)
    if running and running.poll() is None:
        return

    script_path = _script_for_device_type(device.device_type)
    if not script_path:
        return

    mqtt_host, mqtt_port = _mqtt_env()

    cmd = [
        sys.executable,
        script_path,
        "--device_uid",
        device.device_uid,
        "--device_secret",
        device.device_secret,
        "--mqtt_host",
        mqtt_host,
        "--mqtt_port",
        str(mqtt_port),
        # У сенсоров и актуаторов свой "период публикации/обработки". Можно унифицировать.
        "--period_seconds",
        os.getenv("EMULATOR_PERIOD_SECONDS", "5"),
    ]

    # Запускаем в фоне.
    proc = subprocess.Popen(
        cmd,
        cwd="/app",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _running[device.device_uid] = proc

