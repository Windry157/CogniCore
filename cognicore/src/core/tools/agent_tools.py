#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentTool module
实现Agent之间的Task委派功能
"""

import json
from typing import Dict, Any
from src.core.tools.registry import register_tool
from src.core.agent.profiles import get_agent_profile
from src.core.agent.agent import IntelligentAgent
from src.core.skill_manager import SkillManager
from src.core.memory.unified_memory import UnifiedMemorySystem
from src.core.mock_services import MockLLM

# 全局Agent实例cache
_agent_instances = {}


def _initialize_llm():
    """
    InitializationLLM实例
    
    返回:
        LLM实例
    """
    # 使用与assistant.py相同的方式InitializationLLM
    llm_config = {"provider": "mock"}
    return MockLLM(llm_config)


def _get_or_create_agent(agent_name: str) -> IntelligentAgent:
    """
    Get或CreateAgent实例
    
    参数:
        agent_name: AgentName
        
    返回:
        Agent实例
    """
    if agent_name not in _agent_instances:
        # GetAgent配置
        profile = get_agent_profile(agent_name)
        if not profile:
            raise ValueError(f"Agent {agent_name} does not exist")
        
        # CreateAgent实例
        skill_manager = SkillManager()
        memory_system = UnifiedMemorySystem()
        llm = _initialize_llm()
        
        # 过滤Tool, 只保留Agent允许使用的Tool
        allowed_tools = profile.tools
        # 这里需要实现Tool过滤逻辑
        # 暂时使用所有Tool
        
        # CreateAgent
        agent = IntelligentAgent(
            llm=llm,
            skill_manager=skill_manager,
            memory_system=memory_system,
            profile=profile
        )
        
        _agent_instances[agent_name] = agent
    
    return _agent_instances[agent_name]


@register_tool(name="delegate_task")
async def delegate_task(agent_name: str, task_description: str) -> str:
    """
    将Task委派给特定的专家Agent.
    
    Args:
        agent_name: 目标AgentName (例如 'Researcher')
        task_description: 具体需要 complete的TaskDescription
        
    Returns:
        子Agent的执行
    """
    try:
        # Get或CreateAgent实例
        agent = _get_or_create_agent(agent_name)
        
        # executing task
        import asyncio
        result = await agent.run(task_description)
        
        # Processing执行
        if result.get("status") == "success":
            execution_result = result.get("execution_result", {})
            return json.dumps({
                "status": "success",
                "agent": agent_name,
                "task": task_description,
                "message": f"{agent_name} already completeTask",
                "result": execution_result
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "agent": agent_name,
                "task": task_description,
                "message": f"{agent_name} task execution failed: {result.get('message', '未知Error')}"
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
