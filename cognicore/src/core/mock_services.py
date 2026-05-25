#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from typing import Dict, Any, AsyncGenerator, List

# 避免循环导入, 直接定义基类
class BaseLLM:
    async def stream_chat(self, messages, tools=None):
        pass

class BaseBayesianEngine:
    async def infer(self, evidence):
        pass

class BaseKnowledgeGraph:
    async def query(self, query):
        pass

import logging
logger = logging.getLogger(__name__)

class MockLLM(BaseLLM):
    """模拟 LLM 服务"""
    def __init__(self, config: Dict[str, Any]):
        logger.info(f"MockLLM initialized, config: {config}")
        self.config = config
        self.model_name = config.get("model", "mock-gpt-4")
        logger.info(f"MockLLM initialization complete, model_name: {self.model_name}")
    
    async def chat(self, message: str, context: Dict[str, Any] = None) -> str:
        logger.info(f"MockLLM chat  called, message: {message}")
        await asyncio.sleep(0.8)
        response = f"[{self.model_name}] Simulated response: {message}"
        logger.info(f"MockLLM chat  response: {response}")
        return response
    
    async def stream_chat(self, messages: List[Dict[str, Any]], tools: List[Dict] = None, model: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """模拟流式输出"""
        logger.info(f"MockLLM stream_chat  called, messages: {messages}")
        logger.info(f"MockLLM stream_chat  called, tools: {tools}")
        logger.info(f"MockLLM stream_chat  called, model: {model}")
        
        # 检查是否需要Tool调用
        user_message = messages[-1].get("content", "")
        logger.info(f"MockLLM stream_chat  called, user_message: {user_message}")
        
        # 检查是否包含图片
        has_image = False
        if isinstance(user_message, list):
            for item in user_message:
                if item.get("type") == "image":
                    has_image = True
                    break
        
        # 模拟Tool调用场景
        if any(keyword in str(user_message).lower() for keyword in ["打开", "百度", "时间", "计算器"]):
            # 模拟Tool调用
            logger.info("MockLLM simulated tool call")
            tool_call = {
                "type": "tool_call",
                "index": 0,
                "id": "mock-tool-id-123",
                "function": {
                    "name": "system_control",
                    "arguments": '{"action": "open_url", "target": "www.baidu.com"}'
                }
            }
            logger.info(f"MockLLM generated tool call: {tool_call}")
            yield tool_call
        elif has_image:
            # 图片相关 response
            logger.info("MockLLM Simulating image response")
            full_msg = f"[{self.model_name}] 我看到你上传了一张图片.虽然我是模拟服务, 无法真正分析图片Content, 但在实际使用中, 我可以帮你Description图片, 识别物体, 分析场景等."
            logger.info(f"MockLLM Simulating image responseContent: {full_msg}")
            for char in full_msg:
                yield {"type": "content", "content": char}
                await asyncio.sleep(0.05) # 模拟打字机效果
        else:
            # 普通文本 response
            logger.info("MockLLM Simulating regular text response")
            full_msg = f"[{self.model_name}] Simulated response: {user_message}"
            logger.info(f"MockLLM Simulated responseContent: {full_msg}")
            for char in full_msg:
                yield {"type": "content", "content": char}
                await asyncio.sleep(0.05) # 模拟打字机效果
    
    async def generate(self, prompt: str) -> str:
        """generate text """
        logger.info(f"MockLLM generate  called, prompt: {prompt}")
        await asyncio.sleep(1)
        
        # 检查是否需要Save memories
        if "记住" in prompt:
            logger.info("Memory save needed")
            return '''[
    {"step": 1, "thought": "需要将用户的信息Save到 memories中", "tool": "save_knowledge", "args": {"content": "项目架构师的名字叫 'Neo', 他最喜欢的电影是《黑客帝国》"}}
]'''
        # 检查是否需要检索 memories
        elif "叫什么名字" in prompt or "喜欢什么电影" in prompt:
            logger.info("Memory retrieval needed")
            return '''[
    {"step": 1, "thought": "需要From memories中检索用户的信息", "tool": "search_knowledge", "args": {"query": "项目架构师 名字 电影"}}
]'''
        # Default response
        else:
            logger.info("Default response")
            return '''[
    {"step": 1, "thought": "Processing用户请求", "tool": "network_diagnostic", "args": {}}
]''' 
    
    async def shutdown(self): pass

class MockBayesianEngine(BaseBayesianEngine):
    def __init__(self, config): pass
    async def infer(self, evidence): return {}
    async def shutdown(self): pass

class MockKnowledgeGraph(BaseKnowledgeGraph):
    def __init__(self, config): pass
    async def query(self, query): return {}
    async def shutdown(self): pass