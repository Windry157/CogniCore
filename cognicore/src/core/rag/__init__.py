#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG (检索增强生成)  module
"""

from .rag_service import (
    RAGService,
    RAGEnhancedLLM,
    get_rag_service,
    reset_rag_service
)

__all__ = [
    "RAGService",
    "RAGEnhancedLLM",
    "get_rag_service",
    "reset_rag_service"
]