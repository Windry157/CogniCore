#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM服务接口
提供统一的LLM服务接口, 支持多种LLM服务
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class LLMService(ABC):
    """LLM服务接口"""
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        聊天接口
        
        Args:
            messages: 消息列表, 格式为 [{"role": "system", "content": "..."}, ...]
            **kwargs: 额外参数
            
        Returns:
            ModelResponse
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        文本生成接口
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        pass
    
    @abstractmethod
    def embed(self, text: str, **kwargs) -> List[float]:
        """
        文本嵌入接口
        
        Args:
            text: 要嵌入的文本
            **kwargs: 额外参数
            
        Returns:
            embeddings向量
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model info
        
        Returns:
            Model信息
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        Close服务
        """
        pass
    
    def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        带Tool调用的聊天接口
        
        Args:
            messages: 消息列表
            tools: Tool列表
            **kwargs: 额外参数
            
        Returns:
            ModelResponse, 包含Tool调用信息
        """
        raise NotImplementedError("子类必须实现chat_with_tools方法")
    
    def execute_tool_call(self, tool_call: Dict[str, Any], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行Tool调用
        
        Args:
            tool_call: Tool调用信息
            tools: Tool列表
            
        Returns:
            Tool execution result
        """
        raise NotImplementedError("子类必须实现execute_tool_call方法")