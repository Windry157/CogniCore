#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户反馈管理
实现标准化的用户反馈循环机制
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import json
import logging
import time
from pathlib import Path

from src.core.config import config, _get_project_root
from src.core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FeedbackType(Enum):
    """反馈type"""
    RATING = "rating"  # 评分反馈
    CORRECTION = "correction"  # 修正反馈
    SUGGESTION = "suggestion"  # 建议反馈
    COMPLAINT = "complaint"  # 投诉反馈
    PRAISE = "praise"  # 表扬反馈


class FeedbackStatus(Enum):
    """反馈Status"""
    PENDING = "pending"  # 待Processing
    PROCESSING = "processing"  # Processing中
    RESOLVED = "resolved"  # already解决
    DISMISSED = "dismissed"  # already忽略


@dataclass
class UserFeedback:
    """用户反馈数据类"""
    id: str
    user_id: str
    session_id: str
    type: str  # FeedbackType
    content: str
    task_id: Optional[str] = None
    rating: Optional[int] = None  # 1-5
    timestamp: float = field(default_factory=time.time)
    status: str = FeedbackStatus.PENDING.value
    metadata: Dict[str, Any] = field(default_factory=dict)
    response: Optional[str] = None
    processed_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "type": self.type,
            "content": self.content,
            "rating": self.rating,
            "timestamp": self.timestamp,
            "status": self.status,
            "metadata": self.metadata,
            "response": self.response,
            "processed_at": self.processed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserFeedback":
        """From字典Create实例"""
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            task_id=data.get("task_id"),
            type=data.get("type"),
            content=data.get("content"),
            rating=data.get("rating"),
            timestamp=data.get("timestamp", time.time()),
            status=data.get("status", FeedbackStatus.PENDING.value),
            metadata=data.get("metadata", {}),
            response=data.get("response"),
            processed_at=data.get("processed_at")
        )


class FeedbackManager:
    """用户反馈管理器"""
    
    def __init__(self, feedback_dir: str = None):
        """
        Initialization反馈管理器
        
        Args:
            feedback_dir: 反馈存储目录
        """
        self.feedback_dir = feedback_dir or _get_project_root() / config.system.data_dir / "feedback"
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.feedback_file = self.feedback_dir / "feedback.json"
        self.feedback_data = self._load_feedback()
        
        logger.info(f"Feedback manager initialized, loaded {len(self.feedback_data)}  feedback entries")
    
    def _load_feedback(self) -> Dict[str, UserFeedback]:
        """
        Load反馈数据
        
        Returns:
            反馈字典, 键为反馈ID
        """
        if not self.feedback_file.exists():
            return {}
        
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                feedback_dict = {}
                for feedback_id, feedback_data in data.items():
                    feedback_dict[feedback_id] = UserFeedback.from_dict(feedback_data)
                return feedback_dict
        except Exception as e:
            logger.error(f"Failed to load feedback data: {e}")
            return {}
    
    def _save_feedback(self):
        """
        Save反馈数据
        """
        try:
            data = {}
            for feedback_id, feedback in self.feedback_data.items():
                data[feedback_id] = feedback.to_dict()
            
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save feedback data: {e}")
    
    def collect_feedback(self, user_id: str, session_id: str, 
                        feedback_type: str, content: str, 
                        task_id: Optional[str] = None, 
                        rating: Optional[int] = None, 
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        收集用户反馈
        
        Args:
            user_id: 用户ID
            session_id: Session ID
            feedback_type: 反馈type
            content: 反馈Content
            task_id: TaskID
            rating: 评分 (1-5) 
            metadata: 附加信息
            
        Returns:
            反馈ID
        """
        feedback_id = f"feedback_{int(time.time() * 1000)}"
        
        feedback = UserFeedback(
            id=feedback_id,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            type=feedback_type,
            content=content,
            rating=rating,
            metadata=metadata or {}
        )
        
        self.feedback_data[feedback_id] = feedback
        self._save_feedback()
        
        logger.info(f"New feedback collected: {feedback_id}, type: {feedback_type}")
        return feedback_id
    
    def get_feedback(self, feedback_id: str) -> Optional[UserFeedback]:
        """
        Get反馈信息
        
        Args:
            feedback_id: 反馈ID
            
        Returns:
            反馈对象
        """
        return self.feedback_data.get(feedback_id)
    
    def get_feedback_by_task(self, task_id: str) -> List[UserFeedback]:
        """
        Get指定Task的反馈
        
        Args:
            task_id: TaskID
            
        Returns:
            反馈列表
        """
        return [f for f in self.feedback_data.values() if f.task_id == task_id]
    
    def get_feedback_by_user(self, user_id: str) -> List[UserFeedback]:
        """
        Get指定用户的反馈
        
        Args:
            user_id: 用户ID
            
        Returns:
            反馈列表
        """
        return [f for f in self.feedback_data.values() if f.user_id == user_id]
    
    def get_feedback_by_status(self, status: str) -> List[UserFeedback]:
        """
        Get指定Status的反馈
        
        Args:
            status: Status
            
        Returns:
            反馈列表
        """
        return [f for f in self.feedback_data.values() if f.status == status]
    
    def update_feedback_status(self, feedback_id: str, status: str) -> bool:
        """
        Updating feedback status
        
        Args:
            feedback_id: 反馈ID
            status: 新Status
            
        Returns:
            是否Update successful
        """
        if feedback_id not in self.feedback_data:
            return False
        
        self.feedback_data[feedback_id].status = status
        if status in [FeedbackStatus.RESOLVED.value, FeedbackStatus.DISMISSED.value]:
            self.feedback_data[feedback_id].processed_at = time.time()
        
        self._save_feedback()
        logger.info(f"Updating feedback status: {feedback_id}, Status: {status}")
        return True
    
    def add_feedback_response(self, feedback_id: str, response: str) -> bool:
        """
        Adding feedback response
        
        Args:
            feedback_id: 反馈ID
            response: ResponseContent
            
        Returns:
            是否Add successful
        """
        if feedback_id not in self.feedback_data:
            return False
        
        self.feedback_data[feedback_id].response = response
        self.feedback_data[feedback_id].status = FeedbackStatus.RESOLVED.value
        self.feedback_data[feedback_id].processed_at = time.time()
        
        self._save_feedback()
        logger.info(f"Adding feedback response: {feedback_id}")
        return True
    
    def analyze_feedback(self, feedback_type: Optional[str] = None) -> Dict[str, Any]:
        """
        分析反馈数据
        
        Args:
            feedback_type: 反馈type, None表示所有type
            
        Returns:
            分析
        """
        # 过滤反馈
        if feedback_type:
            filtered_feedback = [f for f in self.feedback_data.values() if f.type == feedback_type]
        else:
            filtered_feedback = list(self.feedback_data.values())
        
        if not filtered_feedback:
            return {
                "total": 0,
                "average_rating": 0,
                "status_distribution": {},
                "type_distribution": {},
                "recent_feedback": []
            }
        
        # 计算统计数据
        total = len(filtered_feedback)
        ratings = [f.rating for f in filtered_feedback if f.rating is not None]
        average_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Status分布
        status_distribution = {}
        for f in filtered_feedback:
            status_distribution[f.status] = status_distribution.get(f.status, 0) + 1
        
        # type分布
        type_distribution = {}
        for f in filtered_feedback:
            type_distribution[f.type] = type_distribution.get(f.type, 0) + 1
        
        # 最近的反馈
        recent_feedback = sorted(
            filtered_feedback,
            key=lambda x: x.timestamp,
            reverse=True
        )[:10]
        
        return {
            "total": total,
            "average_rating": average_rating,
            "status_distribution": status_distribution,
            "type_distribution": type_distribution,
            "recent_feedback": [f.to_dict() for f in recent_feedback]
        }
    
    def get_actionable_feedback(self) -> List[UserFeedback]:
        """
        Get可操作的反馈
        
        Returns:
            可操作的反馈列表
        """
        actionable_types = [
            FeedbackType.CORRECTION.value,
            FeedbackType.SUGGESTION.value,
            FeedbackType.COMPLAINT.value
        ]
        
        return [
            f for f in self.feedback_data.values()
            if f.type in actionable_types and f.status == FeedbackStatus.PENDING.value
        ]
    
    def generate_feedback_summary(self) -> Dict[str, Any]:
        """
        生成反馈摘要
        
        Returns:
            反馈摘要
        """
        analysis = self.analyze_feedback()
        actionable = self.get_actionable_feedback()
        
        return {
            "total_feedback": analysis["total"],
            "average_rating": analysis["average_rating"],
            "pending_feedback": len(self.get_feedback_by_status(FeedbackStatus.PENDING.value)),
            "actionable_feedback": len(actionable),
            "status_distribution": analysis["status_distribution"],
            "type_distribution": analysis["type_distribution"],
            "recent_feedback": analysis["recent_feedback"]
        }
    
    def clear_feedback(self, older_than_days: Optional[int] = None):
        """
        清理反馈数据
        
        Args:
            older_than_days: 清理多少天之前的反馈, None表示清理所有
        """
        if older_than_days is None:
            self.feedback_data = {}
        else:
            cutoff_time = time.time() - (older_than_days * 24 * 3600)
            self.feedback_data = {
                k: v for k, v in self.feedback_data.items()
                if v.timestamp > cutoff_time
            }
        
        self._save_feedback()
        logger.info(f"Cleaning feedback data, remaining {len(self.feedback_data)}  entries")


# 全局反馈管理器实例
_feedback_manager_instance = None


def get_feedback_manager() -> FeedbackManager:
    """
    Get反馈管理器实例
    
    Returns:
        反馈管理器实例
    """
    global _feedback_manager_instance
    if _feedback_manager_instance is None:
        _feedback_manager_instance = FeedbackManager()
    return _feedback_manager_instance


def reset_feedback_manager() -> FeedbackManager:
    """
    重置反馈管理器实例
    
    Returns:
        新的反馈管理器实例
    """
    global _feedback_manager_instance
    _feedback_manager_instance = FeedbackManager()
    return _feedback_manager_instance