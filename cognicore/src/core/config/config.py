#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理 module
使用Pydantic V2和pydantic-settings管理系统配置
支持从YAML文件加载配置，适应U盘便携项目
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, List
import os
from pathlib import Path
import yaml


def _get_config_dir():
    """获取配置文件所在目录，支持U盘便携"""
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    return Path(config_path).resolve().parent


def _get_project_root():
    """获取项目根目录（相对于配置文件的上上级目录）"""
    config_dir = _get_config_dir()
    return config_dir.parent


class LLMConfig(BaseSettings):
    """
    LLM服务配置
    """
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:1b"
    ollama_timeout: int = 30
    
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_timeout: int = 30
    
    huggingface_model: Optional[str] = None
    huggingface_token: Optional[str] = None


class AgentConfig(BaseSettings):
    """
    Agent配置
    """
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    planner_max_retries: int = 3
    planner_timeout: int = 60
    
    executor_max_retries: int = 3
    executor_timeout: int = 60
    executor_retry_delay: float = 1.0
    
    validator_timeout: int = 30
    critic_timeout: int = 30
    
    reflection_enabled: bool = True
    reflection_max_attempts: int = 3


class MemoryConfig(BaseSettings):
    """
    记忆系统配置
    """
    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    memory_dir: str = "data/memory"
    ltm_enabled: bool = True
    ltm_max_size: int = 1000
    wm_max_size: int = 100
    stm_max_size: int = 20
    semantic_enabled: bool = True
    vector_enabled: bool = True
    vector_db_path: str = "data/vector_db"
    embedding_provider: str = "ollama"
    ollama_embedding_model: str = "nomic-embed-text-v2-moe:latest"
    sentence_transformers_model: str = "all-MiniLM-L6-v2"


class ToolConfig(BaseSettings):
    """
    工具配置
    """
    model_config = SettingsConfigDict(
        env_prefix="TOOL_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    tool_registry_path: str = "data/tool_registry.json"
    knowledge_base_path: str = "data/knowledge_base.json"
    tool_execution_timeout: int = 30


class LoggingConfig(BaseSettings):
    """
    日志配置
    """
    model_config = SettingsConfigDict(
        env_prefix="LOGGING_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    level: str = "INFO"
    log_file: Optional[str] = None
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class SystemConfig(BaseSettings):
    """
    系统配置
    """
    model_config = SettingsConfigDict(
        env_prefix="SYSTEM_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    system_name: str = "SmartAgent"
    system_version: str = "1.0.0"
    work_dir: str = "."
    data_dir: str = "data"
    temp_dir: str = "temp"
    max_concurrency: int = 5
    api_enabled: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000


def _load_yaml_overrides():
    """从YAML文件加载配置覆盖"""
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    yaml_path = Path(config_path)
    if not yaml_path.exists():
        return {}
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[Config] Failed to load YAML config: {e}")
        return {}


_yaml_overrides = {}


def _apply_yaml_overrides(cfg):
    """将YAML配置覆盖应用到Config实例"""
    data = _yaml_overrides
    mappings = [
        (('models', 'ollama_url'), cfg.llm, 'ollama_base_url'),
        (('models', 'default'), cfg.llm, 'ollama_model'),
        (('server', 'host'), cfg.system, 'api_host'),
        (('server', 'port'), cfg.system, 'api_port'),
        (('memory', 'directory'), cfg.memory, 'memory_dir'),
        (('memory', 'vector_db_path'), cfg.memory, 'vector_db_path'),
        (('memory', 'vector_model'), cfg.memory, 'ollama_embedding_model'),
        (('knowledge', 'enabled'), cfg.memory, 'ltm_enabled'),
    ]
    for (section, key), obj, attr in mappings:
        val = data.get(section, {}).get(key)
        if val is not None:
            setattr(obj, attr, val)


class Config(BaseSettings):
    """
    主配置类
    支持从YAML文件和环境变量加载配置
    """
    llm: LLMConfig = LLMConfig()
    agent: AgentConfig = AgentConfig()
    memory: MemoryConfig = MemoryConfig()
    tool: ToolConfig = ToolConfig()
    logging: LoggingConfig = LoggingConfig()
    system: SystemConfig = SystemConfig()
    
    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        project_root = _get_project_root()
        
        data_dir = project_root / self.system.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        
        memory_dir = project_root / self.memory.memory_dir
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        if self.memory.vector_enabled:
            vector_db_path = project_root / self.memory.vector_db_path
            vector_db_path.mkdir(parents=True, exist_ok=True)
        
        temp_dir = project_root / self.system.temp_dir
        temp_dir.mkdir(parents=True, exist_ok=True)


_yaml_overrides.update(_load_yaml_overrides())
config = Config()
_apply_yaml_overrides(config)
config.ensure_directories()


def get_config() -> Config:
    """获取配置实例"""
    return config


def reload_config() -> Config:
    """重新加载配置（从 YAML 重新读取）"""
    global config, _yaml_overrides
    _yaml_overrides.clear()
    _yaml_overrides.update(_load_yaml_overrides())
    config = Config()
    _apply_yaml_overrides(config)
    config.ensure_directories()
    return config
