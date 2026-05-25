#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
from typing import Dict, Any, List, Optional
from .skills.base import BaseSkill
from .skills.system import SystemControlSkill
from .skills.system_info import SystemInfoSkill
from .skills.file_manager import FileManagerSkill
from .skills.process_manager import ProcessManagerSkill
from .skills.network_diagnostic import NetworkDiagnosticSkill
from .skills.security_monitor import SecurityMonitorSkill
from .skills.code_executor import CodeExecutorSkill
from .skills.search import SearchSkill
from .skills.skill_draw import DrawSkill
from .skills.skill_translate import TranslateSkill
from .skills.skill_data_analyze import DataAnalyzeSkill
# 导入Browser automationSkill
try:
    from .browser_automation import BrowserAutomationSkill
    BROWSER_AUTOMATION_AVAILABLE = True
except ImportError:
    BROWSER_AUTOMATION_AVAILABLE = False

logger = logging.getLogger(__name__)

class SkillManager:
    """Skill manager - 集成HITL人机协同审批"""
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        # 自动Register所有Skill
        self.register_skill(SystemControlSkill())
        self.register_skill(SystemInfoSkill())
        self.register_skill(FileManagerSkill())
        self.register_skill(ProcessManagerSkill())
        self.register_skill(NetworkDiagnosticSkill())
        self.register_skill(SecurityMonitorSkill())
        self.register_skill(CodeExecutorSkill())
        self.register_skill(SearchSkill())
        self.register_skill(DrawSkill())
        self.register_skill(TranslateSkill())
        self.register_skill(DataAnalyzeSkill())
        # RegisterBrowser automationSkill (如果可用) 
        if BROWSER_AUTOMATION_AVAILABLE:
            self.register_skill(BrowserAutomationSkill())
            logger.info("Browser automationSkillRegistered")

    def register_skill(self, skill: BaseSkill):
        self.skills[skill.name] = skill
        logger.info(f"alreadyRegistering skill: {skill.name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """生成 OpenAI 兼容的tool definition列表 (JSON Schema)"""
        tools = []
        for name, skill in self.skills.items():
            tool_def = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": skill.description,
                    "parameters": skill.parameters
                }
            }
            tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, action: str, params: Dict[str, Any]) -> str:
        """执行Tool并返回文本"""
        if tool_name in self.skills:
            logger.info(f"Executing tool: {tool_name} -> {action}")

            # 沙箱安全检查
            try:
                from .sandbox import get_sandbox_security
                sandbox = get_sandbox_security()

                # ==================== HITL人机协同审批检查 ====================
                # 检查Skill执行是否需要人工审批
                allowed, reason, task_id = sandbox.check_skill_execution(tool_name, action)
                if not allowed:
                    logger.warning(f"HITLapproval intercepted: {tool_name}.{action}")
                    return json.dumps({
                        "status": "pending",
                        "message": reason,
                        "task_id": task_id,
                        "skill": tool_name,
                        "action": action,
                        "type": "HITL_APPROVAL_REQUIRED"
                    }, ensure_ascii=False)
                # ==================== HITL检查结束 ====================

                # 检查路径访问 (如果有文件路径参数) 
                if "path" in params:
                    allowed, reason = sandbox.check_path_access(params["path"], "read")
                    if not allowed:
                        logger.warning(f"Path access denied: {params['path']}, Reason: {reason}")
                        return json.dumps({"status": "error", "message": f"Security policy拒绝: {reason}"}, ensure_ascii=False)

                # 检查命令执行
                if tool_name in ["code_executor", "system_control"]:
                    if "command" in params:
                        allowed, reason = sandbox.check_command(params["command"])
                        if not allowed:
                            logger.warning(f"Command execution denied: {params['command']}, Reason: {reason}")
                            return json.dumps({"status": "error", "message": f"Security policy拒绝: {reason}"}, ensure_ascii=False)

                # 检查资源使用
                allowed, reason = sandbox.check_resource("execution_time")
                if not allowed:
                    return json.dumps({"status": "error", "message": f"资源超限: {reason}"}, ensure_ascii=False)

            except ImportError:
                logger.warning("Sandbox security module not installed, skip security check")
            except Exception as e:
                logger.error(f"Sandbox security check failed: {e}")

            # 执行Tool
            try:
                result = await self.skills[tool_name].execute(action, params)
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

        return json.dumps({"status": "error", "message": f"Tool {tool_name} not found"}, ensure_ascii=False)


# 全局Skill manager实例 (避免重复Initialization) 
_skill_manager_instance: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """GetSkill manager单例"""
    global _skill_manager_instance
    if _skill_manager_instance is None:
        _skill_manager_instance = SkillManager()
        logger.info("Skill manager singleton created")
    return _skill_manager_instance