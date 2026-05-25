#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task status管理系统
支持多轮对话和复杂Task链的Status管理
"""

import json
import os
from typing import Dict, Any, Optional, List
import logging
import asyncio

from src.core.config import config, _get_project_root

logger = logging.getLogger(__name__)


class TaskState:
    """
    Task status类
    """
    
    def __init__(self, task_id: str, goal: str, context: Optional[Dict[str, Any]] = None):
        """
        InitializationTask status
        
        Args:
            task_id: TaskID
            goal: Task目标
            context: Task上下文
        """
        self.task_id = task_id
        self.goal = goal
        self.context = context or {}
        self.status = "CREATED"  # CREATED, IN_PROGRESS, COMPLETED, FAILED
        self.start_time = asyncio.get_event_loop().time()
        self.end_time = None
        self.steps = []
        self.results = []
        self.errors = []
        self.current_step = 0
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Task status字典
        """
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "context": self.context,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "steps": self.steps,
            "results": self.results,
            "errors": self.errors,
            "current_step": self.current_step,
            "metadata": self.metadata
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """
        From字典Load
        
        Args:
            data: Task status字典
        """
        self.task_id = data.get("task_id", self.task_id)
        self.goal = data.get("goal", self.goal)
        self.context = data.get("context", self.context)
        self.status = data.get("status", self.status)
        self.start_time = data.get("start_time", self.start_time)
        self.end_time = data.get("end_time", self.end_time)
        self.steps = data.get("steps", self.steps)
        self.results = data.get("results", self.results)
        self.errors = data.get("errors", self.errors)
        self.current_step = data.get("current_step", self.current_step)
        self.metadata = data.get("metadata", self.metadata)
    
    def add_step(self, step_name: str, description: str):
        """
        AddStep
        
        Args:
            step_name: StepName
            description: StepDescription
        """
        self.steps.append({
            "name": step_name,
            "description": description,
            "status": "PENDING",
            "start_time": None,
            "end_time": None,
            "result": None,
            "error": None
        })
    
    def start_step(self, step_index: int):
        """
        开始Step
        
        Args:
            step_index: Step索引
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = "IN_PROGRESS"
            self.steps[step_index]["start_time"] = asyncio.get_event_loop().time()
            self.current_step = step_index
    
    def complete_step(self, step_index: int, result: Any):
        """
         completeStep
        
        Args:
            step_index: Step索引
            result: Step
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = "COMPLETED"
            self.steps[step_index]["end_time"] = asyncio.get_event_loop().time()
            self.steps[step_index]["result"] = result
            self.results.append(result)
    
    def fail_step(self, step_index: int, error: str):
        """
         failedStep
        
        Args:
            step_index: Step索引
            error: Error信息
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = "FAILED"
            self.steps[step_index]["end_time"] = asyncio.get_event_loop().time()
            self.steps[step_index]["error"] = error
            self.errors.append(error)
    
    def start(self):
        """
        开始Task
        """
        self.status = "IN_PROGRESS"
    
    def complete(self, final_result: Any):
        """
         completeTask
        
        Args:
            final_result: 最终
        """
        self.status = "COMPLETED"
        self.end_time = asyncio.get_event_loop().time()
        self.results.append(final_result)
    
    def fail(self, error: str):
        """
         failedTask
        
        Args:
            error: Error信息
        """
        self.status = "FAILED"
        self.end_time = asyncio.get_event_loop().time()
        self.errors.append(error)
    
    def update_context(self, key: str, value: Any):
        """
        Update上下文
        
        Args:
            key: 键
            value: 值
        """
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get上下文值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            上下文值
        """
        return self.context.get(key, default)
    
    def update_metadata(self, key: str, value: Any):
        """
        Update元数据
        
        Args:
            key: 键
            value: 值
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get元数据值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            元数据值
        """
        return self.metadata.get(key, default)
    
    def get_duration(self) -> float:
        """
        GetTask持续时间
        
        Returns:
            持续时间 (s) 
        """
        if self.end_time:
            return self.end_time - self.start_time
        return asyncio.get_event_loop().time() - self.start_time


class TaskStateManager:
    """
    Task status管理器
    """
    
    def __init__(self, state_dir: str = None):
        """
        InitializationTask status管理器
        
        Args:
            state_dir: Status存储目录
        """
        self.state_dir = state_dir or str(_get_project_root() / config.system.data_dir / "task_states")
        os.makedirs(self.state_dir, exist_ok=True)
        self.active_states: Dict[str, TaskState] = {}
        self._load_active_states()
        
        logger.info("Task state manager initialized")
    
    def _load_active_states(self):
        """
        Load活跃的Task status
        """
        try:
            for filename in os.listdir(self.state_dir):
                if filename.endswith(".json"):
                    task_id = filename[:-5]  # 移除.json后缀
                    state_path = os.path.join(self.state_dir, filename)
                    try:
                        with open(state_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            state = TaskState(task_id, data.get("goal"))
                            state.from_dict(data)
                            if state.status in ["CREATED", "IN_PROGRESS"]:
                                self.active_states[task_id] = state
                    except Exception as e:
                        logger.error(f"Failed to load task state {task_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to load active task states: {e}")
    
    def create_state(self, task_id: str, goal: str, context: Optional[Dict[str, Any]] = None) -> TaskState:
        """
        Creating task state
        
        Args:
            task_id: TaskID
            goal: Task目标
            context: Task上下文
            
        Returns:
            Task status对象
        """
        state = TaskState(task_id, goal, context)
        self.active_states[task_id] = state
        self._save_state(state)
        logger.info(f"Creating task state: {task_id}")
        return state
    
    def get_state(self, task_id: str) -> Optional[TaskState]:
        """
        GetTask status
        
        Args:
            task_id: TaskID
            
        Returns:
            Task status对象
        """
        if task_id in self.active_states:
            return self.active_states[task_id]
        
        # 尝试From文件Load
        state_path = os.path.join(self.state_dir, f"{task_id}.json")
        if os.path.exists(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    state = TaskState(task_id, data.get("goal"))
                    state.from_dict(data)
                    self.active_states[task_id] = state
                    return state
            except Exception as e:
                logger.error(f"Failed to load task state {task_id}: {e}")
        
        return None
    
    def save_state(self, task_id: str):
        """
        SaveTask status
        
        Args:
            task_id: TaskID
        """
        if task_id in self.active_states:
            state = self.active_states[task_id]
            self._save_state(state)
    
    def _save_state(self, state: TaskState):
        """
        SaveTask status到文件
        
        Args:
            state: Task status对象
        """
        try:
            state_path = os.path.join(self.state_dir, f"{state.task_id}.json")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save task state {state.task_id}: {e}")
    
    def remove_state(self, task_id: str):
        """
        Removing task state
        
        Args:
            task_id: TaskID
        """
        if task_id in self.active_states:
            del self.active_states[task_id]
        
        # Delete file
        state_path = os.path.join(self.state_dir, f"{task_id}.json")
        if os.path.exists(state_path):
            try:
                os.remove(state_path)
                logger.info(f"Removing task state: {task_id}")
            except Exception as e:
                logger.error(f"Failed to remove task state file {task_id}: {e}")
    
    def list_states(self, status: Optional[str] = None) -> List[TaskState]:
        """
        ListTask status
        
        Args:
            status: Status过滤
            
        Returns:
            Task status列表
        """
        states = list(self.active_states.values())
        if status:
            states = [s for s in states if s.status == status]
        return states
    
    def list_state_ids(self, status: Optional[str] = None) -> List[str]:
        """
        ListTask statusID
        
        Args:
            status: Status过滤
            
        Returns:
            Task statusID列表
        """
        states = self.list_states(status)
        return [s.task_id for s in states]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetStatistics
        
        Returns:
            Statistics
        """
        states = self.list_states()
        total = len(states)
        completed = sum(1 for s in states if s.status == "COMPLETED")
        failed = sum(1 for s in states if s.status == "FAILED")
        in_progress = sum(1 for s in states if s.status == "IN_PROGRESS")
        created = sum(1 for s in states if s.status == "CREATED")
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "created": created,
            "completion_rate": completed / total if total > 0 else 0
        }


# 全局Task status管理器实例
task_state_manager = None


def get_task_state_manager() -> TaskStateManager:
    """
    GetTask status管理器实例
    
    Returns:
        TaskStateManager实例
    """
    global task_state_manager
    if task_state_manager is None:
        task_state_manager = TaskStateManager()
    return task_state_manager


def reset_task_state_manager():
    """
    重置Task status管理器
    """
    global task_state_manager
    task_state_manager = None
