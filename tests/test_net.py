from pathlib import Path

from mgmtlit import net


class _Resp:
    def __init__(self, payload):
        self._payload = payload
        self.text = str(payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def __init__(self):
        self.calls = 0

    def get(self, url, params=None, headers=None):
        self.calls += 1
        return _Resp({"url": url, "params": params or {}, "headers": headers or {}})


def test_cached_get_json_hits_cache(tmp_path: Path):
    cache = net.HTTPCache(tmp_path / "cache.json")
    old_cache = net._CACHE
    net._CACHE = cache
    try:
        c = _Client()
        one = net.cached_get_json(c, "https://example.org/x", params={"q": "a"})
        two = net.cached_get_json(c, "https://example.org/x", params={"q": "a"})
        assert one == two
        assert c.calls == 1
    finally:
        net._CACHE = old_cache


def test_cached_get_json_respects_ttl(tmp_path: Path):
    cache = net.HTTPCache(tmp_path / "cache.json")
    old_cache = net._CACHE
    net._CACHE = cache
    try:
        c = _Client()
        net.cached_get_json(c, "https://example.org/x", params={"q": "a"}, ttl_seconds=0)
        net.cached_get_json(c, "https://example.org/x", params={"q": "a"}, ttl_seconds=0)
        assert c.calls == 2
    finally:
        net._CACHE = old_cache
