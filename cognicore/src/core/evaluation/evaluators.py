#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估框架模块
提供 RAG 系统的评估功能：忠实度、相关性、质量评估
专为U盘便携项目优化
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class ScoreLevel(Enum):
    """评分级别"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


@dataclass
class FaithfulnessScore:
    """忠实度评分"""
    score: float
    level: str
    claims: List[Dict[str, Any]]
    unsupported_claims: List[str]
    context_coverage: float
    hallucination_count: int


@dataclass
class RelevanceScore:
    """相关性评分"""
    score: float
    level: str
    question_relevance: float
    answer_relevance: float
    context_utilization: float
    relevant_chunks: List[Dict[str, Any]]


@dataclass
class QualityScore:
    """质量评分"""
    score: float
    level: str
    completeness: float
    accuracy: float
    coherence: float
    fluency: float


class FaithfulnessEvaluator:
    """忠实度评估器
    
    评估回答是否忠实于给定的上下文
    """
    
    def __init__(self):
        """初始化评估器"""
        self._setup_patterns()
    
    def _setup_patterns(self):
        """设置评估模式"""
        self._hallucination_patterns = [
            r"据.*说",
            r"据说",
            r"可能.*是的",
            r"也许是",
            r"我不确定但是",
            r"虽然.*但是.*没有.*证据",
        ]
        
        self._citation_patterns = [
            r"根据上下文",
            r"从.*中可以看到",
            r"文章.*提到",
            r"材料.*显示",
        ]
    
    async def evaluate(
        self,
        question: str,
        context: str,
        answer: str
    ) -> FaithfulnessScore:
        """评估忠实度
        
        Args:
            question: 问题
            context: 上下文
            answer: 回答
            
        Returns:
            忠实度评分
        """
        try:
            claims = self._extract_claims(answer)
            supported_claims, unsupported_claims = self._check_claim_support(
                claims, context
            )
            
            context_coverage = self._calculate_context_coverage(
                answer, context
            )
            
            hallucination_count = len(unsupported_claims)
            
            score = self._calculate_faithfulness_score(
                len(claims),
                len(supported_claims),
                context_coverage,
                hallucination_count
            )
            
            level = self._get_level(score)
            
            return FaithfulnessScore(
                score=score,
                level=level,
                claims=claims,
                unsupported_claims=unsupported_claims,
                context_coverage=context_coverage,
                hallucination_count=hallucination_count
            )
            
        except Exception as e:
            logger.error(f"忠实度评估失败: {e}")
            return FaithfulnessScore(
                score=0.5,
                level="fair",
                claims=[],
                unsupported_claims=[],
                context_coverage=0.0,
                hallucination_count=0
            )
    
    def _extract_claims(self, text: str) -> List[Dict[str, Any]]:
        """提取声明
        
        Args:
            text: 文本
            
        Returns:
            声明列表
        """
        sentences = re.split(r"[.!?。！？]+", text)
        claims = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:
                claims.append({
                    "id": i,
                    "text": sentence,
                    "has_citation": any(
                        re.search(p, sentence)
                        for p in self._citation_patterns
                    )
                })
        
        return claims
    
    def _check_claim_support(
        self,
        claims: List[Dict[str, Any]],
        context: str
    ) -> tuple:
        """检查声明支持
        
        Args:
            claims: 声明列表
            context: 上下文
            
        Returns:
            (支持的声明, 不支持的声明)
        """
        supported = []
        unsupported = []
        
        context_lower = context.lower()
        
        for claim in claims:
            claim_text = claim["text"].lower()
            
            if claim["has_citation"]:
                supported.append(claim)
                continue
            
            words = claim_text.split()
            matched_words = [
                w for w in words
                if len(w) > 2 and w in context_lower
            ]
            
            if len(matched_words) / max(len(words), 1) > 0.3:
                supported.append(claim)
            else:
                unsupported.append(claim["text"])
        
        return supported, unsupported
    
    def _calculate_context_coverage(
        self,
        answer: str,
        context: str
    ) -> float:
        """计算上下文覆盖率
        
        Args:
            answer: 回答
            context: 上下文
            
        Returns:
            覆盖率（0-1）
        """
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        
        if not answer_words:
            return 0.0
        
        intersection = answer_words.intersection(context_words)
        coverage = len(intersection) / len(answer_words)
        
        return min(1.0, coverage)
    
    def _calculate_faithfulness_score(
        self,
        total_claims: int,
        supported_claims: int,
        context_coverage: float,
        hallucination_count: int
    ) -> float:
        """计算忠实度分数
        
        Args:
            total_claims: 总声明数
            supported_claims: 支持的声明数
            context_coverage: 上下文覆盖率
            hallucination_count: 幻觉数量
            
        Returns:
            忠实度分数（0-1）
        """
        if total_claims == 0:
            return 0.8
        
        claim_score = supported_claims / total_claims
        
        hallucination_penalty = min(0.3, hallucination_count * 0.1)
        
        score = (
            claim_score * 0.5 +
            context_coverage * 0.3 +
            (1 - hallucination_penalty) * 0.2
        )
        
        return max(0.0, min(1.0, score))
    
    def _get_level(self, score: float) -> str:
        """获取评分级别
        
        Args:
            score: 分数
            
        Returns:
            级别名称
        """
        if score >= 0.9:
            return ScoreLevel.EXCELLENT.value
        elif score >= 0.7:
            return ScoreLevel.GOOD.value
        elif score >= 0.5:
            return ScoreLevel.FAIR.value
        elif score >= 0.3:
            return ScoreLevel.POOR.value
        else:
            return ScoreLevel.VERY_POOR.value


class RelevanceEvaluator:
    """相关性评估器
    
    评估回答与问题的相关程度
    """
    
    def __init__(self):
        """初始化评估器"""
        pass
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> RelevanceScore:
        """评估相关性
        
        Args:
            question: 问题
            answer: 回答
            retrieved_chunks: 检索到的文本块
            
        Returns:
            相关性评分
        """
        try:
            question_relevance = self._calculate_question_relevance(
                question, answer
            )
            
            answer_relevance = self._calculate_answer_relevance(
                question, answer
            )
            
            context_utilization = self._calculate_context_utilization(
                answer, retrieved_chunks
            )
            
            relevant_chunks = self._filter_relevant_chunks(
                question, retrieved_chunks
            )
            
            score = self._calculate_relevance_score(
                question_relevance,
                answer_relevance,
                context_utilization
            )
            
            level = self._get_level(score)
            
            return RelevanceScore(
                score=score,
                level=level,
                question_relevance=question_relevance,
                answer_relevance=answer_relevance,
                context_utilization=context_utilization,
                relevant_chunks=relevant_chunks
            )
            
        except Exception as e:
            logger.error(f"相关性评估失败: {e}")
            return RelevanceScore(
                score=0.5,
                level="fair",
                question_relevance=0.5,
                answer_relevance=0.5,
                context_utilization=0.5,
                relevant_chunks=[]
            )
    
    def _calculate_question_relevance(
        self,
        question: str,
        answer: str
    ) -> float:
        """计算问题相关性
        
        Args:
            question: 问题
            answer: 回答
            
        Returns:
            相关性分数（0-1）
        """
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        if not question_words:
            return 0.5
        
        intersection = question_words.intersection(answer_words)
        relevance = len(intersection) / len(question_words)
        
        return min(1.0, relevance * 1.2)
    
    def _calculate_answer_relevance(
        self,
        question: str,
        answer: str
    ) -> float:
        """计算回答相关性
        
        Args:
            question: 问题
            answer: 回答
            
        Returns:
            相关性分数（0-1）
        """
        if not answer or len(answer) < 10:
            return 0.2
        
        question_keywords = self._extract_keywords(question)
        answer_keywords = self._extract_keywords(answer)
        
        if not question_keywords:
            return 0.5
        
        matched = sum(
            1 for kw in question_keywords
            if kw in answer_keywords
        )
        
        return matched / len(question_keywords)
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词
        
        Args:
            text: 文本
            
        Returns:
            关键词集合
        """
        stopwords = {
            "的", "了", "在", "是", "我", "有", "和", "就",
            "不", "人", "都", "一", "一个", "上", "也", "很",
            "到", "说", "要", "去", "你", "会", "着", "没有",
            "看", "好", "自己", "这", "那", "他", "她", "它"
        }
        
        words = text.lower().split()
        keywords = {
            w for w in words
            if len(w) > 1 and w not in stopwords
        }
        
        return keywords
    
    def _calculate_context_utilization(
        self,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> float:
        """计算上下文利用率
        
        Args:
            answer: 回答
            chunks: 检索到的文本块
            
        Returns:
            利用率（0-1）
        """
        if not chunks:
            return 0.3
        
        utilized = 0
        answer_lower = answer.lower()
        
        for chunk in chunks:
            chunk_text = chunk.get("text", "").lower()
            chunk_words = set(chunk_text.split())
            answer_words = set(answer_lower.split())
            
            overlap = len(chunk_words.intersection(answer_words))
            if overlap > 5:
                utilized += 1
        
        return utilized / len(chunks)
    
    def _filter_relevant_chunks(
        self,
        question: str,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """过滤相关文本块
        
        Args:
            question: 问题
            chunks: 文本块列表
            
        Returns:
            相关文本块列表
        """
        question_keywords = self._extract_keywords(question)
        
        if not question_keywords:
            return chunks[:3]
        
        scored_chunks = []
        
        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            chunk_keywords = self._extract_keywords(chunk_text)
            
            overlap = len(question_keywords.intersection(chunk_keywords))
            score = overlap / len(question_keywords)
            
            scored_chunks.append({
                **chunk,
                "relevance_score": score
            })
        
        scored_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return scored_chunks[:5]
    
    def _calculate_relevance_score(
        self,
        question_relevance: float,
        answer_relevance: float,
        context_utilization: float
    ) -> float:
        """计算相关性分数
        
        Args:
            question_relevance: 问题相关性
            answer_relevance: 回答相关性
            context_utilization: 上下文利用率
            
        Returns:
            综合相关性分数
        """
        return (
            question_relevance * 0.35 +
            answer_relevance * 0.35 +
            context_utilization * 0.3
        )
    
    def _get_level(self, score: float) -> str:
        """获取评分级别"""
        if score >= 0.8:
            return ScoreLevel.EXCELLENT.value
        elif score >= 0.6:
            return ScoreLevel.GOOD.value
        elif score >= 0.4:
            return ScoreLevel.FAIR.value
        elif score >= 0.2:
            return ScoreLevel.POOR.value
        else:
            return ScoreLevel.VERY_POOR.value


class QualityEvaluator:
    """质量评估器
    
    评估回答的整体质量
    """
    
    def __init__(self):
        """初始化评估器"""
        pass
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None
    ) -> QualityScore:
        """评估质量
        
        Args:
            question: 问题
            answer: 回答
            context: 上下文
            
        Returns:
            质量评分
        """
        try:
            completeness = self._evaluate_completeness(question, answer)
            accuracy = self._evaluate_accuracy(answer)
            coherence = self._evaluate_coherence(answer)
            fluency = self._evaluate_fluency(answer)
            
            score = self._calculate_quality_score(
                completeness, accuracy, coherence, fluency
            )
            
            level = self._get_level(score)
            
            return QualityScore(
                score=score,
                level=level,
                completeness=completeness,
                accuracy=accuracy,
                coherence=coherence,
                fluency=fluency
            )
            
        except Exception as e:
            logger.error(f"质量评估失败: {e}")
            return QualityScore(
                score=0.5,
                level="fair",
                completeness=0.5,
                accuracy=0.5,
                coherence=0.5,
                fluency=0.5
            )
    
    def _evaluate_completeness(
        self,
        question: str,
        answer: str
    ) -> float:
        """评估完整性
        
        Args:
            question: 问题
            answer: 回答
            
        Returns:
            完整性分数
        """
        if len(answer) < 20:
            return 0.2
        
        question_length = len(question)
        answer_length = len(answer)
        
        if answer_length < question_length:
            return 0.3
        
        ratio = answer_length / max(question_length, 1)
        
        if ratio < 1:
            return 0.4
        elif ratio < 3:
            return 0.8
        elif ratio < 10:
            return 0.9
        else:
            return 0.7
    
    def _evaluate_accuracy(self, answer: str) -> float:
        """评估准确性
        
        Args:
            answer: 回答
            
        Returns:
            准确性分数
        """
        if not answer:
            return 0.0
        
        negation_count = len(re.findall(r"不|没|无|非|别", answer))
        if negation_count > len(answer) / 50:
            return 0.6
        
        uncertainty_markers = len(re.findall(
            r"可能|也许|大概|估计|应该|或许|好像|似乎",
            answer
        ))
        
        if uncertainty_markers > 3:
            return 0.7
        
        return 0.85
    
    def _evaluate_coherence(self, answer: str) -> float:
        """评估连贯性
        
        Args:
            answer: 回答
            
        Returns:
            连贯性分数
        """
        sentences = re.split(r"[.!?。！？]+", answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return 0.7
        
        coherence_scores = []
        for i in range(len(sentences) - 1):
            words1 = set(sentences[i].split())
            words2 = set(sentences[i + 1].split())
            
            if not words1 or not words2:
                coherence_scores.append(0.5)
                continue
            
            overlap = len(words1.intersection(words2))
            score = overlap / min(len(words1), len(words2))
            coherence_scores.append(score)
        
        return statistics.mean(coherence_scores) if coherence_scores else 0.5
    
    def _evaluate_fluency(self, answer: str) -> float:
        """评估流畅性
        
        Args:
            answer: 回答
            
        Returns:
            流畅性分数
        """
        if not answer:
            return 0.0
        
        sentence_count = len(re.findall(r"[.!?。！？]", answer))
        word_count = len(answer.split())
        
        if word_count == 0:
            return 0.0
        
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        if avg_sentence_length < 5:
            return 0.4
        elif avg_sentence_length < 30:
            return 0.9
        else:
            return 0.7
    
    def _calculate_quality_score(
        self,
        completeness: float,
        accuracy: float,
        coherence: float,
        fluency: float
    ) -> float:
        """计算质量分数
        
        Args:
            completeness: 完整性
            accuracy: 准确性
            coherence: 连贯性
            fluency: 流畅性
            
        Returns:
            质量分数
        """
        return (
            completeness * 0.25 +
            accuracy * 0.35 +
            coherence * 0.20 +
            fluency * 0.20
        )
    
    def _get_level(self, score: float) -> str:
        """获取评分级别"""
        if score >= 0.85:
            return ScoreLevel.EXCELLENT.value
        elif score >= 0.7:
            return ScoreLevel.GOOD.value
        elif score >= 0.5:
            return ScoreLevel.FAIR.value
        elif score >= 0.3:
            return ScoreLevel.POOR.value
        else:
            return ScoreLevel.VERY_POOR.value


import statistics

faithfulness_evaluator = FaithfulnessEvaluator()
relevance_evaluator = RelevanceEvaluator()
quality_evaluator = QualityEvaluator()
