#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韧性模块
包含熔断器、事件总线、简单Saga
专为U盘便携项目优化
"""

import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """熔断器错误"""
    pass


class CircuitBreaker:
    """熔断器
    
    防止级联故障，提供优雅降级
    """
    
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: tuple = (Exception,),
        half_open_max_calls: int = 3,
    ):
        """初始化熔断器
        
        Args:
            name: 名称
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间
            expected_exception: 预期异常
            half_open_max_calls: 半开时最大调用数
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0
        self.call_history = deque(maxlen=100)
    
    async def execute(
        self,
        func: Callable,
        fallback: Optional[Callable] = None,
        *args,
        **kwargs,
    ) -> Any:
        """执行被包装执行函数
        
        Args:
            func: 要执行的函数
            fallback: 降级函数
            args, **kwargs: 参数
            
        Returns:
            函数结果
        """
        # 检查状态
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"熔断器 {self.name} 进入半开状态")
            else:
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitBreakerError(f"熔断器 {self.name} 处于打开状态")
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls > self.half_open_max_calls:
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitBreakerError(f"熔断器 {self.name} 半开状态下调用超限")
        
        try:
            result = await self._execute_function(func, *args, **kwargs)
            
            # 成功
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            if fallback:
                return fallback(*args, **kwargs)
            raise
    
    async def _execute_function(
        self, func: Callable, *args, **kwargs
    ) -> Any:
        """执行函数
        
        根据函数类型执行
        
        Args:
            func: 要执行的函数
            args, kwargs: 参数
            
        Returns:
            结果
        """
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # 同步函数在事件循环中执行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    def _on_success(self):
        """成功回调"""
        self.call_history.append({
            "time": datetime.now().isoformat(),
            "type": "success"
        })
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls = 0
            self.state = CircuitState.CLOSED
            logger.info(f"熔断器 {self.name} 恢复到关闭状态")
    
    def _on_failure(self):
        """失败回调"""
        self.call_history.append({
            "time": datetime.now().isoformat(),
            "type": "failure"
        })
        self.failure_count += 1
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self._open_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            self._open_circuit()
    
    def _open_circuit(self):
        """打开熔断器"""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        logger.warning(f"熔断器 {self.name} 打开！")
    
    def get_state(self) -> Dict[str, Any]:
        """获取状态
        
        Returns:
            状态信息
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None,
            "half_open_calls": self.half_open_calls,
        }


circuit_breaker = CircuitBreaker()


def circuit_breaker_decorator(
    name: str = "default",
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    fallback: Optional[Callable] = None,
    expected_exception: tuple = (Exception,),
):
    """熔断器装饰器
    
    用于保护函数调用
    
    Args:
        name: 熔断器名称
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时时间
        fallback: 降级函数
        expected_exception: 预期异常
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
    )
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.execute(func, fallback=fallback, *args, **kwargs)
        return wrapper
    return decorator


@dataclass
class DomainEvent:
    """领域事件"""
    id: str
    source: str
    data: Any
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class EventBus:
    """事件总线
    
    发布-订阅模式
    """
    
    def __init__(self):
        """初始化事件总线"""
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: deque = deque(maxlen=1000)
        self.dead_letter_queue: deque = deque(maxlen=100)
        
        logger.info("事件总线初始化完成")
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
    ):
        """订阅事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        
        logger.debug(f"订阅事件: {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type in self.subscribers and handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            logger.debug(f"取消订阅: {event_type}")
    
    async def publish(self, event: DomainEvent):
        """发布事件
        
        Args:
            event: 事件
        """
        self.event_history.append(event)
        
        if event.id not in self.subscribers:
            return
        
        for handler in self.subscribers.get(event.id, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"事件处理失败: {e}")
                self.dead_letter_queue.append({
                    "event": event,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
    
    def get_subscribers(self, event_type: str) -> List[Callable]:
        """获取订阅者
        
        Args:
            event_type: 事件类型
            
        Returns:
            订阅者列表
        """
        return self.subscribers.get(event_type, [])
    
    def get_history(self, limit: int = 100) -> List[DomainEvent]:
        """获取历史事件
        
        Args:
            limit: 数量限制
            
        Returns:
            事件列表
        """
        return list(self.event_history)[-limit:]


class SagaState(Enum):
    """Saga状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"


@dataclass
class SagaStep:
    """Saga步骤"""
    name: str
    action: Callable
    compensation: Optional[Callable]
    data: Optional[Dict[str, Any]]


class SagaOrchestrator:
    """Saga编排器
    
    简单的Saga实现，提供事务补偿
    """
    
    def __init__(self, name: str):
        """初始化
        
        Args:
            name: 名称
        """
        self.name = name
        self.steps: List[SagaStep] = []
        self.state = SagaState.PENDING
        self.executed_steps: List[SagaStep] = []
        self.failure_step: Optional[SagaStep] = None
        
        logger.info(f"Saga编排器 {name} 初始化完成")
    
    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Optional[Callable] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """添加步骤
        
        Args:
            name: 步骤名
            action: 执行函数
            compensation: 补偿函数
            data: 数据
        """
        step = SagaStep(
            name=name,
            action=action,
            compensation=compensation,
            data=data,
        )
        self.steps.append(step)
        logger.debug(f"添加步骤: {name}")
    
    async def execute(self):
        """执行Saga
        
        Returns:
            成功与否
        """
        self.state = SagaState.RUNNING
        self.executed_steps = []
        
        try:
            for step in self.steps:
                try:
                    await self._execute_step(step)
                    self.executed_steps.append(step)
                except Exception as e:
                    logger.error(f"步骤 {step.name} 失败: {e}")
                    await self._compensate()
                    self.failure_step = step
                    self.state = SagaState.FAILED
                    raise
            
            self.state = SagaState.COMPLETED
            logger.info(f"Saga {self.name} 执行完成")
            return True
            
        except Exception as e:
            logger.error(f"Saga {self.name} 失败: {e}")
            self.state = SagaState.FAILED
            return False
    
    async def _execute_step(self, step: SagaStep):
        """执行单个步骤
        
        Args:
            step: 要执行的步骤
        """
        if asyncio.iscoroutinefunction(step.action):
            if step.data:
                await step.action(**step.data)
            else:
                await step.action()
        else:
            if step.data:
                step.action(**step.data)
            else:
                step.action()
    
    async def _compensate(self):
        """执行补偿"""
        self.state = SagaState.COMPENSATING
        for step in reversed(self.executed_steps):
            if step.compensation:
                try:
                    logger.info(f"执行补偿: {step.name}")
                    if asyncio.iscoroutinefunction(step.compensation):
                        await step.compensation()
                    else:
                        step.compensation()
                except Exception as e:
                    logger.error(f"补偿失败 {step.name}: {e}")
    
    def reset(self):
        """重置Saga"""
        self.state = SagaState.PENDING
        self.executed_steps = []
        self.failure_step = None
        
        logger.debug(f"Saga {self.name} 重置")


# ============================================
# 模块导出
# ============================================
circuit_breaker = CircuitBreaker()
event_bus = EventBus()

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerError",
    "circuit_breaker",
    "circuit_breaker_decorator",
    "EventBus",
    "DomainEvent",
    "event_bus",
    "SagaOrchestrator",
    "SagaState",
    "SagaStep",
]
