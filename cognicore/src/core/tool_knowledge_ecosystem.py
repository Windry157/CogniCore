#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToolRegister与管理中心
提供Tool的Register, 发现, 调用和管理功能
"""

import os
import json
import importlib
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Tool元数据"""
    tool_id: str
    name: str
    description: str
    category: str
    version: str
    author: str
    tags: List[str]
    parameters: Dict[str, Any]
    return_type: str
    dependencies: List[str]
    examples: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolMetadata':
        return cls(**data)


class ToolRegistry:
    """ToolRegister中心"""
    
    def __init__(self, registry_file: str = "tool_registry.json"):
        """
        InitializationToolRegister中心
        
        Args:
            registry_file: Registry文件路径
        """
        self.registry_file = registry_file
        self.tools: Dict[str, ToolMetadata] = {}
        self.tool_instances: Dict[str, Any] = {}
        self.tool_functions: Dict[str, Callable] = {}
        
        self._load_registry()
        self._register_core_tools()
    
    def _load_registry(self):
        """From文件Load registry"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tools = {
                        tool_id: ToolMetadata.from_dict(tool_data)
                        for tool_id, tool_data in data.get('tools', {}).items()
                    }
                logger.info(f"From {self.registry_file} Loaded {len(self.tools)}  tools")
            except Exception as e:
                logger.error(f"Load registry failed: {e}")
                self.tools = {}
    
    def _save_registry(self):
        """Save registry到文件"""
        try:
            data = {
                'tools': {
                    tool_id: tool.to_dict()
                    for tool_id, tool in self.tools.items()
                },
                'saved_at': self._get_timestamp()
            }
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Registrysaved to {self.registry_file}")
        except Exception as e:
            logger.error(f"Save registry failed: {e}")
    
    def _get_timestamp(self) -> str:
        """Get时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _register_core_tools(self):
        """Register核心Tool"""
        core_tools = [
            ToolMetadata(
                tool_id="search",
                name="SearchTool",
                description="Search互联网信息",
                category="information",
                version="1.0.0",
                author="system",
                tags=["search", "information", "web"],
                parameters={
                    "query": {"type": "string", "required": True, "description": "Search查询"},
                    "limit": {"type": "integer", "required": False, "default": 10}
                },
                return_type="json",
                dependencies=[],
                examples=[
                    {"input": {"query": "天气"}, "output": {"results": []}}
                ]
            ),
            ToolMetadata(
                tool_id="calculator",
                name="计算器",
                description="执行数学计算",
                category="utility",
                version="1.0.0",
                author="system",
                tags=["calculate", "math", "utility"],
                parameters={
                    "expression": {"type": "string", "required": True, "description": "数学表达式"}
                },
                return_type="number",
                dependencies=[],
                examples=[
                    {"input": {"expression": "2+2"}, "output": {"result": 4}}
                ]
            ),
            ToolMetadata(
                tool_id="file_manager",
                name="文件管理器",
                description="管理本地文件",
                category="system",
                version="1.0.0",
                author="system",
                tags=["file", "system", "io"],
                parameters={
                    "operation": {"type": "string", "required": True, "description": "操作type"},
                    "path": {"type": "string", "required": True, "description": "文件路径"},
                    "content": {"type": "string", "required": False, "description": "文件Content"}
                },
                return_type="json",
                dependencies=[],
                examples=[]
            ),
            ToolMetadata(
                tool_id="code_executor",
                name="代码执行器",
                description="执行代码",
                category="development",
                version="1.0.0",
                author="system",
                tags=["code", "execute", "development"],
                parameters={
                    "language": {"type": "string", "required": True, "description": "编程语言"},
                    "code": {"type": "string", "required": True, "description": "代码Content"}
                },
                return_type="json",
                dependencies=["python"],
                examples=[]
            )
        ]
        
        for tool in core_tools:
            if tool.tool_id not in self.tools:
                self.register_tool(tool)
        
        logger.info(f"Registered {len(core_tools)} core tools")
    
    def register_tool(self, metadata: ToolMetadata, instance: Any = None):
        """
        RegisterTool
        
        Args:
            metadata: Tool元数据
            instance: Tool实例
        """
        self.tools[metadata.tool_id] = metadata
        if instance:
            self.tool_instances[metadata.tool_id] = instance
        self._save_registry()
        logger.info(f"RegisteredTool: {metadata.name} ({metadata.tool_id})")
    
    def register_function(self, tool_id: str, func: Callable, metadata: Optional[ToolMetadata] = None):
        """
        Register函数作为Tool
        
        Args:
            tool_id: ToolID
            func: 函数
            metadata: Tool元数据 (可选) 
        """
        self.tool_functions[tool_id] = func
        
        if metadata:
            self.register_tool(metadata)
        else:
            # 自动生成元数据
            auto_metadata = ToolMetadata(
                tool_id=tool_id,
                name=func.__name__,
                description=func.__doc__ or "自动Register的函数",
                category="custom",
                version="1.0.0",
                author="auto",
                tags=["custom", "function"],
                parameters={},
                return_type="any",
                dependencies=[],
                examples=[]
            )
            self.register_tool(auto_metadata)
        
        logger.info(f"Registered function tool: {tool_id}")
    
    def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        """
        GetTool元数据
        
        Args:
            tool_id: ToolID
            
        Returns:
            Tool元数据
        """
        return self.tools.get(tool_id)
    
    def get_tool_instance(self, tool_id: str) -> Optional[Any]:
        """
        GetTool实例
        
        Args:
            tool_id: ToolID
            
        Returns:
            Tool实例
        """
        return self.tool_instances.get(tool_id)
    
    def get_tool_function(self, tool_id: str) -> Optional[Callable]:
        """
        GetTool函数
        
        Args:
            tool_id: ToolID
            
        Returns:
            Tool函数
        """
        return self.tool_functions.get(tool_id)
    
    def list_tools(self, category: str = None, tags: List[str] = None) -> List[ToolMetadata]:
        """
        ListTool
        
        Args:
            category: 类别筛选
            tags: 标签筛选
            
        Returns:
            Tool列表
        """
        tools = list(self.tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        if tags:
            tools = [t for t in tools if any(tag in t.tags for tag in tags)]
        
        return tools
    
    def search_tools(self, query: str) -> List[ToolMetadata]:
        """
        SearchTool
        
        Args:
            query: Search查询
            
        Returns:
            匹配的Tool列表
        """
        query_lower = query.lower()
        results = []
        
        for tool in self.tools.values():
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower() or
                query_lower in ' '.join(tool.tags).lower()):
                results.append(tool)
        
        return results
    
    def get_categories(self) -> List[str]:
        """
        Get所有类别
        
        Returns:
            类别列表
        """
        return list(set(tool.category for tool in self.tools.values()))
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetStatistics
        
        Returns:
            Statistics
        """
        categories = {}
        for tool in self.tools.values():
            categories[tool.category] = categories.get(tool.category, 0) + 1
        
        return {
            "total_tools": len(self.tools),
            "categories": categories,
            "total_functions": len(self.tool_functions),
            "total_instances": len(self.tool_instances)
        }
    
    def execute_tool(self, tool_id: str, **kwargs) -> Any:
        """
        执行Tool
        
        Args:
            tool_id: ToolID
            **kwargs: Tool参数
            
        Returns:
            执行
        """
        # 首先尝试执行Register的函数
        func = self.get_tool_function(tool_id)
        if func:
            try:
                return func(**kwargs)
            except Exception as e:
                logger.error(f"Execute tool function {tool_id}  failed: {e}")
                return {"status": "ERROR", "error": str(e)}
        
        # 然后尝试执行Register的实例
        instance = self.get_tool_instance(tool_id)
        if instance and hasattr(instance, 'execute'):
            try:
                return instance.execute(**kwargs)
            except Exception as e:
                logger.error(f"Execute tool instance {tool_id}  failed: {e}")
                return {"status": "ERROR", "error": str(e)}
        
        return {"status": "ERROR", "error": f"Tool {tool_id} does not exist或不可执行"}


class KnowledgeBase:
    """knowledge base"""
    
    def __init__(self, kb_file: str = "knowledge_base.json"):
        """
        Initializationknowledge base
        
        Args:
            kb_file: knowledge base文件路径
        """
        self.kb_file = kb_file
        self.knowledge: Dict[str, Any] = {}
        self.categories: Dict[str, List[str]] = {}
        self.entities: Dict[str, Dict[str, Any]] = {}
        
        self._load_knowledge_base()
        self._init_core_knowledge()
    
    def _load_knowledge_base(self):
        """From文件Loadknowledge base"""
        if os.path.exists(self.kb_file):
            try:
                with open(self.kb_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.knowledge = data.get('knowledge', {})
                    self.categories = data.get('categories', {})
                    self.entities = data.get('entities', {})
                logger.info(f"From {self.kb_file} Loaded {len(self.knowledge)}   knowledge entries")
            except Exception as e:
                logger.error(f"Loadknowledge base failed: {e}")
    
    def _save_knowledge_base(self):
        """Saveknowledge base到文件"""
        try:
            data = {
                'knowledge': self.knowledge,
                'categories': self.categories,
                'entities': self.entities,
                'saved_at': self._get_timestamp()
            }
            with open(self.kb_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"knowledge basesaved to {self.kb_file}")
        except Exception as e:
            logger.error(f"Saveknowledge base failed: {e}")
    
    def _get_timestamp(self) -> str:
        """Get时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _init_core_knowledge(self):
        """Initialization核心知识"""
        core_knowledge = {
            "concepts": {
                "agent": {
                    "definition": "Agent, 能够自主感知, 决策和executing task的系统",
                    "properties": ["自主性", "反应性", "主动性", "社会能力"],
                    "related": ["planner", "executor", "critic", "coordinator"]
                },
                "memory": {
                    "definition": " memories系统, 用于存储和检索信息和 experiences",
                    "types": ["Short-term memory", "中期 memories", "长期 memories", "情境 memories"],
                    "related": ["contextual", "episodic", "semantic"]
                },
                "tool": {
                    "definition": "Tool, 扩展Agent capabilities的软件groups件",
                    "properties": ["可groups合", "可复用", "可发现"],
                    "related": ["registry", "executor"]
                }
            },
            "best_practices": {
                "agent_design": [
                    "保持Agent的职责单一和清晰",
                    "使用接口定义groups件边界",
                    "实现有效的ErrorProcessing和恢复机制"
                ],
                "memory_management": [
                    "根据访问频率选择合适的存储介质",
                    "实施定期的遗忘机制",
                    "保护敏感信息的安全"
                ],
                "tool_development": [
                    "提供清晰的接口定义",
                    "包含详细的文档和示例",
                    "实现完善的ErrorProcessing"
                ]
            },
            "patterns": {
                "plan_execute_validate": "Plan->Execute->Validate 循环",
                "reflection_loop": "反思循环",
                "multi_layer_agent": "多层级Agent"
            }
        }
        
        for key, value in core_knowledge.items():
            if key not in self.knowledge:
                self.add_knowledge(key, value, category="core")
        
        logger.info("Core knowledge initialization complete")
    
    def add_knowledge(self, key: str, value: Any, category: str = "general"):
        """
        Add知识
        
        Args:
            key: 知识键
            value: 知识值
            category: 类别
        """
        self.knowledge[key] = value
        
        if category not in self.categories:
            self.categories[category] = []
        if key not in self.categories[category]:
            self.categories[category].append(key)
        
        self._save_knowledge_base()
        logger.info(f"Already added knowledge: {key}")
    
    def get_knowledge(self, key: str) -> Optional[Any]:
        """
        Get知识
        
        Args:
            key: 知识键
            
        Returns:
            知识值
        """
        return self.knowledge.get(key)
    
    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """
        Search知识
        
        Args:
            query: Search查询
            
        Returns:
            匹配的知识列表
        """
        query_lower = query.lower()
        results = []
        
        for key, value in self.knowledge.items():
            value_str = json.dumps(value, ensure_ascii=False).lower()
            if query_lower in key.lower() or query_lower in value_str:
                results.append({
                    "key": key,
                    "value": value,
                    "match_type": "key" if query_lower in key.lower() else "value"
                })
        
        return results
    
    def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        """
        Add实体
        
        Args:
            entity_id: 实体ID
            entity_type: 实体type
            properties: 实体属性
        """
        self.entities[entity_id] = {
            "type": entity_type,
            "properties": properties,
            "added_at": self._get_timestamp()
        }
        self._save_knowledge_base()
        logger.info(f"Already added entity: {entity_id} ({entity_type})")
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体信息
        """
        return self.entities.get(entity_id)
    
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        按typeGet实体
        
        Args:
            entity_type: 实体type
            
        Returns:
            实体列表
        """
        return [
            {"id": eid, **eval} 
            for eid, eval in self.entities.items() 
            if eval.get("type") == entity_type
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetStatistics
        
        Returns:
            Statistics
        """
        return {
            "total_knowledge": len(self.knowledge),
            "categories": {cat: len(keys) for cat, keys in self.categories.items()},
            "total_entities": len(self.entities),
            "entity_types": list(set(e.get("type") for e in self.entities.values()))
        }


class ToolAndKnowledgeEcosystem:
    """Tool and knowledge ecosystem"""
    
    def __init__(self, tool_registry_file: str = "tool_registry.json",
                knowledge_base_file: str = "knowledge_base.json"):
        """
        InitializationTool and knowledge ecosystem
        
        Args:
            tool_registry_file: ToolRegistry文件
            knowledge_base_file: knowledge base文件
        """
        self.tool_registry = ToolRegistry(tool_registry_file)
        self.knowledge_base = KnowledgeBase(knowledge_base_file)
        
        logger.info("Tool and knowledge ecosysteminitialization complete")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get生态系统Statistics
        
        Returns:
            Statistics
        """
        return {
            "tools": self.tool_registry.get_statistics(),
            "knowledge": self.knowledge_base.get_statistics()
        }
    
    def discover_capabilities(self, query: str) -> Dict[str, Any]:
        """
        发现能力
        
        Args:
            query: 查询字符串
            
        Returns:
            发现
        """
        # SearchTool
        tools = self.tool_registry.search_tools(query)
        
        # Search知识
        knowledge = self.knowledge_base.search_knowledge(query)
        
        return {
            "tools": [tool.to_dict() for tool in tools],
            "knowledge": knowledge,
            "query": query
        }
    
    def get_recommendations(self, context: str) -> Dict[str, Any]:
        """
        Get推荐
        
        Args:
            context: 上下文信息
            
        Returns:
            推荐
        """
        # 基于上下文的Tool推荐
        context_lower = context.lower()
        recommended_tools = []
        
        if any(keyword in context_lower for keyword in ["search", "find", "查询"]):
            recommended_tools.append(self.tool_registry.get_tool("search"))
        if any(keyword in context_lower for keyword in ["calculate", "compute", "计算"]):
            recommended_tools.append(self.tool_registry.get_tool("calculator"))
        if any(keyword in context_lower for keyword in ["file", "文件"]):
            recommended_tools.append(self.tool_registry.get_tool("file_manager"))
        if any(keyword in context_lower for keyword in ["code", "代码"]):
            recommended_tools.append(self.tool_registry.get_tool("code_executor"))
        
        # 基于上下文的相关知识
        related_knowledge = []
        if any(keyword in context_lower for keyword in ["agent", "Agent"]):
            related_knowledge.append(self.knowledge_base.get_knowledge("concepts.agent"))
        if any(keyword in context_lower for keyword in ["memory", " memories"]):
            related_knowledge.append(self.knowledge_base.get_knowledge("concepts.memory"))
        if any(keyword in context_lower for keyword in ["tool", "Tool"]):
            related_knowledge.append(self.knowledge_base.get_knowledge("concepts.tool"))
        
        return {
            "recommended_tools": [t.to_dict() if t else None for t in recommended_tools if t],
            "related_knowledge": [k for k in related_knowledge if k],
            "context": context
        }