#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cache系统
用于cacheLLMResponse, Tool execution result等, 减少重复计算和API调用
"""

import hashlib
import json
import os
from typing import Dict, Any, Optional, Union
import logging
import time

from src.core.config import config, _get_project_root

logger = logging.getLogger(__name__)


class Cache:
    """
    cache基类
    """
    
    def get(self, key: str) -> Optional[Any]:
        """
        Getcache
        
        Args:
            key: cache键
            
        Returns:
            cache值
        """
        raise NotImplementedError
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        设置cache
        
        Args:
            key: cache键
            value: cache值
            expire: 过期时间 (s) 
            
        Returns:
            是否 successful
        """
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """
        Deletecache
        
        Args:
            key: cache键
            
        Returns:
            是否 successful
        """
        raise NotImplementedError
    
    def clear(self) -> bool:
        """
        Clearcache
        
        Returns:
            是否 successful
        """
        raise NotImplementedError
    
    def exists(self, key: str) -> bool:
        """
        检查cache是否存在
        
        Args:
            key: cache键
            
        Returns:
            是否存在
        """
        raise NotImplementedError


class MemoryCache(Cache):
    """
    内存cache
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialization内存cache
        
        Args:
            max_size: 最大cache项数
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        if time.time() > item.get("expire", float('inf')):
            del self._cache[key]
            return None
        
        return item.get("value")
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        # 如果cachealready满, Delete最早的项
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].get("timestamp", 0))
            del self._cache[oldest_key]
        
        self._cache[key] = {
            "value": value,
            "expire": time.time() + expire,
            "timestamp": time.time()
        }
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> bool:
        self._cache.clear()
        return True
    
    def exists(self, key: str) -> bool:
        if key not in self._cache:
            return False
        
        item = self._cache[key]
        if time.time() > item.get("expire", float('inf')):
            del self._cache[key]
            return False
        
        return True
    
    def get_size(self) -> int:
        """
        Getcache大小
        
        Returns:
            cache项数
        """
        # 清理过期项
        for key in list(self._cache.keys()):
            self.get(key)  # 会自动清理过期项
        
        return len(self._cache)


class FileCache(Cache):
    """
    文件cache
    """
    
    def __init__(self, cache_dir: str = None):
        """
        Initialization文件cache
        
        Args:
            cache_dir: cache目录
        """
        self.cache_dir = cache_dir or str(_get_project_root() / config.system.data_dir / "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """
        Getcache文件路径
        
        Args:
            key: cache键
            
        Returns:
            cache文件路径
        """
        # 使用哈希值作为文件名, 避免文件名冲突
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"cache_{key_hash}.json")
    
    def get(self, key: str) -> Optional[Any]:
        cache_path = self._get_cache_path(key)
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if time.time() > data.get("expire", float('inf')):
                os.remove(cache_path)
                return None
            
            return data.get("value")
        except Exception as e:
            logger.error(f"Cache read failed: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        cache_path = self._get_cache_path(key)
        
        try:
            data = {
                "value": value,
                "expire": time.time() + expire,
                "timestamp": time.time()
            }
            
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Cache write failed: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                return True
            except Exception as e:
                logger.error(f"Cache delete failed: {e}")
                return False
        return False
    
    def clear(self) -> bool:
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.startswith("cache_") and filename.endswith(".json"):
                    os.remove(os.path.join(self.cache_dir, filename))
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        cache_path = self._get_cache_path(key)
        if not os.path.exists(cache_path):
            return False
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if time.time() > data.get("expire", float('inf')):
                os.remove(cache_path)
                return False
            
            return True
        except Exception as e:
            logger.error(f"Cache check failed: {e}")
            return False
    
    def get_size(self) -> int:
        """
        Getcache大小
        
        Returns:
            cache文件数
        """
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.startswith("cache_") and filename.endswith(".json"):
                count += 1
        return count


class CacheManager:
    """
    cache管理器
    """
    
    def __init__(self, cache_type: str = "memory", **kwargs):
        """
        Initializationcache管理器
        
        Args:
            cache_type: cachetype (memory, file)
            **kwargs: cacheInitialization参数
        """
        if cache_type == "memory":
            self.cache = MemoryCache(**kwargs)
        elif cache_type == "file":
            self.cache = FileCache(**kwargs)
        else:
            raise ValueError(f"不支持的cachetype: {cache_type}")
        
        logger.info(f"Cache manager initialized, using {cache_type} cache")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Getcache
        
        Args:
            key: cache键
            
        Returns:
            cache值
        """
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        设置cache
        
        Args:
            key: cache键
            value: cache值
            expire: 过期时间 (s) 
            
        Returns:
            是否 successful
        """
        return self.cache.set(key, value, expire)
    
    def delete(self, key: str) -> bool:
        """
        Deletecache
        
        Args:
            key: cache键
            
        Returns:
            是否 successful
        """
        return self.cache.delete(key)
    
    def clear(self) -> bool:
        """
        Clearcache
        
        Returns:
            是否 successful
        """
        return self.cache.clear()
    
    def exists(self, key: str) -> bool:
        """
        检查cache是否存在
        
        Args:
            key: cache键
            
        Returns:
            是否存在
        """
        return self.cache.exists(key)
    
    def get_size(self) -> int:
        """
        Getcache大小
        
        Returns:
            cache项数
        """
        return self.cache.get_size()
    
    def generate_key(self, prefix: str, **kwargs) -> str:
        """
        生成cache键
        
        Args:
            prefix: 键前缀
            **kwargs: 键参数
            
        Returns:
            cache键
        """
        # 对参数进行排序, 确保相同参数生成相同的键
        sorted_kwargs = sorted(kwargs.items())
        key_str = f"{prefix}:{json.dumps(sorted_kwargs, ensure_ascii=False)}"
        return key_str


# 全局cache管理器实例
cache_manager = None


def get_cache_manager() -> CacheManager:
    """
    Getcache管理器实例
    
    Returns:
        CacheManager实例
    """
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager()
    return cache_manager


def reset_cache_manager():
    """
    重置cache管理器
    """
    global cache_manager
    cache_manager = None


# cache装饰器
def cache_result(expire: int = 3600, cache_key: Optional[str] = None):
    """
    cache函数的装饰器
    
    Args:
        expire: 过期时间 (s) 
        cache_key: cache键前缀
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成cache键
            if cache_key:
                key = get_cache_manager().generate_key(cache_key, args=args, kwargs=kwargs)
            else:
                key = get_cache_manager().generate_key(func.__name__, args=args, kwargs=kwargs)
            
            # 尝试FromcacheGet
            cached_result = get_cache_manager().get(key)
            if cached_result is not None:
                logger.debug(f"Got result from cache: {key}")
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # Cached result
            get_cache_manager().set(key, result, expire)
            logger.debug(f"Cached result: {key}")
            
            return result
        return wrapper
    return decorator
