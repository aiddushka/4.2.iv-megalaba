def is_sensor(device_type: str) -> bool:
    return "SENSOR" in (device_type or "")


def container_name(device_uid: str, device_type: str) -> str:
    safe_uid = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in device_uid)
    role = "sensor" if is_sensor(device_type) else "actuator"
    return f"greenhouse_{role}_{safe_uid}".lower()


def legacy_container_name(device_uid: str) -> str:
    safe_uid = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in device_uid)
    return f"greenhouse_device_{safe_uid}".lower()


def device_secret_basename(device_uid: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in device_uid)


def sanitize_cert_cn(raw: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in raw).strip("-")
    return safe or "device"
