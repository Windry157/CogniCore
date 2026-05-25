#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度缓存模块
提供置信度结果的缓存和复用功能
"""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class ConfidenceCache:
    """置信度缓存
    
    使用 LRU 策略缓存置信度评分结果
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存有效期（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix, str(args)]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或 None
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                self._cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"缓存命中: {key[:8]}...")
                return value
            else:
                del self._cache[key]
        
        self._misses += 1
        logger.debug(f"缓存未命中: {key[:8]}...")
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
        
        self._cache[key] = (value, time.time())
        logger.debug(f"缓存设置: {key[:8]}...")
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 3),
            "ttl": self.ttl
        }


class AsyncConfidenceProcessor:
    """异步置信度处理器
    
    支持批量处理和并发置信度评分
    """
    
    def __init__(self, cache: Optional[ConfidenceCache] = None):
        """初始化处理器
        
        Args:
            cache: 置信度缓存实例
        """
        self.cache = cache or ConfidenceCache()
        self._processing = False
    
    async def batch_score_decisions(
        self,
        scorer,
        decisions: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """批量评分决策
        
        Args:
            scorer: 置信度评分器
            decisions: 决策列表
            max_concurrent: 最大并发数
            
        Returns:
            评分结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def score_with_semaphore(decision: Dict[str, Any], idx: int) -> Dict[str, Any]:
            async with semaphore:
                cache_key = self.cache._generate_key(
                    "decision",
                    decision.get("input", ""),
                    idx
                )
                
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return cached
                
                result = await scorer.score_decision_confidence(
                    decision.get("context", {}),
                    decision.get("memories", []),
                    decision.get("knowledge_coverage", 0.5)
                )
                
                self.cache.set(cache_key, result)
                return result
        
        tasks = [score_with_semaphore(d, i) for i, d in enumerate(decisions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"评分失败 {i}: {result}")
                processed_results.append({
                    "confidence_score": 0.5,
                    "confidence_level": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def batch_score_texts(
        self,
        scorer,
        texts: List[Tuple[str, str]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """批量评分文本
        
        Args:
            scorer: 置信度评分器
            texts: (prompt, generated_text) 元组列表
            max_concurrent: 最大并发数
            
        Returns:
            评分结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def score_with_semaphore(item: Tuple[str, str], idx: int) -> Dict[str, Any]:
            prompt, generated_text = item
            async with semaphore:
                cache_key = self.cache._generate_key(
                    "text",
                    prompt[:100],
                    generated_text[:100],
                    idx
                )
                
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return cached
                
                result = await scorer.score_text_generation_confidence(
                    prompt, generated_text
                )
                
                self.cache.set(cache_key, result)
                return result
        
        tasks = [score_with_semaphore(t, i) for i, t in enumerate(texts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"评分失败 {i}: {result}")
                processed_results.append({
                    "confidence_score": 0.5,
                    "confidence_level": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results


confidence_cache = ConfidenceCache()


class ConfidenceCacheManager:
    """置信度缓存管理器"""
    
    def __init__(self):
        """初始化管理器"""
        self._caches: Dict[str, ConfidenceCache] = {}
        self._default_cache = ConfidenceCache()
        self._caches["default"] = self._default_cache
    
    def get_cache(self, name: str = "default") -> ConfidenceCache:
        """获取命名缓存
        
        Args:
            name: 缓存名称
            
        Returns:
            置信度缓存实例
        """
        if name not in self._caches:
            self._caches[name] = ConfidenceCache()
        return self._caches[name]
    
    def create_cache(self, name: str, max_size: int = 1000, ttl: int = 3600) -> ConfidenceCache:
        """创建新的命名缓存
        
        Args:
            name: 缓存名称
            max_size: 最大缓存条目数
            ttl: 缓存有效期
            
        Returns:
            置信度缓存实例
        """
        if name in self._caches:
            logger.warning(f"缓存 {name} 已存在，将被替换")
        
        self._caches[name] = ConfidenceCache(max_size=max_size, ttl=ttl)
        return self._caches[name]
    
    def clear_all(self):
        """清空所有缓存"""
        for cache in self._caches.values():
            cache.clear()
        logger.info("所有缓存已清空")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存统计"""
        return {name: cache.get_stats() for name, cache in self._caches.items()}


confidence_cache_manager = ConfidenceCacheManager()
