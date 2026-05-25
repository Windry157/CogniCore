#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试Tool module
实现指数退避重试策略
"""

import time
import logging
from typing import Callable, Any, Type, Union, List

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retry_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    on_retry: Callable[[int, Exception, float], None] = None
) -> Callable:
    """
    指数退避重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间 (s) 
        max_delay: 最大延迟时间 (s) 
        backoff_factor: 退避因子
        retry_exceptions: 需要重试的exceptiontype
        on_retry: 重试时的回调函数
    
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            current_delay = base_delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    if retries == max_retries:
                        logger.error(f"Reached max retries {max_retries}, execution failed: {e}")
                        raise
                    
                    # 计算下一次重试的延迟
                    delay = min(current_delay, max_delay)
                    
                    # 调用重试回调
                    if on_retry:
                        on_retry(retries + 1, e, delay)
                    else:
                        logger.warning(f"execution failed, {delay:.2f}s retry ({retries + 1}/{max_retries}): {e}")
                    
                    # Waiting
                    time.sleep(delay)
                    
                    # Update延迟时间和重试次数
                    current_delay *= backoff_factor
                    retries += 1
        return wrapper
    return decorator


def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retry_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    on_retry: Callable[[int, Exception, float], None] = None
) -> Callable:
    """
    异步指数退避重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间 (s) 
        max_delay: 最大延迟时间 (s) 
        backoff_factor: 退避因子
        retry_exceptions: 需要重试的exceptiontype
        on_retry: 重试时的回调函数
    
    Returns:
        装饰后的异步函数
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs) -> Any:
            retries = 0
            current_delay = base_delay
            
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as e:
                    if retries == max_retries:
                        logger.error(f"Reached max retries {max_retries}, execution failed: {e}")
                        raise
                    
                    # 计算下一次重试的延迟
                    delay = min(current_delay, max_delay)
                    
                    # 调用重试回调
                    if on_retry:
                        on_retry(retries + 1, e, delay)
                    else:
                        logger.warning(f"execution failed, {delay:.2f}s retry ({retries + 1}/{max_retries}): {e}")
                    
                    # Waiting
                    await asyncio.sleep(delay)
                    
                    # Update延迟时间和重试次数
                    current_delay *= backoff_factor
                    retries += 1
        return wrapper
    return decorator


# 导入asyncio以支持异步重试
import asyncio


class RetryContext:
    """
    重试上下文管理器
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retry_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retry_exceptions = retry_exceptions
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带重试的函数
        """
        retries = 0
        current_delay = self.base_delay
        
        while retries <= self.max_retries:
            try:
                return func(*args, **kwargs)
            except self.retry_exceptions as e:
                if retries == self.max_retries:
                    logger.error(f"Reached max retries {self.max_retries}, execution failed: {e}")
                    raise
                
                delay = min(current_delay, self.max_delay)
                logger.warning(f"execution failed, {delay:.2f}s retry ({retries + 1}/{self.max_retries}): {e}")
                
                time.sleep(delay)
                current_delay *= self.backoff_factor
                retries += 1
    
    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        异步执行带重试的函数
        """
        retries = 0
        current_delay = self.base_delay
        
        while retries <= self.max_retries:
            try:
                return await func(*args, **kwargs)
            except self.retry_exceptions as e:
                if retries == self.max_retries:
                    logger.error(f"Reached max retries {self.max_retries}, execution failed: {e}")
                    raise
                
                delay = min(current_delay, self.max_delay)
                logger.warning(f"execution failed, {delay:.2f}s retry ({retries + 1}/{self.max_retries}): {e}")
                
                await asyncio.sleep(delay)
                current_delay *= self.backoff_factor
                retries += 1