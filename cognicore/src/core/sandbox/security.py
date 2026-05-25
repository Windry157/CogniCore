#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import yaml
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class SandboxSecurity:
    """沙箱Security policy控制器 - 支持HITL人机协同审批"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SandboxSecurity._initialized:
            return

        self.config_path = Path("config/sandbox_policy.yaml")
        self.policy = self._load_policy()
        self.audit_log = []
        self.resource_usage = {
            "file_operations": 0,
            "network_requests": 0,
            "execution_time": 0,
            "memory_usage": 0
        }
        
        # HITL相关Status
        self.suspended_tasks = {}  # task_id -> {skill, payload, timestamp}
        self.approval_callbacks = {}  # task_id -> callback
        
        # 高危Skill白名单 (需要人工审批的Skill) 
        self.dangerous_skills = {
            "system_control",
            "code_executor",
            "process_manager",
            "file_manager"
        }
        
        # 高危操作模式
        self.dangerous_operations = {
            "system_control": ["shutdown", "restart", "hibernate", "open_app"],
            "code_executor": ["execute", "run"],
            "process_manager": ["kill", "terminate"],
            "file_manager": ["delete", "remove", "write", "move"]
        }

        SandboxSecurity._initialized = True
        logger.info("Sandbox security module initialized - HITL enabled")

    def _load_policy(self) -> Dict[str, Any]:
        """LoadSecurity policy配置"""
        if not self.config_path.exists():
            logger.warning(f"Security policy file does not exist: {self.config_path}, using default policy")
            return self._get_default_policy()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                policy = yaml.safe_load(f)
                logger.info(f"Security policyloaded: {self.config_path}")
                return policy
        except Exception as e:
            logger.error(f"LoadSecurity policy failed: {e}, using default policy")
            return self._get_default_policy()

    def _get_default_policy(self) -> Dict[str, Any]:
        """Get默认Security policy"""
        return {
            "sandbox": {"enabled": True, "mode": "strict"},
            "allowed_paths": ["/tmp", "/media/wl/D盘/zhinengti"],
            "blocked_commands": ["rm -rf /", "shutdown", "sudo"],
            "network_rules": {"allow": ["localhost:*"], "deny": ["*"]},
            "resource_limits": {
                "max_file_size_mb": 100,
                "max_memory_mb": 4096,
                "max_cpu_percent": 80,
                "max_execution_time_seconds": 300
            },
            "audit": {"enabled": True, "log_file": "logs/sandbox_audit.log"},
            "dangerous_patterns": ["rm -rf", "format", "fdisk"],
            "hitl": {"enabled": True, "require_approval_for_dangerous_skills": True}
        }

    def check_path_access(self, path: str, operation: str = "read") -> Tuple[bool, str]:
        """检查路径访问权限"""
        if not self.policy.get("sandbox", {}).get("enabled", True):
            return True, "沙箱未启用"

        path = os.path.abspath(os.path.expanduser(path))
        allowed_paths = self.policy.get("allowed_paths", [])

        for allowed in allowed_paths:
            allowed = os.path.abspath(os.path.expanduser(allowed))
            if path.startswith(allowed) or allowed in path:
                self._audit_log("path_access", operation, path, "allowed")
                return True, f"路径在白名单内: {allowed}"

        self._audit_log("path_access", operation, path, "denied")
        return False, f"路径不在白名单内: {path}"

    def check_command(self, command: str) -> Tuple[bool, str]:
        """检查命令是否危险"""
        if not self.policy.get("sandbox", {}).get("enabled", True):
            return True, "沙箱未启用"

        blocked = self.policy.get("blocked_commands", [])
        for block in blocked:
            if block.lower() in command.lower():
                self._audit_log("command", "execute", command, "denied")
                return False, f"命令被禁用: {block}"

        dangerous = self.policy.get("dangerous_patterns", [])
        for pattern in dangerous:
            if re.search(pattern, command, re.IGNORECASE):
                self._audit_log("command", "execute", command, "denied")
                return False, f"命令包含危险模式: {pattern}"

        self._audit_log("command", "execute", command, "allowed")
        return True, "命令检查通过"

    def check_network(self, host: str, port: Optional[int] = None) -> Tuple[bool, str]:
        """检查网络访问权限"""
        if not self.policy.get("sandbox", {}).get("enabled", True):
            return True, "沙箱未启用"

        rules = self.policy.get("network_rules", {})
        allow_list = rules.get("allow", [])
        deny_list = rules.get("deny", ["*"])

        target = f"{host}:{port}" if port else host

        for deny in deny_list:
            if self._match_pattern(target, deny):
                for allow in allow_list:
                    if self._match_pattern(target, allow):
                        self._audit_log("network", "access", target, "allowed")
                        return True, "网络访问允许"
                self._audit_log("network", "access", target, "denied")
                return False, f"网络访问被拒绝: {target}"

        self._audit_log("network", "access", target, "allowed")
        return True, "网络访问允许"

    def check_resource(self, resource_type: str) -> Tuple[bool, str]:
        """检查资源使用配额"""
        limits = self.policy.get("resource_limits", {})

        if resource_type == "execution_time":
            max_time = limits.get("max_execution_time_seconds", 300)
            if self.resource_usage["execution_time"] >= max_time:
                return False, f"执行时间超限: {max_time}s"
            self.resource_usage["execution_time"] += 1

        elif resource_type == "file_size":
            pass

        return True, "资源检查通过"

    def check_skill_execution(self, skill_name: str, action: str = None) -> Tuple[bool, str, Optional[str]]:
        """
        检查Skill执行权限 - HITL核心方法
        
        Args:
            skill_name: SkillName
            action: 操作type
            
        Returns:
            (允许执行, Reason, task_id/None)
        """
        hitl_enabled = self.policy.get("hitl", {}).get("enabled", True)
        
        if not hitl_enabled:
            return True, "HITL未启用", None
            
        if not self.policy.get("sandbox", {}).get("enabled", True):
            return True, "沙箱未启用", None
            
        if skill_name not in self.dangerous_skills:
            self._audit_log("skill_execution", skill_name, action, "allowed")
            return True, "Skill不在高危列表", None
            
        # 检查是否是高危操作
        if action and skill_name in self.dangerous_operations:
            if action in self.dangerous_operations[skill_name]:
                # 需要人工审批 - 挂起Task
                task_id = self._suspend_task(skill_name, action)
                self._audit_log("skill_execution", skill_name, action, "suspended")
                return False, f"高危操作需要人工审批", task_id
                
        self._audit_log("skill_execution", skill_name, action, "allowed")
        return True, "操作安全检查通过", None

    def _suspend_task(self, skill_name: str, action: str) -> str:
        """挂起Task并生成task_id"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        self.suspended_tasks[task_id] = {
            "skill": skill_name,
            "action": action,
            "payload": {},
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # 发送审批请求到前端
        self._notify_approval_required(task_id, skill_name, action)
        
        return task_id

    def _notify_approval_required(self, task_id: str, skill_name: str, action: str):
        """通过WebSocket向前端发送审批请求"""
        try:
            from src.api.websocket_manager import websocket_manager
            
            message = {
                "type": "HITL_APPROVAL_REQUIRED",
                "task_id": task_id,
                "skill": skill_name,
                "action": action,
                "timestamp": datetime.now().isoformat(),
                "message": f"需要您批准执行 '{skill_name}' Skill的 '{action}' 操作"
            }
            
            asyncio.create_task(websocket_manager.broadcast(message))
            logger.info(f"HITL approval request sent: {task_id} - {skill_name}.{action}")
        except Exception as e:
            logger.error(f"Send HITL approval request failed: {e}")

    def approve_task(self, task_id: str) -> bool:
        """批准挂起的Task"""
        if task_id not in self.suspended_tasks:
            return False
            
        self.suspended_tasks[task_id]["status"] = "approved"
        self._audit_log("hitl_approval", "approve", task_id, "approved")
        
        # 触发回调
        if task_id in self.approval_callbacks:
            callback = self.approval_callbacks.pop(task_id)
            asyncio.create_task(callback(True))
            
        logger.info(f"HITL task approved: {task_id}")
        return True

    def deny_task(self, task_id: str) -> bool:
        """拒绝挂起的Task"""
        if task_id not in self.suspended_tasks:
            return False
            
        self.suspended_tasks[task_id]["status"] = "denied"
        self._audit_log("hitl_approval", "deny", task_id, "denied")
        
        # 触发回调
        if task_id in self.approval_callbacks:
            callback = self.approval_callbacks.pop(task_id)
            asyncio.create_task(callback(False))
            
        logger.info(f"HITL task rejected: {task_id}")
        return True

    def get_suspended_tasks(self) -> List[Dict[str, Any]]:
        """Get所有挂起的Task"""
        return list(self.suspended_tasks.values())

    def _match_pattern(self, target: str, pattern: str) -> bool:
        """通配符模式匹配"""
        if pattern == "*":
            return True
        pattern = pattern.replace(".", r"\.").replace("*", ".*")
        return bool(re.match(f"^{pattern}$", target, re.IGNORECASE))

    def _audit_log(self, action_type: str, operation: str, target: str, result: str):
        """记录审计日志"""
        if not self.policy.get("audit", {}).get("enabled", True):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "operation": operation,
            "target": target,
            "result": result,
            "resource_usage": dict(self.resource_usage)
        }

        self.audit_log.append(log_entry)

        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-500:]

        log_file = self.policy.get("audit", {}).get("log_file", "logs/sandbox_audit.log")
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get最近的审计日志"""
        return self.audit_log[-limit:]

    def reset_resources(self):
        """重置资源使用计数"""
        self.resource_usage = {
            "file_operations": 0,
            "network_requests": 0,
            "execution_time": 0,
            "memory_usage": 0
        }


_sandbox_security_instance = None


def get_sandbox_security() -> SandboxSecurity:
    """Get沙箱安全单例"""
    global _sandbox_security_instance
    if _sandbox_security_instance is None:
        _sandbox_security_instance = SandboxSecurity()
    return _sandbox_security_instance