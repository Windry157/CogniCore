#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cacheTool module
用于cacheAPI请求和 memories查询
"""

import time
from typing import Dict, Any, Optional
import hashlib


class RequestCache:
    """
    请求cache类
    用于cacheAPI请求, 减少重复计算
    """
    
    def __init__(self, max_size: int = 1000, expiration_time: int = 3600):
        """
        Initialization请求cache
        
        Args:
            max_size: cache最大容量
            expiration_time: cache过期时间 (s) 
        """
        self.max_size = max_size
        self.expiration_time = expiration_time
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
    
    def _generate_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """
        生成cache键
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            cache键
        """
        key_data = f"{endpoint}:{params}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Getcache数据
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            cache的数据, 如果does not exist或already过期则返回None
        """
        key = self._generate_key(endpoint, params)
        
        # 检查cache是否存在
        if key not in self.cache:
            return None
        
        # 检查cache是否过期
        cache_data = self.cache[key]
        if time.time() - cache_data['timestamp'] > self.expiration_time:
            del self.cache[key]
            del self.access_times[key]
            return None
        
        # Update访问时间
        self.access_times[key] = time.time()
        
        return cache_data['data']
    
    def set(self, endpoint: str, params: Dict[str, Any], data: Any):
        """
        设置cache数据
        
        Args:
            endpoint: API端点
            params: 请求参数
            data: 要cache的数据
        """
        key = self._generate_key(endpoint, params)
        
        # 检查cache大小
        if len(self.cache) >= self.max_size:
            # Delete最久未使用的cache
            oldest_key = min(self.access_times, key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        # 设置cache
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        self.access_times[key] = time.time()
    
    def clear(self):
        """
        Clearcache
        """
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        GetcacheStatistics
        
        Returns:
            cacheStatistics
        """
        return {
            'current_size': len(self.cache),
            'max_size': self.max_size,
            'expiration_time': self.expiration_time
        }


class MemoryCache:
    """
     memoriescache类
    用于cache memories查询, 提高 memories检索速度
    """
    
    def __init__(self, max_size: int = 500, expiration_time: int = 1800):
        """
        Initialization memoriescache
        
        Args:
            max_size: cache最大容量
            expiration_time: cache过期时间 (s) 
        """
        self.max_size = max_size
        self.expiration_time = expiration_time
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
    
    def get_memory(self, query: str) -> Optional[Any]:
        """
        Get memoriescache
        
        Args:
            query: 查询Content
            
        Returns:
            cache的 memories, 如果does not exist或already过期则返回None
        """
        key = hashlib.md5(query.encode()).hexdigest()
        
        # 检查cache是否存在
        if key not in self.cache:
            return None
        
        # 检查cache是否过期
        cache_data = self.cache[key]
        if time.time() - cache_data['timestamp'] > self.expiration_time:
            del self.cache[key]
            del self.access_times[key]
            return None
        
        # Update访问时间
        self.access_times[key] = time.time()
        
        return cache_data['data']
    
    def set_memory(self, query: str, data: Any):
        """
        设置 memoriescache
        
        Args:
            query: 查询Content
            data: 要cache的 memories数据
        """
        key = hashlib.md5(query.encode()).hexdigest()
        
        # 检查cache大小
        if len(self.cache) >= self.max_size:
            # Delete最久未使用的cache
            oldest_key = min(self.access_times, key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        # 设置cache
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        self.access_times[key] = time.time()
    
    def clear(self):
        """
        Clearcache
        """
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        GetcacheStatistics
        
        Returns:
            cacheStatistics
        """
        return {
            'current_size': len(self.cache),
            'max_size': self.max_size,
            'expiration_time': self.expiration_time
        }


# Create全局cache实例
request_cache = RequestCache()
memory_cache = MemoryCache()


def get_request_cache() -> RequestCache:
    """
    Get请求cache实例
    
    Returns:
        请求cache实例
    """
    return request_cache


def get_memory_cache() -> MemoryCache:
    """
    Get memoriescache实例
    
    Returns:
         memoriescache实例
    """
    return memory_cache
