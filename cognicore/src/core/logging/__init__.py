#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志 module
"""
from .structured_logger import (
    get_logger,
    debug,
    info,
    warning,
    error,
    critical,
    structured_logger
)

__all__ = [
    'get_logger',
    'debug',
    'info',
    'warning',
    'error',
    'critical',
    'structured_logger'
]
