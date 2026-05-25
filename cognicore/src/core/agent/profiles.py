#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent配置 module
用于定义和管理不同type的Agent
"""

import logging
from typing import Dict, Any, List

from src.core.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class AgentProfile:
    """
    Agent配置类
    定义Agent的角色, Description和Tool
    """
    
    def __init__(self, name: str, role: str, description: str, tools: List[str]):
        """
        InitializationAgent配置
        
        Args:
            name: AgentName
            role: Agent角色
            description: AgentDescription
            tools: Agent可以使用的Tool列表
        """
        self.name = name
        self.role = role
        self.description = description
        self.tools = tools
        self.system_prompt = self._generate_system_prompt()
    
    def _generate_system_prompt(self) -> str:
        """
        生成系统提示词
        
        Returns:
            系统提示词
        """
        prompt = f"你是{self.role}, {self.description}\n"
        prompt += f"你的名字是{self.name}, 专Register于{self.role}的Task.\n"
        prompt += "请根据用户的需求, 使用可用的Tool来 completeTask.\n"
        prompt += "如果遇到问题, 请尝试使用不同的Tool或方法来解决.\n"
        prompt += "请提供清晰, 详细的Answer."
        return prompt
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get可用的Tool (支持 Skills 系统) 
        
        Returns:
            Tool列表
        """
        available_tools = []
        
        # 尝试From Skills 系统Gettool definition
        try:
            from src.core.skill_manager import SkillManager
            skill_manager = SkillManager()
            
            for tool_name in self.tools:
                if tool_name in skill_manager.skills:
                    skill = skill_manager.skills[tool_name]
                    available_tools.append({
                        "name": skill.name,
                        "description": skill.description,
                        "parameters": skill.parameters
                    })
                else:
                    logger.warning(f"Skill {tool_name} does not exist in SkillManager")
        except Exception as e:
            logger.error(f"Failed to get tool from SkillManager: {e}")
            # 降级到ToolRegistry
            for tool_name in self.tools:
                tool_info = tool_registry.get_tool(tool_name)
                if tool_info:
                    available_tools.append(tool_info)
                else:
                    logger.warning(f"Tool {tool_name} does not exist")
        
        return available_tools


# 预定义的Agent配置
# Update为使用 Skills 系统的ToolName
AGENT_PROFILES = {
    "general_agent": AgentProfile(
        name="通用助手",
        role="通用智能助手",
        description="一 全能的智能助手, 可以Processing各种type的Task",
        tools=["file_manager", "network_diagnostic", "system_info", "search", "translate"]
    ),
    "weather_agent": AgentProfile(
        name="天气助手",
        role="天气专家",
        description="专Register于提供天气相关的信息和建议",
        tools=["network_diagnostic", "search"]
    ),
    "search_agent": AgentProfile(
        name="Search助手",
        role="Search专家",
        description="专Register于在网络上Search信息并提供准确的答案",
        tools=["search", "network_diagnostic"]
    ),
    "data_agent": AgentProfile(
        name="数据助手",
        role="数据分析专家",
        description="专Register于数据分析和ProcessingTask",
        tools=["data_analyze", "file_manager", "code_executor"]
    ),
    "strategic_agent": AgentProfile(
        name="战略助手",
        role="战略规划专家",
        description="专Register于Analyzing task并制定执行计划",
        tools=["system_info", "process_manager", "search"]
    ),
    "developer_agent": AgentProfile(
        name="开发助手",
        role="代码开发专家",
        description="专Register于代码编写, 调试和执行",
        tools=["code_executor", "file_manager", "search"]
    ),
    "security_agent": AgentProfile(
        name="安全助手",
        role="安全监控专家",
        description="专Register于系统安全监控和诊断",
        tools=["security_monitor", "network_diagnostic", "system_info"]
    ),
    "creative_agent": AgentProfile(
        name="创意助手",
        role="创意创作专家",
        description="专Register于绘图和创意Content生成",
        tools=["draw", "translate"]
    ),
    "all_in_one_agent": AgentProfile(
        name="全能助手",
        role="全能智能助手",
        description="一 拥有所有Tool的全能助手, 可以 complete任何type的Task",
        tools=[
            "process_manager", "file_manager", "system_info", "code_executor",
            "network_diagnostic", "security_monitor", "search", "draw",
            "translate", "data_analyze", "system_control"
        ]
    )
}


def get_agent_profile(name: str) -> AgentProfile:
    """
    GetAgent配置
    
    Args:
        name: AgentName
        
    Returns:
        AgentProfile实例
    """
    return AGENT_PROFILES.get(name)


def get_all_agent_profiles() -> Dict[str, AgentProfile]:
    """
    Get所有Agent配置
    
    Returns:
        Agent配置字典
    """
    return AGENT_PROFILES


def register_agent_profile(name: str, profile: AgentProfile):
    """
    Registering Agent config
    
    Args:
        name: AgentName
        profile: AgentProfile实例
    """
    AGENT_PROFILES[name] = profile
    logger.info(f"Registering Agent config: {name}")