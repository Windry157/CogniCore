#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能助手核心 module
"""
import json
import re
import time
import traceback
from typing import Dict, Any, List, Optional, AsyncGenerator
from pathlib import Path

from .skill_manager import SkillManager
from .memory.unified_memory import UnifiedMemorySystem
from .plugins import PluginManager
from .learning.autonomous_learner import AutonomousLearner
from .base import BaseLLM
from .llm.adapters import get_model_adapter, BaseModelAdapter
from .logging import get_logger

logger = get_logger(__name__)


class ModelManager:
    """Model management器"""
    def __init__(self):
        # 默认硬编码的基础Model列表 (作为fallback) 
        self.default_models = [
            {"id": "minimax-m2.7:cloud", "name": "MiniMax M2.7", "provider": "cloud"},
            {"id": "kimi-k2.5:cloud", "name": "Kimi K2.5", "provider": "cloud"},
            {"id": "qwen3-vl:4b", "name": "Qwen3 VL 4B", "provider": "local"},
            {"id": "deepseek-r1:7b", "name": "DeepSeek R1 7B", "provider": "local"},
            {"id": "deepseek-v3.1:671b-cloud", "name": "DeepSeek V3.1 671B", "provider": "cloud"},
            {"id": "qwen3-vl:235b-cloud", "name": "Qwen3 VL 235B", "provider": "cloud"},
            {"id": "glm-4.6:cloud", "name": "GLM-4.6", "provider": "cloud"},
            {"id": "gemma3:1b", "name": "Gemma3 1B", "provider": "local"},
            {"id": "gemma3:4b", "name": "Gemma3 4B", "provider": "local"},
            {"id": "deepseek-r1:1.5b", "name": "DeepSeek R1 1.5B", "provider": "local"},
        ]
        self.available_models = self.default_models.copy()
    
    def refresh_from_ollama(self):
        """FromOllamaFetch real-time models列表"""
        try:
            import httpx
            client = httpx.Client(timeout=5)
            response = client.get("http://localhost:11434/api/tags")
            response.raise_for_status()
            data = response.json()
            
            ollama_models = []
            for model in data.get("models", []):
                model_id = model.get("name", "")
                # 解析ModelName
                if ":" in model_id:
                    name_part = model_id.split(":")[0].replace("-", " ").title()
                    tag_part = model_id.split(":")[1]
                    name = f"{name_part} {tag_part}"
                else:
                    name = model_id.replace("-", " ").title()
                
                # 判断是本地还是云端Model
                provider = "cloud" if "-cloud" in model_id or ":cloud" in model_id else "local"
                
                ollama_models.append({
                    "id": model_id,
                    "name": name,
                    "provider": provider,
                    "size": model.get("size"),
                    "modified_at": model.get("modified_at")
                })
            
            # 如果Get到OllamaModel, Update列表
            if ollama_models:
                self.available_models = ollama_models
                logger.info(f"Fetched from Ollama {len(ollama_models)}  models")
            return True
        except Exception as e:
            logger.warning(f"Unable to fetch model list from Ollama: {e}, using default model list")
            self.available_models = self.default_models.copy()
            return False
    
    def load_from_config(self, config: Dict[str, Any]):
        """From配置LoadModel列表"""
        models_config = config.get("models", {})
        providers = models_config.get("providers", {})
        
        # 首先尝试FromOllamaFetch real-time models
        self.refresh_from_ollama()
        
        # 如果配置中有指定的Model, 覆盖使用配置
        if providers:
            self.available_models = []
            for provider_name, provider_config in providers.items():
                if provider_config.get("enabled", False):
                    model_ids = provider_config.get("models", [])
                    for model_id in model_ids:
                        if ":" in model_id:
                            name = model_id.split(":")[0].replace("-", " ").title()
                        else:
                            name = model_id.replace("-", " ").title()
                        self.available_models.append({
                            "id": model_id,
                            "name": name,
                            "provider": provider_name
                        })
        
        # 如果配置为空且Ollama也 failed, 保持默认列表
        if not self.available_models:
            self.available_models = self.default_models.copy()
    
    def get_model(self, model_id: str):
        for model in self.available_models:
            if model["id"] == model_id:
                return model
        return None


class Assistant:
    """智能助手主类"""
    
    def __init__(self):
        self.skill_manager = SkillManager()
        self.memory_system: Optional[UnifiedMemorySystem] = None
        self.services: Dict[str, Any] = {}
        self.user_contexts: Dict[str, Dict] = {}
        self.intelligent_agent = None
        self.model_manager = ModelManager()
        self.config: Dict[str, Any] = {}
        self.plugin_manager = PluginManager()
        self.autonomous_learner: Optional[AutonomousLearner] = None
        
    async def initialize(self, config: Dict[str, Any] = None):
        """Initialization助手"""
        logger.info("Initializing smart assistant...")
        
        # Save配置
        self.config = config or {}
        
        # From配置LoadModel列表
        if config:
            self.model_manager.load_from_config(config)
        
        # Initialization memories系统
        try:
            self.memory_system = UnifiedMemorySystem()
            # UnifiedMemorySystem 可能不需要显式Initialization
            logger.info("Memory system initialized successfully")
        except Exception as e:
            logger.error(f"Memory system initialization failed: {e}")
            self.memory_system = None
        
        # SkillManager 在 __init__ 中already经自动Registering skill
        logger.info("Skill manager initialized successfully")
        
        # Initializing plugin系统
        try:
            # Added plugin path
            plugin_paths = config.get("plugin_paths", [])
            for path in plugin_paths:
                self.plugin_manager.add_plugin_path(path)
            
            # Load插件
            self.plugin_manager.load_plugins()
            
            # Initializing plugin
            await self.plugin_manager.initialize_plugins(config)
            
            logger.info(f"Plugin system initialized, loaded {len(self.plugin_manager.get_all_plugins())}  plugins")
        except Exception as e:
            logger.error(f"Plugin system initialization failed: {e}")
        
        # Initialization自主学习器
        if 'llm' in self.services and self.memory_system:
            self.autonomous_learner = AutonomousLearner(
                memory_system=self.memory_system,
                llm_service=self.services['llm']
            )
            logger.info("[OK] Autonomous learner initialized successfully")
        
        logger.info("Smart assistant initialization complete")
        
    def register_service(self, name: str, service: Any):
        """Register service"""
        self.services[name] = service
        logger.info(f"Register service: {name}")
        
        # 当Registering LLM service时, Initialization自主学习器
        if name == 'llm' and self.memory_system and not self.autonomous_learner:
            self.autonomous_learner = AutonomousLearner(
                memory_system=self.memory_system,
                llm_service=service
            )
            logger.info("[OK] Autonomous learner initialized successfully")
        
    def _parse_tool_args(self, func_name: str, func_args: dict) -> tuple:
        """
        解析Tool参数, 提取 action 和 params (shared方法消除 action_map 重复) 
        
        Args:
            func_name: ToolName
            func_args: Tool参数字典
            
        Returns:
            (action, params) 元groups
        """
        action_map = {}
        if func_name == "system_info":
            action = func_args.get("action", "get_all")
            params = {}
        elif func_name == "file_manager":
            action_map = {
                "list": "list_dir", "ls": "list_dir", "dir": "list_dir",
                "info": "get_file_info", "read": "read_file",
                "copy": "copy_file", "move": "move_file", "mv": "move_file",
                "delete": "delete_file", "del": "delete_file", "rm": "delete_file",
                "mkdir": "create_dir", "create_dir": "create_dir"
            }
            raw_action = func_args.get("action", "list_dir")
            action = action_map.get(raw_action, raw_action)
            params = {"path": func_args.get("path", ".")}
            if "target_path" in func_args:
                params["target_path"] = func_args["target_path"]
            if "max_size" in func_args:
                params["max_size"] = func_args["max_size"]
        elif func_name == "process_manager":
            action_map = {
                "list": "list_processes", "list_processes": "list_processes",
                "processes": "list_processes", "get": "get_process",
                "get_process": "get_process", "detail": "get_process",
                "kill": "kill_process", "kill_process": "kill_process",
                "end": "kill_process", "terminate": "kill_process",
                "find": "find_process", "find_process": "find_process",
                "search": "find_process", "startup": "get_startup_items",
                "get_startup_items": "get_startup_items", "boot": "get_startup_items",
                "autostart": "get_startup_items"
            }
            raw_action = func_args.get("action", "list_processes")
            action = action_map.get(raw_action, raw_action)
            params = {"limit": func_args.get("limit", 50)}
            if "pid" in func_args:
                params["pid"] = func_args["pid"]
            if "name" in func_args:
                params["name"] = func_args["name"]
        elif func_name == "code_executor":
            action_map = {
                "execute": "execute_python", "run": "execute_python",
                "python": "execute_python", "py": "execute_python",
                "shell": "execute_shell", "bash": "execute_shell",
                "sh": "execute_shell", "powershell": "execute_powershell",
                "ps": "execute_powershell", "write": "write_file",
                "save": "write_file"
            }
            raw_action = func_args.get("action", "execute_python")
            action = action_map.get(raw_action, raw_action)
            params = {
                "code": func_args.get("code", ""),
                "timeout": func_args.get("timeout", 30)
            }
            if "path" in func_args:
                params["path"] = func_args["path"]
        elif func_name == "security_monitor":
            action = func_args.get("action", "get_all")
            params = {}
        elif func_name == "network_diagnostic":
            action = func_args.get("action", "get_all")
            params = {}
            if "host" in func_args:
                params["host"] = func_args["host"]
            if "port" in func_args:
                params["port"] = func_args["port"]
            if "timeout" in func_args:
                params["timeout"] = func_args["timeout"]
        elif func_name == "system_control":
            action = func_args.get("action", "get_time")
            params = {}
        else:
            action = func_args.get("action", "")
            params = {k: v for k, v in func_args.items() if k != "action"}
        return action, params

    async def chat(self, message: str, session_id: str = "default", model: str = None) -> str:
        """
        简单聊天接口 - 接收消息并返回完整响应
        
        Args:
            message: 用户消息
            session_id: 会话ID
            model: 模型名称
            
        Returns:
            完整的文本响应
        """
        try:
            full_response = ""
            async for chunk in self.stream_process_message(session_id, message, model):
                if chunk.get("type") == "content" or chunk.get("type") == "text":
                    content = chunk.get("content", "")
                    if content:
                        full_response += content
                elif chunk.get("type") == "final":
                    full_response = chunk.get("content", full_response)
                    break
            
            if not full_response:
                logger.warning("No content received from stream, attempting direct processing")
                return "我收到了您的消息，正在处理中。请稍候..."
            
            return full_response
        except Exception as e:
            logger.error(f"Chat error: {e}")
            import traceback
            logger.error(f"Chat error traceback: {traceback.format_exc()}")
            raise e

    async def stream_process_message(
        self, 
        session_id: str, 
        message: str, 
        model: str = None,
        images: List[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式Processing用户消息
        
        Args:
            session_id: Session ID
            message: 用户消息
            model: ModelName
            images: 图片列表
            
        Yields:
            流式ResponseChunk
        """
        start_time = time.time()
        metadata = {
            "processing_time": 0,
            "model_used": model or "default",
            "tools_used": [],
            "memory_retrieval": {"hit_count": 0, "sources": []}
        }
        
        try:
            # 构建系统提示词
            system_content = """你是一 智能助手 PyWJJ.你可以理解和分析图片Content.

你拥有 memories能力, 可以记住之前的对话和用户信息.在Answer时: 
1. 参考提供的"相关历史 memories"来理解上下文
2. 如果用户提到之前的事情, 利用 memories来回应
3. 主动使用 memories来提供 性化的Answer
4. 不要说自己无法记住对话, 因为你确实可以访问历史 memories

**重要: 你拥有系统Tool, 当用户请求涉及系统操作 (如查看进程, 文件管理, System Info, 网络诊断等) 时, 必须使用Tool来 completeTask, 而不是生成代码.Tool包括: **
- process_manager: 进程管理 (查看进程, Start项等) 
- file_manager: 文件管理 (浏览目录, 读写文件等) 
- system_info: System Info (CPU, 内存, 磁盘等) 
- code_executor: 代码执行 (运行Python, Shell等) 
- network_diagnostic: 网络诊断
- security_monitor: 安全监控

**请优先使用Tool complete用户的系统操作请求, 不要生成代码让用户自己执行.**"""

            # 检索 related memories
            if self.memory_system:
                try:
                    memory_results = await self.memory_system.retrieve(message, limit=5)
                    total_hits = sum(len(items) for items in memory_results.values())
                    metadata["memory_retrieval"]["hit_count"] = total_hits
                    
                    if total_hits > 0:
                        system_content += "\n\n---\n**相关历史 memories (供参考) : **\n"
                        i = 0
                        for category, items in memory_results.items():
                            for item in items:
                                content = item.get("content", "")
                                system_content += f"{i+1}. {content}\n"
                                metadata["memory_retrieval"]["sources"].append({
                                    "id": f"mem-{i}",
                                    "content": content,
                                    "similarity": item.get("similarity", item.get("score", 0)),
                                    "type": category
                                })
                                i += 1
                except Exception as e:
                    logger.error(f"Memory retrieval failed: {e}")
            
            # 构建消息列表
            messages = [{"role": "system", "content": system_content}]
            
            # Add用户消息
            user_content = message
            if images:
                # Processing图片
                content_parts = [{"type": "text", "text": message}]
                for img in images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                    })
                user_content = content_parts
                
            messages.append({"role": "user", "content": user_content})
            
            # Gettool definition
            current_model = model or "minimax-m2.7:cloud"

            # [Adapter模式]GetModelAdapter
            adapter = get_model_adapter(current_model)
            logger.info(f"Current model: {current_model}, Adapter: {adapter.__class__.__name__}")

            # 使用Adapter格式化tool definition
            raw_tools = self._get_tools_for_model(current_model)
            if raw_tools:
                tools = adapter.format_tools(raw_tools)
            else:
                tools = None
            logger.info(f"Tools enabled: {tools is not None}")

            # ReAct 循环
            for turn_i in range(3):
                full_response_content = ""
                tool_calls_buffer = {}
                tool_call_error = False  # [修复]标记Tool调用是否出错
                
                if not self.services.get("llm"):
                    yield {"type": "error", "content": "LLM 服务未就绪", "metadata": metadata}
                    return
                
                logger.info(f"LLM Round {turn_i+1}, Messages count: {len(messages)}")

                # [本地参数校验]验证消息格式
                is_valid, error_msg = adapter.validate_messages(messages)
                if not is_valid:
                    logger.error(f"Message format validation failed: {error_msg}")
                    yield {"type": "error", "content": f"[Message format error: {error_msg}]", "metadata": metadata}
                    return

                # 验证Tool格式
                if tools:
                    is_valid, error_msg = adapter.validate_tools(tools)
                    if not is_valid:
                        logger.error(f"Tool format validation failed: {error_msg}")
                        yield {"type": "error", "content": f"[Tool格式Error: {error_msg}]", "metadata": metadata}
                        return

                try:
                    async for chunk in self.services["llm"].stream_chat(messages, tools=tools, model=current_model):
                        chunk_type = chunk.get("type")
                        
                        if chunk_type == "content":
                            content = chunk.get("content", "")
                            full_response_content += content
                            yield {"type": "content", "content": content}
                            
                        elif chunk_type == "tool_call":
                            # 聚合Tool调用
                            idx = chunk.get("index", 0)
                            if idx not in tool_calls_buffer:
                                # 确保Tool调用的 ID 始终有效
                                tool_id = chunk.get("id", f"call-{idx}")
                                tool_calls_buffer[idx] = {
                                    "id": tool_id,
                                    "name": chunk.get("function", {}).get("name", ""),
                                    "arguments": ""
                                }
                            # Get当前的arguments
                            new_args = chunk.get("function", {}).get("arguments", "")
                            tool_calls_buffer[idx]["arguments"] += new_args
                            
                        elif chunk_type == "error":
                            error_content = chunk.get("content", "")
                            logger.error(f"LLM Error: {error_content}")
                            # [修复]当Tool call parameter error时, 尝试不使用Tool重新请求
                            if "invalid tool call arguments" in error_content:
                                logger.warning("Tool call parameter error, retrying without tools")
                                # 标记为ToolError, 后续会尝试From文本中提取Tool调用
                                tool_call_error = True
                            else:
                                yield {"type": "content", "content": error_content}
                            
                except Exception as e:
                    logger.error(f"LLM Call failed: {e}")
                    yield {"type": "error", "content": f"[Error: {str(e)}]", "metadata": metadata}
                    return
                
                # [修复]如果发生Tool调用Error, 尝试不使用Tool重新请求
                if tool_call_error:
                    logger.warning("Tool call error detected, retrying without tools")
                    try:
                        # 不使用Tool重新请求
                        async for chunk in self.services["llm"].stream_chat(messages, tools=None, model=current_model):
                            chunk_type = chunk.get("type")
                            if chunk_type == "content":
                                content = chunk.get("content", "")
                                full_response_content += content
                                yield {"type": "content", "content": content}
                            elif chunk_type == "error":
                                error_content = chunk.get("content", "")
                                logger.error(f"LLM Error: {error_content}")
                                yield {"type": "content", "content": error_content}
                        
                        # 尝试From文本中提取Tool调用
                        extracted_tool_calls = self._extract_tool_calls_from_text(full_response_content)
                        if extracted_tool_calls:
                            logger.info(f"Extracted from text {len(extracted_tool_calls)}  tool calls")
                            # 将提取的Tool调用转换为 tool_calls_buffer 格式
                            for idx, match in enumerate(extracted_tool_calls):
                                tool_calls_buffer[idx] = {
                                    "id": f"extracted-{idx}",
                                    "name": match["name"],
                                    "arguments": match["arguments"]
                                }
                        else:
                            # 没有提取到Tool调用, 直接返回
                            await self._update_user_context(session_id, message, full_response_content)
                            metadata["processing_time"] = round(time.time() - start_time, 2)
                            
                            # 转换 memories数据格式, 适配前端显示
                            if metadata["memory_retrieval"]["sources"]:
                                metadata["retrieved_memories"] = [
                                    {
                                        "id": source["id"],
                                        "content": source["content"],
                                        "similarity": source.get("similarity", 0)
                                    }
                                    for source in metadata["memory_retrieval"]["sources"]
                                ]
                            
                            yield {
                                "type": "complete",
                                "content": full_response_content,
                                "metadata": metadata
                            }
                            return
                    except Exception as e:
                        logger.error(f"Retry without tools failed: {e}")
                        yield {"type": "error", "content": f"[Error: {str(e)}]", "metadata": metadata}
                        return
                
                # ProcessingTool调用
                if tool_calls_buffer:
                    logger.info(f"Processing {len(tool_calls_buffer)}  tool calls")

                    # 验证和修复Tool call parameters
                    for idx, tool_data in tool_calls_buffer.items():
                        args = tool_data.get("arguments", "")
                        if args:
                            # 确保arguments是字符串
                            if not isinstance(args, str):
                                try:
                                    args = json.dumps(args)
                                    tool_calls_buffer[idx]["arguments"] = args
                                    logger.info(f"Converting non-string parameters to JSON string: {args}")
                                except Exception:
                                    # 如果转换 failed, 使用空对象
                                    tool_calls_buffer[idx]["arguments"] = "{}"
                                    logger.warning(f"Parameter type conversion failed, using empty object")
                            else:
                                # 尝试修复JSON格式
                                try:
                                    # 先尝试直接解析
                                    json.loads(args)
                                except json.JSONDecodeError:
                                    # JSONParse failed, 使用修复方法
                                    try:
                                        fixed_args = self._fix_json_arguments(args)
                                        json.loads(fixed_args)
                                        tool_calls_buffer[idx]["arguments"] = fixed_args
                                        logger.info(f"Fixed tool call parameters: {fixed_args}")
                                    except Exception:
                                        # 如果修复 failed, 使用空对象
                                        tool_calls_buffer[idx]["arguments"] = "{}"
                                        logger.warning(f"Tool call parameter fix failed, using empty object")
                        else:
                            # 如果没有参数, 使用空对象
                            tool_calls_buffer[idx]["arguments"] = "{}"

                    # [防死循环保护]检查是否重复调用同一 tools
                    current_call_keys = []
                    for idx, tool_data in tool_calls_buffer.items():
                        call_key = f"{tool_data['name']}:{tool_data['arguments']}"
                        current_call_keys.append(call_key)

                    # 检查最近3轮是否有重复
                    if not hasattr(self, '_recent_tool_calls'):
                        self._recent_tool_calls = []

                    repeat_count = sum(1 for key in current_call_keys if key in self._recent_tool_calls)
                    # 只有当重复次数超过阈值 (至少3次重复) 且最近记录中有较多重复时才判定为循环
                    if repeat_count >= 3 and len(self._recent_tool_calls) >= 5:
                        logger.warning(f"Detected repeated tool call loop, repeat count: {repeat_count}/{len(current_call_keys)}")
                        yield {
                            "type": "content",
                            "content": "\n[系统提示: 检测到Tool调用循环, already自动停止.请尝试用不同的方式Description您的需求.]\n"
                        }
                        metadata["processing_time"] = round(time.time() - start_time, 2)
                        
                        # 转换 memories数据格式, 适配前端显示
                        if metadata["memory_retrieval"]["sources"]:
                            metadata["retrieved_memories"] = [
                                {
                                    "id": source["id"],
                                    "content": source["content"],
                                    "similarity": source.get("similarity", 0)
                                }
                                for source in metadata["memory_retrieval"]["sources"]
                            ]
                        
                        yield {
                            "type": "complete",
                            "content": full_response_content + "\n[因检测到循环而提前结束]",
                            "metadata": metadata
                        }
                        return

                    # 记录当前调用
                    self._recent_tool_calls.extend(current_call_keys)
                    # 只保留最近10 记录
                    self._recent_tool_calls = self._recent_tool_calls[-10:]

                    assistant_msg = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": []
                    }
                    
                    for idx, tool_data in tool_calls_buffer.items():
                        assistant_msg["tool_calls"].append({
                            "id": tool_data["id"],
                            "type": "function",
                            "function": {
                                "name": tool_data["name"],
                                "arguments": tool_data["arguments"]
                            }
                        })
                    
                    messages.append(assistant_msg)
                    
                    # 执行Tool
                    for idx, tool_call in enumerate(assistant_msg["tool_calls"]):
                        tool_id = tool_call.get("id", f"call-{idx}")
                        func_name = tool_call["function"]["name"]
                        func_args_str = tool_call["function"]["arguments"]
                        
                        # ProcessingToolName问题
                        if "," in func_name:
                            func_name = func_name.split(",")[0].strip()
                        elif "system_info" in func_name:
                            func_name = "system_info"
                        elif "process_manager" in func_name:
                            func_name = "process_manager"
                        elif "file_manager" in func_name:
                            func_name = "file_manager"
                        
                        # 通知前端
                        yield {
                            "type": "tool_call_notification",
                            "content": f"\n[正在执行: {func_name}...]\n"
                        }
                        
                        try:
                            logger.info(f"Tool call parameters: func_name={func_name}, func_args_str={func_args_str}")
                            if isinstance(func_args_str, dict):
                                func_args = func_args_str
                            else:
                                # [增强修复]使用专门的JSON修复方法Processing各种格式问题
                                if func_args_str:
                                    # 先使用修复方法Processing常见JSON格式问题
                                    func_args_str = self._fix_json_arguments(func_args_str)
                                    # 确保参数是有效的 JSON
                                    try:
                                        func_args = json.loads(func_args_str)
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"JSONParse failed, attempting secondary fix: {e}")
                                        # 二次修复: 尝试更激进的修复
                                        try:
                                            # 移除所有非JSON字符, 只保留 {...} Content
                                            json_match = re.search(r'\{.*\}', func_args_str, re.DOTALL)
                                            if json_match:
                                                func_args_str = json_match.group(0)
                                                func_args = json.loads(func_args_str)
                                            else:
                                                func_args = {}
                                        except Exception:
                                            # 如果参数不是有效的 JSON, 使用空对象
                                            func_args = {}
                                else:
                                    func_args = {}
                            if not isinstance(func_args, dict):
                                func_args = {}
                            logger.info(f"Parsed parameters: {func_args}")
                            action, params = self._parse_tool_args(func_name, func_args)
                            
                            # 执行Tool
                            if func_name in self.skill_manager.skills:
                                tool_result = await self.skill_manager.execute_tool(func_name, action, params)
                                logger.info(f"Tool execution result: {tool_result}")
                            elif func_name in self.plugin_manager.get_all_plugins():
                                # 执行插件
                                plugin_result = await self.plugin_manager.execute_plugin(func_name, action, params)
                                tool_result = json.dumps(plugin_result, ensure_ascii=False)
                                logger.info(f"Plugin execution result: {tool_result}")
                            else:
                                tool_result = json.dumps({"status": "error", "message": f"Tooldoes not exist: {func_name}"})
                            
                            # 记录Tool使用
                            metadata["tools_used"].append({
                                "name": func_name,
                                "action": action,
                                "params": params
                            })

                            # [Adapter模式]使用Adapter格式化Tool消息
                            # 截断Tool, 防止消息过长
                            # 网络诊断和System InfoTool允许更长的
                            if func_name == "network_diagnostic":
                                max_length = 10000
                            elif func_name == "system_info":
                                max_length = 8000
                            else:
                                max_length = 2000
                            if isinstance(tool_result, str):
                                tool_result = self._truncate_tool_result(tool_result, max_length=max_length)
                            elif isinstance(tool_result, dict):
                                tool_result = json.dumps(tool_result, ensure_ascii=False)
                                tool_result = self._truncate_tool_result(tool_result, max_length=max_length)
                            
                            # 将Tool execution result返回给用户
                            # 对于网络诊断Tool, 格式化使其更易读
                            if func_name == "network_diagnostic":
                                try:
                                    result_data = json.loads(tool_result)
                                    if result_data.get("status") == "success":
                                        data = result_data.get("data", {})
                                        formatted_result = self._format_network_diagnostic_result(data)
                                        yield {
                                            "type": "content",
                                            "content": f"\n**网络诊断: **\n{formatted_result}\n"
                                        }
                                    else:
                                        yield {
                                            "type": "content",
                                            "content": f"\n**网络诊断: **\n{tool_result}\n"
                                        }
                                except Exception:
                                    yield {
                                        "type": "content",
                                        "content": f"\n**网络诊断: **\n{tool_result}\n"
                                    }
                            elif func_name == "security_monitor":
                                try:
                                    result_data = json.loads(tool_result)
                                    if result_data.get("status") == "success":
                                        data = result_data.get("data", {})
                                        formatted_result = self._format_security_monitor_result(data)
                                        yield {
                                            "type": "content",
                                            "content": f"\n**安全监控: **\n{formatted_result}\n"
                                        }
                                    else:
                                        yield {
                                            "type": "content",
                                            "content": f"\n**安全监控: **\n{tool_result}\n"
                                        }
                                except Exception:
                                    yield {
                                        "type": "content",
                                        "content": f"\n**安全监控: **\n{tool_result}\n"
                                    }
                            else:
                                yield {
                                    "type": "content",
                                    "content": f"\n**Tool execution result: **\n{tool_result}\n"
                                }
                            
                            tool_message = adapter.format_tool_message(
                                tool_call_id=tool_id,
                                name=func_name,
                                content=tool_result
                            )
                            messages.append(tool_message)
                            
                        except Exception as e:
                            error_result = json.dumps({"status": "error", "message": str(e)})
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": func_name,
                                "content": error_result
                            })
                    
                    # 继续下一轮
                    continue
                
                # 如果没有原生Tool调用, 尝试From文本Content中提取Tool调用 (适配不支持原生 function calling 的Model) 
                extracted_tool_calls = self._extract_tool_calls_from_text(full_response_content)
                if extracted_tool_calls:
                    logger.info(f"Extracted tool calls from text: {len(extracted_tool_calls)}  ")
                    
                    # 清理文本中的Tool调用代码Chunk和Status提示
                    cleaned_content = full_response_content
                    for match in extracted_tool_calls:
                        cleaned_content = cleaned_content.replace(match["full_match"], "").strip()
                    
                    # 清理LLM输出的Status提示和Error信息
                    cleaned_content = re.sub(r'\[正在执行:\s*[^\]]+\]\s*', '', cleaned_content)
                    cleaned_content = re.sub(r'\[API Error:[^\]]+\]\s*', '', cleaned_content)
                    # 清理空行
                    cleaned_content = re.sub(r'\n\s*\n', '\n', cleaned_content)
                    cleaned_content = cleaned_content.strip()
                    
                    # 如果清理后还有Content, 输出清理后的Content
                    if cleaned_content.strip():
                        full_response_content = cleaned_content
                        yield {
                            "type": "content",
                            "content": cleaned_content + "\n"
                        }
                    
                    # 逐 执行提取到的Tool调用
                    assistant_msg = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": []
                    }
                    
                    for idx, match in enumerate(extracted_tool_calls):
                        try:
                            func_name = match["name"]
                            func_args_str = match["arguments"]
                            func_args = json.loads(func_args_str) if func_args_str else {}
                            if not isinstance(func_args, dict):
                                func_args = {}
                            action, params = self._parse_tool_args(func_name, func_args)
                            
                            assistant_msg["tool_calls"].append({
                                "id": f"extracted-{idx}",
                                "type": "function",
                                "function": {
                                    "name": func_name,
                                    "arguments": func_args_str
                                }
                            })
                            
                            # 通知前端
                            yield {
                                "type": "tool_call_notification",
                                "content": f"\n[正在执行: {func_name}...]\n"
                            }
                            
                            # 执行Tool
                            if func_name in self.skill_manager.skills:
                                tool_result = await self.skill_manager.execute_tool(func_name, action, params)
                                logger.info(f"Tool execution result: {tool_result}")
                            elif func_name in self.plugin_manager.get_all_plugins():
                                # 执行插件
                                plugin_result = await self.plugin_manager.execute_plugin(func_name, action, params)
                                tool_result = json.dumps(plugin_result, ensure_ascii=False)
                                logger.info(f"Plugin execution result: {tool_result}")
                            else:
                                tool_result = json.dumps({"status": "error", "message": f"Tooldoes not exist: {func_name}"})
                            
                            # 记录Tool使用
                            metadata["tools_used"].append({
                                "name": func_name,
                                "action": action,
                                "params": params
                            })

                            # [Adapter模式]使用Adapter格式化Tool消息
                            # 截断Tool, 防止消息过长
                            # 网络诊断和System InfoTool允许更长的
                            if func_name == "network_diagnostic":
                                max_length = 10000
                            elif func_name == "system_info":
                                max_length = 8000
                            else:
                                max_length = 2000
                            if isinstance(tool_result, str):
                                tool_result = self._truncate_tool_result(tool_result, max_length=max_length)
                            elif isinstance(tool_result, dict):
                                tool_result = json.dumps(tool_result, ensure_ascii=False)
                                tool_result = self._truncate_tool_result(tool_result, max_length=max_length)
                            
                            # 将Tool execution result返回给用户
                            # 对于网络诊断Tool, 格式化使其更易读
                            if func_name == "network_diagnostic":
                                try:
                                    result_data = json.loads(tool_result)
                                    if result_data.get("status") == "success":
                                        data = result_data.get("data", {})
                                        formatted_result = self._format_network_diagnostic_result(data)
                                        yield {
                                            "type": "content",
                                            "content": f"\n**网络诊断: **\n{formatted_result}\n"
                                        }
                                    else:
                                        yield {
                                            "type": "content",
                                            "content": f"\n**网络诊断: **\n{tool_result}\n"
                                        }
                                except Exception:
                                    yield {
                                        "type": "content",
                                        "content": f"\n**网络诊断: **\n{tool_result}\n"
                                    }
                            elif func_name == "security_monitor":
                                try:
                                    result_data = json.loads(tool_result)
                                    if result_data.get("status") == "success":
                                        data = result_data.get("data", {})
                                        formatted_result = self._format_security_monitor_result(data)
                                        yield {
                                            "type": "content",
                                            "content": f"\n**安全监控: **\n{formatted_result}\n"
                                        }
                                    else:
                                        yield {
                                            "type": "content",
                                            "content": f"\n**安全监控: **\n{tool_result}\n"
                                        }
                                except Exception:
                                    yield {
                                        "type": "content",
                                        "content": f"\n**安全监控: **\n{tool_result}\n"
                                    }
                            else:
                                yield {
                                    "type": "content",
                                    "content": f"\n**Tool execution result: **\n{tool_result}\n"
                                }
                            
                            tool_message = adapter.format_tool_message(
                                tool_call_id=f"extracted-{idx}",
                                name=func_name,
                                content=tool_result
                            )
                            messages.append(tool_message)
                        except Exception as e:
                            logger.error(f"Tool call extraction failed: {e}")
                            error_result = json.dumps({"status": "error", "message": str(e)})
                            messages.append({
                                "role": "tool",
                                "tool_call_id": f"extracted-{idx}",
                                "name": match["name"],
                                "content": error_result
                            })
                    
                    messages.append(assistant_msg)
                    # Tool执行完, 进入下一轮循环
                    continue
                
                # 没有Tool调用, 结束循环
                logger.info(f"Final reply: {full_response_content[:100]}...")
                await self._update_user_context(session_id, message, full_response_content)
                
                metadata["processing_time"] = round(time.time() - start_time, 2)
                
                # 转换 memories数据格式, 适配前端显示
                if metadata["memory_retrieval"]["sources"]:
                    metadata["retrieved_memories"] = [
                        {
                            "id": source["id"],
                            "content": source["content"],
                            "similarity": source.get("similarity", 0)
                        }
                        for source in metadata["memory_retrieval"]["sources"]
                    ]
                
                yield {
                    "type": "complete",
                    "content": full_response_content,
                    "metadata": metadata
                }
                break
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            metadata["processing_time"] = round(time.time() - start_time, 2)
            yield {"type": "error", "content": f"[Error: {str(e)}]", "metadata": metadata}
    
    def _extract_tool_calls_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        From文本Content中提取Tool调用 (适配不支持原生 function calling 的Model) 
        
        支持的格式: 
        1. ```json\ntool_name\n{...}\n```
        2. tool_name { ... }
        3. `tool_name` { ... }
        
        Returns:
            List[Dict]: [{"name": "tool_name", "arguments": "...", "full_match": "..."}, ...]
        """
        results = []
        
        # 先清理掉Error信息中的 JSON, 避免误匹配
        # 移除类似 [API Error: ...]{...} 这样的Content
        text_cleaned = re.sub(r'\[API Error:[^\]]*\]\s*', '', text)
        
        # 模式1: 代码Chunk中的Tool调用
        # 匹配: ```json\ntool_name\n{...}\n``` 或 ```\ntool_name { ... }\n```
        code_block_pattern = r'```(?:json)?\s*([a-zA-Z_]+)\s*({[\s\S]*?})\s*```'
        matches = re.finditer(code_block_pattern, text_cleaned)
        for match in matches:
            tool_name = match.group(1).strip()
            args_json = match.group(2).strip()
            full_match = match.group(0)
            # 验证是否是有效的 JSON
            try:
                # 先尝试直接解析
                json.loads(args_json)
                results.append({
                    "name": tool_name,
                    "arguments": args_json,
                    "full_match": match.group(0)
                })
            except json.JSONDecodeError:
                # JSON Parse failed, 使用完整的修复方法修复常见的格式问题
                try:
                    fixed_args = self._fix_json_arguments(args_json)
                    json.loads(fixed_args)
                    results.append({
                        "name": tool_name,
                        "arguments": fixed_args,
                        "full_match": match.group(0)
                    })
                except Exception:
                    # JSON 无效, skip
                    continue
            except Exception:
                # 其他Error, skip
                continue
        
        # 模式2: 行内Tool调用 tool_name { ... }
        # 使用更严格的匹配: ToolName必须后跟着空格然后是 {
        inline_pattern = r'\b([a-zA-Z_]+)\b\s+\{([\s\S]*?)}'
        matches = re.finditer(inline_pattern, text_cleaned)
        for match in matches:
            tool_name = match.group(1).strip()
            args_json = "{" + match.group(2).strip() + "}"
            full_match = match.group(0)
            # 检查是否是already知ToolName
            known_tools = ["system_info", "file_manager", "process_manager", 
                         "security_monitor", "network_diagnostic", "code_executor",
                         "search", "system_control"]
            if tool_name in known_tools:
                # 验证 JSON 是否有效
                try:
                    # 先尝试直接解析
                    json.loads(args_json)
                    # 避免重复匹配
                    if not any(r["name"] == tool_name and r["arguments"] == args_json for r in results):
                        results.append({
                            "name": tool_name,
                            "arguments": args_json,
                            "full_match": full_match
                        })
                except json.JSONDecodeError:
                    # JSON Parse failed, 使用完整的修复方法修复常见的格式问题
                    try:
                        fixed_args = self._fix_json_arguments(args_json)
                        json.loads(fixed_args)
                        # 避免重复匹配
                        if not any(r["name"] == tool_name and r["arguments"] == fixed_args for r in results):
                            results.append({
                                "name": tool_name,
                                "arguments": fixed_args,
                                "full_match": full_match
                            })
                    except Exception:
                        # JSON 无效, skip
                        continue
                except Exception:
                    # 其他Error, skip
                    continue
        
        # 模式3: tool_call_name + tool_call_arguments 格式
        # 匹配: tool_call_name\n  tool_name\n  tool_call_arguments\n  {...}
        tc_pattern = r'tool_call_name\s*([a-zA-Z_]+)\s*tool_call_arguments\s*({[\s\S]*?})'
        matches = re.finditer(tc_pattern, text_cleaned)
        for match in matches:
            tool_name = match.group(1).strip()
            args_json = match.group(2).strip()
            full_match = match.group(0)
            try:
                args_json = self._fix_json_arguments(args_json)
                json.loads(args_json)
                results.append({
                    "name": tool_name,
                    "arguments": args_json,
                    "full_match": full_match
                })
            except Exception:
                continue
        
        # 模式4: 宽松匹配 - ToolName后跟着任何JSON对象 (支持多行) 
        # 匹配各种格式: tool_name { ... }, tool_name\n { ... }, tool_name\n{...}
        relaxed_pattern = r'\b([a-zA-Z_]+)\b\s*(\{[\s\S]*?\})'
        matches = re.finditer(relaxed_pattern, text_cleaned)
        for match in matches:
            tool_name = match.group(1).strip()
            args_json = match.group(2).strip()
            full_match = match.group(0)
            # 检查是否是already知ToolName
            known_tools = ["system_info", "file_manager", "process_manager", 
                         "security_monitor", "network_diagnostic", "code_executor",
                         "search", "system_control"]
            if tool_name in known_tools:
                # 使用完整修复方法ProcessingJSON格式
                try:
                    fixed_args = self._fix_json_arguments(args_json)
                    json.loads(fixed_args)
                    # 避免重复匹配
                    if not any(r["name"] == tool_name and r["arguments"] == fixed_args for r in results):
                        results.append({
                            "name": tool_name,
                            "arguments": fixed_args,
                            "full_match": full_match
                        })
                except Exception:
                    continue
        
        # 模式5: 超级宽松匹配 - 只要FoundJSON对象, 前面很可能就是ToolName
        # 匹配: ... tool_name ... {...}
        any_json_pattern = r'([a-zA-Z_]+)[^\n{}]*({[\s\S]*?})'
        matches = re.finditer(any_json_pattern, text_cleaned)
        for match in matches:
            tool_name = match.group(1).strip()
            args_json = match.group(2).strip()
            full_match = match.group(0)
            known_tools = ["system_info", "file_manager", "process_manager", 
                         "security_monitor", "network_diagnostic", "code_executor",
                         "search", "system_control"]
            if tool_name in known_tools:
                try:
                    fixed_args = self._fix_json_arguments(args_json)
                    json.loads(fixed_args)
                    if not any(r["name"] == tool_name and r["arguments"] == fixed_args for r in results):
                        results.append({
                            "name": tool_name,
                            "arguments": fixed_args,
                            "full_match": full_match
                        })
                except Exception:
                    continue
        
        logger.info(f"Extracted from text {len(results)}  valid tool calls")
        return results

    def _fix_json_arguments(self, json_str: str) -> str:
        """
        修复Tool call parameters中的JSON格式问题
        
        Args:
            json_str: 原始JSON字符串
            
        Returns:
            修复后的JSON字符串
        """
        if not json_str or not isinstance(json_str, str):
            return json_str
            
        # 1. 修复Windows路径反斜杠转义问题
        json_str = json_str.replace('\\\\', '/')
        
        # 2. 修复常见的JSON格式Error
        # 修复单引号包围的字符串
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        
        # 3. 修复缺少引号的键名
        json_str = re.sub(r'(\{|\,|\s)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # 4. 修复尾随逗号
        json_str = re.sub(r',\s*}(?=\s*$)', '}', json_str)
        json_str = re.sub(r',\s*\](?=\s*$)', ']', json_str)
        
        # Register意: 不要替换true/false/null, 这些是JSON关键字, 不是Python关键字
        
        return json_str

    def _truncate_tool_result(self, result: str, max_length: int = 3000) -> str:
        """
        截断Tool, 防止消息过长导致APIError

        Args:
            result: Tool返回的JSON字符串
            max_length: 最大允许Length

        Returns:
            截断后的JSON字符串
        """
        if len(result) <= max_length:
            return result

        try:
            # 尝试解析为JSON
            data = json.loads(result)

            # 如果是列表, 截断列表
            if isinstance(data, list):
                truncated_list = data[:20]  # 最多保留20项
                if len(data) > 20:
                    truncated_list.append({"_truncated": True, "total_items": len(data), "shown": 20})
                truncated = json.dumps(truncated_list, ensure_ascii=False)
                if len(truncated) > max_length:
                    truncated = json.dumps({
                        "_truncated": True,
                        "message": f"过长, already截断.原始Length: {len(result)} 字符"
                    }, ensure_ascii=False)
                return truncated

            # 如果是字典, 尝试截断其中的列表
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 20:
                        data[key] = value[:20]
                        data["_truncated"] = True
                        data["_truncated_key"] = key
                        data["_total_items"] = len(value)
                truncated = json.dumps(data, ensure_ascii=False)
                if len(truncated) > max_length:
                    truncated = json.dumps({
                        "_truncated": True,
                        "message": f"过长, already截断.原始Length: {len(result)} 字符",
                        "keys": list(data.keys())[:10]  # 只显示前10 键
                    }, ensure_ascii=False)
                return truncated

            # 其他type, 直接截断字符串
            return result[:max_length] + "...[already截断]"

        except json.JSONDecodeError:
            # 不是有效的JSON, 直接截断字符串
            return result[:max_length] + "...[already截断]"

    def _get_tools_for_model(self, model_name: str) -> Optional[List[Dict[str, Any]]]:
        """根据ModelName决定是否enabled tool calls - returning all 11  tools!"""
        tools_supported_models = [
            "qwen3-vl:4b", "qwen3-vl:8b", "qwen3:4b", "qwen3:8b", "qwen2.5:7b",
            "kimi-k2.5:cloud", "minimax-m2.7:cloud", "qwen3-vl:235b-cloud",
            "deepseek-v3.1:671b-cloud", "glm-4.6:cloud"
        ]
        
        tools_unsupported_models = [
            "gemma3:1b", "gemma3:4b", "deepseek-r1:7b", "deepseek-r1:1.5b"
        ]
        
        if model_name in tools_unsupported_models:
            logger.info(f"Model {model_name} does not support tool calls, disabled")
            return None
        
        # 对于其他所有Model, 都返回所有 11  tools!From SkillManager 中Get
        logger.info(f"Model {model_name} enabled tool calls - returning all {len(self.skill_manager.skills)}  tools")
        return self.skill_manager.get_tool_definitions()
    
    def _get_user_context(self, session_id: str) -> Dict:
        """Get用户上下文"""
        if session_id not in self.user_contexts:
            self.user_contexts[session_id] = {"history": []}
        return self.user_contexts[session_id]
    
    async def _update_user_context(self, session_id: str, message: str, response: str):
        """Update用户上下文"""
        ctx = self._get_user_context(session_id)
        ctx["history"].append({"u": message, "a": response})
        if len(ctx["history"]) > 20:
            ctx["history"] = ctx["history"][-20:]
        
        # 存储到 memories系统
        if self.memory_system:
            try:
                memory_content = f"会话: {session_id}\n\n用户: {message}\n助手: {response}"
                await self.memory_system.store_experience(
                    content=memory_content,
                    context=f"Session ID: {session_id}",
                    importance=0.5,
                    tags=['conversation', 'interaction']
                )
            except Exception as e:
                logger.error(f"Memory storage failed: {e}")
        
        # From客户交流中学习
        if self.autonomous_learner:
            try:
                await self.autonomous_learner.learn_from_customer_interaction(
                    user_input=message,
                    assistant_response=response,
                    context=f"Session ID: {session_id}"
                )
            except Exception as e:
                logger.error(f"Learning from client interaction failed: {e}")
    
    async def run_autonomous_learning(self):
        """
        运行自主学习
        使系统能够自主查找资料, 学习和自我提高
        """
        if not self.autonomous_learner:
            logger.error("Autonomous learner not initialized")
            return {"error": "Autonomous learner not initialized"}
        
        try:
            logger.info("[AI] Starting autonomous learning...")
            result = await self.autonomous_learner.run_autonomous_learning_cycle()
            logger.info("[OK] Autonomous learning complete")
            return result
        except Exception as e:
            logger.error(f"Error during autonomous learning: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
            return {"error": str(e)}

    def _format_network_diagnostic_result(self, data: Dict[str, Any]) -> str:
        """
        格式化网络诊断, 使其更易读
        
        Args:
            data: 网络诊断数据
            
        Returns:
            格式化后的字符串
        """
        result = []
        
        # 格式化网络接口信息
        if "interfaces" in data:
            interfaces = data["interfaces"]
            result.append("### 网络接口信息")
            
            for iface_name, iface_info in interfaces.items():
                result.append(f"\n**{iface_name}**")
                
                # 显示地址信息
                if "addresses" in iface_info and iface_info["addresses"]:
                    result.append("  地址:")
                    for addr in iface_info["addresses"]:
                        family = addr.get("family", "")
                        address = addr.get("address", "")
                        if "AddressFamily.AF_INET" in family:
                            result.append(f"    IPv4: {address}")
                        elif "AddressFamily.AF_INET6" in family:
                            result.append(f"    IPv6: {address}")
                
                # 显示Status信息
                if "stats" in iface_info:
                    stats = iface_info["stats"]
                    status = "在线" if stats.get("is_up") else "离线"
                    speed = stats.get("speed", "未知")
                    result.append(f"  Status: {status}")
                    result.append(f"  速度: {speed}")
                
                # 显示IO统计
                if "io" in iface_info:
                    io = iface_info["io"]
                    result.append(f"  流量统计:")
                    result.append(f"    发送: {io.get('bytes_sent', '0')}")
                    result.append(f"    接收: {io.get('bytes_recv', '0')}")
        
        # 格式化Connect信息
        if "connections" in data:
            conn_info = data["connections"]
            result.append("\n### 网络Connect信息")
            result.append(f"总Connect数: {conn_info.get('total_connections', 0)}")
            
            # 统计ConnectStatus
            if "connections" in conn_info and conn_info["connections"]:
                status_count = {}
                process_count = {}
                
                for conn in conn_info["connections"]:
                    status = conn.get("status", "UNKNOWN")
                    process = conn.get("process_name", "未知")
                    
                    status_count[status] = status_count.get(status, 0) + 1
                    process_count[process] = process_count.get(process, 0) + 1
                
                # 显示ConnectStatus统计
                result.append("\nConnectStatus:")
                for status, count in sorted(status_count.items(), key=lambda x: -x[1]):
                    if status != "NONE":
                        result.append(f"  - {status}: {count}")
                
                # 显示主要进程
                result.append("\n主要网络进程:")
                sorted_processes = sorted(process_count.items(), key=lambda x: -x[1])[:5]
                for process, count in sorted_processes:
                    if process != "未知":
                        result.append(f"  - {process}: {count}  Connect")
                
                # 只显示重要的外部Connect
                important_connections = []
                for conn in conn_info["connections"]:
                    status = conn.get("status", "")
                    raddr = conn.get("raddr", "")
                    process = conn.get("process_name", "")
                    
                    # 只显示already建立的外部Connect
                    if status == "ESTABLISHED" and raddr and raddr != "None" and process and process != "N/A":
                        important_connections.append(conn)
                
                if important_connections:
                    result.append("\n重要外部Connect (前5 ):")
                    for i, conn in enumerate(important_connections[:5], 1):
                        laddr = conn.get("laddr", "N/A")
                        raddr = conn.get("raddr", "N/A")
                        process = conn.get("process_name", "N/A")
                        result.append(f"  {i}. {process} -> {raddr}")
        
        # 格式化PingTest
        if "ping_tests" in data:
            ping_tests = data["ping_tests"]
            result.append("\n### 网络连通性Test")
            
            for test in ping_tests:
                target = test.get("target", "未知")
                test_result = test.get("result", "Test failed")
                if " successful" in test_result:
                    result.append(f"[OK] {target}: {test_result}")
                else:
                    result.append(f"[ERR] {target}: {test_result}")
        
        # 格式化URL检测
        if "url_tests" in data:
            url_tests = data["url_tests"]
            result.append("\n### 网站访问Test")
            
            for test in url_tests:
                url = test.get("url", "未知")
                status = test.get("status", "Test failed")
                if status == "可访问":
                    result.append(f"[OK] {url}")
                else:
                    result.append(f"[ERR] {url}: {status}")
        
        return "\n".join(result)

    def _format_security_monitor_result(self, data: Dict[str, Any]) -> str:
        """
        格式化安全监控, 使其更易读
        
        Args:
            data: 安全监控数据
            
        Returns:
            格式化后的字符串
        """
        result = []
        
        # 格式化端口检查
        if "open_ports" in data:
            open_ports = data["open_ports"]
            result.append("### 端口安全检查")
            result.append(f"检查的敏感端口数: {data.get('sensitive_ports_checked', 0)}")
            result.append(f"开放的敏感端口数: {data.get('open_sensitive_ports', 0)}")
            
            if open_ports:
                result.append("\n开放的敏感端口:")
                for port_info in open_ports:
                    port = port_info.get("port")
                    address = port_info.get("address")
                    status = port_info.get("status")
                    process_name = port_info.get("process_name", "未知")
                    result.append(f"  - 端口 {port} ({address}) - {status} - {process_name}")
            else:
                result.append("\n没有发现开放的敏感端口")
        
        # 格式化进程扫描
        if "processes" in data:
            processes = data["processes"]
            result.append("\n### 进程安全检查")
            result.append(f"检查的可疑进程Name: {data.get('suspicious_process_names', 0)}")
            result.append(f"发现的可疑进程数: {data.get('found_suspicious_processes', 0)}")
            
            if processes:
                result.append("\n发现的可疑进程:")
                for proc in processes[:10]:  # 只显示前10 进程
                    pid = proc.get("pid")
                    name = proc.get("name")
                    username = proc.get("username", "未知")
                    result.append(f"  - {name} (PID: {pid}) - 用户: {username}")
            else:
                result.append("\n没有发现可疑进程")
        
        # 格式化系统检查
        if "system" in data:
            system_data = data["system"]
            result.append("\n### 系统安全检查")
            
            if "os" in system_data:
                os_info = system_data["os"]
                result.append(f"操作系统: {os_info.get('system')} {os_info.get('release')}")
            
            if "uptime" in system_data:
                result.append(f"系统运行时间: {system_data['uptime']}")
            
            if "users" in system_data and system_data["users"]:
                result.append("\n系统用户:")
                for user in system_data["users"]:
                    name = user.get("name")
                    full_name = user.get("full_name", "")
                    if full_name:
                        result.append(f"  - {name} ({full_name})")
                    else:
                        result.append(f"  - {name}")
        
        # 格式化综合
        if "ports" in data and "processes" in data and "system" in data:
            result = []
            result.append("### 安全监控综合报告")
            
            # 端口部分
            ports_data = data["ports"]
            result.append("\n**端口安全**")
            result.append(f"- 检查的敏感端口: {ports_data.get('sensitive_ports_checked', 0)}")
            result.append(f"- 开放的敏感端口: {ports_data.get('open_sensitive_ports', 0)}")
            
            if ports_data.get("open_ports"):
                result.append("\n开放的端口:")
                for port_info in ports_data["open_ports"]:
                    port = port_info.get("port")
                    address = port_info.get("address")
                    process = port_info.get("process_name", "未知")
                    result.append(f"  - 端口 {port} ({address}) - {process}")
            
            # 进程部分
            processes_data = data["processes"]
            result.append("\n**进程安全**")
            result.append(f"- 检查的可疑进程type: {processes_data.get('suspicious_process_names', 0)}")
            result.append(f"- 发现的可疑进程: {processes_data.get('found_suspicious_processes', 0)}")
            
            if processes_data.get("processes"):
                result.append("\n运行的可疑进程:")
                for proc in processes_data["processes"][:10]:
                    name = proc.get("name")
                    pid = proc.get("pid")
                    result.append(f"  - {name} (PID: {pid})")
            
            # 系统部分
            system_data = data["system"]
            result.append("\n**System Info**")
            if "os" in system_data:
                os_info = system_data["os"]
                result.append(f"- 操作系统: {os_info.get('system')} {os_info.get('release')}")
            if "uptime" in system_data:
                result.append(f"- 运行时间: {system_data['uptime']}")
        
        return "\n".join(result)


# 全局助手实例
assistant = Assistant()
