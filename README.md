Мегалаба по предмету Интернет вещи в 4 курсе 2 семестра.



Для запуска нужно:
1. Скачать файлы
2. Запустить Docker Deckstop
3. Перейти в папку 'docker'
4. За билдить ```docker compose up --build```
Контейнеры запустятся:
backend
postgres
5. Проверить API 
http://localhost:8000
Ответ:
{"message": "IoT Greenhouse API running"}






Структура:
Объяснение каждой папки
backend/

Python сервер.

backend/app
api/

Endpoints API.

devices.py
sensors.py
auth.py
actuators.py
models/

Модели базы данных.

device.py
sensor_data.py
user.py
schemas/

Pydantic схемы.

device_schema.py
sensor_schema.py
services/

Бизнес-логика.

device_service.py
sensor_service.py
automation_service.py
database/

Подключение к БД.

session.py
base.py





5. frontend-dashboard
Основной сайт:
панель управления теплицей
Будет показывать:
температуру
влажность
освещенность
состояние устройств

6. frontend-device-config
Сайт №2:
конфигуратор устройств
Используется чтобы:
зарегистрировать устройство
передать конфигурацию