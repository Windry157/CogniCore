#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多Agent协作系统
实现Agent之间的协作机制
"""
from typing import Dict, List, Optional, Any, Tuple
from .multi_agent import AgentManager, DomainAgent

from src.core.memory.unified_memory import UnifiedMemorySystem
from src.core.logging.structured_logger import StructuredLogger

class AgentCollaborationSystem:
    """多Agent协作系统"""
    
    def __init__(self, memory_system: UnifiedMemorySystem):
        """
        Initialization多Agent协作系统
        
        Args:
            memory_system: 统一 memories系统
        """
        self.memory_system = memory_system
        self.agent_manager = AgentManager(memory_system)
        self.logger = StructuredLogger(name="agent_collaboration")
        self.collaboration_history = []
    
    async def collaborate_on_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        多 Agent协作 completeTask
        
        Args:
            task: TaskDescription
            context: 上下文信息
            
        Returns:
            Collaboration result
        """
        self.logger.info(f"Starting collaborative task processing: {task}")
        
        # 1. Task分析和分解
        task_analysis = self._analyze_task(task, context)
        
        # 2. Task分配
        assigned_tasks = self._assign_tasks(task_analysis)
        
        # 3. 执行子Task
        execution_results = await self._execute_subtasks(assigned_tasks)
        
        # 4. 整合
        final_result = self._integrate_results(execution_results, task)
        
        # 5. Recording collaboration history
        self._record_collaboration_history(task, assigned_tasks, execution_results, final_result)
        
        return final_result
    
    def _analyze_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyzing task并分解为子Task
        
        Args:
            task: TaskDescription
            context: 上下文信息
            
        Returns:
            Task分析
        """
        self.logger.info(f"Analyzing task: {task}")
        
        # 简单的Task分析逻辑
        subtasks = []
        task_lower = task.lower()
        
        # 基于关键词识别需要的Agent和子Task
        if any(keyword in task_lower for keyword in ["代码", "编程", "debug"]):
            subtasks.append({
                "description": "分析代码需求",
                "agent_type": "code_agent",
                "priority": "high"
            })
            subtasks.append({
                "description": "编写代码",
                "agent_type": "code_agent",
                "priority": "high"
            })
        
        if any(keyword in task_lower for keyword in ["文件", "目录"]):
            subtasks.append({
                "description": "Processing文件操作",
                "agent_type": "file_agent",
                "priority": "medium"
            })
        
        if any(keyword in task_lower for keyword in ["网络", "Connect"]):
            subtasks.append({
                "description": "网络诊断",
                "agent_type": "network_agent",
                "priority": "medium"
            })
        
        if any(keyword in task_lower for keyword in ["系统", "进程"]):
            subtasks.append({
                "description": "GetSystem Info",
                "agent_type": "system_agent",
                "priority": "medium"
            })
        
        if any(keyword in task_lower for keyword in ["安全", "监控"]):
            subtasks.append({
                "description": "安全分析",
                "agent_type": "security_agent",
                "priority": "medium"
            })
        
        # 如果没有Identified特定Agent, Add系统Agent作为默认
        if not subtasks:
            subtasks.append({
                "description": "Processing通用Task",
                "agent_type": "system_agent",
                "priority": "medium"
            })
        
        return {
            "original_task": task,
            "context": context,
            "subtasks": subtasks,
            "estimated_complexity": len(subtasks)
        }
    
    def _assign_tasks(self, task_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Assigning subtask给合适的Agent
        
        Args:
            task_analysis: Task分析
            
        Returns:
            分配的子Task列表
        """
        assigned_tasks = []
        
        for subtask in task_analysis["subtasks"]:
            agent = self.agent_manager.get_agent(subtask["agent_type"])
            if agent:
                assigned_tasks.append({
                    "id": f"subtask_{len(assigned_tasks) + 1}",
                    "description": subtask["description"],
                    "agent_name": agent.name,
                    "agent_type": subtask["agent_type"],
                    "priority": subtask["priority"],
                    "status": "pending"
                })
                self.logger.info(f"Assigning subtask '{subtask['description']}' to agent: {agent.name}")
            else:
                self.logger.warning(f"Agent not found: {subtask['agent_type']}")
        
        return assigned_tasks
    
    async def _execute_subtasks(self, assigned_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行子Task
        
        Args:
            assigned_tasks: 分配的子Task列表
            
        Returns:
            执行列表
        """
        execution_results = []
        
        for subtask in assigned_tasks:
            agent = self.agent_manager.get_agent(subtask["agent_name"])
            if agent:
                try:
                    self.logger.info(f"Agent {agent.name} starting subtask: {subtask['description']}")
                    result = agent.process_task(subtask["description"])
                    subtask["status"] = "completed"
                    subtask["result"] = result
                    execution_results.append(subtask)
                    self.logger.info(f"Agent {agent.name} completed subtask: {subtask['description']}")
                except Exception as e:
                    self.logger.error(f"Agent {agent.name} subtask execution failed: {e}")
                    subtask["status"] = "failed"
                    subtask["error"] = str(e)
                    execution_results.append(subtask)
            else:
                self.logger.error(f"Agent not found: {subtask['agent_name']}")
                subtask["status"] = "failed"
                subtask["error"] = f"Agentdoes not exist: {subtask['agent_name']}"
                execution_results.append(subtask)
        
        return execution_results
    
    def _integrate_results(self, execution_results: List[Dict[str, Any]], original_task: str) -> Dict[str, Any]:
        """
        Integrating execution results
        
        Args:
            execution_results: 执行列表
            original_task: 原始Task
            
        Returns:
            整合后的
        """
        self.logger.info("Integrating execution results")
        
        # 收集 successful的
        successful_results = [r for r in execution_results if r["status"] == "completed"]
        failed_results = [r for r in execution_results if r["status"] == "failed"]
        
        # 构建整合
        integrated_result = {
            "status": "success" if len(failed_results) == 0 else "partial_success",
            "original_task": original_task,
            "total_subtasks": len(execution_results),
            "completed_subtasks": len(successful_results),
            "failed_subtasks": len(failed_results),
            "results": []
        }
        
        # 整合每 Agent的
        agent_results = {}
        for result in successful_results:
            agent_name = result["agent_name"]
            if agent_name not in agent_results:
                agent_results[agent_name] = []
            agent_results[agent_name].append(result)
        
        # 生成综合Response
        response_parts = []
        for agent_name, results in agent_results.items():
            agent = self.agent_manager.get_agent(agent_name)
            if agent:
                response_parts.append(f"\n[{agent.description}]")
                for result in results:
                    if "result" in result and "response" in result["result"]:
                        response_parts.append(f"- {result['result']['response']}")
        
        integrated_result["response"] = "\n".join(response_parts)
        integrated_result["details"] = execution_results
        
        if failed_results:
            error_messages = [f"{r['agent_name']}: {r.get('error', '未知Error')}" for r in failed_results]
            integrated_result["error_message"] = "；".join(error_messages)
        
        return integrated_result
    
    def _record_collaboration_history(self, task: str, assigned_tasks: List[Dict[str, Any]], 
                                   execution_results: List[Dict[str, Any]], 
                                   final_result: Dict[str, Any]):
        """
        Recording collaboration history
        
        Args:
            task: 原始Task
            assigned_tasks: 分配的子Task
            execution_results: 执行
            final_result: 最终
        """
        collaboration_record = {
            "timestamp": self.logger.get_timestamp(),
            "task": task,
            "assigned_tasks": assigned_tasks,
            "execution_results": execution_results,
            "final_result": final_result
        }
        
        self.collaboration_history.append(collaboration_record)
        
        # 限制历史记录大小
        if len(self.collaboration_history) > 100:
            self.collaboration_history = self.collaboration_history[-100:]
        
        self.logger.info(f"Recording collaboration history: Task '{task}' processing complete")
    
    def get_collaboration_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        GetCollaboration history
        
        Args:
            limit: 返回的历史记录数量
            
        Returns:
            Collaboration history记录
        """
        return self.collaboration_history[-limit:]
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """
        GetAgent statistics
        
        Returns:
            Agent statistics
        """
        return self.agent_manager.get_agent_statistics()
    
    def add_custom_agent(self, agent: DomainAgent):
        """
        Adding custom agent
        
        Args:
            agent: Agent实例
        """
        self.agent_manager.add_custom_agent(agent)
    
    def remove_agent(self, agent_name: str):
        """
        Removing agent
        
        Args:
            agent_name: AgentName
        """
        self.agent_manager.remove_agent(agent_name)

if __name__ == "__main__":
    """Test多Agent协作系统"""
    import asyncio
    
    async def test_collaboration():
        # Initialization memories系统
        memory_system = UnifiedMemorySystem(memory_dir="test_collaboration")
        
        # Initialization协作系统
        collaboration_system = AgentCollaborationSystem(memory_system)
        
        # Test复杂Task
        test_tasks = [
            "编写一 Python函数来计算斐波那契数列并Save to file",
            "检查网络ConnectStatus并GetSystem Info",
            "分析系统安全Status并提供建议"
        ]
        
        for task in test_tasks:
            print(f"\n=== Test task: {task} ===")
            result = await collaboration_system.collaborate_on_task(task)
            print(f"Collaboration result: {result['status']}")
            print(f"Response: {result['response']}")
        
        # TestCollaboration history
        print("\n=== Collaboration history ===")
        history = collaboration_system.get_collaboration_history()
        for record in history:
            print(f"Task: {record['task']}")
            print(f"Status: {record['final_result']['status']}")
        
        # TestAgent statistics
        print("\n=== Agent statistics ===")
        stats = collaboration_system.get_agent_statistics()
        print(stats)
    
    asyncio.run(test_collaboration())
