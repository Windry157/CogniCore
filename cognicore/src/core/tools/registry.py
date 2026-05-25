#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToolRegistry
动态管理所有可用Tool
"""
import inspect
import functools
from typing import Dict, Any, Callable, List, Optional


class ToolRegistry:
    """ToolRegistry单例"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def register(self, name: str, func: Callable, description: str = None, parameters: Dict[str, Any] = None):
        """
        RegisterTool
        
        Args:
            name: ToolName
            func: Tool函数
            description: ToolDescription
            parameters: Tool参数
        """
        if description is None:
            description = self._extract_description(func)
        
        if parameters is None:
            parameters = self._extract_parameters(func)
        
        self._tools[name] = {
            "name": name,
            "func": func,
            "description": description,
            "parameters": parameters
        }
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """
        GetTool
        
        Args:
            name: ToolName
            
        Returns:
            Tool信息
        """
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get所有Tool
        
        Returns:
            所有Tool信息
        """
        return self._tools
    
    def get_tools_description(self) -> List[Dict[str, Any]]:
        """
        Get所有Tool的Description
        
        Returns:
            ToolDescription列表
        """
        tools = []
        for name, tool in self._tools.items():
            tools.append({
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            })
        return tools
    
    def _extract_description(self, func: Callable) -> str:
        """
        From函数文档字符串提取Description
        
        Args:
            func: Tool函数
            
        Returns:
            ToolDescription
        """
        if func.__doc__:
            # 提取文档字符串的Round 一部分
            lines = func.__doc__.strip().split('\n')
            description = lines[0].strip()
            return description
        return "No description"
    
    def _extract_parameters(self, func: Callable) -> Dict[str, Any]:
        """
        From函数签名提取参数
        
        Args:
            func: Tool函数
            
        Returns:
            参数信息
        """
        parameters = {
            "type": "object",
            "properties": {}
        }
        
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name != "self":
                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    # 简单的type映射
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == list:
                        param_type = "array"
                    elif param.annotation == dict:
                        param_type = "object"
                
                parameters["properties"][param_name] = {
                    "type": param_type,
                    "description": self._extract_param_description(func, param_name)
                }
        
        # 提取必填参数
        required = []
        for param_name, param in sig.parameters.items():
            if param_name != "self" and param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        if required:
            parameters["required"] = required
        
        return parameters
    
    def _extract_param_description(self, func: Callable, param_name: str) -> str:
        """
        From函数文档字符串提取参数Description
        
        Args:
            func: Tool函数
            param_name: 参数Name
            
        Returns:
            参数Description
        """
        if func.__doc__:
            # 查找 Args 部分
            lines = func.__doc__.strip().split('\n')
            in_args = False
            for line in lines:
                line = line.strip()
                if line.startswith("Args:"):
                    in_args = True
                elif in_args:
                    if line.startswith(param_name + ":"):
                        return line.split(":", 1)[1].strip()
                    elif line and not line.startswith(" "):
                        # 退出 Args 部分
                        break
        return f"{param_name} parameter"


# 全局ToolRegistry实例
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """
    GetToolRegistry实例
    
    Returns:
        ToolRegistry: ToolRegistry实例
    """
    return tool_registry


def register_tool(name: str = None, description: str = None, parameters: Dict[str, Any] = None):
    """
    ToolRegister装饰器
    
    Args:
        name: ToolName
        description: ToolDescription
        parameters: Tool参数
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name if name else func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # RegisterTool
        tool_registry.register(tool_name, func, description, parameters)
        return wrapper
    
    return decorator
