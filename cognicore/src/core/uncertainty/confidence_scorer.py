#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
不确定性量化模块
提供置信度评分和不确定性处理功能
专为U盘便携项目优化，轻量化设计
"""

import logging
import math
import statistics
from typing import Dict, List, Optional, Any
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """置信度评分器
    
    实现多种置信度评分方法：
    1. 决策置信度（基于知识覆盖率、记忆匹配度等）
    2. 文本生成置信度（基于一致性、相关性等）
    """
    
    def __init__(self):
        """初始化置信度评分器"""
        self.scoring_history = []
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "very_low": 0.2
        }
        logger.info("置信度评分器初始化完成")
    
    async def score_decision_confidence(
        self, 
        decision_context: Dict[str, Any],
        relevant_memories: List[Dict[str, Any]],
        knowledge_coverage: float = 0.5
    ) -> Dict[str, Any]:
        """评分决策置信度
        
        Args:
            decision_context: 决策上下文
            relevant_memories: 相关记忆列表
            knowledge_coverage: 知识覆盖率（0-1）
            
        Returns:
            置信度评分结果
        """
        try:
            memory_match_score = self._calculate_memory_match_score(relevant_memories)
            context_consistency_score = self._calculate_context_consistency(decision_context)
            knowledge_coverage_score = knowledge_coverage
            historical_similarity_score = self._calculate_historical_similarity(decision_context)
            
            confidence = (
                memory_match_score * 0.3 +
                context_consistency_score * 0.25 +
                knowledge_coverage_score * 0.3 +
                historical_similarity_score * 0.15
            )
            
            confidence_level = self._classify_confidence(confidence)
            uncertainty_analysis = self._analyze_uncertainty(
                memory_match_score,
                context_consistency_score,
                knowledge_coverage_score,
                historical_similarity_score
            )
            
            result = {
                "confidence_score": round(confidence, 3),
                "confidence_level": confidence_level,
                "uncertainty_analysis": uncertainty_analysis,
                "factor_scores": {
                    "memory_match": round(memory_match_score, 3),
                    "context_consistency": round(context_consistency_score, 3),
                    "knowledge_coverage": round(knowledge_coverage_score, 3),
                    "historical_similarity": round(historical_similarity_score, 3)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            self._record_scoring(result)
            logger.debug(f"决策置信度评分: {confidence:.3f} ({confidence_level})")
            return result
            
        except Exception as e:
            logger.error(f"决策置信度评分失败: {e}")
            return self._default_result()
    
    async def score_text_generation_confidence(
        self,
        prompt: str,
        generated_text: str,
        model_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """评分文本生成置信度
        
        Args:
            prompt: 输入提示
            generated_text: 生成的文本
            model_output: 模型原始输出
            
        Returns:
            置信度评分结果
        """
        try:
            consistency_score = self._calculate_text_consistency(generated_text)
            relevance_score = self._calculate_prompt_relevance(prompt, generated_text)
            grammar_score = self._calculate_grammar_score(generated_text)
            model_confidence_score = self._extract_model_confidence(model_output)
            
            confidence = (
                consistency_score * 0.3 +
                relevance_score * 0.3 +
                grammar_score * 0.2 +
                model_confidence_score * 0.2
            )
            
            confidence_level = self._classify_confidence(confidence)
            
            result = {
                "confidence_score": round(confidence, 3),
                "confidence_level": confidence_level,
                "factor_scores": {
                    "consistency": round(consistency_score, 3),
                    "relevance": round(relevance_score, 3),
                    "grammar": round(grammar_score, 3),
                    "model_confidence": round(model_confidence_score, 3)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            self._record_scoring(result)
            logger.debug(f"文本生成置信度评分: {confidence:.3f} ({confidence_level})")
            return result
            
        except Exception as e:
            logger.error(f"文本生成置信度评分失败: {e}")
            return self._default_result()
    
    async def score_retrieval_confidence(
        self,
        query: str,
        retrieved_items: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """评分记忆检索置信度
        
        Args:
            query: 查询文本
            retrieved_items: 检索结果列表
            top_k: 返回结果数量
            
        Returns:
            检索置信度评分结果
        """
        try:
            if not retrieved_items:
                return {
                    "confidence_score": 0.1,
                    "confidence_level": "very_low",
                    "factor_scores": {
                        "relevance": 0.0,
                        "diversity": 0.0,
                        "coverage": 0.0
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            relevance_scores = []
            for item in retrieved_items[:top_k]:
                score = item.get("score", item.get("similarity", 0.5))
                relevance_scores.append(score)
            
            avg_relevance = statistics.mean(relevance_scores)
            relevance_score = min(1.0, avg_relevance * 1.2)
            
            score_variance = statistics.variance(relevance_scores) if len(relevance_scores) > 1 else 0
            diversity_score = max(0.0, 1.0 - min(1.0, score_variance * 10))
            
            coverage_score = min(1.0, len(retrieved_items) / max(1, top_k))
            
            confidence = (
                relevance_score * 0.5 +
                diversity_score * 0.25 +
                coverage_score * 0.25
            )
            
            confidence_level = self._classify_confidence(confidence)
            
            result = {
                "confidence_score": round(confidence, 3),
                "confidence_level": confidence_level,
                "factor_scores": {
                    "relevance": round(relevance_score, 3),
                    "diversity": round(diversity_score, 3),
                    "coverage": round(coverage_score, 3)
                },
                "retrieved_count": len(retrieved_items),
                "timestamp": datetime.now().isoformat()
            }
            
            self._record_scoring(result)
            return result
            
        except Exception as e:
            logger.error(f"检索置信度评分失败: {e}")
            return self._default_result()
    
    def _calculate_memory_match_score(self, memories: List[Dict[str, Any]]) -> float:
        """计算记忆匹配度"""
        if not memories:
            return 0.2
        
        memory_count = len(memories)
        similarity_scores = []
        for memory in memories:
            if "similarity" in memory:
                similarity_scores.append(memory["similarity"])
            elif "score" in memory:
                similarity_scores.append(memory["score"])
        
        if similarity_scores:
            avg_similarity = statistics.mean(similarity_scores)
            match_score = min(0.95, avg_similarity * (0.5 + 0.5 * (min(memory_count, 5) / 5)))
        else:
            match_score = min(0.8, 0.2 + 0.6 * (min(memory_count, 5) / 5))
        
        return match_score
    
    def _calculate_context_consistency(self, context: Dict[str, Any]) -> float:
        """计算上下文一致性"""
        required_fields = ["input", "context", "thought_chain"]
        present_fields = [field for field in required_fields if field in context]
        
        if len(present_fields) == len(required_fields):
            base_score = 0.7
            thought_chain = context.get("thought_chain", [])
            if len(thought_chain) >= 3:
                base_score += 0.2
            relevant_history = context.get("context", {}).get("relevant_history", [])
            if relevant_history:
                base_score += 0.1
            return min(0.95, base_score)
        else:
            missing_count = len(required_fields) - len(present_fields)
            return max(0.1, 0.5 - missing_count * 0.2)
    
    def _calculate_historical_similarity(self, context: Dict[str, Any]) -> float:
        """计算历史相似度"""
        input_text = context.get("input", "")
        if not input_text:
            return 0.5
        
        text_length = len(input_text)
        if text_length < 10:
            return 0.3
        elif text_length < 50:
            return 0.6
        else:
            return 0.4
    
    def _calculate_text_consistency(self, text: str) -> float:
        """计算文本一致性"""
        if not text:
            return 0.0
        
        words = text.lower().split()
        if len(words) < 3:
            return 0.8
        
        word_count = {}
        for word in words:
            if len(word) > 3:
                word_count[word] = word_count.get(word, 0) + 1
        
        total_words = len([w for w in words if len(w) > 3])
        if total_words == 0:
            return 0.7
        
        repeated_words = sum(1 for count in word_count.values() if count > 1)
        repetition_ratio = repeated_words / total_words
        consistency = 1.0 - min(1.0, repetition_ratio * 2)
        
        return max(0.1, consistency)
    
    def _calculate_prompt_relevance(self, prompt: str, generated_text: str) -> float:
        """计算提示相关性"""
        if not prompt or not generated_text:
            return 0.0
        
        prompt_words = set(prompt.lower().split())
        generated_words = set(generated_text.lower().split())
        
        if not prompt_words:
            return 0.5
        
        overlap = len(prompt_words.intersection(generated_words))
        relevance = overlap / len(prompt_words)
        
        return min(1.0, relevance * 1.5)
    
    def _calculate_grammar_score(self, text: str) -> float:
        """计算语法正确性分数"""
        if not text:
            return 0.0
        
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        if len(sentences) < 2:
            return 0.7
        
        sentence_lengths = [len(s.strip()) for s in sentences if s.strip()]
        if len(sentence_lengths) < 2:
            return 0.7
        
        mean_length = statistics.mean(sentence_lengths)
        if mean_length == 0:
            return 0.5
        
        stdev_length = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0
        cv = stdev_length / mean_length if mean_length > 0 else 0
        
        ideal_cv = 0.5
        grammar_score = 1.0 - min(1.0, abs(cv - ideal_cv) * 2)
        
        return max(0.2, grammar_score)
    
    def _extract_model_confidence(self, model_output: Optional[Dict[str, Any]]) -> float:
        """从模型输出提取置信度"""
        if not model_output:
            return 0.5
        
        confidence_fields = ["confidence", "score", "probability", "prob"]
        
        for field in confidence_fields:
            if field in model_output:
                value = model_output[field]
                if isinstance(value, (int, float)):
                    return max(0.0, min(1.0, float(value)))
        
        if "logprobs" in model_output:
            logprobs = model_output["logprobs"]
            if logprobs:
                avg_logprob = statistics.mean(logprobs)
                confidence = 1.0 / (1.0 + math.exp(-avg_logprob))
                return confidence
        
        return 0.5
    
    def _analyze_uncertainty(
        self,
        memory_match: float,
        context_consistency: float,
        knowledge_coverage: float,
        historical_similarity: float
    ) -> Dict[str, Any]:
        """分析不确定性来源"""
        uncertainty_sources = []
        
        if memory_match < 0.3:
            uncertainty_sources.append({
                "source": "memory_match",
                "score": memory_match,
                "description": "缺乏相关记忆支持",
                "recommendation": "需要更多领域知识或示例"
            })
        
        if context_consistency < 0.4:
            uncertainty_sources.append({
                "source": "context_consistency",
                "score": context_consistency,
                "description": "上下文信息不完整",
                "recommendation": "需要澄清问题背景"
            })
        
        if knowledge_coverage < 0.3:
            uncertainty_sources.append({
                "source": "knowledge_coverage",
                "score": knowledge_coverage,
                "description": "知识覆盖不足",
                "recommendation": "需要扩展相关知识库"
            })
        
        if historical_similarity < 0.3:
            uncertainty_sources.append({
                "source": "historical_similarity",
                "score": historical_similarity,
                "description": "缺乏类似历史案例",
                "recommendation": "需要更多类似问题的经验"
            })
        
        scores = [memory_match, context_consistency, knowledge_coverage, historical_similarity]
        avg_score = statistics.mean(scores) if scores else 0.5
        overall_uncertainty = 1.0 - avg_score
        
        return {
            "overall_uncertainty": round(overall_uncertainty, 3),
            "uncertainty_sources": uncertainty_sources,
            "primary_source": uncertainty_sources[0]["source"] if uncertainty_sources else None
        }
    
    def _classify_confidence(self, confidence_score: float) -> str:
        """分类置信度"""
        if confidence_score >= self.confidence_thresholds["high"]:
            return "high"
        elif confidence_score >= self.confidence_thresholds["medium"]:
            return "medium"
        elif confidence_score >= self.confidence_thresholds["low"]:
            return "low"
        else:
            return "very_low"
    
    def _record_scoring(self, scoring_result: Dict[str, Any]):
        """记录评分结果"""
        self.scoring_history.append(scoring_result)
        if len(self.scoring_history) > 1000:
            self.scoring_history = self.scoring_history[-1000:]
    
    def _default_result(self) -> Dict[str, Any]:
        """返回默认结果"""
        return {
            "confidence_score": 0.5,
            "confidence_level": "medium",
            "factor_scores": {},
            "timestamp": datetime.now().isoformat()
        }
    
    def get_scoring_history(self) -> List[Dict[str, Any]]:
        """获取评分历史"""
        return self.scoring_history
    
    def set_confidence_threshold(self, level: str, threshold: float):
        """设置置信度阈值"""
        if level in self.confidence_thresholds:
            self.confidence_thresholds[level] = max(0.0, min(1.0, threshold))
    
    def get_confidence_thresholds(self) -> Dict[str, float]:
        """获取置信度阈值"""
        return self.confidence_thresholds.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取评分统计"""
        if not self.scoring_history:
            return {"total_scores": 0}
        
        scores = [s["confidence_score"] for s in self.scoring_history]
        return {
            "total_scores": len(scores),
            "avg_confidence": round(statistics.mean(scores), 3),
            "min_confidence": round(min(scores), 3),
            "max_confidence": round(max(scores), 3),
            "recent_avg": round(statistics.mean(scores[-10:]), 3) if len(scores) >= 10 else None
        }


confidence_scorer = ConfidenceScorer()
