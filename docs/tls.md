# MQTT TLS: перевыпуск сертификатов (dev)

Этот документ описывает, как перевыпустить TLS-сертификаты для Mosquitto в локальной среде.

## Что используется

- Локальный CA (`ca.crt` + приватный `ca.key`)
- Серверный сертификат брокера (`server.crt` + `server.key`)
- Конфиг SAN: `docker/mosquitto/certs/server-openssl.cnf`

Файлы лежат в `docker/mosquitto/certs/`.

## Важно

- `server.key` и `ca.key` не коммитить в git.
- В SAN обязательно должен быть `mqtt-broker` (иначе клиенты в Docker-сети не пройдут проверку имени).

## 1) Перейти в папку сертификатов

```powershell
cd docker/mosquitto/certs
```

## 2) Перевыпустить CA и server cert через Docker+OpenSSL

```powershell
docker run --rm -v "${PWD}:/work" alpine:3.20 sh -c "apk add --no-cache openssl >/dev/null && \
openssl req -x509 -new -nodes -key /work/ca.key -sha256 -days 365 -out /work/ca.crt -subj '/C=RU/ST=Tyumen/L=Tyumen/O=Greenhouse Dev/OU=IoT/CN=Greenhouse Dev CA' && \
openssl req -new -key /work/server.key -out /work/server.csr -config /work/server-openssl.cnf && \
openssl x509 -req -in /work/server.csr -CA /work/ca.crt -CAkey /work/ca.key -CAcreateserial -out /work/server.crt -days 365 -sha256 -extensions req_ext -extfile /work/server-openssl.cnf"
```

Если нужно сгенерировать ключи с нуля, сначала:

```powershell
docker run --rm -v "${PWD}:/work" alpine:3.20 sh -c "apk add --no-cache openssl >/dev/null && \
openssl genrsa -out /work/ca.key 4096 && \
openssl genrsa -out /work/server.key 2048"
```

## 3) Проверить сертификат

```powershell
docker run --rm -v "${PWD}:/work" alpine:3.20 sh -c "apk add --no-cache openssl >/dev/null && \
openssl x509 -in /work/server.crt -noout -subject -issuer -dates -ext subjectAltName"
```

Ожидаемо:

- `subject ... CN=mqtt-broker`
- SAN содержит `DNS:mqtt-broker`

## 4) Перезапустить стек

```powershell
cd ../../
docker compose up -d --build mqtt-broker backend sensor-emulator-manager
```

## 5) Проверить, что MQTT остался TLS-only

```powershell
docker compose ps mqtt-broker
docker compose logs mqtt-broker --tail=120
docker compose logs backend --tail=120
```

Ожидаемо:

- только порт `8883`;
- в логах broker есть `negotiated TLSv1.3`;
- backend логирует `connecting to mqtt-broker:8883`.

## mTLS (первая итерация, единый порт)

В проекте используется один MQTT-порт `8883` с обязательным client certificate.

Схема сертификатов:

- server TLS: `ca.crt` + `server.crt/server.key`
- client mTLS CA: `device-ca.crt` (+ локальный `device-ca.key`)
- backend client cert: `backend_client.crt/backend_client.key` (CN=`backend_user`)
- device client cert: `device_client.crt/device_client.key` (CN=`device_user`)

### Быстрая проверка mTLS

1) Без client cert к `8883` подключение должно падать.
2) С валидным client cert к `8883` подключение должно проходить.
3) В логах broker ожидаемо:
   - `tlsv1 alert unknown ca` или `peer did not return a certificate` для невалидного/отсутствующего cert;
   - `u'backend_user'` и `u'device_user'` + `negotiated TLSv1.3` для успешных подключений.

## Per-device cert и ACL

- `sensor_manager` автоматически выпускает cert/key для каждого `device_uid` в
  `/mqtt-certs-rw/devices/<uid>.crt|.key`.
- В MQTT ACL используется шаблон `%u` (identity из client certificate), поэтому
  устройство может публиковать только в свои топики.

Проверка идеи:

- publish `greenhouse/devices/<same_uid>/heartbeat` проходит;
- publish `greenhouse/devices/<other_uid>/heartbeat` не доставляется подписчику.

## Lifecycle automation: issue / rotate / revoke

Теперь lifecycle можно выполнять одной командой через менеджер (без ручного `openssl`).

Из папки `docker/`:

```powershell
docker compose exec -T sensor-emulator-manager python sensor_manager.py issue <device_uid>
docker compose exec -T sensor-emulator-manager python sensor_manager.py rotate <device_uid>
docker compose exec -T sensor-emulator-manager python sensor_manager.py revoke <device_uid>
```

Что делает каждая команда:

- `issue`: выпускает cert/key устройства, если их еще нет.
- `rotate`: отзывает текущий cert, выпускает новый cert/key, обновляет CRL.
- `revoke`: отзывает текущий cert, удаляет активные cert/key, обновляет CRL.

После `rotate/revoke` менеджер отправляет `HUP` в `mqtt-broker`, чтобы Mosquitto перечитал CRL.

### Мини-проверка "старый cert больше не работает"

1) Сделать `issue`, сохранить копию старого cert/key.
2) Выполнить `rotate`.
3) Попробовать подключиться старой парой cert/key к `8883` -> подключение должно быть отклонено.
4) Подключиться новой парой cert/key -> подключение проходит.
