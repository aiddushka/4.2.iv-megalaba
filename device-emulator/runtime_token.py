"""Перечитывание device_token из JSON (менеджер обновляет файл — симуляция смены конфига на устройстве)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class DeviceTokenHolder:
    def __init__(
        self,
        device_uid: str,
        fallback_token: str = "",
        secrets_dir: str | None = None,
        reload_interval: float = 5.0,
    ) -> None:
        self.device_uid = device_uid
        self._fallback = fallback_token or ""
        self._secrets_dir = Path(secrets_dir or os.getenv("RUNTIME_SECRETS_DIR", "/runtime-secrets"))
        self._reload_interval = float(os.getenv("TOKEN_RELOAD_INTERVAL_SECONDS", str(reload_interval)))
        self._token = self._fallback
        self._last_check = 0.0
        self._mtime: float | None = None
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in device_uid)
        self._file = self._secrets_dir / f"{safe}.json"
        self._apply_file_if_needed(force=True)

    def _apply_file_if_needed(self, force: bool = False) -> None:
        if not self._file.is_file():
            return
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            tok = data.get("device_token")
            if isinstance(tok, str) and tok:
                self._token = tok
        except Exception:
            if force:
                self._token = self._fallback

    def current(self) -> str:
        try:
            mtime = self._file.stat().st_mtime if self._file.is_file() else None
        except OSError:
            mtime = None
        now = time.monotonic()
        changed = mtime != self._mtime
        if changed:
            self._mtime = mtime
            self._apply_file_if_needed(force=True)
        elif now - self._last_check >= self._reload_interval:
            self._last_check = now
            self._apply_file_if_needed()
        return self._token
