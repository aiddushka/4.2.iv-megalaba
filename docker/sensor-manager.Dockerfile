FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests docker

COPY device-emulator/sensor_manager.py /app/sensor_manager.py

CMD ["python", "sensor_manager.py"]
