#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) 协议实现
支持MCP protocol 的Tool调用, 资源管理和提示词模板
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime
import asyncio

from src.core.config import config
from src.core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class MCPMethod(Enum):
    """MCP方法"""
    # Tool相关
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # 资源相关
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"

    # 提示词相关
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # 采样相关
    SAMPLING_CREATE = "sampling/create"

    # 根目录相关
    ROOTS_LIST = "roots/list"


@dataclass
class MCPRequest:
    """MCP request"""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class MCPResponse:
    """MCPResponse"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@dataclass
class MCPTool:
    """MCPTool"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None


@dataclass
class MCPResource:
    """MCP资源"""
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class MCPPrompt:
    """MCP提示词模板"""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    template: str = ""


class MCPProtocol:
    """MCP protocol Processor"""

    def __init__(self):
        """InitializationMCP protocol Processor"""
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}

        logger.info("MCP protocol Processing initialization complete")

    def register_tool(self, tool: MCPTool):
        """
        MCP Tool

        Args:
            tool: MCPTool
        """
        self.tools[tool.name] = tool
        logger.info(f"MCP Tool: {tool.name}")

    def register_resource(self, resource: MCPResource):
        """
        MCP resource

        Args:
            resource: MCP资源
        """
        self.resources[resource.uri] = resource
        logger.info(f"MCP resource: {resource.uri}")

    def register_prompt(self, prompt: MCPPrompt):
        """
        MCP prompt

        Args:
            prompt: MCP提示词模板
        """
        self.prompts[prompt.name] = prompt
        logger.info(f"MCP prompt: {prompt.name}")

    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ProcessingTool列表请求"""
        tools = []
        for tool in self.tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })
        return {"tools": tools}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ProcessingTool调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return {"error": {"code": -32601, "message": f"Tooldoes not exist: {tool_name}"}}

        tool = self.tools[tool_name]

        if tool.handler is None:
            return {"error": {"code": -32603, "message": f"ToolProcessor未设置: {tool_name}"}}

        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                    }
                ],
                "isError": False
            }
        except Exception as e:
            logger.error(f"ToolCall failed: {tool_name}, Error: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }

    def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Processing资源列表请求"""
        resources = []
        for resource in self.resources.values():
            resources.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type
            })
        return {"resources": resources}

    def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Processing资源读取请求"""
        uri = params.get("uri")

        if uri not in self.resources:
            return {"error": {"code": -32601, "message": f"资源does not exist: {uri}"}}

        resource = self.resources[uri]
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.mime_type,
                    "text": ""  # 实际Content应由资源Processor提供
                }
            ]
        }

    def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Processing提示词列表请求"""
        prompts = []
        for prompt in self.prompts.values():
            prompts.append({
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments
            })
        return {"prompts": prompts}

    def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ProcessingGet提示词请求"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name not in self.prompts:
            return {"error": {"code": -32601, "message": f"提示词does not exist: {name}"}}

        prompt = self.prompts[name]
        template = prompt.template

        for key, value in arguments.items():
            template = template.replace(f"{{{key}}}", str(value))

        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": template
                    }
                }
            ]
        }

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        ProcessingMCP request

        Args:
            request: MCP request

        Returns:
            MCPResponse
        """
        try:
            method = request.method
            params = request.params or {}

            if method == MCPMethod.TOOLS_LIST.value:
                result = self._handle_tools_list(params)
            elif method == MCPMethod.TOOLS_CALL.value:
                result = await self._handle_tools_call(params)
            elif method == MCPMethod.RESOURCES_LIST.value:
                result = self._handle_resources_list(params)
            elif method == MCPMethod.RESOURCES_READ.value:
                result = self._handle_resources_read(params)
            elif method == MCPMethod.PROMPTS_LIST.value:
                result = self._handle_prompts_list(params)
            elif method == MCPMethod.PROMPTS_GET.value:
                result = self._handle_prompts_get(params)
            else:
                return MCPResponse(
                    error={"code": -32601, "message": f"未知方法: {method}"},
                    id=request.id
                )

            return MCPResponse(result=result, id=request.id)

        except Exception as e:
            logger.error(f"MCP requestProcessing failed: {e}")
            return MCPResponse(
                error={"code": -32603, "message": str(e)},
                id=request.id
            )


class MCPClient:
    """MCP客户端"""

    def __init__(self, server_url: str):
        """
        InitializationMCP客户端

        Args:
            server_url: MCPserverURL
        """
        self.server_url = server_url
        self.session_id = None

        logger.info(f"MCP client initialization, server: {server_url}")

    async def connect(self):
        """Connected to MCP server"""
        logger.info(f"Connected to MCP server: {self.server_url}")

    async def disconnect(self):
        """Disconnected from MCP server"""
        logger.info(f"Disconnected from MCP server")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List可用Tool

        Returns:
            Tool列表
        """
        request = MCPRequest(method=MCPMethod.TOOLS_LIST.value)
        response = await self._send_request(request)

        if response.error:
            raise Exception(f"Failed to list tools: {response.error}")

        return response.result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用Tool

        Args:
            tool_name: ToolName
            arguments: Tool参数

        Returns:
            Tool execution result
        """
        request = MCPRequest(
            method=MCPMethod.TOOLS_CALL.value,
            params={"name": tool_name, "arguments": arguments}
        )
        response = await self._send_request(request)

        if response.error:
            raise Exception(f"调用Tool failed: {response.error}")

        return response.result

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        List可用资源

        Returns:
            资源列表
        """
        request = MCPRequest(method=MCPMethod.RESOURCES_LIST.value)
        response = await self._send_request(request)

        if response.error:
            raise Exception(f"List资源 failed: {response.error}")

        return response.result.get("resources", [])

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List可用提示词

        Returns:
            提示词列表
        """
        request = MCPRequest(method=MCPMethod.PROMPTS_LIST.value)
        response = await self._send_request(request)

        if response.error:
            raise Exception(f"List提示词 failed: {response.error}")

        return response.result.get("prompts", [])

    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """
        发送MCP request

        Args:
            request: MCP request

        Returns:
            MCPResponse
        """
        logger.warning(f"MCPClient does not implement actual request sending: {request.method}")
        return MCPResponse(result={}, id=request.id)


class MCPServerAdapter:
    """MCPserverAdapter"""

    def __init__(self, protocol: MCPProtocol):
        """
        InitializationMCPserverAdapter

        Args:
            protocol: MCP protocol Processor
        """
        self.protocol = protocol

    def create_fastapi_routes(self):
        """
        CreateFastAPI路由

        Returns:
            FastAPI路由列表
        """
        from fastapi import APIRouter, HTTPException

        router = APIRouter()

        @router.get("/mcp/tools")
        async def list_tools():
            request = MCPRequest(method=MCPMethod.TOOLS_LIST.value)
            response = await self.protocol.handle_request(request)
            if response.error:
                raise HTTPException(status_code=500, detail=response.error)
            return response.result

        @router.post("/mcp/tools/call")
        async def call_tool(request_data: dict):
            request = MCPRequest(
                method=MCPMethod.TOOLS_CALL.value,
                params=request_data
            )
            response = await self.protocol.handle_request(request)
            if response.error:
                raise HTTPException(status_code=500, detail=response.error)
            return response.result

        @router.get("/mcp/resources")
        async def list_resources():
            request = MCPRequest(method=MCPMethod.RESOURCES_LIST.value)
            response = await self.protocol.handle_request(request)
            if response.error:
                raise HTTPException(status_code=500, detail=response.error)
            return response.result

        @router.get("/mcp/prompts")
        async def list_prompts():
            request = MCPRequest(method=MCPMethod.PROMPTS_LIST.value)
            response = await self.protocol.handle_request(request)
            if response.error:
                raise HTTPException(status_code=500, detail=response.error)
            return response.result

        return router


class MCPToolAdapter:
    """MCPToolAdapter"""

    @staticmethod
    def create_tool_from_function(func: Callable, name: str = None,
                                 description: str = None) -> MCPTool:
        """
        From普通函数CreateMCPTool

        Args:
            func: 函数
            name: ToolName
            description: ToolDescription

        Returns:
            MCPTool
        """
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or ""

        import inspect
        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_type = "string"
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

            properties[param_name] = {"type": param_type}

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        input_schema = {
            "type": "object",
            "properties": properties,
            "required": required
        }

        return MCPTool(
            name=tool_name,
            description=tool_description,
            input_schema=input_schema,
            handler=func
        )


class MCPToolRegistry:
    """MCPToolRegistry"""

    def __init__(self):
        """InitializationMCPToolRegistry"""
        self.tools: Dict[str, MCPTool] = {}

    def register(self, tool: MCPTool):
        """
        RegisterTool

        Args:
            tool: MCPTool
        """
        self.tools[tool.name] = tool

    def register_function(self, func: Callable, name: str = None,
                         description: str = None) -> MCPTool:
        """
        Register函数为MCPTool

        Args:
            func: 函数
            name: ToolName
            description: ToolDescription

        Returns:
            Create的MCPTool
        """
        tool = MCPToolAdapter.create_tool_from_function(func, name, description)
        self.register(tool)
        return tool

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        GetTool

        Args:
            name: ToolName

        Returns:
            MCPTool
        """
        return self.tools.get(name)

    def list_tools(self) -> List[MCPTool]:
        """
        List所有Tool

        Returns:
            Tool列表
        """
        return list(self.tools.values())


# 全局MCP protocol Processor实例
_mcp_protocol_instance = None


def get_mcp_protocol() -> MCPProtocol:
    """
    GetMCP protocol Processor实例

    Returns:
        MCP protocol Processor实例
    """
    global _mcp_protocol_instance
    if _mcp_protocol_instance is None:
        _mcp_protocol_instance = MCPProtocol()
    return _mcp_protocol_instance


def reset_mcp_protocol() -> MCPProtocol:
    """
    重置MCP protocol Processor实例

    Returns:
        新的MCP protocol Processor实例
    """
    global _mcp_protocol_instance
    _mcp_protocol_instance = MCPProtocol()
    return _mcp_protocol_instance