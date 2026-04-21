# Архитектура проекта "IoT Greenhouse"

Документ описывает фактическую архитектуру решения и взаимодействие компонентов Интернета вещей.

## 1. Компоненты системы

- **Backend**: FastAPI + SQLAlchemy + JWT (`backend/main.py`).
- **PostgreSQL**: хранение пользователей, устройств, телеметрии, состояний актуаторов и связей.
- **MQTT-брокер**: Eclipse Mosquitto (TLS/mTLS, ACL для топиков).
- **Frontend Dashboard**: `frontend-dashboard`, внешний URL `https://localhost:8443/`.
- **Frontend Device Configurator**: `frontend-device-config`, внешний URL `https://localhost:8443/config/`.
- **Nginx**: TLS-терминация и прокси запросов `/api/*` на backend.
- **Эмуляторы устройств**: `device-emulator` (датчики и тестовые актуаторы).

## 2. Docker-сеть и точки доступа

Сервисы описаны в `docker/docker-compose.yml`.

- `backend`: доступен только внутри сети Docker как `http://backend:8000`.
- `postgres`: опубликован на хост `localhost:5432`.
- `mqtt-broker`: TLS-подключение на `localhost:8883`.
- `greenhouse_backend_https_proxy`: внешний вход через `https://localhost:8443`, HTTP-редирект с `http://localhost:8080`.
- `frontend-dashboard` и `frontend-device-config`: работают в контейнерах и доступны извне только через Nginx.
- `sensor-emulator-manager`: служебный контейнер без внешнего порта.

## 3. Поток IoT-данных (end-to-end)

### 3.1 Регистрация устройства

1. Оператор открывает `https://localhost:8443/config/`.
2. Форма отправляет `POST /api/devices/register`.
3. Устройство создается в БД со статусом `unassigned`.

### 3.2 Активация устройства

1. Администратор входит на Dashboard.
2. Получает список через `GET /api/devices/unassigned`.
3. Назначает устройство (`POST /api/devices/assign`), после чего статус становится `active`.

### 3.3 Сбор телеметрии

1. `sensor_manager.py` запрашивает `GET /api/devices/active-sensors`.
2. Для активных датчиков запускаются соответствующие скрипты.
3. Устройства публикуют данные в MQTT-топики вида `greenhouse/sensors/<device_uid>/data`.
4. Backend получает телеметрию, валидирует ее и сохраняет в `sensor_data`.

### 3.4 Управление актуаторами

- ручное управление: `POST /api/actuators/control`;
- чтение состояния: `GET /api/actuators/status` и `GET /api/dashboard/state`.

### 3.5 Автоматизация "датчик -> актуатор"

- связи хранятся в `device_links` и управляются через `/api/automation/links`;
- при входящем измерении backend может автоматически изменять состояние актуатора, если у связи включен `auto_control_enabled` и заданы пороги.

## 4. Модель данных (PostgreSQL)

### `users`

`id`, `username`, `hashed_password`, `is_admin`, `can_view_dashboard`.

### `devices`

`id`, `device_uid`, `device_type`, `description`, `status`, `location`, `controller`, `pin`, `bus`, `bus_address`, `components`, `last_maintenance`, `maintenance_notes`, `change_history`.

### `sensor_data`

`id`, `device_uid`, `value`, `sensor_type`, `created_at`.

### `actuators`

`id`, `device_uid`, `actuator_type`, `state`.

### `device_links`

`id`, `source_device_uid`, `target_device_uid`, `description`, `controller`, `active`, `auto_control_enabled`, `min_value`, `max_value`, `created_at`.

### `automation_rules` (заготовка)

`id`, `name`, `sensor_type`, `condition`, `threshold`, `actuator_type`, `action`.


