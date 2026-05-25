#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户反馈管理 module
实现标准化的用户反馈循环机制
"""

from .feedback_manager import (
    FeedbackManager,
    FeedbackType,
    FeedbackStatus,
    UserFeedback,
    get_feedback_manager,
    reset_feedback_manager
)

__all__ = [
    "FeedbackManager",
    "FeedbackType",
    "FeedbackStatus",
    "UserFeedback",
    "get_feedback_manager",
    "reset_feedback_manager"
]