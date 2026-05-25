#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
user profiles module
构建user profiles, 包括偏好提取, 行为分析, 知识图谱
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path

from src.core.config import config
from src.core.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class UserPreference:
    """用户偏好"""
    category: str  # 偏好类别
    value: Any  # 偏好值
    confidence: float = 1.0  # 置信度
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class BehaviorPattern:
    """行为模式"""
    pattern_type: str  # 模式type
    description: str  # Description
    frequency: int = 0  # 出现频率
    last_observed: float = 0  # 上次观察时间


@dataclass
class UserKnowledgeNode:
    """用户知识图谱节点"""
    id: str
    label: str  # 节点标签
    node_type: str  # 节点type: person, concept, object, event
    properties: Dict[str, Any] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)  # Connect的节点ID列表


@dataclass
class UserProfile:
    """user profiles"""
    user_id: str
    preferences: Dict[str, UserPreference] = field(default_factory=dict)
    behavior_patterns: Dict[str, BehaviorPattern] = field(default_factory=dict)
    knowledge_graph: Dict[str, UserKnowledgeNode] = field(default_factory=dict)
    interaction_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_active: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "preferences": {k: {
                "category": v.category,
                "value": v.value,
                "confidence": v.confidence,
                "updated_at": v.updated_at
            } for k, v in self.preferences.items()},
            "behavior_patterns": {k: {
                "pattern_type": v.pattern_type,
                "description": v.description,
                "frequency": v.frequency,
                "last_observed": v.last_observed
            } for k, v in self.behavior_patterns.items()},
            "knowledge_graph": {k: {
                "id": v.id,
                "label": v.label,
                "node_type": v.node_type,
                "properties": v.properties,
                "connections": v.connections
            } for k, v in self.knowledge_graph.items()},
            "interaction_count": self.interaction_count,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """From字典Create"""
        profile = cls(user_id=data["user_id"])
        profile.interaction_count = data.get("interaction_count", 0)
        profile.created_at = data.get("created_at", datetime.now().timestamp())
        profile.last_active = data.get("last_active", datetime.now().timestamp())
        profile.metadata = data.get("metadata", {})

        for k, v in data.get("preferences", {}).items():
            profile.preferences[k] = UserPreference(
                category=v["category"],
                value=v["value"],
                confidence=v.get("confidence", 1.0),
                updated_at=v.get("updated_at", datetime.now().timestamp())
            )

        for k, v in data.get("behavior_patterns", {}).items():
            profile.behavior_patterns[k] = BehaviorPattern(
                pattern_type=v["pattern_type"],
                description=v["description"],
                frequency=v.get("frequency", 0),
                last_observed=v.get("last_observed", 0)
            )

        for k, v in data.get("knowledge_graph", {}).items():
            profile.knowledge_graph[k] = UserKnowledgeNode(
                id=v["id"],
                label=v["label"],
                node_type=v["node_type"],
                properties=v.get("properties", {}),
                connections=v.get("connections", [])
            )

        return profile


class UserProfileService:
    """User profile service"""

    def __init__(self, profile_dir: str = None):
        """
        InitializationUser profile service

        Args:
            profile_dir: 画像存储目录
        """
        self.profile_dir = profile_dir or _get_project_root() / config.system.data_dir / "user_profiles"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.profile_dir / "user_profiles.json"
        self.profiles = self._load_profiles()

        logger.info(f"User profile service initialized, loaded {len(self.profiles)}  user profiles")

    def _load_profiles(self) -> Dict[str, UserProfile]:
        """Load user profile"""
        if not self.profile_file.exists():
            return {}

        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                profiles = {}
                for user_id, profile_data in data.items():
                    profiles[user_id] = UserProfile.from_dict(profile_data)
                return profiles
        except Exception as e:
            logger.error(f"Load user profile failed: {e}")
            return {}

    def _save_profiles(self):
        """Save user profile"""
        try:
            data = {}
            for user_id, profile in self.profiles.items():
                data[user_id] = profile.to_dict()

            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Save user profile failed: {e}")

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Getuser profiles

        Args:
            user_id: 用户ID

        Returns:
            user profiles
        """
        return self.profiles.get(user_id)

    def create_profile(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> UserProfile:
        """
        Create user profile

        Args:
            user_id: 用户ID
            metadata: 附加信息

        Returns:
            user profiles
        """
        if user_id in self.profiles:
            return self.profiles[user_id]

        profile = UserProfile(
            user_id=user_id,
            metadata=metadata or {}
        )
        self.profiles[user_id] = profile
        self._save_profiles()
        logger.info(f"Create user profile: {user_id}")
        return profile

    def update_preference(self, user_id: str, category: str, value: Any, confidence: float = 1.0):
        """
        Update user preference

        Args:
            user_id: 用户ID
            category: 偏好类别
            value: 偏好值
            confidence: 置信度
        """
        if user_id not in self.profiles:
            self.create_profile(user_id)

        preference_key = f"{category}_{value}"
        self.profiles[user_id].preferences[preference_key] = UserPreference(
            category=category,
            value=value,
            confidence=confidence,
            updated_at=datetime.now().timestamp()
        )
        self._save_profiles()
        logger.info(f"Update user preference: {user_id}, {category}={value}")

    def update_behavior_pattern(self, user_id: str, pattern_type: str, description: str):
        """
        Update behavior pattern

        Args:
            user_id: 用户ID
            pattern_type: 模式type
            description: Description
        """
        if user_id not in self.profiles:
            self.create_profile(user_id)

        if pattern_type in self.profiles[user_id].behavior_patterns:
            pattern = self.profiles[user_id].behavior_patterns[pattern_type]
            pattern.frequency += 1
            pattern.last_observed = datetime.now().timestamp()
            pattern.description = description
        else:
            self.profiles[user_id].behavior_patterns[pattern_type] = BehaviorPattern(
                pattern_type=pattern_type,
                description=description,
                frequency=1,
                last_observed=datetime.now().timestamp()
            )
        self._save_profiles()
        logger.info(f"Update behavior pattern: {user_id}, {pattern_type}")

    def add_knowledge_node(self, user_id: str, node_id: str, label: str,
                          node_type: str, properties: Optional[Dict[str, Any]] = None,
                          connections: Optional[List[str]] = None):
        """
        Add知识图谱节点

        Args:
            user_id: 用户ID
            node_id: 节点ID
            label: 节点标签
            node_type: 节点type
            properties: 节点属性
            connections: Connect的节点
        """
        if user_id not in self.profiles:
            self.create_profile(user_id)

        self.profiles[user_id].knowledge_graph[node_id] = UserKnowledgeNode(
            id=node_id,
            label=label,
            node_type=node_type,
            properties=properties or {},
            connections=connections or []
        )
        self._save_profiles()
        logger.info(f"Add knowledge node: {user_id}, {node_id}")

    def connect_knowledge_nodes(self, user_id: str, node_id1: str, node_id2: str):
        """
        Connect两 知识图谱节点

        Args:
            user_id: 用户ID
            node_id1: 节点1 ID
            node_id2: 节点2 ID
        """
        if user_id not in self.profiles:
            return

        if node_id1 in self.profiles[user_id].knowledge_graph:
            if node_id2 not in self.profiles[user_id].knowledge_graph[node_id1].connections:
                self.profiles[user_id].knowledge_graph[node_id1].connections.append(node_id2)

        if node_id2 in self.profiles[user_id].knowledge_graph:
            if node_id1 not in self.profiles[user_id].knowledge_graph[node_id2].connections:
                self.profiles[user_id].knowledge_graph[node_id2].connections.append(node_id1)

        self._save_profiles()
        logger.info(f"Connect knowledge nodes: {user_id}, {node_id1} <-> {node_id2}")

    def increment_interaction(self, user_id: str):
        """
        增加交互计数

        Args:
            user_id: 用户ID
        """
        if user_id not in self.profiles:
            self.create_profile(user_id)

        self.profiles[user_id].interaction_count += 1
        self.profiles[user_id].last_active = datetime.now().timestamp()
        self._save_profiles()

    def extract_preferences_from_interactions(self, user_id: str, interactions: List[Dict[str, Any]]):
        """
        From交互历史中提取用户偏好

        Args:
            user_id: 用户ID
            interactions: 交互历史列表
        """
        preference_keywords = {
            "language": ["python", "javascript", "java", "go", "rust", "c++", "typescript"],
            "topic": ["ai", "machine learning", "web", "mobile", "backend", "frontend", "devops"],
            "style": ["concise", "detailed", "technical", "simple", "beginner"]
        }

        for interaction in interactions:
            content = interaction.get("content", "").lower()
            response = interaction.get("response", "").lower()

            for category, keywords in preference_keywords.items():
                for keyword in keywords:
                    if keyword in content or keyword in response:
                        self.update_preference(user_id, category, keyword, confidence=0.8)

    def analyze_behavior_patterns(self, user_id: str, interactions: List[Dict[str, Any]]):
        """
        分析用户行为模式

        Args:
            user_id: 用户ID
            interactions: 交互历史列表
        """
        task_keywords = {
            "coding": ["写代码", "代码", "program", "function", "class", "implement"],
            "debugging": ["debug", "Error", "bug", "修复", "问题", "issue"],
            "learning": ["学习", "教程", "teach", "explain", "understand", "概念"],
            "planning": ["规划", "计划", "design", "architecture", "方案"]
        }

        task_counts = {k: 0 for k in task_keywords.keys()}

        for interaction in interactions:
            content = interaction.get("content", "").lower()
            for task_type, keywords in task_keywords.items():
                if any(kw in content for kw in keywords):
                    task_counts[task_type] += 1

        dominant_task = max(task_counts, key=task_counts.get)
        if task_counts[dominant_task] > 0:
            self.update_behavior_pattern(
                user_id,
                "dominant_task",
                f"主要Tasktype: {dominant_task} ({task_counts[dominant_task]}次)"
            )

        if len(interactions) > 10:
            self.update_behavior_pattern(
                user_id,
                "engagement_level",
                f"高活跃度用户 (Total{len(interactions)}次交互)"
            )

    def build_profile(self, user_id: str, interactions: Optional[List[Dict[str, Any]]] = None) -> UserProfile:
        """
        构建完整user profiles

        Args:
            user_id: 用户ID
            interactions: 交互历史列表

        Returns:
            user profiles
        """
        if user_id not in self.profiles:
            self.create_profile(user_id)

        if interactions:
            self.extract_preferences_from_interactions(user_id, interactions)
            self.analyze_behavior_patterns(user_id, interactions)

        self.increment_interaction(user_id)
        return self.profiles[user_id]

    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get用户摘要

        Args:
            user_id: 用户ID

        Returns:
            用户摘要
        """
        profile = self.get_profile(user_id)
        if not profile:
            return {"error": "user profilesdoes not exist"}

        return {
            "user_id": profile.user_id,
            "interaction_count": profile.interaction_count,
            "last_active": datetime.fromtimestamp(profile.last_active).isoformat(),
            "preference_count": len(profile.preferences),
            "behavior_pattern_count": len(profile.behavior_patterns),
            "knowledge_node_count": len(profile.knowledge_graph),
            "top_preferences": [
                {"category": p.category, "value": p.value, "confidence": p.confidence}
                for p in list(profile.preferences.values())[:5]
            ],
            "dominant_behavior": [
                {"type": b.pattern_type, "description": b.description}
                for b in list(profile.behavior_patterns.values())[:3]
            ]
        }

    def recall_relevant_info(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        召回与查询相关的用户信息

        Args:
            user_id: 用户ID
            query: 查询字符串

        Returns:
            召回的信息
        """
        profile = self.get_profile(user_id)
        if not profile:
            return {"relevant_preferences": [], "relevant_knowledge": []}

        query_lower = query.lower()
        relevant_preferences = []
        relevant_knowledge = []

        for pref in profile.preferences.values():
            if pref.category.lower() in query_lower or str(pref.value).lower() in query_lower:
                relevant_preferences.append({
                    "category": pref.category,
                    "value": pref.value,
                    "confidence": pref.confidence
                })

        for node in profile.knowledge_graph.values():
            if (query_lower in node.label.lower() or
                query_lower in str(node.properties).lower()):
                relevant_knowledge.append({
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type,
                    "properties": node.properties
                })

        return {
            "relevant_preferences": relevant_preferences,
            "relevant_knowledge": relevant_knowledge,
            "interaction_count": profile.interaction_count
        }


# 全局User profile service实例
_user_profile_service = None


def get_user_profile_service() -> UserProfileService:
    """
    GetUser profile service实例

    Returns:
        User profile service实例
    """
    global _user_profile_service
    if _user_profile_service is None:
        _user_profile_service = UserProfileService()
    return _user_profile_service