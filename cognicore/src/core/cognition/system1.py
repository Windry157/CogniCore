#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统1模块
负责快速直觉决策，基于启发式和经验
专为U盘便携项目优化
"""

import time
import hashlib
import random
from typing import Dict, List, Optional, Any
from collections import Counter, OrderedDict
import logging

logger = logging.getLogger(__name__)


class System1:
    """系统1 - 快速直觉决策
    
    特点：
    - 毫秒级响应
    - 基于启发式规则
    - 利用经验缓存
    - 低资源消耗
    """
    
    def __init__(self, cache_size: int = 1000):
        """初始化系统1
        
        Args:
            cache_size: 经验缓存大小
        """
        # 启发式规则
        self.heuristics = {
            "similarity": self._similarity_heuristic,
            "availability": self._availability_heuristic,
            "anchoring": self._anchoring_heuristic,
            "recency": self._recency_heuristic,
            "frequency": self._frequency_heuristic,
        }
        
        # 经验记忆（LRU缓存）
        self.experience_memory = OrderedDict()
        self._max_cache_size = cache_size
        
        # 快速响应模板
        self.response_templates = {
            "greeting": "你好！有什么我可以帮助你的吗？",
            "time": f"现在是{time.strftime('%Y-%m-%d %H:%M:%S')}",
            "error": "抱歉，我现在无法处理这个请求，请稍后再试。",
            "simple_query": "让我来帮你回答这个问题。",
        }
        
        # 快速关键词匹配模式
        self.keyword_patterns = {
            "时间": ["几点", "时间", "现在", "日期"],
            "问候": ["你好", "您好", "哈喽", "嗨"],
            "帮助": ["帮助", "帮忙", "怎么", "如何"],
            "确认": ["好的", "可以", "行", "是"],
            "退出": ["再见", "拜拜", "退出", "结束"],
        }
        
        logger.info("System1 初始化完成")
    
    async def make_decision(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """快速决策
        
        Args:
            situation: 当前情况
            
        Returns:
            决策结果
        """
        start_time = time.time()
        
        try:
            # 识别情况类型
            situation_type = self._identify_situation_type(situation)
            
            # 快速检查是否有预定义响应
            quick_response = self._check_quick_response(situation)
            if quick_response:
                decision_time = time.time() - start_time
                return {
                    "decision": quick_response,
                    "confidence": 0.9,
                    "time_taken": decision_time,
                    "system": "System1",
                    "type": "quick_response",
                }
            
            # 检查经验缓存
            cached_result = self._check_experience_cache(situation)
            if cached_result:
                decision_time = time.time() - start_time
                return {
                    **cached_result,
                    "time_taken": decision_time,
                    "system": "System1",
                    "type": "cached",
                }
            
            # 应用启发式规则
            decision = self._apply_heuristics(situation, situation_type)
            
            # 计算置信度
            confidence = self._calculate_confidence(situation, decision)
            
            # 记录经验
            if confidence > 0.6:
                self._record_experience(situation, decision, confidence)
            
            decision_time = time.time() - start_time
            
            return {
                "decision": decision,
                "confidence": confidence,
                "time_taken": decision_time,
                "system": "System1",
                "type": "heuristic",
                "situation_type": situation_type,
            }
            
        except Exception as e:
            logger.error(f"System1 决策失败: {e}")
            decision_time = time.time() - start_time
            return {
                "decision": self.response_templates["error"],
                "confidence": 0.3,
                "time_taken": decision_time,
                "system": "System1",
                "type": "fallback",
                "error": str(e),
            }
    
    def _identify_situation_type(self, situation: Dict[str, Any]) -> str:
        """识别情况类型
        
        Args:
            situation: 当前情况
            
        Returns:
            情况类型
        """
        input_text = situation.get("input", "").lower()
        
        # 快速关键词识别
        for situation_type, keywords in self.keyword_patterns.items():
            if any(keyword in input_text for keyword in keywords):
                return situation_type
        
        # 基于特征判断
        if len(input_text) < 10:
            return "simple"
        elif len(input_text) < 50:
            return "normal"
        else:
            return "complex"
    
    def _check_quick_response(self, situation: Dict[str, Any]) -> Optional[str]:
        """检查是否有预定义快速响应
        
        Args:
            situation: 当前情况
            
        Returns:
            快速响应或None
        """
        input_text = situation.get("input", "").lower()
        
        # 问候检测
        if any(greeting in input_text for greeting in self.keyword_patterns["问候"]):
            return self.response_templates["greeting"]
        
        # 时间询问
        if any(time_word in input_text for time_word in self.keyword_patterns["时间"]):
            return self.response_templates["time"]
        
        # 简单确认
        if len(input_text) < 5 and any(confirm in input_text for confirm in self.keyword_patterns["确认"]):
            return "好的，明白了！"
        
        return None
    
    def _check_experience_cache(self, situation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检查经验缓存
        
        Args:
            situation: 当前情况
            
        Returns:
            缓存结果或None
        """
        input_text = situation.get("input", "")
        if not input_text:
            return None
        
        # 生成缓存键
        cache_key = self._hash_input(input_text)
        
        # 检查缓存
        if cache_key in self.experience_memory:
            # LRU更新
            result = self.experience_memory.pop(cache_key)
            self.experience_memory[cache_key] = result
            
            # 检查置信度衰减
            current_time = time.time()
            age = current_time - result.get("timestamp", 0)
            decay_factor = max(0.5, 1.0 - age / 86400.0)  # 一天衰减到0.5
            
            return {
                "decision": result.get("decision"),
                "confidence": result.get("confidence", 0.5) * decay_factor,
            }
        
        return None
    
    def _apply_heuristics(self, situation: Dict[str, Any], situation_type: str) -> Any:
        """应用启发式规则
        
        Args:
            situation: 当前情况
            situation_type: 情况类型
            
        Returns:
            决策结果
        """
        # 根据情况类型选择启发式
        if situation_type in ["simple", "greeting"]:
            return self.heuristics["similarity"](situation)
        elif situation_type in ["normal", "help"]:
            return self.heuristics["recency"](situation)
        elif situation_type in ["complex"]:
            # 复杂问题需要更多启发式
            similarity_result = self.heuristics["similarity"](situation)
            frequency_result = self.heuristics["frequency"](situation)
            
            # 简单融合
            if similarity_result != "unknown":
                return similarity_result
            return frequency_result
        else:
            # 默认综合启发式
            return self.heuristics["similarity"](situation)
    
    def _similarity_heuristic(self, situation: Dict[str, Any]) -> Any:
        """相似性启发式
        
        寻找相似的过去经验
        """
        input_text = situation.get("input", "").lower()
        
        # 寻找相似的输入
        best_match = None
        best_score = 0
        
        for cache_key, result in list(self.experience_memory.items()):
            cached_input = result.get("input", "").lower()
            
            # 简单相似度计算
            similarity = self._compute_string_similarity(input_text, cached_input)
            
            if similarity > best_score and similarity > 0.7:
                best_score = similarity
                best_match = result.get("decision")
        
        if best_match:
            return best_match
        
        # 如果没有相似经验
        if len(input_text) < 10:
            return "好的，我明白了。"
        else:
            return "让我来帮你处理。"
    
    def _availability_heuristic(self, situation: Dict[str, Any]) -> Any:
        """可用性启发式
        
        基于最近的经验做出决策
        """
        # 取最近5个决策
        recent_decisions = []
        for result in reversed(self.experience_memory.values()):
            recent_decisions.append(result.get("decision"))
            if len(recent_decisions) >= 5:
                break
        
        if recent_decisions:
            # 返回最常见的决策
            counter = Counter(recent_decisions)
            return counter.most_common(1)[0][0]
        
        return "让我想想..."
    
    def _anchoring_heuristic(self, situation: Dict[str, Any]) -> Any:
        """锚定启发式
        
        基于初始信息做出决策
        """
        # 检查是否有锚定点
        context = situation.get("context", {})
        
        if "anchor" in context:
            return context["anchor"]
        elif "previous_response" in context:
            return context["previous_response"]
        else:
            return "default_decision"
    
    def _recency_heuristic(self, situation: Dict[str, Any]) -> Any:
        """近期启发式
        
        基于最近的经验
        """
        if self.experience_memory:
            # 返回最新的决策
            last_key = next(reversed(self.experience_memory))
            last_result = self.experience_memory[last_key]
            return last_result.get("decision", "default_decision")
        
        return "default_decision"
    
    def _frequency_heuristic(self, situation: Dict[str, Any]) -> Any:
        """频率启发式
        
        基于经验中出现最频繁的决策
        """
        if not self.experience_memory:
            return "default_decision"
        
        # 统计所有决策的频率
        all_decisions = [
            result.get("decision") 
            for result in self.experience_memory.values()
        ]
        
        if all_decisions:
            counter = Counter(all_decisions)
            return counter.most_common(1)[0][0]
        
        return "default_decision"
    
    def _compute_string_similarity(self, text1: str, text2: str) -> float:
        """计算字符串相似度
        
        简化版的词重叠相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度（0-1）
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _calculate_confidence(self, situation: Dict[str, Any], decision: Any) -> float:
        """计算决策的置信度
        
        Args:
            situation: 当前情况
            decision: 决策结果
            
        Returns:
            置信度（0-1）
        """
        base_confidence = 0.5
        
        # 基于经验数量
        if len(self.experience_memory) > 100:
            base_confidence += 0.2
        elif len(self.experience_memory) > 10:
            base_confidence += 0.1
        
        # 基于决策稳定性
        recent_decisions = []
        for result in list(self.experience_memory.values())[-5:]:
            recent_decisions.append(result.get("decision"))
        
        if len(recent_decisions) >= 3 and decision in recent_decisions:
            base_confidence += 0.15
        
        # 基于输入复杂度
        input_text = situation.get("input", "")
        if len(input_text) < 20:
            base_confidence += 0.15
        elif len(input_text) < 50:
            base_confidence += 0.1
        
        # 限制在0-1之间
        return max(0.0, min(1.0, base_confidence))
    
    def _record_experience(self, situation: Dict[str, Any], decision: Any, confidence: float):
        """记录经验
        
        Args:
            situation: 当前情况
            decision: 决策结果
            confidence: 置信度
        """
        input_text = situation.get("input", "")
        if not input_text:
            return
        
        # 生成缓存键
        cache_key = self._hash_input(input_text)
        
        # 存入缓存
        self.experience_memory[cache_key] = {
            "input": input_text,
            "decision": decision,
            "confidence": confidence,
            "timestamp": time.time(),
        }
        
        # LRU移除
        while len(self.experience_memory) > self._max_cache_size:
            self.experience_memory.popitem(last=False)
    
    def _hash_input(self, input_text: str) -> str:
        """为输入生成哈希键
        
        Args:
            input_text: 输入文本
            
        Returns:
            哈希键
        """
        # 简单归一化
        normalized = input_text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计信息
        """
        return {
            "cache_size": len(self.experience_memory),
            "max_cache_size": self._max_cache_size,
            "cache_hit_rate": 0.0,  # 可以添加统计计算
        }


system1 = System1()
