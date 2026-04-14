# IoT Greenhouse MegaLab

Лабораторный проект «**Умная теплица**» (IoT): backend + БД + два фронтенда + эмуляторы устройств.

## Что внутри

- **Backend**: Python, FastAPI, SQLAlchemy, JWT auth
- **БД**: PostgreSQL
- **MQTT**: Eclipse Mosquitto (брокер телеметрии)
- **Frontend**:
  - **Dashboard** (порт **3000**) — просмотр и управление (для админа)
  - **Device Configurator** (порт **3001**) — регистрация/первичная конфигурация устройств (без авторизации)
- **Эмуляторы**:
  - менеджер сенсоров в Docker — сам запускает сенсорные скрипты для активных датчиков
  - актуаторы — отдельные скрипты для ручного запуска

## Ссылки на документацию

- `docs/api-docs.md` — эндпоинты и примеры запросов
- `docs/architecture.md` — архитектура и поток данных
- `docs/sites.md` — страницы/модули фронтенда

## Быстрый старт (Docker)

### Требования

- установлен **Docker Desktop**
- Docker Desktop в состоянии Running

### Запуск

Из корня репозитория:

```bash
cd docker
docker compose up --build
```

Поднимутся контейнеры:

- `greenhouse_postgres` — PostgreSQL (порт **5432**)
- `greenhouse_mqtt_broker` — MQTT broker (порт **1883**)
- `greenhouse_backend` — FastAPI (порт **8000**)
- `greenhouse_frontend_dashboard` — Vite dev server (наружу **3000**)
- `greenhouse_frontend_device_config` — Vite dev server (наружу **3001**)
- `greenhouse_sensor_emulator_manager` — менеджер сенсоров (без порта)

### Проверка

- **API health**: `http://localhost:8000/` → `{"message":"IoT Greenhouse API running"}`
- **Swagger**: `http://localhost:8000/docs`
- **Dashboard**: `http://localhost:3000`
- **Device Configurator**: `http://localhost:3001`

### Учётные записи

- **Админ по умолчанию**: `admin / 123` (создаётся автоматически при старте backend, если нет пользователя `admin`)

## Как “живет” система (коротко)

1) На `http://localhost:3001` регистрируем устройства (`POST /devices/register`). Устройство попадает в статус `unassigned`.
2) На Dashboard (админ) “устанавливаем” устройство (`POST /devices/assign`) → статус становится `active`.
3) Менеджер сенсоров в Docker опрашивает `GET /devices/active-sensors` и запускает скрипты сенсоров для активных устройств.
4) Сенсоры публикуют телеметрию в MQTT-топики `greenhouse/sensors/<device_uid>/data`, backend подписывается и сохраняет данные (HTTP `POST /sensor-data/` также остаётся доступным).
5) Dashboard показывает агрегированное состояние через `GET /dashboard/state`. Админ может вручную управлять актуаторами `POST /actuators/control`, а также создавать “связи” датчик → актуатор (`/automation/links`).

## Дерево проекта (актуальное)

Ниже дерево репозитория (как в `tree /a /f`).

```
4.2.iv-megalaba
|   .gitignore
|   README.md
|
+---backend
|   |   main.py
|   |   requirements.txt
|   |
|   +---app
|   |   |   main.py
|   |   |   __init__.py
|   |   |
|   |   +---api
|   |   |       actuators.py
|   |   |       auth.py
|   |   |       automation.py
|   |   |       dashboard.py
|   |   |       devices.py
|   |   |       sensors.py
|   |   |
|   |   +---database
|   |   |       base.py
|   |   |       session.py
|   |   |
|   |   +---models
|   |   |       actuator.py
|   |   |       automation_rule.py
|   |   |       device.py
|   |   |       device_link.py
|   |   |       sensor_data.py
|   |   |       user.py
|   |   |
|   |   +---schemas
|   |   |       actuator_schema.py
|   |   |       auth_schema.py
|   |   |       automation_schema.py
|   |   |       device_schema.py
|   |   |       sensor_schema.py
|   |   |
|   |   \---services
|   |           actuator_service.py
|   |           auth_service.py
|   |           automation_service.py
|   |           device_service.py
|   |           sensor_service.py
|   |
|   \---images
|       \---ArduinoUnoComponents
|               AUno_��������_����������.png
|               AUno_��������_�����_�_�������.png
|               AUno_���������_���������.png
|               AUno_������_���������_�����.png
|               AUno_������_������������.png
|               AUno_������_�����������.png
|               AUno_���������������_�������.png
|
+---database
|       init.sql
|
+---device-emulator
|   |   sensor_manager.py
|   |
|   +---actuators
|   |       heater.py
|   |       irrigation.py
|   |       light.py
|   |       ventilation.py
|   |
|   \---sensors
|           humidity_air_sensor.py
|           humidity_soil_sensor.py
|           light_sensor.py
|           temperature_sensor.py
|
+---docker
|   |   backend.Dockerfile
|   |   docker-compose.yml
|   |   frontend-dashboard.Dockerfile
|   |   frontend-device-config.Dockerfile
|   |
|   \---database
|
+---docs
|       api-docs.md
|       architecture.md
|       sites.md
|
+---frontend-dashboard
|   |   index.html
|   |   package.json
|   |   tsconfig.json
|   |   vite.config.ts
|   |
|   \---src
|       |   App.tsx
|       |   main.tsx
|       |
|       +---api
|       |       actuatorsApi.ts
|       |       apiClient.ts
|       |       authApi.ts
|       |       automationApi.ts
|       |       dashboardApi.ts
|       |       devicesApi.ts
|       |       workersApi.ts
|       |
|       +---components
|       |       DeviceHistoryBlock.tsx
|       |       DeviceInfoBlock.tsx
|       |       DeviceManagementBlock.tsx
|       |
|       \---pages
|               DashboardPage.tsx
|               LoginPage.tsx
|               RegisterPage.tsx
|               UnassignedDevicesPage.tsx
|               WorkersPage.tsx
|
\---frontend-device-config
    |   index.html
    |   package.json
    |   tsconfig.json
    |   vite.config.ts
    |
    \---src
        |   App.tsx
        |   main.tsx
        |
        +---api
        |       apiClient.ts
        |       automationApi.ts
        |       devicesApi.ts
        |
        +---components
        |       DeviceForm.tsx
        |
        \---pages
                RegisterDevicePage.tsx
```

## Примечания по backend entrypoint’ам

В репозитории есть два файла `main.py`:

- `backend/main.py` — **используется Docker’ом** (`uvicorn main:app`)

