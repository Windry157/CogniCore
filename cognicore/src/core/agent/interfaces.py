#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agentgroups件接口定义
定义各 groups件的抽象接口, 确保groups件之间通过接口交互
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class PlannerInterface(ABC):
    """规划器接口"""
    
    @abstractmethod
    def decompose_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        将复杂Task分解为子Task
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            子Task列表
        """
        pass
    
    @abstractmethod
    def optimize_task_order(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        优化Task执行顺序
        
        Args:
            tasks: Task列表
            
        Returns:
            优化后的Task列表
        """
        pass
    
    @abstractmethod
    def validate_task_plan(self, tasks: List[Dict[str, Any]]) -> bool:
        """
        验证Task计划的Effectiveness
        
        Args:
            tasks: Task列表
            
        Returns:
            是否有效
        """
        pass


class ExecutorInterface(ABC):
    """执行器接口"""
    
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行单 tasks
        
        Args:
            task: Task信息
            context: Task上下文信息
            
        Returns:
            执行
        """
        pass
    
    @abstractmethod
    async def execute_task_chain(self, tasks: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        executing task链
        
        Args:
            tasks: Task列表
            context: 初始上下文信息
            
        Returns:
            执行汇总
        """
        pass
    
    @abstractmethod
    async def execute_with_retry(self, task: Dict[str, Any], max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
        """
        带重试机制的Task执行
        
        Args:
            task: Task信息
            max_retries: 最大重试次数
            retry_delay: 重试延迟 (s) 
            
        Returns:
            执行
        """
        pass
    
    @abstractmethod
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        GetTask执行历史
        
        Returns:
            Task执行历史
        """
        pass
    
    @abstractmethod
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get当前Status
        
        Returns:
            当前Status
        """
        pass
    
    @abstractmethod
    def reset_state(self):
        """
        重置Status
        """
        pass
    
    @abstractmethod
    def clear_history(self):
        """
        清除Task执行历史
        """
        pass


class CriticInterface(ABC):
    """批判器接口"""
    
    @abstractmethod
    def analyze_error(self, error: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzing error并生成修正策略
        
        Args:
            error: Error信息
            task:  failed的Task信息
            
        Returns:
            Error analysis result
        """
        pass
    
    @abstractmethod
    def evaluate_task_result(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估Task execution result
        
        Args:
            task: Task信息
            result: 执行
            
        Returns:
            评估
        """
        pass
    
    @abstractmethod
    def generate_improvement_plan(self, task_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        根据Task历史生成改进计划
        
        Args:
            task_history: Task执行历史
            
        Returns:
            改进计划
        """
        pass


class ValidatorInterface(ABC):
    """验证器接口"""
    
    @abstractmethod
    def validate_plan(self, plan: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validating execution plan的安全性和可行性
        
        Args:
            plan: 执行计划, 包含多 子Task
            context: Task上下文信息
            
        Returns:
            验证
        """
        pass
    
    @abstractmethod
    def validate_execution(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validating task execution result的安全性和Effectiveness
        
        Args:
            task: 执行的Task信息
            result: 执行
            
        Returns:
            验证
        """
        pass
    
    @abstractmethod
    def generate_risk_assessment(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generating risk assessment report
        
        Args:
            task: Task信息
            context: Task上下文信息
            
        Returns:
            风险评估报告
        """
        pass
    
    @abstractmethod
    def generate_explanation(self, task: Dict[str, Any], result: Dict[str, Any], validation: Dict[str, Any]) -> str:
        """
        生成执行解释
        
        Args:
            task: Task信息
            result: 执行
            validation: 验证
            
        Returns:
            执行解释字符串
        """
        pass


class AgentCoordinatorInterface(ABC):
    """Agent协调器接口"""
    
    @abstractmethod
    async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processing复杂Task
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            TaskProcessing result
        """
        pass
    
    @abstractmethod
    async def process_with_reflection(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        带反思机制的TaskProcessing
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            TaskProcessing result
        """
        pass
    
    @abstractmethod
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        GetTask执行历史
        
        Returns:
            Task执行历史
        """
        pass
    
    @abstractmethod
    def get_executor_history(self) -> List[Dict[str, Any]]:
        """
        Get执行器的Task执行历史
        
        Returns:
            执行器的Task执行历史
        """
        pass
    
    @abstractmethod
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get当前Status
        
        Returns:
            当前Status
        """
        pass
    
    @abstractmethod
    def reset_state(self):
        """
        重置Status
        """
        pass
    
    @abstractmethod
    def clear_history(self):
        """
        清除历史记录
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetAgent statistics
        
        Returns:
            Statistics
        """
        pass
    
    @abstractmethod
    async def shutdown(self):
        """
        CloseAgent, 清理资源
        """
        pass
