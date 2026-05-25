#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全监控Skill: 安全检查和日志分析
"""
import os
import platform
import psutil
import hashlib
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from .base import BaseSkill


class SecurityMonitorSkill(BaseSkill):
    """安全监控Skill"""

    @property
    def name(self) -> str:
        return "security_monitor"

    @property
    def description(self) -> str:
        return "安全监控, 包括检查敏感端口, 扫描可疑进程, 文件哈希计算, 系统安全检查等."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check_ports", "scan_processes", "file_hash", "system_check", "get_all"],
                    "description": "要执行的操作"
                },
                "path": {
                    "type": "string",
                    "description": "文件路径 (用于文件哈希计算) "
                },
                "algorithm": {
                    "type": "string",
                    "description": "哈希算法 (md5, sha1, sha256, sha512) , 默认sha256",
                    "enum": ["md5", "sha1", "sha256", "sha512"]
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {"status": "success", "data": {}}

        try:
            if action == "check_ports":
                result["data"] = self._check_sensitive_ports()
            elif action == "scan_processes":
                result["data"] = self._scan_suspicious_processes()
            elif action == "file_hash":
                path = params.get("path")
                if not path:
                    return {"status": "error", "message": "需要提供文件路径 (path)"}
                algorithm = params.get("algorithm", "sha256")
                result["data"] = self._calculate_file_hash(path, algorithm)
            elif action == "system_check":
                result["data"] = self._system_security_check()
            elif action == "get_all":
                result["data"] = {
                    "ports": self._check_sensitive_ports(),
                    "processes": self._scan_suspicious_processes(),
                    "system": self._system_security_check()
                }
            else:
                result["status"] = "error"
                result["message"] = f"未知的动作: {action}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"执行出错: {str(e)}"

        return result

    def _check_sensitive_ports(self) -> Dict[str, Any]:
        """检查敏感端口"""
        sensitive_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 993, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017]
        open_ports = []
        
        for conn in psutil.net_connections(kind='inet'):
            try:
                if conn.laddr and conn.status == 'LISTEN':
                    port = conn.laddr.port
                    if port in sensitive_ports:
                        port_info = {
                            "port": port,
                            "address": conn.laddr.ip,
                            "status": conn.status,
                            "pid": conn.pid
                        }
                        if conn.pid:
                            try:
                                proc = psutil.Process(conn.pid)
                                port_info["process_name"] = proc.name()
                                port_info["process_exe"] = proc.exe() if proc.exe() else None
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        open_ports.append(port_info)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        
        return {
            "sensitive_ports_checked": len(sensitive_ports),
            "open_sensitive_ports": len(open_ports),
            "open_ports": open_ports
        }

    def _scan_suspicious_processes(self) -> Dict[str, Any]:
        """扫描可疑进程"""
        suspicious_names = [
            "cmd.exe", "powershell.exe", "wscript.exe", "cscript.exe",
            "mshta.exe", "rundll32.exe", "regsvr32.exe", "svchost.exe",
            "taskmgr.exe", "taskkill.exe", "net.exe", "netstat.exe",
            "ncat.exe", "nc.exe", "telnet.exe", "ftp.exe"
        ]
        suspicious_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'exe']):
            try:
                with proc.oneshot():
                    proc_name = proc.info['name'].lower()
                    if proc_name in [name.lower() for name in suspicious_names]:
                        suspicious_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "username": proc.info['username'],
                            "exe": proc.info['exe'] if proc.info['exe'] else None
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return {
            "suspicious_process_names": len(suspicious_names),
            "found_suspicious_processes": len(suspicious_processes),
            "processes": suspicious_processes
        }

    def _calculate_file_hash(self, path: str, algorithm: str) -> Dict[str, Any]:
        """计算文件哈希"""
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"File does not exist或不是文件: {path}")
        
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)
        
        return {
            "path": str(file_path.resolve()),
            "algorithm": algorithm,
            "hash": hash_func.hexdigest(),
            "size": self._format_bytes(file_path.stat().st_size),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }

    def _system_security_check(self) -> Dict[str, Any]:
        """系统安全检查"""
        checks = {}
        
        if platform.system() == 'Windows':
            checks["os"] = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine()
            }
            
            checks["users"] = []
            try:
                import ctypes
                import ctypes.wintypes
                ADVAPI32 = ctypes.windll.advapi32
                MAX_PREFERRED_LENGTH = ctypes.wintypes.DWORD(-1)
                class USER_INFO_3(ctypes.Structure):
                    _fields_ = [
                        ("usri3_name", ctypes.wintypes.LPWSTR),
                        ("usri3_password", ctypes.wintypes.LPWSTR),
                        ("usri3_password_age", ctypes.wintypes.DWORD),
                        ("usri3_priv", ctypes.wintypes.DWORD),
                        ("usri3_home_dir", ctypes.wintypes.LPWSTR),
                        ("usri3_comment", ctypes.wintypes.LPWSTR),
                        ("usri3_flags", ctypes.wintypes.DWORD),
                        ("usri3_script_path", ctypes.wintypes.LPWSTR),
                        ("usri3_auth_flags", ctypes.wintypes.DWORD),
                        ("usri3_full_name", ctypes.wintypes.LPWSTR),
                        ("usri3_usr_comment", ctypes.wintypes.LPWSTR),
                        ("usri3_parms", ctypes.wintypes.LPWSTR),
                        ("usri3_workstations", ctypes.wintypes.LPWSTR),
                        ("usri3_last_logon", ctypes.wintypes.DWORD),
                        ("usri3_last_logoff", ctypes.wintypes.DWORD),
                        ("usri3_acct_expires", ctypes.wintypes.DWORD),
                        ("usri3_max_storage", ctypes.wintypes.DWORD),
                        ("usri3_units_per_week", ctypes.wintypes.DWORD),
                        ("usri3_logon_hours", ctypes.POINTER(ctypes.c_byte)),
                        ("usri3_bad_pw_count", ctypes.wintypes.DWORD),
                        ("usri3_num_logons", ctypes.wintypes.DWORD),
                        ("usri3_logon_server", ctypes.wintypes.LPWSTR),
                        ("usri3_country_code", ctypes.wintypes.DWORD),
                        ("usri3_code_page", ctypes.wintypes.DWORD),
                        ("usri3_user_id", ctypes.wintypes.DWORD),
                        ("usri3_primary_group_id", ctypes.wintypes.DWORD),
                        ("usri3_profile", ctypes.wintypes.LPWSTR),
                        ("usri3_home_dir_drive", ctypes.wintypes.LPWSTR),
                        ("usri3_password_expired", ctypes.wintypes.DWORD)
                    ]
                lp_buffer = ctypes.wintypes.LPVOID()
                entries_read = ctypes.wintypes.DWORD()
                total_entries = ctypes.wintypes.DWORD()
                if ADVAPI32.NetUserEnum(None, 3, 0, ctypes.byref(lp_buffer), MAX_PREFERRED_LENGTH,
                                        ctypes.byref(entries_read), ctypes.byref(total_entries), None) == 0:
                    array_type = USER_INFO_3 * entries_read.value
                    users = ctypes.cast(lp_buffer, ctypes.POINTER(USER_INFO_3))
                    for i in range(entries_read.value):
                        user = users[i]
                        checks["users"].append({
                            "name": user.usri3_name,
                            "full_name": user.usri3_full_name or "",
                            "privilege": user.usri3_priv
                        })
                    ADVAPI32.NetApiBufferFree(lp_buffer)
            except Exception as e:
                checks["users_error"] = str(e)
        else:
            checks["os"] = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine()
            }
        
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        checks["uptime"] = str(datetime.now() - boot_time).split('.')[0]
        
        return checks

    def _format_bytes(self, bytes_value: int) -> str:
        """格式化 bytes数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
