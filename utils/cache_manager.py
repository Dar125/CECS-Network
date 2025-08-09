"""
Cache Manager for Multi-Agent Code Review System

Implements caching for code analysis results to reduce API calls and improve performance.
Uses Modal Dict for distributed caching across serverless functions.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

try:
    import modal
    MODAL_AVAILABLE = True
except ImportError:
    MODAL_AVAILABLE = False

@dataclass
class CacheEntry:
    """Represents a cached analysis result"""
    key: str
    result: Dict[str, Any]
    timestamp: float
    hit_count: int = 0
    agent_type: str = ""
    
    def is_expired(self, ttl: int = 3600) -> bool:
        """Check if cache entry has expired (default 1 hour TTL)"""
        return time.time() - self.timestamp > ttl

class CacheManager:
    """Manages caching for code review analysis results"""
    
    def __init__(self, cache_name: str = "code-review-cache", ttl: int = 3600):
        self.cache_name = cache_name
        self.ttl = ttl  # Time to live in seconds
        self.local_cache = {}  # In-memory cache for same function instance
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def _generate_cache_key(self, code: str, agent_type: str, context: Optional[Dict] = None) -> str:
        """Generate unique cache key based on code content and analysis type"""
        cache_data = {
            "code": code,
            "agent_type": agent_type,
            "context": context or {}
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def get(self, code: str, agent_type: str, context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis result if available"""
        key = self._generate_cache_key(code, agent_type, context)
        
        # Check local cache first
        if key in self.local_cache:
            entry = self.local_cache[key]
            if not entry.is_expired(self.ttl):
                entry.hit_count += 1
                self.stats["hits"] += 1
                return entry.result
            else:
                # Remove expired entry
                del self.local_cache[key]
                self.stats["evictions"] += 1
        
        self.stats["misses"] += 1
        return None
    
    def set(self, code: str, agent_type: str, result: Dict[str, Any], context: Optional[Dict] = None):
        """Cache an analysis result"""
        key = self._generate_cache_key(code, agent_type, context)
        
        entry = CacheEntry(
            key=key,
            result=result,
            timestamp=time.time(),
            agent_type=agent_type
        )
        
        self.local_cache[key] = entry
        
        # Implement simple LRU eviction if cache gets too large
        if len(self.local_cache) > 1000:
            self._evict_oldest()
    
    def _evict_oldest(self):
        """Evict oldest cache entries when cache is full"""
        # Sort by timestamp and remove oldest 10%
        sorted_entries = sorted(
            self.local_cache.items(),
            key=lambda x: x[1].timestamp
        )
        
        to_evict = len(sorted_entries) // 10
        for key, _ in sorted_entries[:to_evict]:
            del self.local_cache[key]
            self.stats["evictions"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "hit_rate": hit_rate,
            "cache_size": len(self.local_cache)
        }
    
    def clear(self):
        """Clear all cached entries"""
        self.local_cache.clear()
        self.stats["evictions"] += len(self.local_cache)

class ModalCacheManager(CacheManager):
    """Extended cache manager using Modal Dict for distributed caching"""
    
    def __init__(self, cache_name: str = "code-review-cache", ttl: int = 3600):
        super().__init__(cache_name, ttl)
        self.modal_dict = None
        self._init_modal_dict()
    
    def _init_modal_dict(self):
        """Initialize Modal Dict for distributed caching"""
        if not MODAL_AVAILABLE:
            self.modal_dict = None
            return
            
        try:
            self.modal_dict = modal.Dict.from_name(
                self.cache_name,
                create_if_missing=True
            )
        except Exception as e:
            print(f"Failed to initialize Modal Dict: {e}")
            # Fall back to local cache only
            self.modal_dict = None
    
    async def get_async(self, code: str, agent_type: str, context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Async version for Modal Dict access"""
        # Check local cache first
        result = self.get(code, agent_type, context)
        if result:
            return result
        
        # Check Modal Dict if available
        if self.modal_dict:
            key = self._generate_cache_key(code, agent_type, context)
            try:
                entry_data = await self.modal_dict.get(key)
                if entry_data:
                    entry = CacheEntry(**entry_data)
                    if not entry.is_expired(self.ttl):
                        # Update local cache
                        self.local_cache[key] = entry
                        self.stats["hits"] += 1
                        return entry.result
                    else:
                        # Remove expired entry
                        await self.modal_dict.delete(key)
            except Exception as e:
                print(f"Modal Dict access error: {e}")
        
        return None
    
    async def set_async(self, code: str, agent_type: str, result: Dict[str, Any], context: Optional[Dict] = None):
        """Async version for Modal Dict storage"""
        # Store in local cache
        self.set(code, agent_type, result, context)
        
        # Store in Modal Dict if available
        if self.modal_dict:
            key = self._generate_cache_key(code, agent_type, context)
            entry = self.local_cache[key]
            try:
                await self.modal_dict.put(key, asdict(entry))
            except Exception as e:
                print(f"Modal Dict storage error: {e}")

# Singleton instance for easy access
_cache_manager = None

def get_cache_manager(use_modal: bool = True) -> CacheManager:
    """Get singleton cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        if use_modal:
            _cache_manager = ModalCacheManager()
        else:
            _cache_manager = CacheManager()
    return _cache_manager