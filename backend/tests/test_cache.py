"""TTLCache ユニットテスト"""

import time
from app.core.cache import TTLCache


class TestTTLCache:
    """TTLCacheの基本動作テスト"""

    def setup_method(self):
        self.cache = TTLCache()

    def test_set_and_get(self):
        self.cache.set("key1", {"data": "value"}, ttl_seconds=60)
        assert self.cache.get("key1") == {"data": "value"}

    def test_get_missing_key_returns_none(self):
        assert self.cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        self.cache.set("key1", "value", ttl_seconds=0)
        time.sleep(0.01)
        assert self.cache.get("key1") is None

    def test_invalidate_by_prefix(self):
        self.cache.set("slides:user1:20", [1, 2], ttl_seconds=60)
        self.cache.set("slides:user1:50", [1, 2, 3], ttl_seconds=60)
        self.cache.set("slides:user2:20", [4], ttl_seconds=60)
        self.cache.set("samples", [5, 6], ttl_seconds=60)

        self.cache.invalidate("slides:user1")

        assert self.cache.get("slides:user1:20") is None
        assert self.cache.get("slides:user1:50") is None
        assert self.cache.get("slides:user2:20") == [4]
        assert self.cache.get("samples") == [5, 6]

    def test_invalidate_all(self):
        self.cache.set("a", 1, ttl_seconds=60)
        self.cache.set("b", 2, ttl_seconds=60)
        self.cache.invalidate()
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None

    def test_ttl_boundary(self):
        """TTL内は有効、TTL後は無効、再setでリセット"""
        self.cache.set("key", "val", ttl_seconds=1)
        # TTL内: 有効
        assert self.cache.get("key") == "val"
        # TTL後: 無効
        time.sleep(1.05)
        assert self.cache.get("key") is None
        # 再setでTTLリセット
        self.cache.set("key", "val2", ttl_seconds=60)
        assert self.cache.get("key") == "val2"
