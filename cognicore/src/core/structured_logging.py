#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志系统
支持 JSON 格式, Trace ID, ELK Stack 集成
"""

import logging
import json
import sys
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from functools import wraps
import asyncio

try:
    from pythonjsonlogger import jsonlogger
    HAS_PYTHONJSONLOGGER = True
except ImportError:
    HAS_PYTHONJSONLOGGER = False


class StructuredLogFormatter(logging.Formatter):
    """
    结构化日志格式化器
    输出 JSON 格式日志, 支持 ELK Stack
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = kwargs.get('service_name', 'cognicore')
        self.environment = kwargs.get('environment', 'development')

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': self.service_name,
            'environment': self.environment,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add Trace ID (如果存在) 
        if hasattr(record, 'trace_id'):
            log_data['trace_id'] = record.trace_id

        # Add请求 ID (如果存在) 
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        # Add用户 ID (如果存在) 
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        # Add会话 ID (如果存在) 
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id

        # Add额外的自定义字段
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Addexception信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add性能指标 (如果存在) 
        if hasattr(record, 'duration'):
            log_data['duration_ms'] = record.duration

        # Add上下文信息
        if hasattr(record, 'context'):
            log_data['context'] = record.context

        return json.dumps(log_data, ensure_ascii=False)


class TraceContext:
    """
    Trace 上下文管理器
    用于在请求Processing过程中追踪 Trace ID
    """

    _local = None

    @classmethod
    def get_local(cls):
        """Get线程本地上下文"""
        if cls._local is None:
            try:
                import contextvars
                cls._local = contextvars.ContextVar('trace_context', default=None)
            except ImportError:
                cls._local = None
        return cls._local

    @classmethod
    def set_trace_id(cls, trace_id: str):
        """设置 Trace ID"""
        local = cls.get_local()
        if local is not None:
            try:
                context = local.get() or {}
                context['trace_id'] = trace_id
                local.set(context)
            except Exception:
                pass

    @classmethod
    def get_trace_id(cls) -> Optional[str]:
        """Get当前 Trace ID"""
        local = cls.get_local()
        if local is not None:
            try:
                context = local.get()
                return context.get('trace_id') if context else None
            except Exception:
                return None
        return None

    @classmethod
    def generate_trace_id(cls) -> str:
        """生成新的 Trace ID"""
        trace_id = str(uuid.uuid4())
        cls.set_trace_id(trace_id)
        return trace_id


class StructuredLogger:
    """
    结构化日志记录器
    提供带有 Trace ID 支持的日志记录功能
    """

    def __init__(self, name: str, service_name: str = 'cognicore'):
        self.logger = logging.getLogger(name)
        self.service_name = service_name
        self._setup_handler()

    def _setup_handler(self):
        """设置日志Processor"""
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredLogFormatter(service_name=self.service_name)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _log(self, level: int, message: str, **kwargs):
        """内部日志记录方法"""
        extra = {}

        # Add Trace ID
        trace_id = TraceContext.get_trace_id() or kwargs.pop('trace_id', None)
        if trace_id:
            extra['trace_id'] = trace_id

        # Add其他自定义字段
        for key, value in kwargs.items():
            extra[key] = value

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """记录 DEBUG 级别日志"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """记录 INFO 级别日志"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录 WARNING 级别日志"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录 ERROR 级别日志"""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """记录 CRITICAL 级别日志"""
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """记录exception日志 (包含堆栈信息) """
        kwargs['exc_info'] = True
        self._log(logging.ERROR, message, **kwargs)

    def log_request(self, method: str, path: str, status_code: int = None,
                    duration: float = None, **kwargs):
        """记录 HTTP 请求日志"""
        self.info(
            f"HTTP {method} {path}",
            request_method=method,
            request_path=path,
            status_code=status_code,
            duration_ms=duration,
            **kwargs
        )

    def log_ai_interaction(self, prompt: str, response: str = None,
                           model: str = None, duration: float = None, **kwargs):
        """记录 AI 交互日志"""
        self.info(
            "AI interaction",
            prompt_length=len(prompt),
            response_length=len(response) if response else None,
            model=model,
            duration_ms=duration,
            **kwargs
        )

    def log_memory_operation(self, operation: str, memory_type: str,
                             items_count: int = None, duration: float = None, **kwargs):
        """记录 memories操作日志"""
        self.info(
            f"Memory {operation}",
            memory_operation=operation,
            memory_type=memory_type,
            items_count=items_count,
            duration_ms=duration,
            **kwargs
        )

    def log_skill_execution(self, skill_name: str, action: str,
                            success: bool = True, duration: float = None, **kwargs):
        """记录Skill执行日志"""
        level = logging.INFO if success else logging.ERROR
        self._log(
            level,
            f"Skill execution: {skill_name}.{action}",
            skill_name=skill_name,
            skill_action=action,
            success=success,
            duration_ms=duration,
            **kwargs
        )

    def log_evolution(self, cycle: int, phase: str, status: str, **kwargs):
        """记录Lobster evolution日志"""
        self.info(
            f"Lobster evolution cycle #{cycle}: {phase}",
            evolution_cycle=cycle,
            evolution_phase=phase,
            evolution_status=status,
            **kwargs
        )


# 全局限流器日志记录器实例
def get_logger(name: str = __name__, service_name: str = 'cognicore') -> StructuredLogger:
    """
    Get结构化日志记录器

    参数:
        name: 日志记录器Name
        service_name: 服务Name

    返回:
        StructuredLogger 实例
    """
    return StructuredLogger(name, service_name)


# 异步日志装饰器
def log_async_call(logger: StructuredLogger = None, operation_name: str = None):
    """
    异步函数日志装饰器
    自动记录函数执行时间和
    """
    def decorator(func):
        nonlocal logger, operation_name
        if logger is None:
            logger = get_logger(func.__module__)
        if operation_name is None:
            operation_name = func.__name__

        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            trace_id = TraceContext.generate_trace_id()

            logger.info(f"Starting {operation_name}", trace_id=trace_id)

            try:
                result = await func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(
                    f"Completed {operation_name}",
                    trace_id=trace_id,
                    duration_ms=duration,
                    status="success"
                )
                return result
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.error(
                    f"Failed {operation_name}: {str(e)}",
                    trace_id=trace_id,
                    duration_ms=duration,
                    status="error",
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


# 同步日志装饰器
def log_call(logger: StructuredLogger = None, operation_name: str = None):
    """
    函数日志装饰器
    自动记录函数执行时间和
    """
    def decorator(func):
        nonlocal logger, operation_name
        if logger is None:
            logger = get_logger(func.__module__)
        if operation_name is None:
            operation_name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            trace_id = TraceContext.generate_trace_id()

            logger.info(f"Starting {operation_name}", trace_id=trace_id)

            try:
                result = func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(
                    f"Completed {operation_name}",
                    trace_id=trace_id,
                    duration_ms=duration,
                    status="success"
                )
                return result
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.error(
                    f"Failed {operation_name}: {str(e)}",
                    trace_id=trace_id,
                    duration_ms=duration,
                    status="error",
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


# 日志上下文管理器
class LogContext:
    """
    日志上下文管理器
    在代码Chunk执行期间设置日志上下文
    """

    def __init__(self, logger: StructuredLogger, **context):
        self.logger = logger
        self.context = context
        self._old_extra = None

    def __enter__(self):
        self._old_extra = {}
        for key, value in self.context.items():
            self._old_extra[key] = getattr(self.logger.logger, key, None)
            setattr(self.logger.logger, key, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key in self.context.keys():
            if self._old_extra.get(key) is not None:
                setattr(self.logger.logger, key, self._old_extra[key])
            else:
                try:
                    delattr(self.logger.logger, key)
                except AttributeError:
                    pass

        if exc_type is not None:
            self.logger.error(
                f"Exception in log context: {str(exc_val)}",
                exception_type=exc_type.__name__
            )

        return False


# ELK Stack 配置
class ELKHandler:
    """
    ELK Stack 日志Processor
    支持将日志发送到 Elasticsearch
    """

    def __init__(self, elasticsearch_url: str = None, index_prefix: str = 'cognicore-logs'):
        self.elasticsearch_url = elasticsearch_url
        self.index_prefix = index_prefix
        self._client = None

    def _get_client(self):
        """Get Elasticsearch 客户端"""
        if self._client is None and self.elasticsearch_url:
            try:
                from elasticsearch import Elasticsearch
                self._client = Elasticsearch([self.elasticsearch_url])
            except ImportError:
                logging.warning("elasticsearch-py not installed, ELK logging disabled")
            except Exception as e:
                logging.warning(f"Failed to connect to Elasticsearch: {e}")
        return self._client

    def send_log(self, log_data: Dict[str, Any]):
        """发送日志到 Elasticsearch"""
        client = self._get_client()
        if client is None:
            return False

        try:
            index_name = f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
            client.index(index=index_name, document=log_data)
            return True
        except Exception as e:
            logging.error(f"Failed to send log to ELK: {e}")
            return False

    def search_logs(self, query: str, size: int = 100) -> list:
        """Search日志"""
        client = self._get_client()
        if client is None:
            return []

        try:
            index_pattern = f"{self.index_prefix}-*"
            result = client.search(index=index_pattern, body={"query": {"query_string": {"query": query}}, "size": size})
            return [hit['_source'] for hit in result['hits']['hits']]
        except Exception as e:
            logging.error(f"Failed to search logs: {e}")
            return []


# 全局 ELK Processor实例
elk_handler = ELKHandler()


def setup_logging(service_name: str = 'cognicore', environment: str = 'development',
                  log_level: int = logging.INFO,
                  enable_console: bool = True,
                  enable_file: bool = True,
                  log_dir: str = './logs',
                  elasticsearch_url: str = None):
    """
    设置全局日志配置

    参数:
        service_name: 服务Name
        environment: 运行环境
        log_level: 日志级别
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        log_dir: 日志目录
        elasticsearch_url: Elasticsearch URL
    """

    # Create根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有Processor
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 设置格式化器
    formatter = StructuredLogFormatter(
        service_name=service_name,
        environment=environment
    )

    # Add控制台Processor
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

    # Add文件Processor
    if enable_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 普通日志文件
        file_handler = logging.FileHandler(log_path / 'app.log', encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

        # Error日志文件
        error_handler = logging.FileHandler(log_path / 'error.log', encoding="utf-8")
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

    # 配置 ELK Handler
    if elasticsearch_url:
        global elk_handler
        elk_handler = ELKHandler(elasticsearch_url=elasticsearch_url)

    # 记录Start日志
    logger = get_logger(__name__, service_name)
    logger.info(
        f"Logging configured for {service_name} in {environment} mode",
        service_name=service_name,
        environment=environment,
        log_level=logging.getLevelName(log_level)
    )

    return logger