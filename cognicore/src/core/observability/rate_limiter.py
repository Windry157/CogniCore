#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
速率限制模块
提供令牌桶和滑动窗口速率限制功能
专为U盘便携项目优化
"""

import time
import asyncio
from typing import Any, Dict, Optional, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RateLimiterExceededError(Exception):
    """速率限制超出异常"""
    pass


class TokenBucket:
    """令牌桶速率限制器"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """初始化令牌桶
        
        Args:
            capacity: 桶容量（最大令牌数）
            refill_rate: 补充速率（令牌/秒）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """获取令牌
        
        Args:
            tokens: 请求的令牌数
            
        Returns:
            是否成功获取
        """
        async with self._lock:
            await self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            
            return False
    
    async def try_acquire(self, tokens: int = 1, timeout: float = 0) -> bool:
        """尝试获取令牌（带超时）
        
        Args:
            tokens: 请求的令牌数
            timeout: 超时时间（秒）
            
        Returns:
            是否成功获取
        """
        start_time = time.time()
        
        while True:
            if await self.acquire(tokens):
                return True
            
            if timeout > 0 and (time.time() - start_time) >= timeout:
                return False
            
            await asyncio.sleep(0.01)
    
    async def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self._last_refill
        
        tokens_to_add = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + tokens_to_add)
        self._last_refill = now
    
    def get_available_tokens(self) -> float:
        """获取可用令牌数
        
        Returns:
            可用令牌数
        """
        elapsed = time.time() - self._last_refill
        tokens_to_add = elapsed * self.refill_rate
        return min(self.capacity, self._tokens + tokens_to_add)


class SlidingWindowRateLimiter:
    """滑动窗口速率限制器"""
    
    def __init__(self, max_requests: int, window_size: float):
        """初始化滑动窗口限制器
        
        Args:
            max_requests: 时间窗口内最大请求数
            window_size: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_size = window_size
        self._requests: Dict[str, list] = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str = "default") -> bool:
        """检查是否允许请求
        
        Args:
            key: 限流键
            
        Returns:
            是否允许
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_size
            
            if key not in self._requests:
                self._requests[key] = []
            
            self._requests[key] = [
                t for t in self._requests[key]
                if t > window_start
            ]
            
            if len(self._requests[key]) < self.max_requests:
                self._requests[key].append(now)
                return True
            
            return False
    
    async def try_acquire(self, key: str = "default", timeout: float = 0) -> bool:
        """尝试获取请求许可
        
        Args:
            key: 限流键
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        start_time = time.time()
        
        while True:
            if await self.is_allowed(key):
                return True
            
            if timeout > 0 and (time.time() - start_time) >= timeout:
                return False
            
            await asyncio.sleep(0.01)
    
    def get_remaining(self, key: str = "default") -> int:
        """获取剩余请求数
        
        Args:
            key: 限流键
            
        Returns:
            剩余请求数
        """
        now = time.time()
        window_start = now - self.window_size
        
        if key not in self._requests:
            return self.max_requests
        
        recent_requests = [
            t for t in self._requests[key]
            if t > window_start
        ]
        
        return max(0, self.max_requests - len(recent_requests))


class RateLimiter:
    """综合速率限制器
    
    支持多种速率限制策略
    """
    
    def __init__(self):
        """初始化限制器"""
        self._token_buckets: Dict[str, TokenBucket] = {}
        self._window_limiters: Dict[str, SlidingWindowRateLimiter] = {}
    
    def create_token_bucket(
        self,
        name: str,
        capacity: int,
        refill_rate: float
    ) -> TokenBucket:
        """创建令牌桶
        
        Args:
            name: 桶名称
            capacity: 桶容量
            refill_rate: 补充速率
            
        Returns:
            令牌桶实例
        """
        self._token_buckets[name] = TokenBucket(capacity, refill_rate)
        return self._token_buckets[name]
    
    def create_window_limiter(
        self,
        name: str,
        max_requests: int,
        window_size: float
    ) -> SlidingWindowRateLimiter:
        """创建滑动窗口限制器
        
        Args:
            name: 限制器名称
            max_requests: 最大请求数
            window_size: 窗口大小
            
        Returns:
            滑动窗口限制器实例
        """
        self._window_limiters[name] = SlidingWindowRateLimiter(
            max_requests, window_size
        )
        return self._window_limiters[name]
    
    def get_token_bucket(self, name: str) -> Optional[TokenBucket]:
        """获取令牌桶
        
        Args:
            name: 桶名称
            
        Returns:
            令牌桶或 None
        """
        return self._token_buckets.get(name)
    
    def get_window_limiter(self, name: str) -> Optional[SlidingWindowRateLimiter]:
        """获取滑动窗口限制器
        
        Args:
            name: 限制器名称
            
        Returns:
            限制器或 None
        """
        return self._window_limiters.get(name)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "token_buckets": {
                name: {
                    "capacity": tb.capacity,
                    "refill_rate": tb.refill_rate,
                    "available_tokens": tb.get_available_tokens()
                }
                for name, tb in self._token_buckets.items()
            },
            "window_limiters": {
                name: {
                    "max_requests": wl.max_requests,
                    "window_size": wl.window_size
                }
                for name, wl in self._window_limiters.items()
            }
        }


rate_limiter = RateLimiter()


rate_limiter.create_token_bucket(
    "llm_calls",
    capacity=10,
    refill_rate=1.0
)

rate_limiter.create_window_limiter(
    "api_requests",
    max_requests=60,
    window_size=60.0
)

rate_limiter.create_window_limiter(
    "file_operations",
    max_requests=100,
    window_size=60.0
)


def rate_limit(
    limiter_name: str,
    limiter_type: str = "token_bucket",
    tokens: int = 1,
    timeout: float = 0,
    raise_on_failure: bool = True
):
    """速率限制装饰器
    
    Args:
        limiter_name: 限制器名称
        limiter_type: 限制器类型（token_bucket 或 window）
        tokens: 请求的令牌数
        timeout: 超时时间（秒）
        raise_on_failure: 超限是否抛出异常
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            limiter = None
            
            if limiter_type == "token_bucket":
                limiter = rate_limiter.get_token_bucket(limiter_name)
            elif limiter_type == "window":
                limiter = rate_limiter.get_window_limiter(limiter_name)
            
            if not limiter:
                logger.warning(f"限制器不存在: {limiter_name}")
                return await func(*args, **kwargs)
            
            if limiter_type == "token_bucket":
                acquired = await limiter.try_acquire(tokens, timeout)
            else:
                acquired = await limiter.try_acquire(limiter_name, timeout)
            
            if not acquired:
                error_msg = f"速率限制超出: {limiter_name}"
                logger.warning(error_msg)
                if raise_on_failure:
                    raise RateLimiterExceededError(error_msg)
                return None
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.warning(f"同步函数不支持速率限制装饰器: {func.__name__}")
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def setup_default_rate_limits():
    """设置默认速率限制"""
    global rate_limiter
    
    rate_limiter = RateLimiter()
    
    rate_limiter.create_token_bucket(
        "default",
        capacity=10,
        refill_rate=2.0
    )
    
    rate_limiter.create_token_bucket(
        "llm_calls",
        capacity=10,
        refill_rate=1.0
    )
    
    rate_limiter.create_window_limiter(
        "api_requests",
        max_requests=60,
        window_size=60.0
    )
    
    logger.info("默认速率限制已设置")


__all__ = [
    "RateLimiter",
    "rate_limiter",
    "TokenBucket",
    "SlidingWindowRateLimiter",
    "RateLimiterExceededError",
    "rate_limit",
    "setup_default_rate_limits",
]
