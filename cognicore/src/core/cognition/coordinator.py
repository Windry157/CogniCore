#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认知协调器模块
协调系统1和系统2的决策
专为U盘便携项目优化
"""

import time
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio

from .system1 import system1
from .system2 import system2, ReasoningMode
from .bayesian_brain import bayesian_brain

logger = logging.getLogger(__name__)


class DecisionMode(Enum):
    """决策模式"""
    AUTO = "auto"
    SYSTEM1_ONLY = "system1_only"
    SYSTEM2_ONLY = "system2_only"
    HYBRID = "hybrid"


class CognitionCoordinator:
    """认知协调器
    
    功能：
    - 协调系统1和系统2决策
    - 智能路由决策请求
    - 管理置信度阈值
    - 处理决策冲突
    """
    
    def __init__(self):
        """初始化协调器"""
        self.decision_mode = DecisionMode.AUTO
        self.system1_confidence_threshold = 0.7
        self.system2_threshold = 0.6
        self.system1_timeout = 0.05  # 50ms
        self.max_system2_time = 2.0  # 2秒
        
        # 决策统计
        self.decision_stats = {
            "total": 0,
            "system1": 0,
            "system2": 0,
            "hybrid": 0,
            "fallback": 0,
        }
        
        # 系统2的贝叶斯大脑引用
        system2.bayesian_brain = bayesian_brain
        
        logger.info("CognitionCoordinator 初始化完成")
    
    async def make_decision(
        self,
        situation: Dict[str, Any],
        mode: Optional[DecisionMode] = None,
    ) -> Dict[str, Any]:
        """做出决策
        
        Args:
            situation: 决策情况
            mode: 决策模式（可选）
            
        Returns:
            决策结果
        """
        self.decision_stats["total"] += 1
        
        if mode is None:
            mode = self.decision_mode
        
        try:
            if mode == DecisionMode.SYSTEM1_ONLY:
                return await self._system1_only(situation)
            elif mode == DecisionMode.SYSTEM2_ONLY:
                return await self._system2_only(situation)
            elif mode == DecisionMode.HYBRID:
                return await self._hybrid_decision(situation)
            else:
                return await self._auto_decision(situation)
                
        except Exception as e:
            logger.error(f"决策失败: {e}")
            self.decision_stats["fallback"] += 1
            return self._fallback_decision(situation)
    
    async def _auto_decision(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """自动决策（默认模式）
        
        策略：
        1. 先尝试系统1快速响应
        2. 如果置信度足够，直接返回
        3. 否则升级到系统2
        """
        # 先尝试系统1
        start_time = time.time()
        system1_result = await system1.make_decision(situation)
        s1_time = time.time() - start_time
        
        # 检查系统1置信度
        if system1_result.get("confidence", 0) >= self.system1_confidence_threshold:
            self.decision_stats["system1"] += 1
            return {
                **system1_result,
                "coordinator_mode": "auto_system1",
            }
        
        # 升级到系统2
        self.decision_stats["system2"] += 1
        system2_result = await system2.make_decision(situation)
        
        return {
            **system2_result,
            "coordinator_mode": "auto_system2",
            "system1_fallback": system1_result,
            "system1_time": s1_time,
        }
    
    async def _system1_only(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """仅系统1决策"""
        self.decision_stats["system1"] += 1
        result = await system1.make_decision(situation)
        return {
            **result,
            "coordinator_mode": "system1_only",
        }
    
    async def _system2_only(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """仅系统2决策"""
        self.decision_stats["system2"] += 1
        result = await system2.make_decision(situation)
        return {
            **result,
            "coordinator_mode": "system2_only",
        }
    
    async def _hybrid_decision(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """混合决策
        
        并行运行系统1和系统2，选择最佳结果
        """
        self.decision_stats["hybrid"] += 1
        
        # 并行执行
        task1 = asyncio.create_task(system1.make_decision(situation))
        task2 = asyncio.create_task(system2.make_decision(situation))
        
        # 先等待系统1（带超时）
        try:
            s1_result = await asyncio.wait_for(task1, timeout=self.system1_timeout)
        except asyncio.TimeoutError:
            s1_result = None
        
        # 等待系统2（如果需要）
        s2_result = await task2
        
        # 比较选择
        if s1_result and s2_result:
            s1_conf = s1_result.get("confidence", 0)
            s2_conf = s2_result.get("confidence", 0)
            
            if s1_conf >= s2_conf and s1_conf >= self.system1_confidence_threshold:
                chosen = "system1"
                final_result = s1_result
            else:
                chosen = "system2"
                final_result = s2_result
        elif s1_result:
            chosen = "system1"
            final_result = s1_result
        else:
            chosen = "system2"
            final_result = s2_result
        
        return {
            **final_result,
            "coordinator_mode": "hybrid",
            "chosen_system": chosen,
            "system1_result": s1_result,
            "system2_result": s2_result,
        }
    
    def _fallback_decision(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """回退决策"""
        return {
            "decision": "抱歉，我现在无法处理这个问题。请稍后再试。",
            "confidence": 0.2,
            "time_taken": 0.01,
            "system": "coordinator_fallback",
            "coordinator_mode": "fallback",
            "situation_summary": self._summarize_situation(situation),
        }
    
    def _summarize_situation(self, situation: Dict[str, Any]) -> str:
        """总结情况（用于日志）"""
        input_text = situation.get("input", "")
        if len(input_text) > 50:
            return input_text[:50] + "..."
        return input_text
    
    def set_decision_mode(self, mode: DecisionMode):
        """设置决策模式"""
        self.decision_mode = mode
        logger.info(f"决策模式设置为: {mode}")
    
    def set_confidence_thresholds(
        self,
        system1_threshold: Optional[float] = None,
        system2_threshold: Optional[float] = None,
    ):
        """设置置信度阈值"""
        if system1_threshold is not None:
            self.system1_confidence_threshold = max(0.0, min(1.0, system1_threshold))
        
        if system2_threshold is not None:
            self.system2_threshold = max(0.0, min(1.0, system2_threshold))
        
        logger.info(f"阈值更新: System1={self.system1_confidence_threshold}, System2={self.system2_threshold}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = max(1, self.decision_stats["total"])
        
        return {
            "decision_stats": self.decision_stats.copy(),
            "decision_rates": {
                "system1": self.decision_stats["system1"] / total,
                "system2": self.decision_stats["system2"] / total,
                "hybrid": self.decision_stats["hybrid"] / total,
                "fallback": self.decision_stats["fallback"] / total,
            },
            "config": {
                "decision_mode": self.decision_mode.value,
                "system1_threshold": self.system1_confidence_threshold,
                "system2_threshold": self.system2_threshold,
            },
            "system1_stats": system1.get_statistics(),
        }
    
    def reset_statistics(self):
        """重置统计"""
        self.decision_stats = {
            "total": 0,
            "system1": 0,
            "system2": 0,
            "hybrid": 0,
            "fallback": 0,
        }


cognition_coordinator = CognitionCoordinator()
