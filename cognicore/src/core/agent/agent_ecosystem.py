#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent生态系统 module
构建完整的Agent生态系统, 包括Register, 发现, 管理和监控
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import threading
from src.core.agent.multi_agent import AgentManager, DomainAgent
from src.core.agent.agent_coordinator import AgentCoordinator
from src.core.logging.structured_logger import StructuredLogger


class AgentRegistry:
    """AgentRegistry"""
    
    def __init__(self):
        """Initializing agentRegistry"""
        self.agents = {}
        self.capabilities = {}
        self.lock = threading.RLock()
    
    def register_agent(self, agent: DomainAgent):
        """
        RegisterAgent
        
        参数:
            agent: Agent实例
        """
        with self.lock:
            self.agents[agent.name] = agent
            # RegisterAgent capabilities
            for capability in agent.get_capabilities():
                if capability not in self.capabilities:
                    self.capabilities[capability] = []
                if agent.name not in self.capabilities[capability]:
                    self.capabilities[capability].append(agent.name)
    
    def unregister_agent(self, agent_name: str):
        """
        Register销Agent
        
        参数:
            agent_name: AgentName
        """
        with self.lock:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                # From能力映射中移除
                for capability in agent.get_capabilities():
                    if capability in self.capabilities and agent_name in self.capabilities[capability]:
                        self.capabilities[capability].remove(agent_name)
                del self.agents[agent_name]
    
    def get_agent(self, agent_name: str) -> Optional[DomainAgent]:
        """
        GetAgent
        
        参数:
            agent_name: AgentName
            
        返回:
            Agent实例
        """
        with self.lock:
            return self.agents.get(agent_name)
    
    def get_all_agents(self) -> Dict[str, DomainAgent]:
        """
        Get所有Agent
        
        返回:
            Agent字典
        """
        with self.lock:
            return self.agents.copy()
    
    def get_agents_by_capability(self, capability: str) -> List[str]:
        """
        根据能力GetAgent
        
        参数:
            capability: 能力Name
            
        返回:
            AgentName列表
        """
        with self.lock:
            return self.capabilities.get(capability, [])
    
    def get_all_capabilities(self) -> List[str]:
        """
        Get所有能力
        
        返回:
            能力列表
        """
        with self.lock:
            return list(self.capabilities.keys())


class AgentMonitor:
    """Agent监控器"""
    
    def __init__(self):
        """Initializing agent监控器"""
        self.metrics = {}
        self.lock = threading.RLock()
    
    def record_metric(self, agent_name: str, metric_name: str, value: float):
        """
        记录指标
        
        参数:
            agent_name: AgentName
            metric_name: 指标Name
            value: 指标值
        """
        with self.lock:
            if agent_name not in self.metrics:
                self.metrics[agent_name] = {}
            if metric_name not in self.metrics[agent_name]:
                self.metrics[agent_name][metric_name] = []
            self.metrics[agent_name][metric_name].append((time.time(), value))
    
    def get_metrics(self, agent_name: str) -> Dict[str, List[Tuple[float, float]]]:
        """
        GetAgent指标
        
        参数:
            agent_name: AgentName
            
        返回:
            指标字典
        """
        with self.lock:
            return self.metrics.get(agent_name, {})
    
    def get_all_metrics(self) -> Dict[str, Dict[str, List[Tuple[float, float]]]]:
        """
        Get所有指标
        
        返回:
            所有指标
        """
        with self.lock:
            return self.metrics.copy()
    
    def clear_metrics(self, agent_name: str = None):
        """
        清理指标
        
        参数:
            agent_name: AgentName, None表示清理所有
        """
        with self.lock:
            if agent_name:
                if agent_name in self.metrics:
                    del self.metrics[agent_name]
            else:
                self.metrics.clear()


class AgentEcosystem:
    """Agent生态系统"""
    
    def __init__(self, agent_manager: AgentManager):
        """
        Initializing agent生态系统
        
        参数:
            agent_manager: Agent管理器
        """
        self.agent_manager = agent_manager
        self.registry = AgentRegistry()
        self.monitor = AgentMonitor()
        self.coordinator = AgentCoordinator(agent_manager)
        self.logger = StructuredLogger(name="agent_ecosystem")
        self._initialize_registry()
    
    def _initialize_registry(self):
        """
        InitializationRegistry
        """
        # Register所有Agent
        for agent_name, agent in self.agent_manager.get_all_agents().items():
            self.registry.register_agent(agent)
            self.logger.info(f"Registering agent to ecosystem: {agent_name}")
    
    def register_agent(self, agent: DomainAgent):
        """
        Registering agent to ecosystem
        
        参数:
            agent: Agent实例
        """
        self.registry.register_agent(agent)
        self.agent_manager.add_custom_agent(agent)
        self.logger.info(f"Agent {agent.name} registered to ecosystem")
    
    def unregister_agent(self, agent_name: str):
        """
        From生态系统中Register销Agent
        
        参数:
            agent_name: AgentName
        """
        self.registry.unregister_agent(agent_name)
        self.agent_manager.remove_agent(agent_name)
        self.logger.info(f"Agent {agent_name} unregistered from ecosystem")
    
    def get_agent(self, agent_name: str) -> Optional[DomainAgent]:
        """
        GetAgent
        
        参数:
            agent_name: AgentName
            
        返回:
            Agent实例
        """
        return self.registry.get_agent(agent_name)
    
    def get_all_agents(self) -> Dict[str, DomainAgent]:
        """
        Get所有Agent
        
        返回:
            Agent字典
        """
        return self.registry.get_all_agents()
    
    def get_agents_by_capability(self, capability: str) -> List[str]:
        """
        根据能力GetAgent
        
        参数:
            capability: 能力Name
            
        返回:
            AgentName列表
        """
        return self.registry.get_agents_by_capability(capability)
    
    def get_all_capabilities(self) -> List[str]:
        """
        Get所有能力
        
        返回:
            能力列表
        """
        return self.registry.get_all_capabilities()
    
    def execute_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        executing task
        
        参数:
            task_description: TaskDescription
            context: 上下文信息
            
        返回:
            执行
        """
        start_time = time.time()
        
        # 使用协调器executing task
        result = self.coordinator.coordinate_complex_task(task_description, context)
        
        execution_time = time.time() - start_time
        
        # 记录执行时间
        self.monitor.record_metric("coordinator", "execution_time", execution_time)
        
        self.logger.info(f"Task execution complete: {task_description}, Time taken: {execution_time:.2f}s")
        
        return result
    
    def get_ecosystem_status(self) -> Dict[str, Any]:
        """
        GetEcosystem status
        
        返回:
            Ecosystem status
        """
        agents = self.get_all_agents()
        agent_status = {}
        
        for agent_name, agent in agents.items():
            agent_status[agent_name] = {
                "description": agent.description,
                "capabilities": agent.get_capabilities(),
                "metrics": self.monitor.get_metrics(agent_name)
            }
        
        return {
            "total_agents": len(agents),
            "agents": agent_status,
            "capabilities": self.get_all_capabilities(),
            "coordination_stats": self.coordinator.get_coordination_statistics(),
            "metrics": self.monitor.get_all_metrics()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        返回:
            健康Status
        """
        agents = self.get_all_agents()
        healthy_agents = []
        unhealthy_agents = []
        
        for agent_name, agent in agents.items():
            try:
                # 简单的健康检查
                test_result = agent.process_task("健康检查")
                if test_result.get("status") == "success":
                    healthy_agents.append(agent_name)
                else:
                    unhealthy_agents.append(agent_name)
            except Exception as e:
                self.logger.error(f"Agent {agent_name} health check failed: {e}")
                unhealthy_agents.append(agent_name)
        
        return {
            "status": "healthy" if not unhealthy_agents else "unhealthy",
            "healthy_agents": healthy_agents,
            "unhealthy_agents": unhealthy_agents,
            "total_agents": len(agents),
            "healthy_count": len(healthy_agents),
            "unhealthy_count": len(unhealthy_agents)
        }
    
    def optimize_ecosystem(self):
        """
        优化生态系统
        """
        self.logger.info("Starting ecosystem optimization")
        
        # 1. 清理无效Agent
        agents = self.get_all_agents()
        for agent_name, agent in agents.items():
            try:
                # TestAgent是否正常
                agent.process_task("Test")
            except Exception as e:
                self.logger.error(f"Agent {agent_name} exception: {e}")
                self.unregister_agent(agent_name)
        
        # 2. 优化Task分配策略
        # 这里可以Add更复杂的优化逻辑
        
        self.logger.info("Ecosystem optimization complete")
    
    def shutdown(self):
        """
        Close生态系统
        """
        self.logger.info("Closing agent ecosystem")
        
        # 清理资源
        agents = list(self.get_all_agents().keys())
        for agent_name in agents:
            self.unregister_agent(agent_name)
        
        # 清理监控数据
        self.monitor.clear_metrics()
        
        self.logger.info("Agent ecosystem closed")


if __name__ == "__main__":
    # TestAgent生态系统
    from src.core.memory.unified_memory import UnifiedMemorySystem
    
    # Initialization memories系统
    memory_system = UnifiedMemorySystem(memory_dir="test_ecosystem")
    
    # Initializing agent管理器
    agent_manager = AgentManager(memory_system)
    
    # Initialization生态系统
    ecosystem = AgentEcosystem(agent_manager)
    
    # Test task execution
    print("=== Test task execution ===")
    task = "Create一 新的Python项目, 包含代码文件和README文档"
    result = ecosystem.execute_task(task)
    print(f"Task execution result: {result}")
    
    # Test ecosystem status
    print("\n=== Test ecosystem status ===")
    status = ecosystem.get_ecosystem_status()
    print(f"Ecosystem status: {status}")
    
    # Test health check
    print("\n=== Test health check ===")
    health = ecosystem.health_check()
    print(f"Health check result: {health}")
    
    # Test ecosystem optimization
    print("\n=== Test ecosystem optimization ===")
    ecosystem.optimize_ecosystem()
    
    # Test ecosystem shutdown
    print("\n=== Test ecosystem shutdown ===")
    ecosystem.shutdown()
