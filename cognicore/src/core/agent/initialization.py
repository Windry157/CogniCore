#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentInitialization module
用于Initialization和管理不同type的Agent
"""

import logging
from typing import Dict, Any

from src.core.agent.orchestration import get_agent_orchestrator, SpecializedAgent
from src.core.agent.profiles import get_all_agent_profiles, get_agent_profile

logger = logging.getLogger(__name__)


def initialize_agents():
    """
    Initialization所有Agent
    """
    orchestrator = get_agent_orchestrator()
    
    # Get所有Agent配置
    profiles = get_all_agent_profiles()
    
    # Create并Register专业Agent
    for name, profile in profiles.items():
        # GetAgent可以使用的Tool
        tools = profile.get_available_tools()
        
        # Creating specialist agent
        agent = SpecializedAgent(
            name=name,
            role=profile.role,
            tools=tools
        )
        
        # Register Agent
        orchestrator.register_agent(agent)
    
    # Setting strategy agent
    strategic_profile = get_agent_profile("strategic_agent")
    if strategic_profile:
        strategic_tools = strategic_profile.get_available_tools()
        strategic_agent = SpecializedAgent(
            name="strategic_agent",
            role=strategic_profile.role,
            tools=strategic_tools
        )
        orchestrator.set_strategic_agent(strategic_agent)
    
    logger.info("Agent initialization complete")


def get_initialized_agents() -> Dict[str, SpecializedAgent]:
    """
    GetInitialization的Agent
    
    Returns:
        Agent字典
    """
    orchestrator = get_agent_orchestrator()
    return orchestrator.agents


def get_agent(name: str) -> SpecializedAgent:
    """
    Get指定Name的Agent
    
    Args:
        name: AgentName
        
    Returns:
        SpecializedAgent实例
    """
    orchestrator = get_agent_orchestrator()
    return orchestrator.agents.get(name)


def run_agent(name: str, task: str) -> Dict[str, Any]:
    """
    运行指定的Agentexecuting task
    
    Args:
        name: AgentName
        task: TaskDescription
        
    Returns:
        执行
    """
    agent = get_agent(name)
    if agent:
        return agent.run(task)
    else:
        logger.error(f"Agent {name}does not exist")
        return {
            "status": "ERROR",
            "message": f"Agent {name}does not exist"
        }
