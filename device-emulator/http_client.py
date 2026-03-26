import json
import urllib.request
from typing import Any


def http_get_json(url: str, timeout_seconds: float = 5.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)

