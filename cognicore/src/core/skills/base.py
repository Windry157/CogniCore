#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseSkill(ABC):
    """Skill基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Skill的唯一标识符 (例如: system_control)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """SkillDescription, 用于告诉 LLM 这 skills是干什么的"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """参数Description (JSON Schema 格式), 告诉 LLM 需要传什么参数"""
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体的动作"""
        pass