#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强Skill系统
支持Skill的Create, 优化和跨会话持久化
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path

from src.core.config import config, _get_project_root
from src.core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class SkillStatus(Enum):
    """SkillStatus"""
    ACTIVE = "active"  # 活跃
    INACTIVE = "inactive"  # 未激活
    LEARNING = "learning"  # 学习中
    OPTIMIZING = "optimizing"  # 优化中
    DEPRECATED = "deprecated"  # already废弃


class SkillCategory(Enum):
    """Skill类别"""
    CODING = "coding"  # 编程
    ANALYSIS = "analysis"  # 分析
    CREATION = "creation"  # 创作
    RESEARCH = "research"  # 研究
    PLANNING = "planning"  # 规划
    COMMUNICATION = "communication"  # 沟通
    AUTOMATION = "automation"  # 自动化
    CUSTOM = "custom"  # 自定义


@dataclass
class SkillVersion:
    """Skill版本"""
    version: str
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    description: str = ""
    performance_score: float = 0.0  # 性能评分
    usage_count: int = 0


@dataclass
class Skill:
    """Skill定义"""
    id: str
    name: str
    description: str
    category: str  # SkillCategory
    status: str = SkillStatus.ACTIVE.value
    prompts: List[str] = field(default_factory=list)  # Skill提示词
    tools: List[str] = field(default_factory=list)  # 关联的Tool
    examples: List[Dict[str, str]] = field(default_factory=list)  # 示例
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加信息
    performance_history: List[SkillVersion] = field(default_factory=list)  # 性能历史
    current_version: str = "1.0.0"
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    tags: Set[str] = field(default_factory=set)  # Skill标签

    def get_success_rate(self) -> float:
        """Get successful率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    def get_performance_score(self) -> float:
        """Get性能评分"""
        return self.get_success_rate() * 0.7 + min(self.usage_count / 100, 1.0) * 0.3

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "prompts": self.prompts,
            "tools": self.tools,
            "examples": self.examples,
            "metadata": self.metadata,
            "performance_history": [
                {
                    "version": v.version,
                    "created_at": v.created_at,
                    "description": v.description,
                    "performance_score": v.performance_score,
                    "usage_count": v.usage_count
                }
                for v in self.performance_history
            ],
            "current_version": self.current_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.get_success_rate(),
            "performance_score": self.get_performance_score(),
            "tags": list(self.tags)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """From字典Create"""
        skill = cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            status=data.get("status", SkillStatus.ACTIVE.value),
            prompts=data.get("prompts", []),
            tools=data.get("tools", []),
            examples=data.get("examples", []),
            metadata=data.get("metadata", {}),
            current_version=data.get("current_version", "1.0.0"),
            created_at=data.get("created_at", datetime.now().timestamp()),
            updated_at=data.get("updated_at", datetime.now().timestamp()),
            usage_count=data.get("usage_count", 0),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            tags=set(data.get("tags", []))
        )

        for v_data in data.get("performance_history", []):
            skill.performance_history.append(SkillVersion(
                version=v_data["version"],
                created_at=v_data.get("created_at", datetime.now().timestamp()),
                description=v_data.get("description", ""),
                performance_score=v_data.get("performance_score", 0.0),
                usage_count=v_data.get("usage_count", 0)
            ))

        return skill


class SkillOptimizer:
    """Skill优化器"""

    def __init__(self, llm_service=None):
        """
        InitializationSkill优化器

        Args:
            llm_service: LLM服务实例
        """
        self.llm_service = llm_service

    def analyze_skill_performance(self, skill: Skill) -> Dict[str, Any]:
        """
        分析Skill性能

        Args:
            skill: Skill对象

        Returns:
            性能分析
        """
        suggestions = []

        if skill.usage_count == 0:
            suggestions.append("该SkillFrom未被使用, 建议推广或考虑废弃")
        elif skill.get_success_rate() < 0.5:
            suggestions.append(" successful率较低, 建议优化提示词或Add更多示例")
        elif skill.usage_count > 50 and skill.get_success_rate() > 0.8:
            suggestions.append("该Skill表现良好, 可以考虑扩展应用场景")

        if not skill.examples:
            suggestions.append("缺少示例, 建议Add一些 successful案例作为参考")

        if len(skill.prompts) < 2:
            suggestions.append("提示词较少, 建议Add更多变体以提高泛化能力")

        return {
            "skill_id": skill.id,
            "skill_name": skill.name,
            "usage_count": skill.usage_count,
            "success_count": skill.success_count,
            "failure_count": skill.failure_count,
            "success_rate": skill.get_success_rate(),
            "performance_score": skill.get_performance_score(),
            "suggestions": suggestions
        }

    def generate_optimization_prompt(self, skill: Skill, feedback: Optional[str] = None) -> str:
        """
        生成Skill优化提示词

        Args:
            skill: Skill对象
            feedback: 用户反馈

        Returns:
            优化提示词
        """
        prompt = f"""你是一 skills优化专家.请根据以下信息优化Skill: 

SkillName: {skill.name}
SkillDescription: {skill.description}
类别: {skill.category}

当前性能:
- 使用次数: {skill.usage_count}
-  successful率: {skill.get_success_rate():.2%}
- 性能评分: {skill.get_performance_score():.2f}

当前提示词:
{chr(10).join(skill.prompts)}

当前示例:"""

        for i, example in enumerate(skill.examples[:3], 1):
            prompt += f"\n示例{i}: 输入={example.get('input', '')}, 输出={example.get('output', '')}"

        if feedback:
            prompt += f"\n\n用户反馈:\n{feedback}"

        prompt += """

请提供优化建议, 包括: 
1. 提示词优化建议
2. 新增示例建议
3. 可能的Tool扩展
"""

        return prompt

    async def optimize_skill(self, skill: Skill, feedback: Optional[str] = None) -> Dict[str, Any]:
        """
        优化Skill

        Args:
            skill: Skill对象
            feedback: 用户反馈

        Returns:
            优化
        """
        if not self.llm_service:
            return {
                "status": "skipped",
                "message": "没有LLM服务, skip优化"
            }

        try:
            optimization_prompt = self.generate_optimization_prompt(skill, feedback)
            response = self.llm_service.generate(optimization_prompt)

            return {
                "status": "success",
                "optimization_suggestions": response,
                "skill_id": skill.id
            }
        except Exception as e:
            logger.error(f"Skill optimization failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


class SkillManager:
    """Skill manager"""

    def __init__(self, skill_dir: str = None):
        """
        InitializationSkill manager

        Args:
            skill_dir: Skill存储目录
        """
        self.skill_dir = skill_dir or _get_project_root() / config.system.data_dir / "skills"
        self.skill_dir.mkdir(parents=True, exist_ok=True)
        self.skill_file = self.skill_dir / "skills.json"
        self.skills = self._load_skills()
        self.optimizer = SkillOptimizer()
        self._initialize_default_skills()

        logger.info(f"Skill manager initialization complete, loaded {len(self.skills)} skills")

    def _load_skills(self) -> Dict[str, Skill]:
        """LoadSkill"""
        if not self.skill_file.exists():
            return {}

        try:
            with open(self.skill_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                skills = {}
                for skill_id, skill_data in data.items():
                    skills[skill_id] = Skill.from_dict(skill_data)
                return skills
        except Exception as e:
            logger.error(f"Failed to load skill: {e}")
            return {}

    def _save_skills(self):
        """SaveSkill"""
        try:
            data = {}
            for skill_id, skill in self.skills.items():
                data[skill_id] = skill.to_dict()

            with open(self.skill_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save skill: {e}")

    def _initialize_default_skills(self):
        """Initializationdefault skills"""
        if self.skills:
            return

        default_skills = [
            {
                "id": "skill_coding",
                "name": "代码编写",
                "description": "帮助用户编写各种编程语言的代码",
                "category": SkillCategory.CODING.value,
                "prompts": [
                    "请用{language}编写一 {description}的程序",
                    "帮我实现{requirement}功能"
                ],
                "tools": ["code_executor", "file_writer"],
                "examples": [
                    {"input": "用Python写一 快速排序", "output": "def quick_sort..."},
                    {"input": "用JavaScript实现一 Promise", "output": "class MyPromise..."}
                ],
                "tags": {"python", "javascript", "code", "programming"}
            },
            {
                "id": "skill_debug",
                "name": "代码调试",
                "description": "帮助用户定位和修复代码中的Error",
                "category": SkillCategory.CODING.value,
                "prompts": [
                    "帮我debug这 代码: {code}",
                    "这段代码有什么问题?"
                ],
                "tools": ["code_executor", "error_analyzer"],
                "examples": [
                    {"input": "代码报错IndexError", "output": "索引越界, 应该检查数groupsLength"}
                ],
                "tags": {"debug", "error", "fix", "bug"}
            },
            {
                "id": "skill_analysis",
                "name": "数据分析",
                "description": "帮助用户analyzing data并生成报告",
                "category": SkillCategory.ANALYSIS.value,
                "prompts": [
                    "分析这 数据集: {data}",
                    "帮我生成数据报告"
                ],
                "tools": ["data_analyzer", "chart_generator"],
                "examples": [],
                "tags": {"data", "analysis", "report", "chart"}
            },
            {
                "id": "skill_planning",
                "name": "Task规划",
                "description": "帮助用户分解复杂Task并制定执行计划",
                "category": SkillCategory.PLANNING.value,
                "prompts": [
                    "帮我规划{goal}Task",
                    "如何 complete这 复杂Task?"
                ],
                "tools": ["task_planner", "task_executor"],
                "examples": [],
                "tags": {"planning", "task", "goal", "milestone"}
            }
        ]

        for skill_data in default_skills:
            skill = Skill(
                id=skill_data["id"],
                name=skill_data["name"],
                description=skill_data["description"],
                category=skill_data["category"],
                prompts=skill_data["prompts"],
                tools=skill_data["tools"],
                examples=skill_data["examples"],
                tags=set(skill_data["tags"])
            )
            self.skills[skill.id] = skill

        self._save_skills()
        logger.info(f"Initialized {len(default_skills)}  default skills")

    def create_skill(self, name: str, description: str, category: str,
                    prompts: Optional[List[str]] = None,
                    tools: Optional[List[str]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Skill:
        """
        Creating new skill

        Args:
            name: SkillName
            description: SkillDescription
            category: Skill类别
            prompts: 提示词列表
            tools: Tool列表
            metadata: 附加信息

        Returns:
            Create的Skill
        """
        skill_id = f"skill_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"

        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            category=category,
            prompts=prompts or [],
            tools=tools or [],
            metadata=metadata or {}
        )

        self.skills[skill_id] = skill
        self._save_skills()
        logger.info(f"Creating new skill: {skill_id}")
        return skill

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """
        GetSkill

        Args:
            skill_id: SkillID

        Returns:
            Skill对象
        """
        return self.skills.get(skill_id)

    def update_skill(self, skill_id: str, **kwargs) -> bool:
        """
        Updating skill

        Args:
            skill_id: SkillID
            **kwargs: 要Update的字段

        Returns:
            是否Update successful
        """
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]
        for key, value in kwargs.items():
            if hasattr(skill, key):
                setattr(skill, key, value)

        skill.updated_at = datetime.now().timestamp()
        self._save_skills()
        logger.info(f"Updating skill: {skill_id}")
        return True

    def delete_skill(self, skill_id: str) -> bool:
        """
        DeleteSkill

        Args:
            skill_id: SkillID

        Returns:
            是否Delete successful
        """
        if skill_id not in self.skills:
            return False

        self.skills[skill_id].status = SkillStatus.DEPRECATED.value
        self._save_skills()
        logger.info(f"Marking skill as deprecated: {skill_id}")
        return True

    def record_skill_usage(self, skill_id: str, success: bool):
        """
        记录Skill使用

        Args:
            skill_id: SkillID
            success: 是否 successful
        """
        if skill_id not in self.skills:
            return

        skill = self.skills[skill_id]
        skill.usage_count += 1
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1

        skill.updated_at = datetime.now().timestamp()
        self._save_skills()

    def search_skills(self, query: str, category: Optional[str] = None,
                     tags: Optional[Set[str]] = None) -> List[Skill]:
        """
        SearchSkill

        Args:
            query: Search查询
            category: Skill类别
            tags: Skill标签

        Returns:
            匹配的Skill列表
        """
        results = []
        query_lower = query.lower()

        for skill in self.skills.values():
            if skill.status == SkillStatus.DEPRECATED.value:
                continue

            if category and skill.category != category:
                continue

            if tags and not skill.tags.intersection(tags):
                continue

            if (query_lower in skill.name.lower() or
                query_lower in skill.description.lower() or
                any(query_lower in p.lower() for p in skill.prompts) or
                query_lower in list(skill.tags)):
                results.append(skill)

        return sorted(results, key=lambda s: s.get_performance_score(), reverse=True)

    def get_skills_by_category(self, category: str) -> List[Skill]:
        """
        按类别GetSkill

        Args:
            category: Skill类别

        Returns:
            Skill列表
        """
        return [s for s in self.skills.values()
                if s.category == category and s.status != SkillStatus.DEPRECATED.value]

    def get_all_skills(self, include_deprecated: bool = False) -> List[Skill]:
        """
        Get所有Skill

        Args:
            include_deprecated: 是否包含already废弃的Skill

        Returns:
            Skill列表
        """
        if include_deprecated:
            return list(self.skills.values())
        return [s for s in self.skills.values()
                if s.status != SkillStatus.DEPRECATED.value]

    def get_skill_stats(self) -> Dict[str, Any]:
        """
        GetSkillStatistics

        Returns:
            Statistics
        """
        skills = self.get_all_skills()
        total_usage = sum(s.usage_count for s in skills)
        total_success = sum(s.success_count for s in skills)
        total_failure = sum(s.failure_count for s in skills)

        category_stats = {}
        for skill in skills:
            if skill.category not in category_stats:
                category_stats[skill.category] = {
                    "count": 0,
                    "total_usage": 0,
                    "total_success": 0
                }
            category_stats[skill.category]["count"] += 1
            category_stats[skill.category]["total_usage"] += skill.usage_count
            category_stats[skill.category]["total_success"] += skill.success_count

        return {
            "total_skills": len(skills),
            "total_usage": total_usage,
            "total_success": total_success,
            "total_failure": total_failure,
            "overall_success_rate": total_success / (total_success + total_failure) if (total_success + total_failure) > 0 else 0,
            "category_stats": category_stats
        }

    def export_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        导出Skill

        Args:
            skill_id: SkillID

        Returns:
            Skill数据
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return None

        return skill.to_dict()

    def import_skill(self, skill_data: Dict[str, Any]) -> bool:
        """
        Importing skill

        Args:
            skill_data: Skill数据

        Returns:
            是否导入 successful
        """
        try:
            skill = Skill.from_dict(skill_data)
            skill.id = f"{skill.id}_imported_{int(datetime.now().timestamp())}"
            self.skills[skill.id] = skill
            self._save_skills()
            logger.info(f"Importing skill: {skill.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to import skill: {e}")
            return False


# 全局Skill manager实例
_skill_manager_instance = None


def get_skill_manager() -> SkillManager:
    """
    GetSkill manager实例

    Returns:
        Skill manager实例
    """
    global _skill_manager_instance
    if _skill_manager_instance is None:
        _skill_manager_instance = SkillManager()
    return _skill_manager_instance


def reset_skill_manager() -> SkillManager:
    """
    重置Skill manager实例

    Returns:
        新的Skill manager实例
    """
    global _skill_manager_instance
    _skill_manager_instance = SkillManager()
    return _skill_manager_instance