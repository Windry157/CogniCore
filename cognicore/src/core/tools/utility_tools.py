#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实用ToolCollection
包含各种常用Tool, 如网络Tool, 文件Tool, 系统Tool和计算Tool
"""

import os
import ast
import math
import subprocess
import requests
import json
from typing import Dict, Any, List, Optional
import logging

from .registry import register_tool

logger = logging.getLogger(__name__)


@register_tool(name="get_weather", description="Get指定城市的天气信息")
def get_weather(city: str) -> Dict[str, Any]:
    """
    Get指定城市的天气信息
    
    Args:
        city: 城市Name
        
    Returns:
        天气信息字典
    """
    try:
        # 使用OpenWeatherMap APIGet weather info
        # Register意: 这里需要替换为实际的API密钥
        api_key = "YOUR_OPENWEATHER_API_KEY"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=zh_cn"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather_info = {
            "city": data.get("name"),
            "temperature": data.get("main", {}).get("temp"),
            "humidity": data.get("main", {}).get("humidity"),
            "description": data.get("weather", [{}])[0].get("description"),
            "wind_speed": data.get("wind", {}).get("speed")
        }
        
        return weather_info
    except Exception as e:
        logger.error(f"Get weather info failed: {e}")
        return {"error": str(e)}


@register_tool(name="search_web", description="在网络上Search信息")
def search_web(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    在网络上Search信息
    
    Args:
        query: Search查询
        num_results: 返回数量
        
    Returns:
        Search字典
    """
    try:
        # 使用SerpAPI进行Search
        # Register意: 这里需要替换为实际的API密钥
        api_key = "YOUR_SERPAPI_KEY"
        url = "https://serpapi.com/search.json"
        params = {
            "q": query,
            "api_key": api_key,
            "num": num_results
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet")
            })
        
        return {"results": results}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"error": str(e)}


@register_tool(name="read_file", description="Read fileContent")
def read_file(file_path: str) -> Dict[str, Any]:
    """
    Read fileContent
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件Content字典
    """
    try:
        if not os.path.exists(file_path):
            return {"error": "File does not exist"}
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {"content": content, "file_path": file_path}
    except Exception as e:
        logger.error(f"Read file failed: {e}")
        return {"error": str(e)}


@register_tool(name="write_file", description="Write fileContent")
def write_file(file_path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    Write fileContent
    
    Args:
        file_path: 文件路径
        content: 文件Content
        overwrite: 是否覆盖现有文件
        
    Returns:
        写入字典
    """
    try:
        if os.path.exists(file_path) and not overwrite:
            return {"error": "文件exists, 请设置overwrite=True来覆盖"}
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        logger.error(f"Write file failed: {e}")
        return {"error": str(e)}


@register_tool(name="get_system_info", description="GetSystem Info")
def get_system_info() -> Dict[str, Any]:
    """
    GetSystem Info
    
    Returns:
        System Info字典
    """
    try:
        import platform
        system_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
        return system_info
    except Exception as e:
        logger.error(f"GetSystem Info failed: {e}")
        return {"error": str(e)}


@register_tool(name="execute_command", description="执行系统命令")
def execute_command(command: str, shell: bool = True) -> Dict[str, Any]:
    """
    执行系统命令
    
    Args:
        command: 要执行的命令
        shell: 是否使用shell
        
    Returns:
        命令执行
    """
    try:
        result = subprocess.run(
            command, 
            shell=shell, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        logger.error(f"Execute command failed: {e}")
        return {"error": str(e)}


@register_tool(name="calculate", description="执行数学计算")
def calculate(expression: str) -> Dict[str, Any]:
    """
    执行数学计算
    
    Args:
        expression: 数学表达式
        
    Returns:
        计算
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        allowed = (
            ast.Expression, ast.Constant, ast.UnaryOp, ast.BinOp,
            ast.Call, ast.Name, ast.Load,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
            ast.UAdd, ast.USub, ast.Invert, ast.Not, ast.Compare,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                return {"error": "unsupported syntax"}
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    return {"error": "unsupported call"}
                if node.func.id not in dir(math):
                    return {"error": f"unknown function: {node.func.id}"}
        code = compile(tree, "<safe>", "eval")
        result = eval(code, {"__builtins__": {}}, vars(math))
        return {"expression": expression, "result": result}
    except Exception as e:
        logger.error(f"Calculation failed: {e}")
        return {"error": str(e)}


@register_tool(name="convert_units", description="Unit conversion")
def convert_units(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """
    Unit conversion
    
    Args:
        value: 要转换的值
        from_unit: 源单位
        to_unit: 目标单位
        
    Returns:
        转换
    """
    try:
        # 简单的Unit conversion
        conversions = {
            "m_to_km": lambda x: x / 1000,
            "km_to_m": lambda x: x * 1000,
            "m_to_miles": lambda x: x * 0.000621371,
            "miles_to_m": lambda x: x / 0.000621371,
            "kg_to_lbs": lambda x: x * 2.20462,
            "lbs_to_kg": lambda x: x / 2.20462,
            "celsius_to_fahrenheit": lambda x: (x * 9/5) + 32,
            "fahrenheit_to_celsius": lambda x: (x - 32) * 5/9
        }
        
        conversion_key = f"{from_unit}_to_{to_unit}"
        if conversion_key not in conversions:
            return {"error": f"不支持的Unit conversion: {from_unit} to {to_unit}"}
        
        result = conversions[conversion_key](value)
        return {
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "result": result
        }
    except Exception as e:
        logger.error(f"Unit conversion failed: {e}")
        return {"error": str(e)}


@register_tool(name="generate_summary", description="generate text 摘要")
def generate_summary(text: str, max_length: int = 100) -> Dict[str, Any]:
    """
    generate text 摘要
    
    Args:
        text: 要摘要的文本
        max_length: 摘要最大Length
        
    Returns:
        摘要
    """
    try:
        # 简单的摘要算法, 实际项目中可以使用更复杂的NLP技术
        sentences = text.split('. ')
        summary = '. '.join(sentences[:3])  # 取前3 句子
        
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return {"summary": summary, "original_length": len(text), "summary_length": len(summary)}
    except Exception as e:
        logger.error(f"Generate summary failed: {e}")
        return {"error": str(e)}


@register_tool(name="translate_text", description="Translation文本")
def translate_text(text: str, target_language: str = "en") -> Dict[str, Any]:
    """
    Translation文本
    
    Args:
        text: 要Translation的文本
        target_language: 目标语言代码
        
    Returns:
        Translation
    """
    try:
        # 使用Google Translate API
        # Register意: 这里需要替换为实际的API密钥
        api_key = "YOUR_GOOGLE_TRANSLATE_API_KEY"
        url = f"https://translation.googleapis.com/language/translate/v2"
        params = {
            "q": text,
            "target": target_language,
            "key": api_key
        }
        response = requests.post(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        translated_text = data.get("data", {}).get("translations", [{}])[0].get("translatedText", "")
        
        return {"original_text": text, "translated_text": translated_text, "target_language": target_language}
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return {"error": str(e)}


# RegisterTool到ToolRegistry
# Register意: 由于使用了装饰器, Tool会自动Register


def get_utility_tools() -> List[str]:
    """
    Get所有实用Tool的Name
    
    Returns:
        ToolName列表
    """
    from .registry import tool_registry
    tools = tool_registry.get_all_tools()
    return list(tools.keys())
