#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置管理 module"""

from typing import Dict, Any
from .manager import ConfigManager

# 使用单例模式的ConfigManager
config_manager = ConfigManager()

def load_config() -> Dict[str, Any]:
    """Load系统配置
    From配置文件中Get配置
    """
    return {
        "app_name": config_manager.get("app.name", "PyWJJ"),
        "version": config_manager.get("app.version", "0.2.0"),
        "models": {
            "default": config_manager.get("models.default", "gemma4:e4b"),
            "ollama_url": config_manager.get("models.ollama_url", "http://localhost:11434"),
            "refresh_interval": config_manager.get("models.refresh_interval", 300),
            "providers": {},  # 留空, 让系统FromOllamaFetch real-time models列表
        },
        "llm": {
            # 支持: openai, deepseek, moonshot, ollama, mock
            "provider": config_manager.get("models.providers.ollama.enabled", True) and "ollama" or "mock",
            "api_key": "ollama",  # Ollama 不需要真实API key, 但需要设置一 值
            "base_url": config_manager.get("models.ollama_url", "http://localhost:11434") + "/v1",
            "model": config_manager.get("models.default", "gemma4:e4b"),
            "temperature": 0.7
        },
        "bayesian": {
            "enabled": True
        },
        "knowledge": {
            "path": "./data/knowledge"
        },
        "memory": {
            "directory": config_manager.get("memory.directory", "memory"),
            "vector_model": config_manager.get("memory.vector_model", "ollama:nomic-embed-text")
        },
    }

# 导出配置管理器
def get_config_manager() -> ConfigManager:
    return config_manager
