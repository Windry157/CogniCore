#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
from typing import Dict, Any, AsyncGenerator, List, Optional
from ..base import BaseLLM

logger = logging.getLogger(__name__)

class OpenAILLM(BaseLLM):
    """
    基于 OpenAI 接口的通用 LLM 服务
    支持 Native Function Calling
    """
    def __init__(self, config: Dict[str, Any]):
        # 延迟导入, 只有在Initialization时才导入 OpenAI  module
        try:
            from openai import AsyncOpenAI, APIError
        except Exception as e:
            logging.error(f"OpenAI module import failed: {e}")
            raise Exception("OpenAI module import failed, 无法Initialization OpenAILLM")
        
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            timeout=30.0,  # 减少超时时间, 快速 failed
            max_retries=2,  # Add重试机制
            http_client=None  # 使用默认的异步HTTP客户端
        )
        self.model = config.get("model", "gpt-3.5-turbo")
        self.temperature = config.get("temperature", 0.7)
        self.top_p = config.get("top_p", 0.9)
        self.max_tokens = config.get("max_tokens", 1024)
        
        # 请求cache
        self._request_cache = {}  # cache键: (messages_hash, tools_hash) -> (response, timestamp)
        self._cache_size = 100  # cache大小限制

    async def chat(self, message: str, context: Dict[str, Any] = None) -> str:
        # ... (保持不变, 或者为了完整性也可以加上 tools 支持, 但主要用 stream)
        pass
    
    async def chat_completion(self, messages: List[Dict]) -> Any:
        """
        Chat complete
        
        Args:
            messages: 消息列表
            
        Returns:
            Chat complete
        """
        try:
            # 调用 API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                stream=False
            )
            
            return response
        except Exception as e:
            logger.error(f"Chat complete failed: {e}")
            raise
    
    async def generate(self, prompt: str) -> str:
        """
        generate text 
        
        Args:
            prompt: 提示词
            
        Returns:
            str: 生成的文本
        """
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": "你是一 智能助手"},
                {"role": "user", "content": prompt}
            ]
            
            # 调用 API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                stream=False
            )
            
            # 返回生成的文本
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"generate text  failed: {e}")
            raise

    async def stream_chat(self, 
                         messages: List[Dict[str, Any]], 
                         tools: Optional[List[Dict[str, Any]]] = None,
                         model: Optional[str] = None
                         ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        [Updated] 流式调用, 支持 tools
        Register意: 参数From message(str) 变为 messages(list), 由调用方构建完整历史
        Yields: {"type": "content"|"tool_call", "data": ...}
        """
        try:
            # 导入 APIError
            from openai import APIError
            import hashlib
            import time
            from datetime import datetime
            import json as json_module
            
            # 生成请求cache键
            messages_str = json_module.dumps(messages, sort_keys=True)
            tools_str = json_module.dumps(tools, sort_keys=True) if tools else ""
            request_hash = hashlib.md5((messages_str + tools_str).encode()).hexdigest()
            
            # 检查cache
            if request_hash in self._request_cache:
                cached_response, timestamp = self._request_cache[request_hash]
                # cache有效期: 10 minutes
                if (datetime.now().timestamp() - timestamp) < 600:
                    logger.info("Using cached LLMResponse")
                    # 模拟流式输出
                    for chunk in cached_response:
                        yield chunk
                    return
            
            # 优先使用传入的Model, 否则使用默认Model
            current_model = model or self.model
            logger.info(f"Calling  LLM: {current_model}")
            logger.info(f"Messages: {messages}")
            logger.info(f"Tools: {tools}")
            
            # [Ollama 专属修复]构建 Ollama 兼容的请求体
            api_kwargs = {
                "model": current_model,
                "messages": messages,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "stream": True
            }
            
            # AddTool (already由Adapter格式化) 
            if tools and isinstance(tools, list) and len(tools) > 0:
                api_kwargs["tools"] = tools
                api_kwargs["tool_choice"] = "auto"

            logger.info(f"API params: {api_kwargs}")
            
            # 记录开始时间
            start_time = time.time()
            stream = await self.client.chat.completions.create(**api_kwargs)
            logger.info(f"API call successful, streaming (Time taken: {time.time() - start_time:.2f}s)")

            # cacheResponse
            response_chunks = []
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    if choice.delta:
                        delta = choice.delta
                        if hasattr(delta, 'content') and delta.content:
                            chunk_data = {"type": "content", "content": delta.content}
                            response_chunks.append(chunk_data)
                            yield chunk_data
                        elif hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                if tool_call.type == "function":
                                    # [Ollama 专属修复]清理Tool call parameters
                                    function_name = ""
                                    function_arguments = "{}"
                                    
                                    if hasattr(tool_call, 'function') and tool_call.function:
                                        func = tool_call.function
                                        if hasattr(func, 'name'):
                                            function_name = func.name
                                        if hasattr(func, 'arguments') and func.arguments:
                                            # 清理 JSON 格式
                                            function_arguments = func.arguments.replace("\n", "").strip()
                                            # 确保参数是有效的 JSON
                                            try:
                                                json_module.loads(function_arguments)
                                            except Exception:
                                                # 如果参数不是有效的 JSON, 使用空对象
                                                function_arguments = "{}"
                                    
                                    # 直接返回Tool调用信息, 不包装在data字段中
                                    # 确保Tool调用的 ID 始终有效
                                    tool_id = tool_call.id if hasattr(tool_call, 'id') and tool_call.id else f"call-{tool_call.index}"
                                    chunk_data = {
                                        "type": "tool_call",
                                        "index": tool_call.index,
                                        "id": tool_id,
                                        "function": {
                                            "name": function_name,
                                            "arguments": function_arguments
                                        }
                                    }
                                    response_chunks.append(chunk_data)
                                    yield chunk_data
            
            # cacheResponse
            if response_chunks:
                self._request_cache[request_hash] = (response_chunks, datetime.now().timestamp())
                # 限制cache大小
                if len(self._request_cache) > self._cache_size:
                    # Delete最旧的cache
                    oldest_key = min(self._request_cache, key=lambda k: self._request_cache[k][1])
                    del self._request_cache[oldest_key]
        except APIError as e:
            # [Ollama 专属修复]详细记录 API Error
            error_msg = str(e)
            error_body = getattr(e, 'body', None)
            error_code = getattr(e, 'code', None)
            logger.error(f"OpenAI API Error: {error_msg}, code={error_code}, body={error_body}")

            # 针对特定Error提供更详细的Error信息
            if "invalid tool call arguments" in error_msg.lower():
                error_msg = "Tool call parameter error: 消息历史过长或Tool过大.already自动重试."
            elif "context length" in error_msg.lower() or "too long" in error_msg.lower():
                error_msg = "消息历史过长, already自动截断Processing."

            yield {"type": "error", "content": f"[API Error: {error_msg}]"}
        except Exception as e:
            logger.error(f"LLM Error: {e}", exc_info=True)
            yield {"type": "error", "content": f"[Error: {str(e)}]"}
