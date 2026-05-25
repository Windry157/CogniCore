#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent协作管理器
实现Agent间的通信和协作机制
"""

from typing import Dict, List, Optional, Any, Tuple
from src.core.agent.multi_agent import AgentManager, DomainAgent
from src.core.logging.structured_logger import StructuredLogger


class Message:
    """Agent消息类"""
    
    def __init__(self, sender: str, recipient: str, content: str, message_type: str = "task", metadata: Dict[str, Any] = None):
        """
        Initialization消息
        
        参数:
            sender: 发送者
            recipient: 接收者
            content: 消息Content
            message_type: 消息type
            metadata: 元数据
        """
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.message_type = message_type
        self.metadata = metadata or {}
        self.timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        返回:
            消息字典
        """
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata
        }


class Task:
    """Task类"""
    
    def __init__(self, task_id: str, description: str, priority: str = "medium", metadata: Dict[str, Any] = None):
        """
        InitializationTask
        
        参数:
            task_id: TaskID
            description: TaskDescription
            priority: 优先级
            metadata: 元数据
        """
        self.task_id = task_id
        self.description = description
        self.priority = priority
        self.metadata = metadata or {}
        self.status = "pending"
        self.assigned_agent = None
        self.result = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        返回:
            Task字典
        """
        return {
            "task_id": self.task_id,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "assigned_agent": self.assigned_agent,
            "result": self.result,
            "metadata": self.metadata
        }


class AgentCoordinator:
    """Agent协作协调器"""
    
    def __init__(self, agent_manager: AgentManager):
        """
        Initialization协作协调器
        
        参数:
            agent_manager: Agent管理器
        """
        self.agent_manager = agent_manager
        self.logger = StructuredLogger(name="agent_coordinator")
        self.message_queue = []
        self.tasks = {}
        self.task_counter = 0
    
    def send_message(self, message: Message):
        """
        Send message
        
        参数:
            message: 消息对象
        """
        self.message_queue.append(message)
        self.logger.info(f"Send message: {message.sender} -> {message.recipient}: {message.content}")
    
    def process_messages(self):
        """
        Process message队列
        """
        while self.message_queue:
            message = self.message_queue.pop(0)
            self._process_message(message)
    
    def _process_message(self, message: Message):
        """
        Processing单 消息
        
        参数:
            message: 消息对象
        """
        agent = self.agent_manager.get_agent(message.recipient)
        if agent:
            if message.message_type == "task":
                # ProcessingTask消息
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                task = Task(
                    task_id=task_id,
                    description=message.content,
                    metadata=message.metadata
                )
                self.tasks[task_id] = task
                
                # 分配Task
                result = agent.process_task(message.content, message.metadata)
                task.status = "completed"
                task.result = result
                task.assigned_agent = message.recipient
                
                # 发送回给发送者
                if message.sender != "coordinator":
                    response = Message(
                        sender=message.recipient,
                        recipient=message.sender,
                        content=f"Task complete: {message.content}",
                        message_type="task_result",
                        metadata={"task_id": task_id, "result": result}
                    )
                    self.send_message(response)
            elif message.message_type == "task_result":
                # ProcessingTask
                self.logger.info(f"Task result received: {message.sender} -> {message.recipient}: {message.content}")
            elif message.message_type == "request":
                # Process request消息
                self.logger.info(f"Process request: {message.sender} -> {message.recipient}: {message.content}")
            else:
                # Processing其他type消息
                self.logger.info(f"Process message: {message.sender} -> {message.recipient}: {message.content}")
        else:
            self.logger.error(f"Recipient agent not found: {message.recipient}")
    
    def create_task(self, description: str, priority: str = "medium", metadata: Dict[str, Any] = None) -> str:
        """
        CreateTask
        
        参数:
            description: TaskDescription
            priority: 优先级
            metadata: 元数据
            
        返回:
            TaskID
        """
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1
        task = Task(
            task_id=task_id,
            description=description,
            priority=priority,
            metadata=metadata
        )
        self.tasks[task_id] = task
        return task_id
    
    def assign_task(self, task_id: str, agent_name: str) -> bool:
        """
        分配Task
        
        参数:
            task_id: TaskID
            agent_name: AgentName
            
        返回:
            是否分配 successful
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            agent = self.agent_manager.get_agent(agent_name)
            if agent:
                task.assigned_agent = agent_name
                task.status = "in_progress"
                
                # 发送Taskto agent
                message = Message(
                    sender="coordinator",
                    recipient=agent_name,
                    content=task.description,
                    message_type="task",
                    metadata=task.metadata
                )
                self.send_message(message)
                self.process_messages()
                
                # UpdateTask status
                if task.status != "completed":
                    # ProcessingTask
                    result = agent.process_task(task.description, task.metadata)
                    task.status = "completed"
                    task.result = result
                
                return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        GetTask status
        
        参数:
            task_id: TaskID
            
        返回:
            Task status
        """
        if task_id in self.tasks:
            return self.tasks[task_id].to_dict()
        return None
    
    def coordinate_complex_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Coordinating complex task
        
        参数:
            task_description: TaskDescription
            context: 上下文信息
            
        返回:
            Processing result
        """
        self.logger.info(f"Coordinating complex task: {task_description}")
        
        # Analyzing task, 分解为子Task
        subtasks = self._decompose_task(task_description, context)
        
        # Assigning subtask
        results = {}
        for subtask in subtasks:
            # 自动选择合适的Agent
            agent_name = self._select_agent_for_task(subtask["description"])
            if agent_name:
                task_id = self.create_task(
                    description=subtask["description"],
                    priority=subtask.get("priority", "medium"),
                    metadata=subtask.get("metadata", {})
                )
                self.assign_task(task_id, agent_name)
                task_status = self.get_task_status(task_id)
                results[subtask["id"]] = task_status
            else:
                self.logger.error(f"No suitable agent for subtask: {subtask['description']}")
                results[subtask["id"]] = {"status": "error", "message": "找不到合适的Agent"}
        
        # 整合
        final_result = self._integrate_results(results, task_description)
        
        return {
            "status": "success",
            "task": task_description,
            "subtasks": results,
            "result": final_result
        }
    
    def _decompose_task(self, task_description: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Decomposing task
        
        参数:
            task_description: TaskDescription
            context: 上下文信息
            
        返回:
            子Task列表
        """
        # 简单的Task分解逻辑
        # 实际应用中可以使用LLM进行更智能的分解
        subtasks = []
        
        if "代码" in task_description or "编程" in task_description:
            subtasks.append({
                "id": "subtask_1",
                "description": f"分析代码需求: {task_description}",
                "priority": "high"
            })
            subtasks.append({
                "id": "subtask_2",
                "description": f"编写代码: {task_description}",
                "priority": "high"
            })
            subtasks.append({
                "id": "subtask_3",
                "description": "Test代码",
                "priority": "medium"
            })
        elif "文件" in task_description:
            subtasks.append({
                "id": "subtask_1",
                "description": f"执行文件操作: {task_description}",
                "priority": "medium"
            })
        elif "网络" in task_description:
            subtasks.append({
                "id": "subtask_1",
                "description": f"执行网络操作: {task_description}",
                "priority": "medium"
            })
        elif "系统" in task_description:
            subtasks.append({
                "id": "subtask_1",
                "description": f"执行系统操作: {task_description}",
                "priority": "medium"
            })
        elif "安全" in task_description:
            subtasks.append({
                "id": "subtask_1",
                "description": f"执行安全操作: {task_description}",
                "priority": "high"
            })
        else:
            # 默认Task
            subtasks.append({
                "id": "subtask_1",
                "description": task_description,
                "priority": "medium"
            })
        
        return subtasks
    
    def _select_agent_for_task(self, task_description: str) -> str:
        """
        为Task选择合适的Agent
        
        参数:
            task_description: TaskDescription
            
        返回:
            AgentName
        """
        task_lower = task_description.lower()
        
        if any(keyword in task_lower for keyword in ["code", "编程", "代码", "debug", "调试"]):
            return "code_agent"
        elif any(keyword in task_lower for keyword in ["file", "文件", "目录", "folder"]):
            return "file_agent"
        elif any(keyword in task_lower for keyword in ["network", "网络", "internet", "Connect"]):
            return "network_agent"
        elif any(keyword in task_lower for keyword in ["system", "系统", "进程", "process"]):
            return "system_agent"
        elif any(keyword in task_lower for keyword in ["security", "安全", "监控", "monitor"]):
            return "security_agent"
        else:
            return "system_agent"
    
    def _integrate_results(self, results: Dict[str, Any], original_task: str) -> str:
        """
        整合
        
        参数:
            results: 子Task
            original_task: 原始Task
            
        返回:
            整合后的
        """
        # 简单的整合逻辑
        # 实际应用中可以使用LLM进行更智能的整合
        successful_tasks = []
        failed_tasks = []
        
        for subtask_id, result in results.items():
            if result.get("status") == "completed":
                successful_tasks.append(result)
            else:
                failed_tasks.append(result)
        
        if failed_tasks:
            return f"Task '{original_task}' 部分 complete, {len(successful_tasks)}   successful, {len(failed_tasks)}   failed"
        else:
            return f"Task '{original_task}' already successful complete, {len(successful_tasks)}  Step"
    
    def get_coordination_statistics(self) -> Dict[str, Any]:
        """
        GetCollaboration statistics信息
        
        返回:
            Statistics
        """
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == "completed"])
        pending_tasks = len([t for t in self.tasks.values() if t.status == "pending"])
        in_progress_tasks = len([t for t in self.tasks.values() if t.status == "in_progress"])
        
        agent_task_count = {}
        for task in self.tasks.values():
            if task.assigned_agent:
                if task.assigned_agent not in agent_task_count:
                    agent_task_count[task.assigned_agent] = 0
                agent_task_count[task.assigned_agent] += 1
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "agent_task_count": agent_task_count,
            "message_queue_size": len(self.message_queue)
        }


if __name__ == "__main__":
    # TestAgent协作
    from src.core.memory.unified_memory import UnifiedMemorySystem
    
    # Initialization memories系统
    memory_system = UnifiedMemorySystem(memory_dir="test_coordinator")
    
    # Initializing agent管理器
    agent_manager = AgentManager(memory_system)
    
    # Initialization协作协调器
    coordinator = AgentCoordinator(agent_manager)
    
    # Test sending message
    print("=== Test sending message ===")
    message = Message(
        sender="code_agent",
        recipient="file_agent",
        content="请Create一 新的Python文件",
        message_type="request"
    )
    coordinator.send_message(message)
    coordinator.process_messages()
    
    # Test creating and assigning tasks
    print("\n=== Test creating and assigning tasks ===")
    task_id = coordinator.create_task("编写一 Python函数来计算阶乘")
    coordinator.assign_task(task_id, "code_agent")
    task_status = coordinator.get_task_status(task_id)
    print(f"Task status: {task_status}")
    
    # Test coordinating complex task
    print("\n=== Test coordinating complex task ===")
    complex_task = "Create一 新的Python项目, 包含代码文件和README文档"
    result = coordinator.coordinate_complex_task(complex_task)
    print(f"Complex task result: {result}")
    
    # Test statistics
    print("\n=== Test statistics ===")
    stats = coordinator.get_coordination_statistics()
    print(f"Collaboration statistics: {stats}")
