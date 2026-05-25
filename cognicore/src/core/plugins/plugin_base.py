#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件基类
所有插件都需要继承这 基类
"""
from typing import Dict, Any, Optional

class BasePlugin:
    """插件基类"""
    
    # 插件Name (必须唯一) 
    name: str = "base_plugin"
    
    # 插件Description
    description: str = "基础插件"
    
    # 插件版本
    version: str = "1.0.0"
    
    # 插件作者
    author: str = "Unknown"
    
    # 插件依赖
    dependencies: list = []
    
    def __init__(self):
        """Initializing plugin"""
        pass
    
    async def initialize(self, config: Dict[str, Any] = None):
        """
        Initializing plugin
        
        Args:
            config: 插件配置
        """
        pass
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute plugin operation
        
        Args:
            action: 操作Name
            params: 操作参数
            
        Returns:
            执行
        """
        return {
            "status": "error",
            "message": f"插件 {self.name} 未实现 execute 方法"
        }
    
    def get_actions(self) -> Dict[str, str]:
        """
        Get plugin支持的操作列表
        
        Returns:
            操作Name到操作Description的映射
        """
        return {
            "help": "显示插件帮助信息"
        }
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Gettool definition (用于 LLM Tool调用) 
        
        Returns:
            tool definition
        """
        actions = self.get_actions()
        parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": f"操作Name, 支持: {', '.join(actions.keys())}",
                    "enum": list(actions.keys())
                }
            },
            "required": ["action"]
        }
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters
            }
        }
    
    async def shutdown(self):
        """
        Closing plugin
        """
        pass
