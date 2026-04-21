# MQTT Security Architecture

Этот документ подробно описывает, как в проекте реализована защита MQTT-контурa:

- шифрование канала (TLS);
- взаимная аутентификация (mTLS);
- авторизация на уровне топиков (ACL);
- изоляция устройств по идентичности;
- отзыв и ротация сертификатов без ручной пересборки broker.

Все примеры путей и команд даны для текущей dev-среды проекта.

## 1. Цели безопасности

При проектировании MQTT-контурa мы закрываем четыре ключевых риска:

1. **Подслушивание трафика**  
   Решение: TLS, весь MQTT трафик идет только по `8883`.
2. **Подмена брокера (MITM)**  
   Решение: клиент проверяет серверный сертификат `server.crt`.
3. **Подключение неавторизованных клиентов**  
   Решение: broker принимает только клиентов с валидным client certificate.
4. **Горизонтальный доступ между устройствами**  
   Решение: ACL-шаблоны с `%u`, где `%u` берется из identity сертификата.

## 2. Слои защиты в текущей конфигурации

В `docker/mosquitto/mosquitto.conf` включены критичные параметры:

- `listener 8883` - единственный защищенный порт.
- `require_certificate true` - сертификат клиента обязателен.
- `use_identity_as_username true` - username формируется из cert identity.
- `cafile /mosquitto/data/certs/device-ca.crt` - доверенный CA для клиентов.
- `crlfile /mosquitto/data/certs/device-ca.crl` - список отозванных cert.
- `certfile`/`keyfile` - серверная пара broker.

Итог: подключение к брокеру возможно только по mTLS, без client cert сессия не установится.

## 3. Роли сертификатов и ключей

Каталог: `docker/mosquitto/certs/`.

### 3.1 Server TLS (доверие к брокеру)

- `ca.crt` / `ca.key` - CA, подписывающий серверный сертификат Mosquitto.
- `server.crt` / `server.key` - сертификат и приватный ключ брокера.
- `server-openssl.cnf` - OpenSSL-конфиг для CSR и SAN (например `mqtt-broker`).
- `server.csr` - промежуточный файл запроса на выпуск server cert.
- `ca.srl` - служебный serial-файл OpenSSL для `ca.crt`.

Назначение: клиент (backend/device) проверяет, что говорит именно с легитимным MQTT broker.

### 3.2 Client mTLS (доверие к клиентам)

- `device-ca.crt` / `device-ca.key` - CA, которому брокер доверяет для client cert.
- `device-ca.crl` - CRL со списком отозванных client cert.
- `device-ca.srl` - служебный serial-файл OpenSSL для `device-ca`.
- `backend_client.crt` / `backend_client.key` - client cert backend (CN=`backend_user`).
- `device_client.crt` / `device_client.key` - пример/базовый client cert устройства.
- `*.csr` (например `backend_client.csr`, `device_client.csr`) - запросы на выпуск.

Назначение: брокер допускает только клиентов с валидным cert от `device-ca.crt`, не входящим в CRL.

## 4. Авторизация: как ACL ограничивает доступ

Файл: `docker/mosquitto/acl.conf`.

### Backend (`backend_user`)

Backend может:

- читать телеметрию и heartbeat всех устройств;
- писать команды в топики управления актуаторами.

Это задается явными правилами:

- `topic read greenhouse/sensors/+/data`
- `topic read greenhouse/actuators/+/state`
- `topic read greenhouse/devices/+/heartbeat`
- `topic write greenhouse/actuators/+/cmd`

### Устройства (pattern + `%u`)

Для runtime устройств используются шаблоны:

- `pattern write greenhouse/sensors/%u/data`
- `pattern write greenhouse/actuators/%u/state`
- `pattern write greenhouse/devices/%u/heartbeat`
- `pattern read greenhouse/actuators/%u/cmd`

`%u` - это identity клиента из сертификата (поскольку `use_identity_as_username true`).

Практический эффект: устройство с identity `sensor-01` не может писать/читать топики `sensor-02`.

## 5. Per-device сертификаты и lifecycle

В `device-emulator/manager/cert_lifecycle.py` реализован полный жизненный цикл сертификатов устройства.

### 5.1 Что делает lifecycle-код

- подготавливает CA DB (`index.txt`, `serial`, `crlnumber`, OpenSSL config);
- выпускает ключ + CSR + сертификат для каждого `device_uid`;
- отзывает сертификат при `revoke`;
- обновляет `device-ca.crl` после issue/revoke/rotate;
- отправляет `HUP` в контейнер broker, чтобы Mosquitto перечитал CRL/конфиг.

### 5.2 Команды управления

Из директории `docker/`:

```powershell
docker compose exec -T sensor-emulator-manager python sensor_manager.py issue <device_uid>
docker compose exec -T sensor-emulator-manager python sensor_manager.py rotate <device_uid>
docker compose exec -T sensor-emulator-manager python sensor_manager.py revoke <device_uid>
```

- `issue` - выпускает первую пару cert/key.
- `rotate` - отзывает старую пару и выпускает новую.
- `revoke` - отзывает cert и удаляет активные cert/key устройства.

После каждой операции выполняется reload broker через `SIGHUP`.

## 6. Почему выбрано разделение CA (server vs client)

Мы используем разные центры доверия:

- `ca.*` для server TLS;
- `device-ca.*` для client mTLS.

Это снижает blast radius:

- компрометация клиентского CA не означает автоматическую компрометацию server TLS;
- проще ротация и эксплуатация (разные процессы, разные цели);
- легче аудировать контур: кто кому и зачем доверяет.

## 7. Операционная безопасность: что нельзя делать

1. Не коммитить приватные ключи:  
   `ca.key`, `server.key`, `device-ca.key`, `*_client.key`.
2. Не использовать одинаковый cert для разных устройств.
3. Не отключать `require_certificate true`.
4. Не убирать `crlfile`, иначе отзыв перестанет работать.
5. Не менять SAN server cert так, чтобы исчез `mqtt-broker`.

## 8. Проверки безопасности (чек-лист)

### 8.1 Проверка TLS-only

```powershell
docker compose ps mqtt-broker
docker compose logs mqtt-broker --tail=120
```

Ожидаемо:

- брокер слушает `8883`;
- в логах есть успешные TLS negotiation (`TLSv1.3`).

### 8.2 Проверка обязательного mTLS

1. Подключение без client cert должно быть отклонено.
2. Подключение с cert, подписанным не тем CA, должно быть отклонено.
3. Подключение с валидным cert из `device-ca.crt` должно пройти.

В логах типовые ошибки:

- `peer did not return a certificate`
- `tlsv1 alert unknown ca`

### 8.3 Проверка ACL-изоляции

1. Устройство публикует в `greenhouse/devices/<its_uid>/heartbeat` - успешно.
2. Попытка публикации в `greenhouse/devices/<other_uid>/heartbeat` - блокируется ACL.

### 8.4 Проверка отзыва сертификата

1. Выполнить `issue`, сохранить старые cert/key.
2. Выполнить `rotate` или `revoke`.
3. Повторить подключение старой парой - должно быть отклонено.
4. При `rotate` новая пара должна подключаться успешно.

## 9. Краткий итог архитектуры

Текущая схема обеспечивает defense-in-depth:

- **TLS** защищает канал связи.
- **mTLS** удостоверяет обе стороны соединения.
- **ACL + `%u`** ограничивает устройство только его топиками.
- **CRL + lifecycle** позволяет быстро отзывать скомпрометированные cert.

Это дает управляемый и проверяемый контур безопасности для MQTT в dev и как основу для production hardening.

