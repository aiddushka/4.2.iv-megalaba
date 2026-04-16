FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --timeout 60 --retries 10 paho-mqtt

COPY device-emulator/sensors/ /app/sensors/
COPY device-emulator/actuators/ /app/actuators/

CMD ["python", "-u", "-c", "import time; print('device runtime image ready'); time.sleep(10**9)"]
