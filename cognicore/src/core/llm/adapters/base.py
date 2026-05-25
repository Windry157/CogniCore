#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ModelAdapter基类
所有ModelAdapter必须继承此类并实现相应方法
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseModelAdapter(ABC):
    """所有ModelAdapter的基类"""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        把通用tool definition, 转换成Current model要求的tools格式

        Args:
            tools: 通用tool definition列表

        Returns:
            Current model要求的Tool格式
        """
        pass

    @abstractmethod
    def format_tool_message(self, tool_call_id: str, name: str, content: str) -> Dict[str, Any]:
        """
        把Tool返回, 转换成Current model要求的消息格式

        Args:
            tool_call_id: Tool调用ID
            name: ToolName
            content: Tool返回Content

        Returns:
            Current model要求的Tool消息格式
        """
        pass

    @abstractmethod
    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """
        把Model的Response, 解析成通用的Tool调用列表

        Args:
            response: Model的raw response

        Returns:
            通用的Tool调用列表, 每 元素包含:
            - id: Tool调用ID
            - name: ToolName
            - arguments: Tool参数(JSON字符串)
        """
        pass

    def format_assistant_tool_call(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        格式化助手的Tool调用消息

        Args:
            tool_calls: Tool调用列表

        Returns:
            助手消息字典
        """
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"]
                    }
                }
                for tc in tool_calls
            ]
        }

    def validate_tool_message(self, message: Dict[str, Any]) -> bool:
        """
        验证Tool消息格式是否正确

        Args:
            message: 消息字典

        Returns:
            是否有效
        """
        if message.get("role") != "tool":
            return False

        required_fields = ["tool_call_id", "name", "content"]
        for field in required_fields:
            if field not in message:
                return False

        return True

    def truncate_tool_result(self, result: str, max_length: int = 3000) -> str:
        """
        截断Tool, 防止消息过长

        Args:
            result: Tool返回的JSON字符串
            max_length: 最大允许Length

        Returns:
            截断后的JSON字符串
        """
        import json

        if len(result) <= max_length:
            return result

        try:
            data = json.loads(result)

            if isinstance(data, list):
                truncated_list = data[:20]
                if len(data) > 20:
                    truncated_list.append({"_truncated": True, "total_items": len(data), "shown": 20})
                truncated = json.dumps(truncated_list, ensure_ascii=False)
                if len(truncated) > max_length:
                    truncated = json.dumps({
                        "_truncated": True,
                        "message": f"过长, already截断.原始Length: {len(result)} 字符"
                    }, ensure_ascii=False)
                return truncated

            if isinstance(data, dict):
                # 先收集需要截断的键, 避免在迭代时修改字典
                lists_to_truncate = []
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 20:
                        lists_to_truncate.append((key, value))

                # 然后执行截断
                for key, value in lists_to_truncate:
                    data[key] = value[:20]
                    data["_truncated"] = True
                    data["_truncated_key"] = key
                    data["_total_items"] = len(value)

                truncated = json.dumps(data, ensure_ascii=False)
                if len(truncated) > max_length:
                    truncated = json.dumps({
                        "_truncated": True,
                        "message": f"过长, already截断.原始Length: {len(result)} 字符",
                        "keys": list(data.keys())[:10]
                    }, ensure_ascii=False)
                return truncated

            return result[:max_length] + "...[already截断]"

        except json.JSONDecodeError:
            return result[:max_length] + "...[already截断]"

    def validate_messages(self, messages: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        验证消息列表格式是否正确

        Args:
            messages: 消息列表

        Returns:
            (是否有效, Error信息)
        """
        import json

        if not isinstance(messages, list):
            return False, "messages 必须是列表"

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return False, f"Round  {i}  entries消息必须是字典"

            # 检查必需字段
            if "role" not in msg:
                return False, f"Round  {i}  entries消息缺少 role 字段"

            role = msg.get("role")
            valid_roles = ["system", "user", "assistant", "tool"]
            if role not in valid_roles:
                return False, f"Round  {i}  entries消息的 role '{role}' 无效"

            # 检查 tool 消息的特殊要求
            if role == "tool":
                required_fields = ["tool_call_id", "name", "content"]
                for field in required_fields:
                    if field not in msg:
                        return False, f"Round  {i}  entries tool 消息缺少 {field} 字段"

                # 验证 content 是字符串
                if not isinstance(msg.get("content"), str):
                    return False, f"Round  {i}  entries tool 消息的 content 必须是字符串"

            # 检查 assistant 消息的 tool_calls
            if role == "assistant" and msg.get("tool_calls"):
                tool_calls = msg["tool_calls"]
                if not isinstance(tool_calls, list):
                    return False, f"Round  {i}  entries assistant 消息的 tool_calls 必须是列表"

                for j, tc in enumerate(tool_calls):
                    if not isinstance(tc, dict):
                        return False, f"Round  {i}  entries消息的 tool_calls[{j}] 必须是字典"

                    if "id" not in tc:
                        return False, f"Round  {i}  entries消息的 tool_calls[{j}] 缺少 id"

                    if "function" not in tc:
                        return False, f"Round  {i}  entries消息的 tool_calls[{j}] 缺少 function"

                    func = tc["function"]
                    if not isinstance(func, dict):
                        return False, f"Round  {i}  entries消息的 tool_calls[{j}].function 必须是字典"

                    if "name" not in func:
                        return False, f"Round  {i}  entries消息的 tool_calls[{j}].function 缺少 name"

                    if "arguments" not in func:
                        return False, f"Round  {i}  entries消息的 tool_calls[{j}].function 缺少 arguments"

                    # 验证 arguments 是有效的 JSON 字符串
                    try:
                        args = func["arguments"]
                        if isinstance(args, str):
                            json.loads(args)
                    except json.JSONDecodeError:
                        return False, f"Round  {i}  entries消息的 tool_calls[{j}].function.arguments 不是有效的 JSON"

        return True, ""

    def validate_tools(self, tools: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        验证tool definition格式是否正确

        Args:
            tools: tool definition列表

        Returns:
            (是否有效, Error信息)
        """
        if not isinstance(tools, list):
            return False, "tools 必须是列表"

        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                return False, f"Round  {i}  tools必须是字典"

            # 检查 type 字段
            if "type" not in tool:
                return False, f"Round  {i}  tools缺少 type 字段"

            if tool["type"] != "function":
                return False, f"Round  {i}  tools的 type 必须是 'function'"

            # 检查 function 字段
            if "function" not in tool:
                return False, f"Round  {i}  tools缺少 function 字段"

            func = tool["function"]
            if not isinstance(func, dict):
                return False, f"Round  {i}  tools的 function 必须是字典"

            # 检查必需的 function 字段
            if "name" not in func:
                return False, f"Round  {i}  tools的 function 缺少 name"

            if "description" not in func:
                return False, f"Round  {i}  tools的 function 缺少 description"

            # 检查 parameters
            if "parameters" in func:
                params = func["parameters"]
                if not isinstance(params, dict):
                    return False, f"Round  {i}  tools的 parameters 必须是字典"

                if "type" not in params:
                    return False, f"Round  {i}  tools的 parameters 缺少 type"

        return True, ""
