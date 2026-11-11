"""Simple in-memory LRU caching utilities."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Generic, Hashable, TypeVar

V = TypeVar("V")


class LRUCache(Generic[V]):
    """Thread-unsafe LRU cache for single-worker async applications."""

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max_size
        self._store: OrderedDict[Hashable, V] = OrderedDict()

    def get(self, key: Hashable) -> V | None:
        """Retrieve a cached value, returning None on miss."""
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def put(self, key: Hashable, value: V) -> None:
        """Insert a value, evicting the oldest entry if at capacity."""
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: Hashable) -> bool:
        return key in self._store

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()
