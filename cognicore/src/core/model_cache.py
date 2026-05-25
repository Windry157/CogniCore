#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model列表cache module
减少Ollama查询频率, 提高性能
"""

import time
from typing import List, Dict, Optional

class ModelCache:
    """Model列表cache, 减少 Ollama 查询频率"""
    
    def __init__(self, ttl: int = 60):
        self.ttl = ttl  # cache时间 (s) 
        self._cache: Dict[str, tuple] = {}  # {key: (data, timestamp)}
        # cache统计
        self.stats = {
            "hits": 0,        # cache命中次数
            "misses": 0,      # cache未命中次数
            "sets": 0,        # cache设置次数
            "evictions": 0,   # cache过期次数
            "size": 0         # 当前cache大小
        }
    
    def get(self, key: str) -> Optional[List[dict]]:
        """Getcache的Model列表"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                self.stats["hits"] += 1
                return data
            else:
                del self._cache[key]
                self.stats["evictions"] += 1
                self.stats["size"] = len(self._cache)
        self.stats["misses"] += 1
        return None
    
    def set(self, key: str, data: List[dict]):
        """设置cache"""
        self._cache[key] = (data, time.time())
        self.stats["sets"] += 1
        self.stats["size"] = len(self._cache)
    
    def clear(self):
        """Clearcache"""
        self._cache.clear()
        # 重置统计
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "size": 0
        }
    
    def get_stats(self) -> Dict[str, int]:
        """GetcacheStatistics"""
        # 计算命中率
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        return {
            **self.stats,
            "hit_rate": round(hit_rate, 2)
        }

# Create全局Modelcache实例
model_cache = ModelCache(ttl=60)  # 60scache

# cache预热函数
def warmup_cache():
    """预热cache, 提前Load常用Model"""
    import requests
    import logging
    logger = logging.getLogger(__name__)
    
    # 尝试FromOllamaGet model list
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            # cacheModel数据
            model_cache.set("models:http://localhost:11434", models_data)
            logger.info(f"cachepreheat successful, Loaded {len(models_data)}  models")
        else:
            logger.warning(f"cachepreheat failed, Status code: {response.status_code}")
    except Exception as e:
        logger.warning(f"cachepreheat failed: {e}")

# 自动执行cache预热
if __name__ != "__main__":
    # 在module import时执行cache预热
    import threading
    # 使用线程执行, 避免阻塞module import
    thread = threading.Thread(target=warmup_cache, daemon=True)
    thread.start()