#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimi ModelAdapter
Processing Moonshot AI (Kimi) 的 API 格式要求
"""
import json
import logging
from typing import Dict, Any, List
from .base import BaseModelAdapter

logger = logging.getLogger(__name__)


class KimiAdapter(BaseModelAdapter):
    """
    Kimi (Moonshot AI) ModelAdapter

    Kimi 的特点: 
    1. 支持标准的 OpenAI 格式Tool调用
    2. 对Tool消息格式要求严格, 必须包含 tool_call_id 和 name
    3. 多轮调用时上下文必须完整保留 tool_calls 和 tool 消息
    """

    def __init__(self, model_name: str = "kimi-k2.5"):
        super().__init__(model_name)
        self.provider = "moonshot"

    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化tool definition

        Kimi 要求: 
        - type 必须是 "function"
        - function 必须包含 name, description, parameters
        - parameters 必须符合 JSON Schema
        - parameters.properties 中的每 字段都必须有 description
        """
        import copy
        formatted_tools = []

        for tool in tools:
            if isinstance(tool, dict) and "function" in tool:
                # 深拷贝并清理tool definition
                cleaned_tool = copy.deepcopy(tool)
                function = cleaned_tool["function"]

                # 确保 name 是小写下划线格式
                if "name" in function:
                    function["name"] = function["name"].lower().replace(" ", "_")

                # 确保 description 不为空
                if "description" not in function or not function["description"]:
                    function["description"] = f"Tool: {function.get('name', 'unknown')}"

                # 确保 parameters 格式正确
                if "parameters" in function:
                    params = function["parameters"]

                    # 确保基本字段存在
                    if "type" not in params:
                        params["type"] = "object"
                    if "properties" not in params:
                        params["properties"] = {}
                    if "required" not in params:
                        params["required"] = []

                    # [关键]确保每  property 都有 description
                    for prop_name, prop_def in params["properties"].items():
                        if isinstance(prop_def, dict):
                            if "description" not in prop_def or not prop_def["description"]:
                                prop_def["description"] = f"参数: {prop_name}"
                            # 确保 type 存在
                            if "type" not in prop_def:
                                prop_def["type"] = "string"

                formatted_tools.append(cleaned_tool)
            elif isinstance(tool, dict):
                # 需要包装成 Kimi 格式
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "").lower().replace(" ", "_"),
                        "description": tool.get("description", f"Tool: {tool.get('name', '')}"),
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }

                # 复制并清理 parameters
                raw_params = tool.get("parameters", {})
                params = formatted_tool["function"]["parameters"]

                if "properties" in raw_params:
                    for prop_name, prop_def in raw_params["properties"].items():
                        if isinstance(prop_def, dict):
                            params["properties"][prop_name] = {
                                "type": prop_def.get("type", "string"),
                                "description": prop_def.get("description", f"参数: {prop_name}")
                            }
                            # 保留 enum 如果存在
                            if "enum" in prop_def:
                                params["properties"][prop_name]["enum"] = prop_def["enum"]

                if "required" in raw_params:
                    params["required"] = raw_params["required"]

                formatted_tools.append(formatted_tool)

        return formatted_tools

    def format_tool_message(self, tool_call_id: str, name: str, content: str) -> Dict[str, Any]:
        """
        格式化Tool返回消息

        Kimi 要求: 
        - role 必须是 "tool"
        - 必须包含 tool_call_id
        - 必须包含 name
        - content 是字符串格式的
        """
        # 确保 tool_call_id 有效
        if not tool_call_id:
            tool_call_id = "call_default"

        # 截断Content防止过长
        truncated_content = self.truncate_tool_result(content, max_length=3000)

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": truncated_content
        }

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """
        解析 Kimi 的Response, 提取Tool调用

        Args:
            response: OpenAI SDK 的Response对象

        Returns:
            Tool调用列表
        """
        tool_calls = []

        try:
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message

                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tc in message.tool_calls:
                        tool_call = {
                            "id": tc.id if hasattr(tc, 'id') and tc.id else f"call-{len(tool_calls)}",
                            "name": "",
                            "arguments": "{}"
                        }

                        if hasattr(tc, 'function') and tc.function:
                            func = tc.function
                            if hasattr(func, 'name'):
                                tool_call["name"] = func.name
                            if hasattr(func, 'arguments') and func.arguments:
                                # 验证参数是有效的 JSON
                                try:
                                    json.loads(func.arguments)
                                    tool_call["arguments"] = func.arguments
                                except json.JSONDecodeError:
                                    logger.warning(f"Tool parameters are not valid JSON: {func.arguments}")
                                    tool_call["arguments"] = "{}"

                        tool_calls.append(tool_call)

        except Exception as e:
            logger.error(f"Failed to parse Kimi tool call: {e}")

        return tool_calls

    def parse_streaming_tool_call(self, chunk: Any) -> List[Dict[str, Any]]:
        """
        解析流式Response中的Tool调用

        Args:
            chunk: 流式Response的 chunk

        Returns:
            Tool调用列表 (可能为空) 
        """
        tool_calls = []

        try:
            if hasattr(chunk, 'choices') and chunk.choices:
                choice = chunk.choices[0]

                if hasattr(choice, 'delta') and choice.delta:
                    delta = choice.delta

                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        for tc in delta.tool_calls:
                            tool_call = {
                                "index": tc.index if hasattr(tc, 'index') else 0,
                                "id": tc.id if hasattr(tc, 'id') and tc.id else None,
                                "name": "",
                                "arguments": ""
                            }

                            if hasattr(tc, 'function') and tc.function:
                                func = tc.function
                                if hasattr(func, 'name') and func.name:
                                    tool_call["name"] = func.name
                                if hasattr(func, 'arguments') and func.arguments:
                                    tool_call["arguments"] = func.arguments

                            tool_calls.append(tool_call)

        except Exception as e:
            logger.error(f"Failed to parse Kimi streaming tool call: {e}")

        return tool_calls
