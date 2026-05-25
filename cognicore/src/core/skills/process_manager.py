#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程管理Skill: 查看和管理运行中的程序
"""
import psutil
import os
from typing import Dict, Any, List
from datetime import datetime
from .base import BaseSkill


class ProcessManagerSkill(BaseSkill):
    """进程管理Skill"""

    @property
    def name(self) -> str:
        return "process_manager"

    @property
    def description(self) -> str:
        return "进程管理, 包括List进程, Get进程详情, 结束进程等."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_processes", "get_process", "kill_process", "find_process", "get_startup_items"],
                    "description": "要执行的操作"
                },
                "pid": {
                    "type": "integer",
                    "description": "进程 ID (用于Get和结束进程) "
                },
                "name": {
                    "type": "string",
                    "description": "进程Name (用于查找进程) "
                },
                "limit": {
                    "type": "integer",
                    "description": "返回进程数量限制, 默认50"
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {"status": "success", "data": {}}

        try:
            if action == "list_processes":
                limit = params.get("limit", 50)
                result["data"] = self._list_processes(limit)
            elif action == "get_process":
                pid = params.get("pid")
                if pid is None:
                    return {"status": "error", "message": "需要提供进程 ID (pid)"}
                result["data"] = self._get_process(pid)
            elif action == "kill_process":
                pid = params.get("pid")
                if pid is None:
                    return {"status": "error", "message": "需要提供进程 ID (pid)"}
                result["data"] = self._kill_process(pid)
            elif action == "find_process":
                name = params.get("name", "")
                if not name:
                    return {"status": "error", "message": "需要提供进程Name (name)"}
                result["data"] = self._find_process(name)
            elif action == "get_startup_items":
                result["data"] = self._get_startup_items()
            else:
                result["status"] = "error"
                result["message"] = f"未知的动作: {action}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"执行出错: {str(e)}"

        return result

    def _list_processes(self, limit: int) -> Dict[str, Any]:
        """List进程"""
        processes = []
        count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'create_time']):
            try:
                if count >= limit:
                    break
                
                with proc.oneshot():
                    mem_info = proc.info['memory_info']
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "username": proc.info['username'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_rss": self._format_bytes(mem_info.rss),
                        "memory_vms": self._format_bytes(mem_info.vms),
                        "create_time": datetime.fromtimestamp(proc.info['create_time']).strftime("%Y-%m-%d %H:%M:%S")
                    })
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        return {
            "total_processes": len(list(psutil.process_iter())),
            "returned_processes": len(processes),
            "processes": processes
        }

    def _get_process(self, pid: int) -> Dict[str, Any]:
        """Get进程详情"""
        proc = psutil.Process(pid)
        
        with proc.oneshot():
            mem_info = proc.memory_info()
            connections = []
            try:
                for conn in proc.connections():
                    connections.append({
                        "fd": conn.fd,
                        "family": str(conn.family),
                        "type": str(conn.type),
                        "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        "status": conn.status
                    })
            except (psutil.AccessDenied, psutil.ZombieProcess):
                pass
            
            threads = []
            try:
                for thread in proc.threads():
                    threads.append({
                        "id": thread.id,
                        "user_time": thread.user_time,
                        "system_time": thread.system_time
                    })
            except (psutil.AccessDenied, psutil.ZombieProcess):
                pass
            
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "exe": proc.exe() if proc.exe() else None,
                "cmdline": proc.cmdline() if proc.cmdline() else [],
                "username": proc.username(),
                "status": proc.status(),
                "create_time": datetime.fromtimestamp(proc.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
                "cpu_percent": proc.cpu_percent(),
                "cpu_times": {
                    "user": proc.cpu_times().user,
                    "system": proc.cpu_times().system
                },
                "memory": {
                    "rss": self._format_bytes(mem_info.rss),
                    "vms": self._format_bytes(mem_info.vms),
                    "percent": proc.memory_percent()
                },
                "open_files": len(proc.open_files()) if proc.open_files() else 0,
                "connections": connections,
                "threads": threads,
                "nice": proc.nice()
            }

    def _kill_process(self, pid: int) -> Dict[str, Any]:
        """结束进程"""
        proc = psutil.Process(pid)
        name = proc.name()
        
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
                return {
                    "pid": pid,
                    "name": name,
                    "message": "进程already successful结束"
                }
            except psutil.TimeoutExpired:
                proc.kill()
                return {
                    "pid": pid,
                    "name": name,
                    "message": "进程无Response, already强制结束"
                }
        except psutil.AccessDenied:
            return {
                "pid": pid,
                "name": name,
                "message": "权限不足, 无法结束该进程"
            }

    def _find_process(self, name: str) -> Dict[str, Any]:
        """查找进程"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                if name.lower() in proc.info['name'].lower():
                    with proc.oneshot():
                        processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "username": proc.info['username']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return {
            "found_count": len(processes),
            "processes": processes
        }

    def _get_startup_items(self) -> Dict[str, Any]:
        """Get开机Start项 (Windows) """
        import winreg
        startup_items = []
        
        # Registry位置列表
        reg_locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU\\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM\\Run"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU\\RunOnce"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM\\RunOnce"),
        ]
        
        for hkey, subkey, location_name in reg_locations:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            startup_items.append({
                                "name": name,
                                "command": value,
                                "location": location_name,
                                "type": "registry"
                            })
                            i += 1
                        except OSError:
                            break
            except (FileNotFoundError, PermissionError):
                continue
        
        # Start文件夹
        startup_folders = [
            (os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"), "User Startup"),
            (os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\StartUp"), "System Startup"),
        ]
        
        for folder_path, location_name in startup_folders:
            try:
                if os.path.exists(folder_path):
                    for item in os.listdir(folder_path):
                        item_path = os.path.join(folder_path, item)
                        startup_items.append({
                            "name": item,
                            "command": item_path,
                            "location": location_name,
                            "type": "folder"
                        })
            except (PermissionError, OSError):
                continue
        
        return {
            "total_items": len(startup_items),
            "items": startup_items
        }

    def _format_bytes(self, bytes_value: int) -> str:
        """格式化 bytes数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
