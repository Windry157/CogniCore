#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama LLM服务实现
"""

import httpx
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
import logging

from .llm_service import LLMService
from src.core.utils.retry import async_retry_with_backoff, retry_with_backoff
from src.core.config import config
from src.core.cache import cache_result

logger = logging.getLogger(__name__)


class OllamaService(LLMService):
    """Ollama LLM服务实现"""
    
    def __init__(self, base_url: Optional[str] = None, 
                 model: Optional[str] = None,
                 timeout: Optional[int] = None):
        """
        InitializationOllama服务
        
        Args:
            base_url: Ollama服务地址
            model: ModelName
            timeout: 超时时间 (s) 
        """
        self.base_url = base_url or config.llm.ollama_base_url
        self.model = model or config.llm.ollama_model
        self.timeout = timeout or config.llm.ollama_timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout
        )
        self.sync_client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        logger.info(f"Ollama service initialized, model: {self.model}")
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Ollama chat request failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    @cache_result(expire=3600, cache_key="ollama_chat")
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        聊天接口
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            ModelResponse
        """
        response = self.sync_client.post(
            "/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        return data.get("message", {}).get("content", "")
    
    @async_retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Ollama chat request failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    async def async_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        异步聊天接口
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            ModelResponse
        """
        response = await self.client.post(
            "/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        return data.get("message", {}).get("content", "")

    async def chat_completion(self, messages: List[Dict]) -> Any:
        content = await self.async_chat(messages)
        from types import SimpleNamespace
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=content)
            )]
        )

    async def stream_chat(self, messages: List[Dict], tools: Optional[List] = None, model: Optional[str] = None) -> AsyncGenerator[Dict, None]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            async with client.stream(
                "POST", "/api/chat",
                json={"model": model or self.model, "messages": messages, "tools": tools, "stream": True}
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("message", {}).get("content", "")
                    yield {"choices": [{"delta": {"content": delta}}]}
                    if data.get("done"):
                        return

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Ollama generate request  failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    @cache_result(expire=3600, cache_key="ollama_generate")
    def generate(self, prompt: str, **kwargs) -> str:
        """
        文本生成接口
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        response = self.sync_client.post(
            "/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        return data.get("response", "")
    
    @async_retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Ollama generate request  failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    async def async_generate(self, prompt: str, **kwargs) -> str:
        """
        异步文本生成接口
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数
            
        Returns:
            生成的文本
        """
        response = await self.client.post(
            "/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        return data.get("response", "")
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Ollama embed request  failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    def embed(self, text: str, **kwargs) -> List[float]:
        """
        文本嵌入接口
        
        Args:
            text: 要嵌入的文本
            **kwargs: 额外参数
            
        Returns:
            embeddings向量
        """
        response = self.sync_client.post(
            "/api/embed",
            json={
                "model": self.model,
                "input": text,  # 使用input字段而不是prompt
                **kwargs
            }
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        # 检查Response格式, 支持embeddings数groups或embedding字段
        if "embeddings" in data and data["embeddings"]:
            return data["embeddings"][0]  # 返回Round 一 embeddings向量
        return data.get("embedding", [])
    
    @async_retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Ollama embed request  failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    async def async_embed(self, text: str, **kwargs) -> List[float]:
        """
        异步文本嵌入接口
        
        Args:
            text: 要嵌入的文本
            **kwargs: 额外参数
            
        Returns:
            embeddings向量
        """
        response = await self.client.post(
            "/api/embed",
            json={
                "model": self.model,
                "prompt": text,
                **kwargs
            }
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        # 检查Response格式, 支持embeddings数groups或embedding字段
        if "embeddings" in data and data["embeddings"]:
            return data["embeddings"][0]  # 返回Round 一 embeddings向量
        return data.get("embedding", [])
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Get model info failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model info
        
        Returns:
            Model信息
        """
        response = self.sync_client.get("/api/tags")
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        models = data.get("models", [])
        for model in models:
            if model.get("name") == self.model:
                return model
        return {"name": self.model, "status": "unknown"}
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Get model list failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List可用Model (同步) 
        
        Returns:
            Model列表
        """
        response = self.sync_client.get("/api/tags")
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        return data.get("models", [])

    async def async_list_models(self) -> List[Dict[str, Any]]:
        """
        List可用Model (异步) 
        
        Returns:
            Model列表
        """
        response = await self.client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Model pull failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    def pull_model(self, model: str) -> bool:
        """
        拉取Model
        
        Args:
            model: ModelName
            
        Returns:
            是否 successful
        """
        response = self.sync_client.post(
            "/api/pull",
            json={"name": model},
            timeout=600  # 拉取Model可能需要较长时间
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        logger.info(f"Model {model} pull successful")
        return True
    
    def close(self):
        """
        Close服务
        """
        try:
            if hasattr(self.sync_client, 'close'):
                self.sync_client.close()
            # AsyncClient不需要手动Close
            logger.info("Ollamaservice closed")
        except Exception as e:
            logger.error(f"Close Ollama serviceexception: {e}")
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"TestConnect failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
    def test_connection(self) -> bool:
        """
        TestConnect
        
        Returns:
            是否Connect successful
        """
        response = self.sync_client.get("/api/tags", timeout=5)
        response.raise_for_status()  # 自动抛出HTTPError
        return True
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_exceptions=(httpx.RequestError, httpx.HTTPStatusError),
        on_retry=lambda retry, e, delay: logger.warning(f"Ollama tool call request  failed, {delay:.2f}s retry ({retry}/3): {e}")
    )
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
        response = self.sync_client.post(
            "/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "stream": False,
                **kwargs
            }
        )
        
        response.raise_for_status()  # 自动抛出HTTPError
        data = response.json()
        return data
    
    def execute_tool_call(self, tool_call: Dict[str, Any], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行Tool调用
        
        Args:
            tool_call: Tool调用信息
            tools: Tool列表
            
        Returns:
            Tool execution result
        """
        try:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})
            
            # 查找对应的Tool
            from src.core.tools.registry import get_tool_registry
            registry = get_tool_registry()
            tool_info = registry.get_tool(tool_name)
            
            if not tool_info:
                return {
                    "status": "error",
                    "message": f"Tool not found: {tool_name}"
                }
            
            # 执行Tool
            result = tool_info["func"](**tool_args)
            
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.error(f"Tool call execution failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }