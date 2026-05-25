#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指标收集模块
提供性能指标、服务监控和统计分析功能
专为U盘便携项目优化
"""

import time
import asyncio
import statistics
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """指标收集器
    
    收集和统计系统性能指标
    """
    
    def __init__(self, max_history: int = 1000):
        """初始化收集器
        
        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._start_times: Dict[str, float] = {}
    
    def increment(self, name: str, value: int = 1):
        """递增计数器
        
        Args:
            name: 指标名称
            value: 增量值
        """
        self._counters[name] += value
    
    def decrement(self, name: str, value: int = 1):
        """递减计数器
        
        Args:
            name: 指标名称
            value: 减量值
        """
        self._counters[name] -= value
    
    def set_gauge(self, name: str, value: float):
        """设置仪表值
        
        Args:
            name: 指标名称
            value: 仪表值
        """
        self._gauges[name] = value
    
    def record_value(self, name: str, value: float):
        """记录数值
        
        Args:
            name: 指标名称
            value: 数值
        """
        self._histograms[name].append(value)
    
    def start_timer(self, name: str):
        """启动计时器
        
        Args:
            name: 计时器名称
        """
        self._start_times[name] = time.time()
    
    def stop_timer(self, name: str) -> Optional[float]:
        """停止计时器
        
        Args:
            name: 计时器名称
            
        Returns:
            耗时（秒）
        """
        if name not in self._start_times:
            logger.warning(f"计时器未启动: {name}")
            return None
        
        elapsed = time.time() - self._start_times[name]
        del self._start_times[name]
        self._timers[name].append(elapsed)
        
        if len(self._timers[name]) > self.max_history:
            self._timers[name] = self._timers[name][-self.max_history:]
        
        return elapsed
    
    def get_counter(self, name: str) -> int:
        """获取计数器值
        
        Args:
            name: 指标名称
            
        Returns:
            计数器值
        """
        return self._counters.get(name, 0)
    
    def get_gauge(self, name: str) -> Optional[float]:
        """获取仪表值
        
        Args:
            name: 指标名称
            
        Returns:
            仪表值
        """
        return self._gauges.get(name)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """获取直方图统计
        
        Args:
            name: 指标名称
            
        Returns:
            统计信息字典
        """
        values = list(self._histograms.get(name, []))
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "p95": self._percentile(values, 0.95),
            "p99": self._percentile(values, 0.99),
        }
    
    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """获取计时器统计
        
        Args:
            name: 计时器名称
            
        Returns:
            统计信息字典
        """
        values = self._timers.get(name, [])
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "total": sum(values),
            "p95": self._percentile(values, 0.95),
            "p99": self._percentile(values, 0.99),
        }
    
    def _percentile(self, values: List[float], p: float) -> float:
        """计算百分位数
        
        Args:
            values: 数值列表
            p: 百分位（0-1）
            
        Returns:
            百分位数值
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标
        
        Returns:
            所有指标数据
        """
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                name: self.get_histogram_stats(name)
                for name in self._histograms.keys()
            },
            "timers": {
                name: self.get_timer_stats(name)
                for name in self._timers.keys()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def reset(self):
        """重置所有指标"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()
        self._start_times.clear()
        logger.info("指标收集器已重置")
    
    def reset_counter(self, name: str):
        """重置指定计数器
        
        Args:
            name: 指标名称
        """
        if name in self._counters:
            self._counters[name] = 0


metrics_collector = MetricsCollector()


def monitor_latency(threshold: float = 1.0):
    """延迟监控装饰器
    
    Args:
        threshold: 延迟阈值（秒）
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                
                metrics_collector.record_value(f"latency_{func.__name__}", elapsed)
                
                if elapsed > threshold:
                    logger.warning(f"延迟过高: {func.__name__} = {elapsed:.3f}s > {threshold}s")
                
                return result
            except Exception as e:
                elapsed = time.time() - start
                metrics_collector.increment(f"error_{func.__name__}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                
                metrics_collector.record_value(f"latency_{func.__name__}", elapsed)
                
                if elapsed > threshold:
                    logger.warning(f"延迟过高: {func.__name__} = {elapsed:.3f}s > {threshold}s")
                
                return result
            except Exception as e:
                elapsed = time.time() - start
                metrics_collector.increment(f"error_{func.__name__}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def print_metrics_summary():
    """打印指标摘要"""
    metrics = metrics_collector.get_all_metrics()
    
    print("\n" + "=" * 50)
    print("📊 指标摘要")
    print("=" * 50)
    
    counters = metrics.get("counters", {})
    if counters:
        print("\n计数器:")
        for name, value in counters.items():
            print(f"  {name}: {value}")
    
    gauges = metrics.get("gauges", {})
    if gauges:
        print("\n仪表:")
        for name, value in gauges.items():
            print(f"  {name}: {value:.2f}")
    
    timers = metrics.get("timers", {})
    if timers:
        print("\n计时器:")
        for name, stats in timers.items():
            if stats:
                print(f"  {name}:")
                print(f"    次数: {stats['count']}")
                print(f"    平均: {stats['mean']*1000:.1f}ms")
                print(f"    P95: {stats['p95']*1000:.1f}ms")
                print(f"    最大: {stats['max']*1000:.1f}ms")
    
    print("\n" + "=" * 50)


class ServiceMonitor:
    """服务监控器
    
    监控服务健康状态和性能
    """
    
    def __init__(self):
        """初始化监控器"""
        self._services: Dict[str, Dict[str, Any]] = {}
    
    def register_service(
        self,
        name: str,
        check_func: Optional[Callable] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """注册服务
        
        Args:
            name: 服务名称
            check_func: 健康检查函数
            config: 服务配置
        """
        self._services[name] = {
            "name": name,
            "check_func": check_func,
            "config": config or {},
            "status": "unknown",
            "last_check": None,
            "uptime": 0,
            "downtime": 0,
            "error_count": 0
        }
    
    async def check_service(self, name: str) -> Dict[str, Any]:
        """检查服务状态
        
        Args:
            name: 服务名称
            
        Returns:
            健康检查结果
        """
        if name not in self._services:
            return {"status": "not_found", "name": name}
        
        service = self._services[name]
        check_func = service["check_func"]
        
        try:
            if check_func:
                if asyncio.iscoroutinefunction(check_func):
                    is_healthy = await check_func()
                else:
                    is_healthy = check_func()
            else:
                is_healthy = True
            
            service["status"] = "healthy" if is_healthy else "unhealthy"
            service["last_check"] = datetime.now().isoformat()
            
            return {
                "status": service["status"],
                "name": name,
                "last_check": service["last_check"]
            }
            
        except Exception as e:
            service["status"] = "error"
            service["error_count"] += 1
            logger.error(f"服务检查失败: {name} - {e}")
            
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }
    
    async def check_all(self) -> Dict[str, Any]:
        """检查所有服务
        
        Returns:
            所有服务状态
        """
        results = {}
        
        for name in self._services.keys():
            results[name] = await self.check_service(name)
        
        return results
    
    def get_service_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取服务状态
        
        Args:
            name: 服务名称
            
        Returns:
            服务状态信息
        """
        return self._services.get(name)
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """获取所有服务
        
        Returns:
            服务列表
        """
        return [
            {
                "name": name,
                "status": info["status"],
                "last_check": info["last_check"],
                "error_count": info["error_count"]
            }
            for name, info in self._services.items()
        ]


service_monitor = ServiceMonitor()
