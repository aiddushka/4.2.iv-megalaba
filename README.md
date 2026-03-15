# IoT Greenhouse MegaLab

## Описание проекта

Проект "IoT Greenhouse" — лабораторная работа по предмету **Интернет вещей** (4 курс, 2 семестр). Цель проекта — создать систему умной теплицы с поддержкой:

- Подключения датчиков и актуаторов
- Отправки и получения данных через API
- Автоматизации управления теплицей
- Визуализации состояния в Dashboard
- Эмуляции виртуальных устройств

Проект состоит из Backend, Frontend и эмуляторов устройств.

---

## Стек технологий

- Backend: Python + FastAPI
- База данных: PostgreSQL
- ORM: SQLAlchemy
- Миграции: Alembic
- Контейнеризация: Docker + Docker Compose
- Frontend: React (Dashboard и конфигуратор)
- Эмуляторы устройств: Python scripts

---

## Быстрый старт

### 1. Установка

1. Склонируйте репозиторий.
2. Установите и запустите Docker Desktop.
3. Перейдите в папку `docker`.
4. Соберите и запустите контейнеры:

```bash
docker compose up --build
```

Контейнеры, которые будут запущены:
- `backend` — сервер FastAPI
- `postgres` — база данных PostgreSQL

### 2. Проверка API

Откройте в браузере:
```
http://localhost:8000
```
Ожидаемый ответ:
```json
{"message": "IoT Greenhouse API running"}
```

Документация Swagger для API:
```
http://localhost:8000/docs
```

---

## Структура проекта

```
4.2.iv-megalaba/
│
├─ backend/             # Python сервер
│   ├─ app/
│   │   ├─ api/         # Endpoints API: devices.py, sensors.py, actuators.py, auth.py
│   │   ├─ models/      # Модели базы данных: device.py, sensor_data.py, user.py
│   │   ├─ schemas/     # Pydantic схемы: device_schema.py, sensor_schema.py
│   │   ├─ services/    # Бизнес-логика: device_service.py, sensor_service.py, automation_service.py
│   │   └─ database/    # Подключение к БД: session.py, base.py
│   ├─ main.py          # Точка входа FastAPI
│   └─ requirements.txt # Python зависимости
│
├─ device-emulator/    # Эмуляторы устройств
│   ├─ sensors/         # Датчики: temperature, humidity, light
│   └─ actuators/       # Актуаторы: irrigation, heater, ventilation
│
├─ frontend-dashboard/      # Основной сайт (Dashboard)
│   └─ показывает текущие показатели и состояние устройств
│
├─ frontend-device-config/  # Конфигуратор устройств (Сайт №2)
│   └─ регистрация и настройка устройств
│
├─ database/           # SQL скрипты для инициализации БД
│   └─ init.sql
│
├─ docker/             # Docker файлы
├─ docs/               # Документация
├─ tests/              # Тесты
├─ docker-compose.yml  # Поднятие контейнеров
├─ README.md           # Инструкция
└─ .gitignore          # Исключения Git
```

---

## Как работать с проектом

### Backend
- Реализован на FastAPI.
- Таблицы: `devices`, `sensor_data`.
- Эндпоинты:
  - `POST /devices/` — регистрация нового устройства
  - `GET /devices/` — получить список всех устройств
  - `POST /sensor-data/` — отправка данных с датчика
  - `GET /sensor-data/` — получение всех данных датчиков
  - `POST /actuators/control/` — управление актуаторами
  - `GET /actuators/status/` — получение текущего состояния актуаторов

### Эмуляторы устройств
- Скрипты в `device-emulator/` генерируют данные датчиков и управляют актуаторами.
- Каждый эмулятор может быть запущен локально и отправлять данные на Backend через API.

### Frontend
1. **Dashboard** (`frontend-dashboard`) — отображение температуры, влажности, освещенности и состояния всех устройств. Возможность управления актуаторами.
2. **Device Configurator** (`frontend-device-config`) — регистрация и первичная настройка устройств перед подключением к Dashboard.

### База данных
- Инициализация через `database/init.sql`.
- Таблицы создаются автоматически при старте FastAPI с SQLAlchemy.

---

## Рекомендации для команды

- **Backend**: работа с API, сервисами и моделями SQLAlchemy.
- **Frontend**: отображение данных Dashboard, управление актуаторами, UX.
- **Эмуляторы**: генерация тестовых данных и проверка работы API.
- **Документация**: поддерживать `docs/` с архитектурой и схемами данных.

---

Теперь у проекта есть полностью рабочая структура и инструкция для быстрого старта. Все, что нужно, чтобы запустить, тестировать и развивать систему, описано в этом README.

