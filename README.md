# IoT Greenhouse MegaLab

Лабораторный IoT-проект «Умная теплица»: backend, PostgreSQL, MQTT, два веб-интерфейса и эмуляторы устройств.

## Состав проекта

- **Backend**: Python, FastAPI, SQLAlchemy, JWT-аутентификация.
- **База данных**: PostgreSQL.
- **MQTT-брокер**: Eclipse Mosquitto (TLS/mTLS, ACL).
- **Frontend** (доступ через Nginx и HTTPS, порт `8443`):
  - **Dashboard**: `https://localhost:8443/`
  - **Device Configurator**: `https://localhost:8443/config/`
- **Эмуляторы устройств**:
  - менеджер датчиков в Docker;
  - скрипты актуаторов для ручной проверки.

## Документация

- `docs/architecture.md` - архитектура, потоки данных и IoT-контур.
- `docs/sites.md` - описание двух сайтов и пользовательских сценариев.
- `docs/api-docs.md` - API backend с примерами.
- `docs/tls.md` - MQTT-безопасность, mTLS и работа с сертификатами.
- `docs/tls.backup.md` - резервная копия документа по TLS.

## Быстрый запуск

### Требования

- установлен и запущен Docker Desktop.

### Команды запуска

```bash
cd docker
docker compose up --build
```

### Что поднимается

- `greenhouse_postgres` - PostgreSQL (`5432`);
- `greenhouse_mqtt_broker` - MQTT broker, только TLS (`8883`);
- `greenhouse_backend` - FastAPI (внутри Docker-сети);
- `greenhouse_backend_https_proxy` - Nginx (HTTPS, прокси `/api/`, раздача фронтендов);
- `greenhouse_frontend_dashboard` - Vite Dashboard;
- `greenhouse_frontend_device_config` - Vite Device Configurator;
- `greenhouse_sensor_emulator_manager` - менеджер сенсорных эмуляторов.

### Проверка доступности

- `http://localhost:8080/` -> редирект на HTTPS;
- `https://localhost:8443/` -> Dashboard;
- `https://localhost:8443/config/` -> Device Configurator;
- `https://localhost:8443/api/` -> API через Nginx;
- `https://localhost:8443/docs` -> Swagger UI.

## Учетная запись по умолчанию

- Администратор: `admin / 123` (создается автоматически, если пользователя `admin` нет в БД).

## Краткий сценарий работы системы

1. На `https://localhost:8443/config/` регистрируется устройство (`POST /api/devices/register`), статус - `unassigned`.
2. Администратор на Dashboard назначает устройство на локацию (`POST /api/devices/assign`), статус - `active`.
3. Сенсорный менеджер получает список активных датчиков (`GET /api/devices/active-sensors`) и запускает соответствующие эмуляторы.
4. Телеметрия публикуется в MQTT-топики вида `greenhouse/sensors/<device_uid>/data`; backend обрабатывает данные и сохраняет их в БД.
5. Dashboard показывает агрегированное состояние (`GET /api/dashboard/state`) и позволяет управлять актуаторами (`POST /api/actuators/control`).

