from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any, Dict


class SharedState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {
            "running": True,
            "updated_at": time.time(),
            "quality": {},
            "decode": {},
            "audio": {},
            "status_log": [],
        }

    def merge(self, **kwargs: Any) -> None:
        with self._lock:
            self._data.update(kwargs)
            self._data["updated_at"] = time.time()

    def update(self, **kwargs: Any) -> None:
        self.merge(**kwargs)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def append_status(self, message: str) -> None:
        with self._lock:
            items = list(self._data.get("status_log", []))
            items.append(f"{time.strftime('%H:%M:%S')} {message}")
            self._data["status_log"] = items[-30:]
            self._data["updated_at"] = time.time()
