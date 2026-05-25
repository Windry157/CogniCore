#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康监控与自动巡检模块
后台自动巡检、状态历史记录、告警通知
"""

import asyncio
import logging
import json
from collections import deque
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthMonitor:
    """健康监控器"""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.monitoring = False
        self._monitor_task = None
        self._alert_callbacks = []
        self._setup_history_file()

    def _setup_history_file(self):
        """设置历史记录文件"""
        try:
            from src.core.config.config import _get_project_root
            root = _get_project_root()
            history_dir = root / "data" / "health"
            history_dir.mkdir(parents=True, exist_ok=True)
            self._history_file = history_dir / "health_history.jsonl"
        except Exception as e:
            logger.warning(f"Could not set up history file: {e}")
            self._history_file = None

    async def start(self, interval_seconds: int = 60):
        """开始监控"""
        if self.monitoring:
            logger.warning("Monitoring already started")
            return

        self.monitoring = True
        logger.info(f"🔍 Starting health monitor (interval: {interval_seconds}s)")
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))

    async def stop(self):
        """停止监控"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Health monitor stopped")

    async def _monitor_loop(self, interval_seconds: int):
        """监控循环"""
        while self.monitoring:
            try:
                await self._check_and_log()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            await asyncio.sleep(interval_seconds)

    async def _check_and_log(self):
        """执行检查并记录"""
        from src.core.health import get_system_health
        health_data = await get_system_health()
        self._record_health_data(health_data)
        self._check_alerts(health_data)
        return health_data

    def _record_health_data(self, data: Dict[str, Any]):
        """记录健康数据"""
        self.history.append(data)
        self._save_to_history_file(data)

    def _save_to_history_file(self, data: Dict[str, Any]):
        """保存到历史文件"""
        if not self._history_file:
            return
        try:
            with open(self._history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Could not save health history: {e}")

    def _check_alerts(self, data: Dict[str, Any]):
        """检查是否需要告警"""
        status = data.get("overall_status")
        if status == "critical":
            logger.critical(f"🚨 SYSTEM HEALTH CRITICAL: {data}")
            self._trigger_alerts(data, level="critical")
        elif status == "warning":
            logger.warning(f"⚠️  SYSTEM HEALTH WARNING: {data}")
            self._trigger_alerts(data, level="warning")

    def _trigger_alerts(self, data: Dict[str, Any], level: str):
        """触发告警"""
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data, level))
                else:
                    callback(data, level)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def register_alert_callback(self, callback):
        """注册告警回调"""
        self._alert_callbacks.append(callback)
        logger.debug(f"Registered alert callback: {callback.__name__}")

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return list(self.history)[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.history:
            return {"total_checks": 0}

        status_counts = {}
        for record in self.history:
            status = record.get("overall_status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        latest = list(self.history)[-1] if self.history else None

        return {
            "total_checks": len(self.history),
            "status_distribution": status_counts,
            "latest_check": latest,
            "monitoring": self.monitoring,
            "history_size": len(self.history)
        }


_health_monitor = None


def get_health_monitor() -> HealthMonitor:
    """获取健康监控器单例"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


async def start_monitoring(interval_seconds: int = 60):
    """启动监控（便捷函数"""
    monitor = get_health_monitor()
    await monitor.start(interval_seconds)
