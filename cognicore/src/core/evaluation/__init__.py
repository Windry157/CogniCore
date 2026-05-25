#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估框架模块
提供 RAG 系统的评估功能
专为U盘便携项目优化
"""

from .evaluators import (
    ScoreLevel,
    FaithfulnessScore,
    RelevanceScore,
    QualityScore,
    FaithfulnessEvaluator,
    RelevanceEvaluator,
    QualityEvaluator,
    faithfulness_evaluator,
    relevance_evaluator,
    quality_evaluator
)

__all__ = [
    # 评分级别
    "ScoreLevel",
    
    # 评分数据类
    "FaithfulnessScore",
    "RelevanceScore",
    "QualityScore",
    
    # 评估器
    "FaithfulnessEvaluator",
    "RelevanceEvaluator",
    "QualityEvaluator",
    
    # 全局评估器实例
    "faithfulness_evaluator",
    "relevance_evaluator",
    "quality_evaluator",
]
