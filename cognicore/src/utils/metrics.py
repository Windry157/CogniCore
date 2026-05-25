#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能指标收集 module
"""

import time
import threading
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """性能指标收集器"""
    
    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._start_time = time.time()
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        """记录API请求指标"""
        with self._lock:
            if endpoint not in self._metrics:
                self._metrics[endpoint] = {
                    "count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "min_duration": float('inf'),
                    "max_duration": 0,
                    "status_codes": {}
                }
            
            metric = self._metrics[endpoint]
            metric["count"] += 1
            metric["total_duration"] += duration
            metric["avg_duration"] = metric["total_duration"] / metric["count"]
            metric["min_duration"] = min(metric["min_duration"], duration)
            metric["max_duration"] = max(metric["max_duration"], duration)
            
            # 记录Status code
            status_str = str(status_code)
            if status_str not in metric["status_codes"]:
                metric["status_codes"][status_str] = 0
            metric["status_codes"][status_str] += 1
    
    def record_cache_metric(self, cache_name: str, hit: bool):
        """记录cache指标"""
        with self._lock:
            endpoint = f"cache:{cache_name}"
            if endpoint not in self._metrics:
                self._metrics[endpoint] = {
                    "hits": 0,
                    "misses": 0,
                    "hit_rate": 0
                }
            
            metric = self._metrics[endpoint]
            if hit:
                metric["hits"] += 1
            else:
                metric["misses"] += 1
            
            total = metric["hits"] + metric["misses"]
            if total > 0:
                metric["hit_rate"] = (metric["hits"] / total) * 100
    
    def get_metrics(self) -> Dict[str, Dict[str, any]]:
        """Get所有指标"""
        with self._lock:
            return self._metrics.copy()
    
    def get_uptime(self) -> float:
        """Get系统运行时间"""
        return time.time() - self._start_time
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._metrics.clear()
            self._start_time = time.time()

# Create全局指标收集器实例
metrics_collector = MetricsCollector()