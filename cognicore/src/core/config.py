# -*- coding: utf-8 -*-
"""
配置文件
统一使用ConfigManager管理配置
"""
from pathlib import Path
from src.utils.config import config_manager, load_config
from typing import Dict, Any


class Config:
    """
    统一配置类
    使用ConfigManager管理所有配置
    """
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Get配置项
        """
        return config_manager.get(key, default)

    @staticmethod
    def set(key: str, value: Any):
        """
        设置配置项
        """
        config_manager.set(key, value)

    @staticmethod
    def reload():
        """
        重载配置
        """
        config_manager.reload()

    @property
    def DB_USER(self) -> str:
        return self.get("database.user", "postgres")

    @property
    def DB_PASSWORD(self) -> str:
        return self.get("database.password", "")

    @property
    def DB_NAME(self) -> str:
        return self.get("database.name", "postgres")

    @property
    def DB_HOST(self) -> str:
        return self.get("database.host", "localhost")

    @property
    def DB_PORT(self) -> int:
        return int(self.get("database.port", "5432"))

    @property
    def APP_NAME(self) -> str:
        return self.get("app.name", "智能助手")

    @property
    def APP_VERSION(self) -> str:
        return self.get("app.version", "0.2.0")

    @property
    def DEBUG(self) -> bool:
        return self.get("app.debug", False)

    @property
    def SERVER_HOST(self) -> str:
        return self.get("server.host", "0.0.0.0")

    @property
    def SERVER_PORT(self) -> int:
        return self.get("server.port", 8000)

    @property
    def SERVER_WORKERS(self) -> int:
        return self.get("server.workers", 4)

    @property
    def DEFAULT_MODEL(self) -> str:
        return self.get("models.default", "minimax-m2.7:cloud")

    @property
    def OLLAMA_URL(self) -> str:
        return self.get("models.ollama_url", "http://localhost:11434")

    @property
    def MODEL_REFRESH_INTERVAL(self) -> int:
        return self.get("models.refresh_interval", 300)

    @property
    def MEMORY_DIRECTORY(self) -> str:
        return self.get("memory.directory", "memory")

    @property
    def VECTOR_MODEL(self) -> str:
        return self.get("memory.vector_model", "ollama:nomic-embed-text")

    @property
    def EMBEDDING_MODEL_PATH(self) -> str:
        return self.get("embedding.model_path", "./models/all-MiniLM-L6-v2")

    @property
    def BACKUP_DIRECTORY(self) -> str:
        return self.get("backup.directory", str(Path.cwd() / "backups"))

    @property
    def BACKUP_RETENTION_DAYS(self) -> int:
        return self.get("backup.retention_days", 7)


# Create全局配置实例
config = Config()

# 导出配置Load函数
def get_config() -> Dict[str, Any]:
    return load_config()

# 导出配置管理器
def get_config_manager():
    return config_manager
