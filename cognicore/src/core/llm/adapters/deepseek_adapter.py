#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deepseek ModelAdapter
Processing Deepseek API 的格式要求
"""
import json
import logging
from typing import Dict, Any, List
from .base import BaseModelAdapter

logger = logging.getLogger(__name__)


class DeepseekAdapter(BaseModelAdapter):
    """
    Deepseek ModelAdapter

    Deepseek 的特点: 
    1. 支持 OpenAI 兼容格式的Tool调用
    2. 对Tool参数的 JSON 格式要求严格
    3. 某些版本可能出现重复Tool调用的问题, 需要防循环保护
    """

    def __init__(self, model_name: str = "deepseek-chat"):
        super().__init__(model_name)
        self.provider = "deepseek"

    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化tool definition

        Deepseek 要求: 
        - type 必须是 "function"
        - function 必须包含 name, description
        - parameters 必须是有效的 JSON Schema
        """
        formatted_tools = []

        for tool in tools:
            if isinstance(tool, dict) and "function" in tool:
                # already经是正确格式, 进行清理
                cleaned_tool = self._clean_tool_definition(tool)
                formatted_tools.append(cleaned_tool)
            elif isinstance(tool, dict):
                # 需要包装成标准格式
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "").lower().replace(" ", "_"),
                        "description": tool.get("description", f"Tool: {tool.get('name', '')}"),
                        "parameters": self._clean_parameters(tool.get("parameters", {}))
                    }
                }
                formatted_tools.append(formatted_tool)

        return formatted_tools

    def _clean_tool_definition(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """清理tool definition, 确保符合 Deepseek 要求"""
        import copy
        cleaned = copy.deepcopy(tool)

        if "function" in cleaned:
            func = cleaned["function"]

            # 确保 name 是小写下划线格式
            if "name" in func:
                func["name"] = func["name"].lower().replace(" ", "_")

            # 确保 description 不为空
            if "description" not in func or not func["description"]:
                func["description"] = f"Tool: {func.get('name', 'unknown')}"

            # 清理 parameters
            if "parameters" in func:
                func["parameters"] = self._clean_parameters(func["parameters"])

        return cleaned

    def _clean_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """清理参数定义, 确保符合 JSON Schema"""
        if not isinstance(params, dict):
            params = {}

        cleaned = {
            "type": params.get("type", "object"),
            "properties": {},
            "required": []
        }

        # 清理 properties
        if "properties" in params and isinstance(params["properties"], dict):
            for prop_name, prop_def in params["properties"].items():
                if isinstance(prop_def, dict):
                    cleaned_prop = {
                        "type": prop_def.get("type", "string"),
                        "description": prop_def.get("description", f"参数: {prop_name}")
                    }

                    # 保留 enum 如果存在
                    if "enum" in prop_def:
                        cleaned_prop["enum"] = prop_def["enum"]

                    cleaned["properties"][prop_name] = cleaned_prop

        # 清理 required
        if "required" in params and isinstance(params["required"], list):
            cleaned["required"] = [r for r in params["required"] if isinstance(r, str)]

        return cleaned

    def format_tool_message(self, tool_call_id: str, name: str, content: str) -> Dict[str, Any]:
        """
        格式化Tool返回消息

        Deepseek 要求: 
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
        解析 Deepseek 的Response, 提取Tool调用

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
                                # 清理并验证参数
                                cleaned_args = self._clean_arguments(func.arguments)
                                tool_call["arguments"] = cleaned_args

                        tool_calls.append(tool_call)

        except Exception as e:
            logger.error(f"Failed to parse Deepseek tool call: {e}")

        return tool_calls

    def _clean_arguments(self, arguments: str) -> str:
        """清理Tool参数, 确保是有效的 JSON"""
        if not arguments:
            return "{}"

        try:
            # 尝试解析
            args_dict = json.loads(arguments)
            # 重新序列化, 确保格式正确
            return json.dumps(args_dict, ensure_ascii=False)
        except json.JSONDecodeError:
            # 尝试修复常见的 JSON Error
            cleaned = arguments.strip()

            # 移除多余的换行符和空格
            cleaned = cleaned.replace("\n", " ").replace("\r", "")

            # 尝试再次解析
            try:
                args_dict = json.loads(cleaned)
                return json.dumps(args_dict, ensure_ascii=False)
            except json.JSONDecodeError:
                logger.warning(f"Unable to clean tool parameters: {arguments}")
                return "{}"

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
            logger.error(f"Failed to parse Deepseek streaming tool call: {e}")

        return tool_calls
