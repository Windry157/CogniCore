#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 本地ModelAdapter
Processing Ollama 本地部署Model的 API 格式要求
"""
import json
import logging
from typing import Dict, Any, List
from .base import BaseModelAdapter

logger = logging.getLogger(__name__)


class OllamaAdapter(BaseModelAdapter):
    """
    Ollama 本地ModelAdapter

    Ollama 的特点: 
    1. 通过 OpenAI 兼容 API 提供服务
    2. 不同Model对Tool调用的支持程度不同
    3. 某些Model可能不支持原生Tool调用, 需要文本提取
    """

    def __init__(self, model_name: str = "qwen2.5:7b"):
        super().__init__(model_name)
        self.provider = "ollama"

    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化tool definition

        Ollama 要求: 
        - 使用 OpenAI 兼容格式
        - tool definition需要简化, 避免过于复杂的嵌套
        """
        formatted_tools = []

        for tool in tools:
            if isinstance(tool, dict) and "function" in tool:
                # 清理tool definition
                cleaned_tool = self._simplify_tool_definition(tool)
                formatted_tools.append(cleaned_tool)
            elif isinstance(tool, dict):
                # 包装成标准格式
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "").lower().replace(" ", "_"),
                        "description": tool.get("description", f"Tool: {tool.get('name', '')}"),
                        "parameters": self._simplify_parameters(tool.get("parameters", {}))
                    }
                }
                formatted_tools.append(formatted_tool)

        return formatted_tools

    def _simplify_tool_definition(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """简化tool definition, 适配 Ollama 本地Model"""
        import copy
        cleaned = copy.deepcopy(tool)

        if "function" in cleaned:
            func = cleaned["function"]

            # 确保 name 是小写下划线格式
            if "name" in func:
                func["name"] = func["name"].lower().replace(" ", "_")

            # 确保 description 不为空且简洁
            if "description" not in func or not func["description"]:
                func["description"] = f"Tool: {func.get('name', 'unknown')}"

            # 简化 description, 避免过长
            desc = func["description"]
            if len(desc) > 200:
                func["description"] = desc[:200] + "..."

            # 简化 parameters
            if "parameters" in func:
                func["parameters"] = self._simplify_parameters(func["parameters"])

        return cleaned

    def _simplify_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """简化参数定义, 避免过于复杂的嵌套"""
        if not isinstance(params, dict):
            params = {}

        # 只保留最基本的结构
        simplified = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # 简化 properties
        if "properties" in params and isinstance(params["properties"], dict):
            for prop_name, prop_def in params["properties"].items():
                if isinstance(prop_def, dict):
                    # 只保留 type 和 description
                    simple_prop = {
                        "type": prop_def.get("type", "string"),
                        "description": prop_def.get("description", f"参数: {prop_name}")[:100]  # 限制Length
                    }

                    # 保留 enum 如果存在且不长
                    if "enum" in prop_def and len(prop_def["enum"]) <= 10:
                        simple_prop["enum"] = prop_def["enum"]

                    simplified["properties"][prop_name] = simple_prop

        # 简化 required
        if "required" in params and isinstance(params["required"], list):
            # 最多保留 5   required 字段
            simplified["required"] = [r for r in params["required"] if isinstance(r, str)][:5]

        return simplified

    def format_tool_message(self, tool_call_id: str, name: str, content: str) -> Dict[str, Any]:
        """
        格式化Tool返回消息

        Ollama 要求: 
        - role 必须是 "tool"
        - 必须包含 tool_call_id
        - 必须包含 name
        """
        # 确保 tool_call_id 有效
        if not tool_call_id:
            tool_call_id = "call_default"

        # 截断Content防止过长 (Ollama 本地Model对Length更敏感) 
        truncated_content = self.truncate_tool_result(content, max_length=2000)

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": truncated_content
        }

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """
        解析 Ollama 的Response, 提取Tool调用

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
                                # 清理参数
                                cleaned_args = self._clean_arguments(func.arguments)
                                tool_call["arguments"] = cleaned_args

                        tool_calls.append(tool_call)

        except Exception as e:
            logger.error(f"Failed to parse Ollama tool call: {e}")

        return tool_calls

    def _clean_arguments(self, arguments: str) -> str:
        """清理Tool参数, 确保是有效的 JSON"""
        if not arguments:
            return "{}"

        try:
            args_dict = json.loads(arguments)
            return json.dumps(args_dict, ensure_ascii=False)
        except json.JSONDecodeError:
            # 尝试修复
            cleaned = arguments.strip().replace("\n", " ").replace("\r", "")
            try:
                args_dict = json.loads(cleaned)
                return json.dumps(args_dict, ensure_ascii=False)
            except json.JSONDecodeError:
                logger.warning(f"Unable to clean Ollama tool parameters: {arguments}")
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
            logger.error(f"Failed to parse Ollama streaming tool call: {e}")

        return tool_calls

    def supports_native_tool_calling(self) -> bool:
        """
        检查Current model是否支持原生Tool调用

        Returns:
            是否支持
        """
        # already知支持Tool调用的 Ollama Model
        supported_models = [
            "qwen2.5", "qwen3", "qwen3-vl",
            "llama3.1", "llama3.2",
            "mistral", "mixtral"
        ]

        model_lower = self.model_name.lower()
        for supported in supported_models:
            if supported in model_lower:
                return True

        return False
