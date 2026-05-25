#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志 module
提供统一的日志配置和格式化
"""
import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredLogger:
    """
    结构化日志记录器
    """
    _instance = None
    _handlers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self.config = {
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "log_file": os.getenv("LOG_FILE", "logs/app.log"),
                "max_bytes": 10485760,  # 10MB
                "backup_count": 5
            }
            self._setup_logging()
    
    def _setup_logging(self):
        """
        配置日志系统
        """
        # 确保日志目录存在
        log_file = Path(self.config["log_file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config["log_level"]))
        
        # 移除already有的Processor
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add控制台Processor
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config["log_level"]))
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Add文件Processor (带轮转) 
        file_handler = logging.handlers.RotatingFileHandler(
            self.config["log_file"],
            maxBytes=self.config["max_bytes"],
            backupCount=self.config["backup_count"],
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, self.config["log_level"]))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get日志记录器实例
        
        Args:
            name: 记录器Name
            
        Returns:
            logging.Logger 实例
        """
        if name not in self._handlers:
            logger = logging.getLogger(name)
            self._handlers[name] = logger
        return self._handlers[name]
    
    def log_structured(self, level: int, message: str, 
                      extra: Optional[Dict[str, Any]] = None,
                      logger_name: str = "app"):
        """
        记录结构化日志
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外的结构化数据
            logger_name: 日志记录器Name
        """
        logger = self.get_logger(logger_name)
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": logging.getLevelName(level)
        }
        
        if extra:
            log_data.update(extra)
        
        logger.log(level, json.dumps(log_data, ensure_ascii=False))
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None, 
              logger_name: str = "app"):
        """
        记录调试级别日志
        """
        self.log_structured(logging.DEBUG, message, extra, logger_name)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None, 
             logger_name: str = "app"):
        """
        记录信息级别日志
        """
        self.log_structured(logging.INFO, message, extra, logger_name)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None, 
                logger_name: str = "app"):
        """
        记录warning级别日志
        """
        self.log_structured(logging.WARNING, message, extra, logger_name)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, 
              logger_name: str = "app"):
        """
        记录Error级别日志
        """
        self.log_structured(logging.ERROR, message, extra, logger_name)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, 
                 logger_name: str = "app"):
        """
        记录严重Error级别日志
        """
        self.log_structured(logging.CRITICAL, message, extra, logger_name)


# Create全局日志记录器实例
structured_logger = StructuredLogger()


# 导出便捷函数
def get_logger(name: str) -> logging.Logger:
    """
    Get日志记录器
    """
    return structured_logger.get_logger(name)

def debug(message: str, extra: Optional[Dict[str, Any]] = None, 
          logger_name: str = "app"):
    """
    记录调试级别日志
    """
    structured_logger.debug(message, extra, logger_name)

def info(message: str, extra: Optional[Dict[str, Any]] = None, 
         logger_name: str = "app"):
    """
    记录信息级别日志
    """
    structured_logger.info(message, extra, logger_name)

def warning(message: str, extra: Optional[Dict[str, Any]] = None, 
            logger_name: str = "app"):
    """
    记录warning级别日志
    """
    structured_logger.warning(message, extra, logger_name)

def error(message: str, extra: Optional[Dict[str, Any]] = None, 
          logger_name: str = "app"):
    """
    记录Error级别日志
    """
    structured_logger.error(message, extra, logger_name)

def critical(message: str, extra: Optional[Dict[str, Any]] = None, 
             logger_name: str = "app"):
    """
    记录严重Error级别日志
    """
    structured_logger.critical(message, extra, logger_name)
