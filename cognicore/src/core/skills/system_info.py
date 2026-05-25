#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System InfoSkill: Get CPU, 内存, 磁盘, System Info
"""
import os
import platform
import psutil
import datetime
from typing import Dict, Any
from .base import BaseSkill


class SystemInfoSkill(BaseSkill):
    """System InfoSkill"""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "GetSystem Info, 包括 CPU, 内存, 磁盘使用情况, 系统详情等."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "要执行的操作",
                    "enum": ["get_cpu", "get_memory", "get_disk", "get_system", "get_all"]
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {"status": "success", "data": {}}

        try:
            if action == "get_cpu":
                result["data"] = self._get_cpu_info()
            elif action == "get_memory":
                result["data"] = self._get_memory_info()
            elif action == "get_disk":
                result["data"] = self._get_disk_info()
            elif action == "get_system":
                result["data"] = self._get_system_details()
            elif action == "get_all":
                result["data"] = {
                    "cpu": self._get_cpu_info(),
                    "memory": self._get_memory_info(),
                    "disk": self._get_disk_info(),
                    "system": self._get_system_details()
                }
            else:
                result["status"] = "error"
                result["message"] = f"未知的操作: {action}"
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)

        return result

    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU 信息"""
        cpu_count = psutil.cpu_count(logical=True)
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        return {
            "count": cpu_count,
            "percent": cpu_percent,
            "freq": {
                "current": cpu_freq.current if cpu_freq else 0,
                "min": cpu_freq.min if cpu_freq else 0,
                "max": cpu_freq.max if cpu_freq else 0
            },
            "model": platform.processor()
        }

    def _get_memory_info(self) -> Dict[str, Any]:
        """Get内存信息"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        }

    def _get_disk_info(self) -> Dict[str, Any]:
        """Get磁盘信息"""
        disk_info = {}
        for partition in psutil.disk_partitions():
            if partition.fstype:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                        "fstype": partition.fstype
                    }
                except Exception:
                    pass
        return disk_info

    def _get_system_details(self) -> Dict[str, Any]:
        """Get系统详情"""
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "node": platform.node(),
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": str(uptime)
        }
