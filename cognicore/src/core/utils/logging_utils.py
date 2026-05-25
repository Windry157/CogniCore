#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志Tool module
提供结构化的日志记录和Status追踪功能
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime


class StructuredLogger:
    """
    结构化日志记录器
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialization结构化日志记录器
        
        Args:
            name: 日志器Name
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 如果没有Processor, Add默认Processor
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """
        格式化消息
        
        Args:
            message: 消息Content
            **kwargs: 额外参数
            
        Returns:
            格式化后的消息
        """
        if kwargs:
            # 尝试将kwargs转换为JSON格式
            try:
                extra_info = json.dumps(kwargs, ensure_ascii=False)
                return f"{message} | {extra_info}"
            except Exception:
                return message
        return message
    
    def debug(self, message: str, **kwargs):
        """
        记录调试级别的日志
        """
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs):
        """
        记录信息级别的日志
        """
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """
        记录warning级别的日志
        """
        if self.logger.isEnabledFor(logging.WARNING):
            self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """
        记录Error级别的日志
        """
        if self.logger.isEnabledFor(logging.ERROR):
            self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs):
        """
        记录严重级别的日志
        """
        if self.logger.isEnabledFor(logging.CRITICAL):
            self.logger.critical(self._format_message(message, **kwargs))


class StatusTracker:
    """
    Status追踪器
    用于跟踪Task执行的Status和时间
    """
    
    def __init__(self, tracker_id: str):
        """
        InitializationStatus追踪器
        
        Args:
            tracker_id: 追踪器ID
        """
        self.tracker_id = tracker_id
        self.states: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.last_state_time = self.start_time
    
    def add_state(self, state: str, details: Optional[Dict[str, Any]] = None):
        """
        AddStatus
        
        Args:
            state: StatusName
            details: Status详情
        """
        current_time = time.time()
        state_info = {
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "elapsed_from_start": current_time - self.start_time,
            "elapsed_from_last": current_time - self.last_state_time,
            "details": details or {}
        }
        self.states.append(state_info)
        self.last_state_time = current_time
    
    def get_states(self) -> List[Dict[str, Any]]:
        """
        Get所有Status
        
        Returns:
            Status列表
        """
        return self.states
    
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """
        Get当前Status
        
        Returns:
            当前Status
        """
        return self.states[-1] if self.states else None
    
    def get_duration(self) -> float:
        """
        Get总持续时间
        
        Returns:
            总持续时间 (s) 
        """
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            追踪器信息字典
        """
        return {
            "tracker_id": self.tracker_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "duration": self.get_duration(),
            "states": self.states
        }
    
    def to_json(self) -> str:
        """
        转换为JSON字符串
        
        Returns:
            JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class TaskLogger:
    """
    Task日志记录器
    用于记录Task的执行过程
    """
    
    def __init__(self, task_id: str, logger_name: str = "task"):
        """
        InitializationTask日志记录器
        
        Args:
            task_id: TaskID
            logger_name: 日志器Name
        """
        self.task_id = task_id
        self.logger = StructuredLogger(logger_name)
        self.status_tracker = StatusTracker(task_id)
        
        # 记录Task started
        self.start()
    
    def start(self):
        """
        记录Task started
        """
        self.status_tracker.add_state("STARTED")
        self.logger.info(f"Task started", task_id=self.task_id)
    
    def progress(self, message: str, **kwargs):
        """
        记录Task进度
        
        Args:
            message: 进度消息
            **kwargs: 额外信息
        """
        self.status_tracker.add_state("IN_PROGRESS", {
            "message": message,
            **kwargs
        })
        self.logger.info(message, task_id=self.task_id, **kwargs)
    
    def success(self, message: str = "Task complete", **kwargs):
        """
        记录Task successful
        
        Args:
            message:  successful消息
            **kwargs: 额外信息
        """
        self.status_tracker.add_state("SUCCESS", {
            "message": message,
            **kwargs
        })
        self.logger.info(message, task_id=self.task_id, **kwargs)
    
    def failure(self, message: str = "Task failed", error: Optional[Exception] = None, **kwargs):
        """
        记录Task failed
        
        Args:
            message:  failed消息
            error: Errorexception
            **kwargs: 额外信息
        """
        error_info = str(error) if error else None
        self.status_tracker.add_state("FAILURE", {
            "message": message,
            "error": error_info,
            **kwargs
        })
        self.logger.error(message, task_id=self.task_id, error=error_info, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """
        GetTask status
        
        Returns:
            Task status
        """
        return self.status_tracker.to_dict()
    
    def get_duration(self) -> float:
        """
        GetTask持续时间
        
        Returns:
            持续时间 (s) 
        """
        return self.status_tracker.get_duration()


# 全局日志器实例
DEFAULT_LOGGER = StructuredLogger("smart_agent")


def get_logger(name: str) -> StructuredLogger:
    """
    Get日志器
    
    Args:
        name: 日志器Name
        
    Returns:
        结构化日志器
    """
    return StructuredLogger(name)


def get_task_logger(task_id: str) -> TaskLogger:
    """
    GetTask日志器
    
    Args:
        task_id: TaskID
        
    Returns:
        Task日志器
    """
    return TaskLogger(task_id)


def setup_logging(
    level: int = logging.INFO,
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename: Optional[str] = None
):
    """
    配置全局日志
    
    Args:
        level: 日志级别
        format: 日志格式
        filename: 日志文件路径
    """
    handlers = []
    
    # 控制台Processor
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(format))
    handlers.append(console_handler)
    
    # 文件Processor
    if filename:
        file_handler = logging.FileHandler(filename, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(format))
        handlers.append(file_handler)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有Processor
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    # Add新Processor
    for handler in handlers:
        root_logger.addHandler(handler)