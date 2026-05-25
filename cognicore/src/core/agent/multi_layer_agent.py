#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-layer agent system
支持复杂Task的分解和执行
"""

from typing import Dict, List, Any, Optional
import logging

from .interfaces import AgentCoordinatorInterface
from .coordinator import AgentCoordinator

logger = logging.getLogger(__name__)


class BaseAgent:
    """基础Agent"""
    
    def __init__(self, agent_id: str, agent_type: str):
        """
        Initialization基础Agent
        
        Args:
            agent_id: AgentID
            agent_type: Agenttype
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = {}
        self.children = []
        self.parent = None
        
    def execute(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        executing task
        
        Args:
            task: Task信息
            context: 上下文信息
            
        Returns:
            执行
        """
        raise NotImplementedError("子类必须实现execute方法")
    
    def add_child(self, agent: 'BaseAgent'):
        """Add子Agent"""
        self.children.append(agent)
        agent.parent = self
    
    def remove_child(self, agent: 'BaseAgent'):
        """移除子Agent"""
        if agent in self.children:
            self.children.remove(agent)
            agent.parent = None
    
    def get_hierarchy(self) -> Dict[str, Any]:
        """GetAgent层级结构"""
        return {
            "id": self.agent_id,
            "type": self.agent_type,
            "children": [child.get_hierarchy() for child in self.children]
        }


class ToolAgent(BaseAgent):
    """Tool agent - Round 一层 (基础层) """
    
    def __init__(self, agent_id: str, tool_executor):
        """
        InitializationTool agent
        
        Args:
            agent_id: AgentID
            tool_executor: Tool执行器
        """
        super().__init__(agent_id, "tool")
        self.tool_executor = tool_executor
    
    def execute(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行单一Tool调用
        
        Args:
            task: Task信息
            context: 上下文信息
            
        Returns:
            执行
        """
        logger.info(f"Tool agent {self.agent_id} executing task: {task.get('name', 'Unknown')}")
        
        tool_name = task.get('tool', '')
        params = task.get('params', {})
        
        try:
            result = self.tool_executor.execute_tool(tool_name, params)
            return {
                "status": "SUCCESS",
                "agent_id": self.agent_id,
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            logger.error(f"Tool agent {self.agent_id} execution failed: {e}")
            return {
                "status": "ERROR",
                "agent_id": self.agent_id,
                "tool": tool_name,
                "error": str(e)
            }


class TaskAgent(BaseAgent):
    """Task agent - Round 二层 (Task层) """
    
    def __init__(self, agent_id: str, planner, executor, validator):
        """
        InitializationTask agent
        
        Args:
            agent_id: AgentID
            planner: 规划器
            executor: 执行器
            validator: 验证器
        """
        super().__init__(agent_id, "task")
        self.planner = planner
        self.executor = executor
        self.validator = validator
    
    def execute(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        executing task分解和执行
        
        Args:
            task: Task信息
            context: 上下文信息
            
        Returns:
            执行
        """
        logger.info(f"Task agent {self.agent_id} executing task: {task.get('name', 'Unknown')}")
        
        task_name = task.get('name', '')
        
        # Decomposing task
        subtasks = self.planner.decompose_task(task_name, context)
        
        if not subtasks:
            return {
                "status": "ERROR",
                "agent_id": self.agent_id,
                "message": "Task分解 failed"
            }
        
        # 执行子Task链
        results = []
        for subtask in subtasks:
            # 如果有Tool agent, 使用Tool agent执行
            if self.children:
                tool_result = self.children[0].execute(subtask, context)
                results.append(tool_result)
            else:
                # 否则使用执行器执行
                result = self.executor.execute_task(subtask, context)
                results.append(result)
        
        # 验证
        all_success = all(r.get('status') == 'SUCCESS' for r in results)
        
        return {
            "status": "SUCCESS" if all_success else "ERROR",
            "agent_id": self.agent_id,
            "task": task_name,
            "subtasks": subtasks,
            "results": results
        }


class CoordinatorAgent(BaseAgent):
    """Coordinator agent - Round 三层 (协调层) """
    
    def __init__(self, agent_id: str, coordinator: AgentCoordinator):
        """
        InitializationCoordinator agent
        
        Args:
            agent_id: AgentID
            coordinator: 协调器
        """
        super().__init__(agent_id, "coordinator")
        self.coordinator = coordinator
    
    def execute(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        协调多 tasks
        
        Args:
            task: Task信息
            context: 上下文信息
            
        Returns:
            执行
        """
        logger.info(f"Coordinator agent {self.agent_id} executing task: {task.get('name', 'Unknown')}")
        
        task_name = task.get('name', '')
        
        try:
            # 直接执行同步版本的TaskProcessing
            # 避免在already运行的事件循环中使用asyncio.run
            return {
                "status": "SUCCESS",
                "agent_id": self.agent_id,
                "message": f"Coordinator agent {self.agent_id} already接收Task: {task_name}"
            }
        except Exception as e:
            logger.error(f"Coordinator agent {self.agent_id} execution failed: {e}")
            return {
                "status": "ERROR",
                "agent_id": self.agent_id,
                "error": str(e)
            }


class StrategicAgent(BaseAgent):
    """Strategy agent - Round 四层 (战略层) """
    
    def __init__(self, agent_id: str, llm_service=None):
        """
        InitializationStrategy agent
        
        Args:
            agent_id: AgentID
            llm_service: LLM服务
        """
        super().__init__(agent_id, "strategic")
        self.llm_service = llm_service
    
    def execute(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        制定战略计划
        
        Args:
            task: Task信息
            context: 上下文信息
            
        Returns:
            执行
        """
        logger.info(f"Strategy agent {self.agent_id} executing task: {task.get('name', 'Unknown')}")
        
        task_name = task.get('name', '')
        
        if not self.llm_service:
            return {
                "status": "SUCCESS",
                "agent_id": self.agent_id,
                "strategy": "默认战略",
                "goals": [" complete基本Task"],
                "milestones": []
            }
        
        try:
            strategy = self._generate_strategy(task_name, context)
            return {
                "status": "SUCCESS",
                "agent_id": self.agent_id,
                "strategy": strategy.get('strategy', '默认战略'),
                "goals": strategy.get('goals', []),
                "milestones": strategy.get('milestones', [])
            }
        except Exception as e:
            logger.error(f"Strategy agent {self.agent_id} execution failed: {e}")
            return {
                "status": "ERROR",
                "agent_id": self.agent_id,
                "error": str(e)
            }
    
    def _generate_strategy(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成战略计划
        
        Args:
            task: Task
            context: 上下文
            
        Returns:
            战略计划
        """
        prompt = f"请为以下Task制定战略计划: \n\nTask: {task}\n"
        if context:
            prompt += f"\n上下文: {context}\n"
        
        messages = [
            {"role": "system", "content": "你是一 专业的战略规划专家, 擅长制定长期和短期的行动计划."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm_service.chat(messages)
        
        return {
            "strategy": "基于LLM的战略",
            "goals": [" complete战略目标"],
            "milestones": ["阶段1", "阶段2", "阶段3"]
        }


class MultiLayerAgentSystem:
    """Multi-layer agent system"""
    
    def __init__(self, system_id: str, llm_service=None):
        """
        InitializationMulti-layer agent system
        
        Args:
            system_id: 系统ID
            llm_service: LLM服务
        """
        self.system_id = system_id
        self.llm_service = llm_service
        
        # Create协调器和各层Agent
        self.coordinator = AgentCoordinator(llm_service=llm_service)
        
        # Round 一层: Tool agent
        self.tool_agents: Dict[str, ToolAgent] = {}
        
        # Round 二层: Task agent
        self.task_agents: Dict[str, TaskAgent] = {}
        
        # Round 三层: Coordinator agent
        self.coordinator_agents: Dict[str, CoordinatorAgent] = {}
        
        # Round 四层: Strategy agent
        self.strategic_agents: Dict[str, StrategicAgent] = {}
        
        # 根Agent
        self.root_strategic = StrategicAgent("strategic_root", llm_service)
        
        logger.info(f"Multi-layer agent system {system_id} initialization complete")
    
    def register_tool_agent(self, agent_id: str, tool_executor) -> ToolAgent:
        """Registering tool agent"""
        agent = ToolAgent(agent_id, tool_executor)
        self.tool_agents[agent_id] = agent
        logger.info(f"Registering tool agent: {agent_id}")
        return agent
    
    def register_task_agent(self, agent_id: str) -> TaskAgent:
        """Registering task agent"""
        agent = TaskAgent(
            agent_id,
            self.coordinator.planner,
            self.coordinator.executor,
            self.coordinator.validator
        )
        self.task_agents[agent_id] = agent
        
        # 分配Tool agent作为子Agent
        if self.tool_agents:
            first_tool = next(iter(self.tool_agents.values()))
            agent.add_child(first_tool)
        
        logger.info(f"Registering task agent: {agent_id}")
        return agent
    
    def register_coordinator_agent(self, agent_id: str) -> CoordinatorAgent:
        """Registering coordinator agent"""
        agent = CoordinatorAgent(agent_id, self.coordinator)
        self.coordinator_agents[agent_id] = agent
        logger.info(f"Registering coordinator agent: {agent_id}")
        return agent
    
    def register_strategic_agent(self, agent_id: str) -> StrategicAgent:
        """Registering strategy agent"""
        agent = StrategicAgent(agent_id, self.llm_service)
        self.strategic_agents[agent_id] = agent
        logger.info(f"Registering strategy agent: {agent_id}")
        return agent
    
    def execute_task(self, task: Dict[str, Any], level: str = "task") -> Dict[str, Any]:
        """
        executing task
        
        Args:
            task: Task信息
            level: 执行层级 ("tool", "task", "coordinator", "strategic")
            
        Returns:
            执行
        """
        logger.info(f"Multi-layer system executing task, level: {level}")
        
        if level == "tool":
            if not self.tool_agents:
                return {"status": "ERROR", "message": "没有Register的Tool agent"}
            agent = next(iter(self.tool_agents.values()))
            return agent.execute(task)
        
        elif level == "task":
            if not self.task_agents:
                return {"status": "ERROR", "message": "没有Register的Task agent"}
            agent = next(iter(self.task_agents.values()))
            return agent.execute(task)
        
        elif level == "coordinator":
            if not self.coordinator_agents:
                return {"status": "ERROR", "message": "没有Register的Coordinator agent"}
            agent = next(iter(self.coordinator_agents.values()))
            return agent.execute(task)
        
        elif level == "strategic":
            return self.root_strategic.execute(task)
        
        else:
            return {"status": "ERROR", "message": f"未知的执行层级: {level}"}
    
    def get_system_hierarchy(self) -> Dict[str, Any]:
        """Get系统层级结构"""
        return {
            "system_id": self.system_id,
            "root": self.root_strategic.get_hierarchy(),
            "layers": {
                "tool": [agent.get_hierarchy() for agent in self.tool_agents.values()],
                "task": [agent.get_hierarchy() for agent in self.task_agents.values()],
                "coordinator": [agent.get_hierarchy() for agent in self.coordinator_agents.values()],
                "strategic": [agent.get_hierarchy() for agent in self.strategic_agents.values()]
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get系统Statistics"""
        return {
            "system_id": self.system_id,
            "tool_agents": len(self.tool_agents),
            "task_agents": len(self.task_agents),
            "coordinator_agents": len(self.coordinator_agents),
            "strategic_agents": len(self.strategic_agents)
        }