#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent编排 module
用于实现多Agent协同工作
"""

import logging
from typing import Dict, Any, List, Optional
import asyncio

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from src.core.llm import LLMFactory
from src.core.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class SpecializedAgent:
    """
    专业Agent类
    代表一 具有特定角色和Tool的Agent
    """
    
    def __init__(self, name: str, role: str, tools: List[Dict[str, Any]]):
        """
        Initialization专业Agent
        
        Args:
            name: AgentName
            role: Agent角色Description
            tools: Agent可以使用的Tool列表
        """
        self.name = name
        self.role = role
        self.tools = tools
        self.llm = LLMFactory.create_service("ollama")
        self.agent_executor = None
        
        logger.info(f"Creating specialist agent: {name} - {role}")
    
    def create_agent(self):
        """
        CreateAgent
        
        Returns:
            Agent实例
        """
        if not self.agent_executor:
            # Create提示模板
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"你是{self.role}, 专Register于{self.name}领域的Task.请根据用户的需求, 使用可用的Tool来 completeTask."),
                ("user", "{input}"),
                ("assistant", "{agent_scratchpad}")
            ])
            
            # CreateAgent
            self.agent_executor = create_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
        
        return self.agent_executor
    
    async def run(self, task: str) -> Dict[str, Any]:
        """
        运行Agentexecuting task
        
        Args:
            task: TaskDescription
            
        Returns:
            执行
        """
        try:
            agent = self.create_agent()
            # 直接使用LLMProcessingTask
            result = self.llm.generate(f"Task: {task}\n\n请根据你的角色{self.role}来 complete这 tasks.")
            return {
                "status": "SUCCESS",
                "agent": self.name,
                "result": {"output": result}
            }
        except Exception as e:
            logger.error(f"Agent {self.name}task execution failed: {e}")
            return {
                "status": "ERROR",
                "agent": self.name,
                "message": str(e)
            }


class AgentOrchestrator:
    """
    Agent编排器
    用于管理和协调多 Agent协同工作
    """
    
    def __init__(self):
        """
        InitializationAgent编排器
        """
        self.agents: Dict[str, SpecializedAgent] = {}
        self.strategic_agent: Optional[SpecializedAgent] = None
        self.llm = LLMFactory.create_service("ollama")
        
        logger.info("Agent orchestrator initialized")
    
    def register_agent(self, agent: SpecializedAgent):
        """
        Register专业Agent
        
        Args:
            agent: 专业Agent实例
        """
        self.agents[agent.name] = agent
        logger.info(f"Register Agent: {agent.name}")
    
    def set_strategic_agent(self, agent: SpecializedAgent):
        """
        Setting strategy agent
        
        Args:
            agent: 战略Agent实例
        """
        self.strategic_agent = agent
        logger.info(f"Setting strategy agent: {agent.name}")
    
    async def process_task(self, task: str) -> Dict[str, Any]:
        """
        Processing复杂Task
        
        Args:
            task: TaskDescription
            
        Returns:
            Processing result
        """
        try:
            # 战略AgentAnalyzing task并制定计划
            plan = await self._analyze_task(task)
            
            # 执行计划
            results = await self._execute_plan(plan)
            
            # 整合
            final_result = await self._integrate_results(results, task)
            
            return {
                "status": "SUCCESS",
                "plan": plan,
                "results": results,
                "final_result": final_result
            }
        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return {
                "status": "ERROR",
                "message": str(e)
            }
    
    async def _analyze_task(self, task: str) -> Dict[str, Any]:
        """
        Analyzing task并制定计划
        
        Args:
            task: TaskDescription
            
        Returns:
            Task计划
        """
        if self.strategic_agent:
            # 使用战略AgentAnalyzing task
            result = await self.strategic_agent.run(f"分析以下Task并制定执行计划: {task}")
            if result["status"] == "SUCCESS":
                # 解析计划
                plan = self._parse_plan(result["result"].get("output", ""))
                return plan
        
        # Falling back to 默认计划
        return self._default_plan(task)
    
    def _parse_plan(self, plan_text: str) -> Dict[str, Any]:
        """
        解析计划文本
        
        Args:
            plan_text: 计划文本
            
        Returns:
            解析后的计划
        """
        # 简单的计划解析逻辑
        # 实际项目中可以使用更复杂的解析方法
        steps = []
        for i, line in enumerate(plan_text.split("\n")):
            line = line.strip()
            if line and (line.startswith("Step") or line.startswith("Step")):
                steps.append({
                    "id": f"step_{i}",
                    "description": line,
                    "agent": self._select_agent_for_task(line)
                })
        
        return {
            "task": plan_text,
            "steps": steps
        }
    
    def _default_plan(self, task: str) -> Dict[str, Any]:
        """
        默认计划
        
        Args:
            task: TaskDescription
            
        Returns:
            默认计划
        """
        # 根据Tasktype选择合适的Agent
        agent_name = self._select_agent_for_task(task)
        
        return {
            "task": task,
            "steps": [{
                "id": "step_1",
                "description": f"executing task: {task}",
                "agent": agent_name
            }]
        }
    
    def _select_agent_for_task(self, task: str) -> str:
        """
        根据Task选择合适的Agent
        
        Args:
            task: TaskDescription
            
        Returns:
            AgentName
        """
        # 简单的Agent选择逻辑
        # 实际项目中可以使用更复杂的选择方法
        task_lower = task.lower()
        
        if "weather" in task_lower or "天气" in task_lower:
            return "weather_agent"
        elif "search" in task_lower or "Search" in task_lower:
            return "search_agent"
        elif "data" in task_lower or "数据" in task_lower:
            return "data_agent"
        else:
            # 默认使用通用Agent
            return "general_agent"
    
    async def _execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行计划
        
        Args:
            plan: Task计划
            
        Returns:
            执行
        """
        results = {}
        
        for step in plan.get("steps", []):
            agent_name = step.get("agent")
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                result = await agent.run(step.get("description"))
                results[step.get("id")] = result
            else:
                logger.warning(f"Agent {agent_name}does not exist")
                results[step.get("id")] = {
                    "status": "ERROR",
                    "message": f"Agent {agent_name}does not exist"
                }
        
        return results
    
    async def _integrate_results(self, results: Dict[str, Any], task: str) -> str:
        """
        整合
        
        Args:
            results: 执行
            task: 原始Task
            
        Returns:
            整合后的
        """
        # 构建摘要
        summary = f"Task: {task}\n\n执行:\n"
        
        for step_id, result in results.items():
            if result["status"] == "SUCCESS":
                output = result.get("result", {}).get("output", "")
                summary += f"Step {step_id}:  successful\n{output}\n\n"
            else:
                summary += f"Step {step_id}:  failed\n{result.get('message', '未知Error')}\n\n"
        
        # 使用LLM生成最终Answer
        prompt = f"基于以下执行, 总结Task的 complete情况: \n\n{summary}\n请提供一 清晰, 全面的总结."
        final_answer = self.llm.generate(prompt)
        
        return final_answer


# 全局Agent编排器实例
agent_orchestrator = None


def get_agent_orchestrator() -> AgentOrchestrator:
    """
    GetAgent编排器实例
    
    Returns:
        AgentOrchestrator实例
    """
    global agent_orchestrator
    if agent_orchestrator is None:
        agent_orchestrator = AgentOrchestrator()
    return agent_orchestrator


def reset_agent_orchestrator():
    """
    重置Agent编排器
    """
    global agent_orchestrator
    agent_orchestrator = None
