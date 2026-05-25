#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool moduleInitialization
"""
# 导入所有Tool module, 确保装饰器Register生效
from .registry import tool_registry, register_tool
from .network_tools import *
from .memory_tools import *
from .utility_tools import *

__all__ = ["tool_registry", "register_tool"]

# InitializationTool
def initialize_tools():
    """
    Initialization所有Tool
    """
    # 导入所有Tool module, 确保它们被Register
    import src.core.tools.network_tools
    import src.core.tools.memory_tools
    import src.core.tools.utility_tools
    
    tools = tool_registry.get_all_tools()
    print(f"InitializationTool complete, TotalRegister {len(tools)}  tools")

