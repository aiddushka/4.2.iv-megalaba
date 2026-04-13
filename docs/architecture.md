# Архитектура проекта "IoT Greenhouse"

Документ описывает фактическую архитектуру проекта **по текущему коду**.

## Компоненты

- **Backend**: FastAPI + SQLAlchemy + JWT (`backend/main.py`)
- **PostgreSQL**: хранение пользователей, устройств, телеметрии, состояния актуаторов и связей
- **Frontend #1 (Dashboard)**: `frontend-dashboard` (Vite/React, порт 3000)
- **Frontend #2 (Device Configurator)**: `frontend-device-config` (Vite/React, порт 3001)
- **Эмуляторы устройств**: `device-emulator`
  - **менеджер сенсоров** (`sensor_manager.py`) — запускается в Docker, стартует сенсорные скрипты для активных датчиков
  - **актуаторы** (`device-emulator/actuators/*.py`) — скрипты для ручного тестирования

## Запуск и сеть (Docker Compose)

Сервисы в `docker/docker-compose.yml`:

- **backend**: `http://localhost:8000` (uvicorn `main:app`)
- **postgres**: `localhost:5432`
- **frontend-dashboard**: `http://localhost:3000` (внутри контейнера Vite на `5173`)
- **frontend-device-config**: `http://localhost:3001` (внутри контейнера Vite на `5174`)
- **sensor-emulator-manager**: без порта, общается с backend по `http://backend:8000`

## Поток данных (end-to-end)

### 1) Регистрация устройства

1. Оператор открывает Device Configurator (порт 3001)
2. Форма отправляет `POST /devices/register` (без авторизации)
3. Устройство создаётся со статусом `unassigned`

### 2) “Установка” устройства (активация)

1. Админ заходит на Dashboard (порт 3000) и авторизуется
2. Админ получает `GET /devices/unassigned`
3. Админ выполняет `POST /devices/assign` → устройство получает `location` и `status=active`

### 3) Телеметрия (сенсоры)

1. `device-emulator/sensor_manager.py` опрашивает `GET /devices/active-sensors`
2. Для каждого активного датчика запускается соответствующий скрипт из `device-emulator/sensors/*`
3. Сенсорный скрипт проверяет `GET /devices/status/{device_uid}` и отправляет показание в `POST /sensor-data/`

### 4) Управление актуаторами

- **Ручное управление**: `POST /actuators/control` (admin)
- **Просмотр состояния**: `GET /dashboard/state` и/или `GET /actuators/status`

### 5) Связи “датчик → актуатор” и автоуправление

- Связи задаются через `device_links` (`/automation/links`)
- При приходе сенсорных данных (`POST /sensor-data/`) backend может автоматически выставить состояние актуатора, если у связи включён `auto_control_enabled` и заданы `min_value/max_value`

## Модель данных (PostgreSQL)

### `users`
- `id`, `username`, `hashed_password`, `is_admin`, `can_view_dashboard`

### `devices`
- `id`, `device_uid`, `device_type`, `description`
- конфигурация подключения: `controller`, `pin`, `bus`, `bus_address`, `components`
- эксплуатационные поля: `status`, `location`, `last_maintenance`, `maintenance_notes`, `change_history`

### `sensor_data`
- `id`, `device_uid`, `value`, `sensor_type`, `created_at`

### `actuators`
- `id`, `device_uid`, `actuator_type`, `state`

### `device_links`
- `id`, `source_device_uid`, `target_device_uid`, `controller`, `description`
- `active`, `auto_control_enabled`, `min_value`, `max_value`, `created_at`

### `automation_rules` (заготовка)
- `id`, `name`, `sensor_type`, `condition`, `threshold`, `actuator_type`, `action`


