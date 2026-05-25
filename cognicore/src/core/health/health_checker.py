#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统健康检查模块
提供完整的运行时健康状态报告
"""

import time
import asyncio
import logging
import platform
import psutil
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthStatus:
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheckResult:
    """健康检查结果"""
    def __init__(self, name: str, status: str, message: str,
                 details: Optional[Dict[str, Any]] = None):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class SystemHealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self.checks = []
        self._register_default_checks()

    def _register_default_checks(self):
        """注册默认检查项"""
        self.checks = [
            self._check_cpu,
            self._check_memory,
            self._check_disk,
            self._check_memory_system,
            self._check_config,
            self._check_modules,
            self._check_ollama,
        ]

    async def check_all(self) -> Dict[str, Any]:
        """执行所有健康检查"""
        results = []
        overall_status = HealthStatus.HEALTHY

        for check_func in self.checks:
            try:
                result = await check_func()
                results.append(result)
                if result.status == HealthStatus.CRITICAL:
                    overall_status = HealthStatus.CRITICAL
                elif result.status == HealthStatus.WARNING and overall_status != HealthStatus.CRITICAL:
                    overall_status = HealthStatus.WARNING
            except Exception as e:
                logger.error(f"Check {check_func.__name__} failed: {e}")
                results.append(HealthCheckResult(
                    check_func.__name__,
                    HealthStatus.UNKNOWN,
                    f"Check failed: {str(e)}"
                ))

        return {
            "system": "CogniCore-Portable",
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "checks": [r.to_dict() for r in results],
            "uptime_seconds": self._get_uptime(),
            "system_info": self._get_system_info()
        }

    async def _check_cpu(self) -> HealthCheckResult:
        """检查CPU"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            status = HealthStatus.HEALTHY
            message = f"CPU usage: {cpu_percent:.1f}%"

            if cpu_percent > 90:
                status = HealthStatus.CRITICAL
                message += " - CRITIAL: High CPU load!"
            elif cpu_percent > 75:
                status = HealthStatus.WARNING
                message += " - WARNING: Elevated CPU usage"

            return HealthCheckResult(
                "CPU",
                status,
                message,
                {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                }
            )
        except Exception as e:
            return HealthCheckResult(
                "CPU",
                HealthStatus.UNKNOWN,
                f"Check failed: {e}"
            )

    async def _check_memory(self) -> HealthCheckResult:
        """检查内存"""
        try:
            memory = psutil.virtual_memory()
            mem_percent = memory.percent
            mem_available_gb = memory.available / (1024 ** 3)

            status = HealthStatus.HEALTHY
            message = f"Memory usage: {mem_percent:.1f}% ({mem_available_gb:.1f} GB available)"

            if mem_percent > 95:
                status = HealthStatus.CRITICAL
                message += " - CRITIAL: Out of memory!"
            elif mem_percent > 80:
                status = HealthStatus.WARNING
                message += " - WARNING: Low memory"

            return HealthCheckResult(
                "Memory",
                status,
                message,
                {
                    "used_percent": mem_percent,
                    "available_gb": mem_available_gb,
                    "total_gb": memory.total / (1024 ** 3)
                }
            )
        except Exception as e:
            return HealthCheckResult(
                "Memory",
                HealthStatus.UNKNOWN,
                f"Check failed: {e}"
            )

    async def _check_disk(self) -> HealthCheckResult:
        """检查磁盘"""
        try:
            from src.core.config.config import _get_project_root
            root = _get_project_root()
            disk = psutil.disk_usage(str(root))
            disk_percent = disk.percent

            status = HealthStatus.HEALTHY
            message = f"Disk usage: {disk_percent:.1f}%"

            if disk_percent > 95:
                status = HealthStatus.CRITICAL
                message += " - CRITIAL: Disk almost full!"
            elif disk_percent > 85:
                status = HealthStatus.WARNING
                message += " - WARNING: Low disk space"

            return HealthCheckResult(
                "Disk",
                status,
                message,
                {
                    "used_percent": disk_percent,
                    "free_gb": disk.free / (1024 ** 3),
                    "total_gb": disk.total / (1024 ** 3)
                }
            )
        except Exception as e:
            return HealthCheckResult(
                "Disk",
                HealthStatus.UNKNOWN,
                f"Check failed: {e}"
            )

    async def _check_memory_system(self) -> HealthCheckResult:
        """检查记忆系统"""
        try:
            from src.core.config.config import _get_project_root
            from src.core.config import config
            root = _get_project_root()
            memory_dir = root / config.memory.memory_dir
            ep_file = memory_dir / "episodic_memory.json"

            memory_count = 0
            if ep_file.exists():
                data = json.loads(ep_file.read_text(encoding="utf-8"))
                memory_count = len(data) if isinstance(data, list) else 0

            return HealthCheckResult(
                "Memory System",
                HealthStatus.HEALTHY,
                f"Memory system operational, {memory_count} memories stored",
                {
                    "memory_count": memory_count,
                    "directory_exists": memory_dir.exists()
                }
            )
        except Exception as e:
            return HealthCheckResult(
                "Memory System",
                HealthStatus.WARNING,
                f"Memory system check: {e}",
                {"error": str(e)}
            )

    async def _check_config(self) -> HealthCheckResult:
        """检查配置"""
        try:
            from src.core.config import config
            return HealthCheckResult(
                "Config",
                HealthStatus.HEALTHY,
                "Configuration loaded successfully",
                {
                    "system_name": config.system.system_name,
                    "system_version": config.system.system_version
                }
            )
        except Exception as e:
            return HealthCheckResult(
                "Config",
                HealthStatus.CRITICAL,
                f"Config system failed: {e}"
            )

    async def _check_modules(self) -> HealthCheckResult:
        """检查核心模块"""
        results = {
            "cognition": False,
            "resilience": False,
            "uncertainty": False,
            "observability": False
        }

        try:
            from src.core import cognition
            results["cognition"] = True
        except ImportError:
            pass

        try:
            from src.core import resilience
            results["resilience"] = True
        except ImportError:
            pass

        try:
            from src.core import uncertainty
            results["uncertainty"] = True
        except ImportError:
            pass

        try:
            from src.core import observability
            results["observability"] = True
        except ImportError:
            pass

        all_ok = all(results.values())
        return HealthCheckResult(
            "Modules",
            HealthStatus.HEALTHY if all_ok else HealthStatus.WARNING,
            f"Modules status: {sum(results.values())}/{len(results)} loaded",
            results
        )

    async def _check_ollama(self) -> HealthCheckResult:
        """检查Ollama连接"""
        try:
            from src.core.config import config
            import httpx

            base = config.llm.ollama_base_url.rstrip("/")
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{base}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    models = data.get("models", [])
                    return HealthCheckResult(
                        "Ollama",
                        HealthStatus.HEALTHY,
                        f"Ollama connected, {len(models)} models available",
                        {
                            "connected": True,
                            "model_count": len(models),
                            "model_names": [m.get("name") for m in models]
                        }
                    )
                return HealthCheckResult(
                    "Ollama",
                    HealthStatus.WARNING,
                    "Ollama unreachable (optional)",
                    {"connected": False}
                )
        except Exception as e:
            return HealthCheckResult(
                "Ollama",
                HealthStatus.WARNING,
                "Ollama check failed (optional)",
                {"connected": False, "error": str(e)}
            )

    def _get_uptime(self) -> float:
        """获取系统运行时间（秒）"""
        try:
            return time.time() - psutil.boot_time()
        except Exception:
            return 0.0

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor() or "Unknown"
        }


_health_checker = None


def get_health_checker() -> SystemHealthChecker:
    """获取健康检查器单例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = SystemHealthChecker()
    return _health_checker


async def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    checker = get_health_checker()
    return await checker.check_all()
