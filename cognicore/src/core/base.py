#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础类定义
"""

from typing import Dict, Any, List, Optional, AsyncGenerator


class BaseLLM:
    """LLM 基类"""
    async def stream_chat(self, messages: List[Dict], tools: Optional[List] = None, model: Optional[str] = None):
        raise NotImplementedError
    
    async def chat_completion(self, messages: List[Dict]):
        raise NotImplementedError
