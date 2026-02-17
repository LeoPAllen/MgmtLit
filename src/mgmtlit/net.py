from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlparse


class HTTPCache:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(".mgmtlit_cache/http_cache.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}

    def get(self, key: str, ttl_seconds: int) -> Any | None:
        row = self._data.get(key)
        if not isinstance(row, dict):
            return None
        ts = row.get("ts")
        if not isinstance(ts, (int, float)):
            return None
        if time.time() - float(ts) > ttl_seconds:
            return None
        return row.get("payload")

    def set(self, key: str, payload: Any) -> None:
        self._data[key] = {"ts": time.time(), "payload": payload}
        try:
            self.path.write_text(json.dumps(self._data, ensure_ascii=True), encoding="utf-8")
        except Exception:
            pass


_CACHE = HTTPCache()
_LAST_CALL: dict[str, float] = {}


def _cache_key(url: str, params: dict[str, str] | None, headers: dict[str, str] | None) -> str:
    safe_headers = {k.lower(): len(v or "") for k, v in (headers or {}).items()}
    blob = json.dumps(
        {
            "url": url,
            "params": params or {},
            "headers": safe_headers,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _throttle(url: str, min_interval_sec: float) -> None:
    host = urlparse(url).netloc
    now = time.time()
    prev = _LAST_CALL.get(host)
    if prev is not None:
        wait = min_interval_sec - (now - prev)
        if wait > 0:
            time.sleep(wait)
    _LAST_CALL[host] = time.time()


def cached_get_json(
    client: Any,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    ttl_seconds: int = 86400,
    min_interval_sec: float = 0.35,
) -> dict[str, Any]:
    key = _cache_key(url, params, headers)
    cached = _CACHE.get(key, ttl_seconds)
    if isinstance(cached, dict):
        return cached
    _throttle(url, min_interval_sec)
    resp = client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    payload = resp.json()
    _CACHE.set(key, payload)
    return payload


def cached_get_text(
    client: Any,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    ttl_seconds: int = 86400,
    min_interval_sec: float = 0.35,
) -> str:
    key = _cache_key(url, params, headers)
    cached = _CACHE.get(key, ttl_seconds)
    if isinstance(cached, str):
        return cached
    _throttle(url, min_interval_sec)
    resp = client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    payload = resp.text
    _CACHE.set(key, payload)
    return payload
