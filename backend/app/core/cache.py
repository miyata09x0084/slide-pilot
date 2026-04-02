"""TTL付きインメモリキャッシュ

Supabase（USリージョン）へのRTT (~150ms) を削減するため、
バックエンドプロセス内でクエリ結果をキャッシュする。
Cloud Runインスタンス内で全リクエストが共有する。
"""

import time
from threading import Lock
from typing import Any, Optional


class TTLCache:
    """スレッドセーフなTTL付きインメモリキャッシュ"""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                value, expires_at = self._store[key]
                if time.monotonic() < expires_at:
                    return value
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl_seconds)

    def invalidate(self, prefix: str = "") -> None:
        """キャッシュを無効化。prefixが空なら全クリア。"""
        with self._lock:
            if not prefix:
                self._store.clear()
            else:
                keys = [k for k in self._store if k.startswith(prefix)]
                for k in keys:
                    del self._store[k]


# シングルトンインスタンス
cache = TTLCache()
