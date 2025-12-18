"""
Simple TTL-based in-memory cache for external API responses.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    """A cached item with data, timestamp, and TTL."""
    data: Any
    timestamp: datetime
    ttl_seconds: int


class Cache:
    """Thread-safe in-memory cache with TTL support."""
    
    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data if fresh.
        Returns dict with 'data' and 'last_updated' if valid, else None.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        
        now = datetime.now(timezone.utc)
        age_seconds = (now - entry.timestamp).total_seconds()
        
        if age_seconds > entry.ttl_seconds:
            # Cache expired
            return None
        
        return {
            "data": entry.data,
            "last_updated": entry.timestamp.isoformat(),
            "age_seconds": int(age_seconds),
            "ttl_seconds": entry.ttl_seconds,
        }
    
    def set(self, key: str, data: Any, ttl_seconds: int = 300) -> datetime:
        """Store data with TTL. Returns the timestamp."""
        timestamp = datetime.now(timezone.utc)
        self._store[key] = CacheEntry(
            data=data,
            timestamp=timestamp,
            ttl_seconds=ttl_seconds,
        )
        return timestamp
    
    def invalidate(self, key: str) -> bool:
        """Remove a cache entry. Returns True if entry existed."""
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    def invalidate_all(self) -> int:
        """Clear all cache entries. Returns count of cleared entries."""
        count = len(self._store)
        self._store.clear()
        return count


# Global cache instance
cache = Cache()


# Cache key constants
CACHE_KEY_HOST_STATUS = "host_status"
CACHE_KEY_HOST_HARDWARE = "host_hardware"

# TTL constants (in seconds)
TTL_HOST_STATUS = 30    # 30 seconds
TTL_HOST_HARDWARE = 30  # 30 seconds

