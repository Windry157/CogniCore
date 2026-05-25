#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ModelAdapter工厂
根据ModelName自动Create对应的Adapter
"""
import logging
from typing import Optional
from .base import BaseModelAdapter
from .kimi_adapter import KimiAdapter
from .deepseek_adapter import DeepseekAdapter
from .ollama_adapter import OllamaAdapter

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Adapter工厂类"""

    # ModelName到Adapter类的映射
    _adapter_map = {
        # Kimi Model
        "kimi": KimiAdapter,
        "moonshot": KimiAdapter,

        # Deepseek Model
        "deepseek": DeepseekAdapter,

        # Ollama 本地Model
        "ollama": OllamaAdapter,
    }

    @classmethod
    def get_adapter(cls, model_name: str) -> BaseModelAdapter:
        """
        根据ModelNameGet对应的Adapter

        Args:
            model_name: ModelName, 如 "kimi-k2.5:cloud", "deepseek-r1:7b", "qwen2.5:7b"

        Returns:
            对应的ModelAdapter实例
        """
        model_lower = model_name.lower()

        # 根据ModelName前缀判断Adaptertype
        for prefix, adapter_class in cls._adapter_map.items():
            if prefix in model_lower:
                logger.info(f"For model '{model_name}' creating adapter: {adapter_class.__name__}")
                return adapter_class(model_name)

        # 默认使用 Ollama Adapter (本地Model) 
        logger.info(f"For model '{model_name}' using default adapter: OllamaAdapter")
        return OllamaAdapter(model_name)

    @classmethod
    def register_adapter(cls, prefix: str, adapter_class: type):
        """
        Register新的Adapter

        Args:
            prefix: ModelName前缀
            adapter_class: Adapter类
        """
        cls._adapter_map[prefix.lower()] = adapter_class
        logger.info(f"Registering adapter: {prefix} -> {adapter_class.__name__}")


# 全局Adapter实例cache
_adapter_cache = {}


def get_model_adapter(model_name: str) -> BaseModelAdapter:
    """
    GetModelAdapter (带cache) 

    Args:
        model_name: ModelName

    Returns:
        ModelAdapter实例
    """
    if model_name not in _adapter_cache:
        _adapter_cache[model_name] = AdapterFactory.get_adapter(model_name)

    return _adapter_cache[model_name]


def clear_adapter_cache():
    """清除Adaptercache"""
    global _adapter_cache
    _adapter_cache = {}
    logger.info("Adapter cache cleared")
