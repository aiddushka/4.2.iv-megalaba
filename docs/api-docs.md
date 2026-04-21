# API проекта "IoT Greenhouse" (актуально по коду)

Base URL (через Nginx): `https://localhost:8443/api`

Внутренний URL backend в Docker-сети: `http://backend:8000`

Swagger UI: `https://localhost:8443/docs`

## Авторизация

Большинство эндпоинтов требуют JWT-токен (Bearer).

- **Header**: `Authorization: Bearer <token>`
- **Получение токена**: `POST /auth/login`

## Auth (`/auth`)

### `POST /auth/register`
Регистрация пользователя.

Body:

```json
{ "username": "worker1", "password": "123" }
```

### `POST /auth/login`
Логин. Возвращает JWT.

Формат запроса: `application/x-www-form-urlencoded` (OAuth2PasswordRequestForm), поля `username`, `password`.

Response:

```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

### `GET /auth/me`
Текущий пользователь по токену.

Response (пример):

```json
{ "id": 1, "username": "admin", "is_admin": true, "can_view_dashboard": true }
```

### `GET /auth/workers` (admin only)
Список работников (все пользователи, кроме админов).

### `PATCH /auth/workers/{user_id}/dashboard-access` (admin only)
Выдать/забрать право просмотра Dashboard.

Body:

```json
{ "can_view_dashboard": true }
```

## Devices (`/devices`)

### `POST /devices/register` (public)
Регистрация устройства **без авторизации** (Device Configurator).

Body (минимально):

```json
{
  "device_uid": "temp_sensor_1",
  "device_type": "TEMP_SENSOR",
  "description": "Датчик температуры у входа",
  "location_hint": "Теплица А"
}
```

Доп. поля (опционально): `controller`, `pin`, `bus`, `bus_address`, `components`.

### `GET /devices/unassigned` (admin only)
Список устройств со статусом `unassigned`.

### `GET /devices/assigned` (auth)
Список устройств со статусом, отличным от `unassigned` (включая `active`).

### `POST /devices/assign` (admin only)
“Установка” устройства на локацию: проставляет `location` и переводит в `active`.

Body:

```json
{ "device_uid": "temp_sensor_1", "location": "Теплица А / левая грядка" }
```

### `GET /devices/{device_uid}` (auth)
Получение полной карточки устройства (включая `change_history`).

### `PATCH /devices/{device_uid}` (admin only)
Обновление конфигурации/статуса/обслуживания.

Body (пример):

```json
{
  "description": "Датчик температуры (центр)",
  "location": "Теплица А / центр",
  "status": "active",
  "maintenance_notes": "Проверено 2026-04-13"
}
```

### `DELETE /devices/{device_uid}` (admin only)
Удаление устройства и связанных сущностей (телеметрия, actuator state, links).

### `GET /devices/status/{device_uid}` (public)
Публичный статус устройства (для эмуляторов/устройств без авторизации).

Response:

```json
{ "device_uid": "temp_sensor_1", "device_type": "TEMP_SENSOR", "status": "active" }
```

### `GET /devices/active-sensors` (public)
Публичный список активных датчиков (для `device-emulator/sensor_manager.py`).

Response:

```json
[
  { "device_uid": "temp_sensor_1", "device_type": "TEMP_SENSOR", "status": "active" }
]
```

## Sensors (`/sensor-data`)

### `POST /sensor-data/` (public)
Запись показаний датчика.

Ограничения:
- устройство должно существовать
- устройство должно быть `active`
- тип устройства должен быть сенсором (проверяется по `device_type`, должен содержать `SENSOR`)

Body:

```json
{ "device_uid": "temp_sensor_1", "value": 25.4, "sensor_type": "temperature" }
```

### `GET /sensor-data/`
Список телеметрии (сортировка по времени убывания).

## Actuators (`/actuators`)

### `POST /actuators/control` (admin only)
Ручное управление актуатором.

Body:

```json
{ "device_uid": "irrigation_1", "action": "ON", "actuator_type": "IRRIGATION_ACTUATOR" }
```

### `GET /actuators/status` (admin или worker с доступом)
Список текущих состояний актуаторов.

## Automation (`/automation`)

### Links (датчик → актуатор)

#### `POST /automation/links`
Создать связь (в текущей реализации доступно без авторизации).

Body:

```json
{
  "source_device_uid": "humidity_soil_1",
  "target_device_uid": "irrigation_1",
  "description": "Полив при низкой влажности",
  "active": true,
  "auto_control_enabled": false,
  "min_value": 30,
  "max_value": 70
}
```

#### `GET /automation/links`
Получить список связей. Параметр: `?device_uid=<uid>` (опционально).

#### `PATCH /automation/links/{link_id}` (admin only)
Частичное обновление: `description`, `auto_control_enabled`, `min_value`, `max_value`.

#### `DELETE /automation/links/{link_id}` (admin only)
Удалить связь.

### Rules (заготовка)

#### `POST /automation/rules`
Создать правило автоматизации.

#### `GET /automation/rules`
Список правил.

## Dashboard (`/dashboard`)

### `GET /dashboard/state` (auth)
Агрегированное состояние: последние значения сенсоров, состояния актуаторов, список links.

Доступ:
- админ: всегда
- работник: только если `can_view_dashboard=true`

## Примеры вызова через внешний URL

```bash
curl -k -X POST "https://localhost:8443/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=123"
```

```bash
curl -k "https://localhost:8443/api/dashboard/state" \
  -H "Authorization: Bearer <token>"
```
