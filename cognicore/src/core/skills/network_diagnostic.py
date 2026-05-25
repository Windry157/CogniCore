#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络诊断Skill: 网络Status和ConnectTest
"""
import psutil
import socket
import requests
from typing import Dict, Any, List
from datetime import datetime
from .base import BaseSkill


class NetworkDiagnosticSkill(BaseSkill):
    """网络诊断Skill"""

    @property
    def name(self) -> str:
        return "network_diagnostic"

    @property
    def description(self) -> str:
        return "网络诊断, 包括Get网络接口, ConnectStatus, Ping Test, 网站连通性检查等."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_interfaces", "get_connections", "ping", "check_url", "get_all"],
                    "description": "要执行的操作"
                },
                "host": {
                    "type": "string",
                    "description": "目标主机 (用于 ping 和 url 检查) "
                },
                "port": {
                    "type": "integer",
                    "description": "端口号 (用于 ping Test) , 默认80"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间 (s) , 默认5"
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {"status": "success", "data": {}}

        try:
            if action == "get_interfaces":
                result["data"] = self._get_interfaces()
            elif action == "get_connections":
                result["data"] = self._get_connections()
            elif action == "ping":
                host = params.get("host")
                if not host:
                    return {"status": "error", "message": "需要提供目标主机 (host)"}
                port = params.get("port", 80)
                timeout = params.get("timeout", 5)
                result["data"] = self._ping_test(host, port, timeout)
            elif action == "check_url":
                host = params.get("host")
                if not host:
                    return {"status": "error", "message": "需要提供 URL (host)"}
                timeout = params.get("timeout", 5)
                result["data"] = self._check_url(host, timeout)
            elif action == "get_all":
                result["data"] = {
                    "interfaces": self._get_interfaces(),
                    "connections": self._get_connections()
                }
            else:
                result["status"] = "error"
                result["message"] = f"未知的动作: {action}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"执行出错: {str(e)}"

        return result

    def _get_interfaces(self) -> Dict[str, Any]:
        """Get网络接口信息"""
        interfaces = {}
        
        for iface_name, addrs in psutil.net_if_addrs().items():
            interfaces[iface_name] = {
                "addresses": []
            }
            
            for addr in addrs:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address
                }
                if addr.netmask:
                    addr_info["netmask"] = addr.netmask
                if addr.broadcast:
                    addr_info["broadcast"] = addr.broadcast
                interfaces[iface_name]["addresses"].append(addr_info)
        
        stats = psutil.net_if_stats()
        for iface_name, iface_stats in stats.items():
            if iface_name in interfaces:
                interfaces[iface_name]["stats"] = {
                    "is_up": iface_stats.isup,
                    "duplex": str(iface_stats.duplex),
                    "speed": f"{iface_stats.speed} Mbps",
                    "mtu": iface_stats.mtu
                }
        
        io_counters = psutil.net_io_counters(pernic=True)
        for iface_name, io in io_counters.items():
            if iface_name in interfaces:
                interfaces[iface_name]["io"] = {
                    "bytes_sent": self._format_bytes(io.bytes_sent),
                    "bytes_recv": self._format_bytes(io.bytes_recv),
                    "packets_sent": io.packets_sent,
                    "packets_recv": io.packets_recv,
                    "errin": io.errin,
                    "errout": io.errout,
                    "dropin": io.dropin,
                    "dropout": io.dropout
                }
        
        return {
            "hostname": socket.gethostname(),
            "interfaces": interfaces
        }

    def _get_connections(self) -> Dict[str, Any]:
        """Get网络Connect信息"""
        connections = []
        # 只Get前20 Connect, 避免过长
        for conn in psutil.net_connections(kind='inet')[:20]:
            try:
                conn_info = {
                    "fd": conn.fd,
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid
                }
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        conn_info["process_name"] = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                connections.append(conn_info)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        
        return {
            "total_connections": len(connections),
            "note": "仅显示前20 Connect",
            "connections": connections
        }

    def _ping_test(self, host: str, port: int, timeout: int) -> Dict[str, Any]:
        """Ping Test"""
        start_time = datetime.now()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            if result == 0:
                return {
                    "host": host,
                    "port": port,
                    "reachable": True,
                    "response_time": f"{elapsed:.2f} ms"
                }
            else:
                return {
                    "host": host,
                    "port": port,
                    "reachable": False,
                    "error": f"Connect failed, Error码: {result}"
                }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "reachable": False,
                "error": str(e)
            }

    def _check_url(self, url: str, timeout: int) -> Dict[str, Any]:
        """检查 URL 连通性"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        start_time = datetime.now()
        
        try:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "url": url,
                "status_code": response.status_code,
                "response_time": f"{elapsed:.2f} ms",
                "headers": dict(response.headers),
                "final_url": response.url
            }
        except requests.exceptions.RequestException as e:
            return {
                "url": url,
                "error": str(e)
            }

    def _format_bytes(self, bytes_value: int) -> str:
        """格式化 bytes数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
