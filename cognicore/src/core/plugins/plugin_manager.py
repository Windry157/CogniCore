#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理器
负责Load, 管理和执行插件
"""
import os
import sys
import importlib
import logging
from typing import Dict, Any, List
from .plugin_base import BasePlugin

logger = logging.getLogger(__name__)

class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        """Initializing plugin管理器"""
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_paths: List[str] = []
    
    def add_plugin_path(self, path: str):
        """
        Added plugin path
        
        Args:
            path: 插件路径
        """
        if path not in self.plugin_paths and os.path.exists(path):
            self.plugin_paths.append(path)
            logger.info(f"Added plugin path: {path}")
    
    def load_plugins(self):
        """
        Load所有插件
        """
        # Load内置插件
        self._load_builtin_plugins()
        
        # Load外部插件
        self._load_external_plugins()
    
    def _load_builtin_plugins(self):
        """
        Load内置插件
        """
        # 这里可以Add内置插件的Load逻辑
        # 例如: 
        # from .builtin_plugins import ExamplePlugin
        # self.register_plugin(ExamplePlugin())
        pass
    
    def _load_external_plugins(self):
        """
        Load外部插件
        """
        for plugin_path in self.plugin_paths:
            if not os.path.isdir(plugin_path):
                continue
            
            for item in os.listdir(plugin_path):
                item_path = os.path.join(plugin_path, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    self._load_plugin_from_directory(item_path)
                elif item.endswith('.py') and not item.startswith('__'):
                    self._load_plugin_from_file(item_path)
    
    def _load_plugin_from_directory(self, plugin_dir: str):
        """
        From目录Load插件
        
        Args:
            plugin_dir: 插件目录
        """
        try:
            # 检查是否有 __init__.py 文件
            init_file = os.path.join(plugin_dir, '__init__.py')
            if not os.path.exists(init_file):
                return
            
            # Add插件目录到 Python 路径
            plugin_parent = os.path.dirname(plugin_dir)
            if plugin_parent not in sys.path:
                sys.path.insert(0, plugin_parent)
            
            # 导入插件 module
            plugin_name = os.path.basename(plugin_dir)
            module = importlib.import_module(plugin_name)
            
            # 查找插件类
            for name, obj in module.__dict__.items():
                if (isinstance(obj, type) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin):
                    plugin = obj()
                    self.register_plugin(plugin)
                    break
        except Exception as e:
            logger.error(f"Loading plugin directory {plugin_dir}  failed: {e}")
    
    def _load_plugin_from_file(self, plugin_file: str):
        """
        From文件Load插件
        
        Args:
            plugin_file: 插件文件
        """
        try:
            # Add插件文件所在目录到 Python 路径
            plugin_dir = os.path.dirname(plugin_file)
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)
            
            # 导入插件 module
            plugin_name = os.path.basename(plugin_file).replace('.py', '')
            module = importlib.import_module(plugin_name)
            
            # 查找插件类
            for name, obj in module.__dict__.items():
                if (isinstance(obj, type) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin):
                    plugin = obj()
                    self.register_plugin(plugin)
                    break
        except Exception as e:
            logger.error(f"Load plugin file {plugin_file}  failed: {e}")
    
    def register_plugin(self, plugin: BasePlugin):
        """
        Register plugin
        
        Args:
            plugin: 插件实例
        """
        if plugin.name not in self.plugins:
            self.plugins[plugin.name] = plugin
            logger.info(f"Register plugin: {plugin.name} v{plugin.version} by {plugin.author}")
        else:
            logger.warning(f"Plugin {plugin.name} exists, skipping registration")
    
    async def initialize_plugins(self, config: Dict[str, Any] = None):
        """
        Initialization所有插件
        
        Args:
            config: 配置信息
        """
        for name, plugin in self.plugins.items():
            try:
                await plugin.initialize(config)
                logger.info(f"Initializing plugin: {name}")
            except Exception as e:
                logger.error(f"Initializing plugin {name}  failed: {e}")
    
    async def execute_plugin(self, plugin_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute plugin operation
        
        Args:
            plugin_name: 插件Name
            action: 操作Name
            params: 操作参数
            
        Returns:
            执行
        """
        if plugin_name in self.plugins:
            try:
                result = await self.plugins[plugin_name].execute(action, params)
                return result
            except Exception as e:
                logger.error(f"Execute plugin {plugin_name} action {action} failed: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
        else:
            return {
                "status": "error",
                "message": f"插件 {plugin_name} does not exist"
            }
    
    def get_plugin(self, plugin_name: str) -> BasePlugin:
        """
        Get plugin实例
        
        Args:
            plugin_name: 插件Name
            
        Returns:
            插件实例
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """
        Get所有插件
        
        Returns:
            插件字典
        """
        return self.plugins
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get所有插件的tool definition
        
        Returns:
            tool definition列表
        """
        tools = []
        for plugin in self.plugins.values():
            try:
                tool_def = plugin.get_tool_definition()
                tools.append(tool_def)
            except Exception as e:
                logger.error(f"Get plugin {plugin.name} tool definition failed: {e}")
        return tools
    
    async def shutdown_plugins(self):
        """
        Close所有插件
        """
        for name, plugin in self.plugins.items():
            try:
                await plugin.shutdown()
                logger.info(f"Closing plugin: {name}")
            except Exception as e:
                logger.error(f"Closing plugin {name}  failed: {e}")
