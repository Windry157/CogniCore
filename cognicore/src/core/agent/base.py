#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent基础 module
定义Agent的基本结构和角色档案
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class AgentProfile:
    """Agent角色档案"""
    name: str
    role: str
    description: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)  # 该角色允许使用的Tool列表
    
    def to_dict(self) -> dict:
        """
        转换为字典
        
        返回:
            角色档案字典
        """
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tools": self.tools
        }
