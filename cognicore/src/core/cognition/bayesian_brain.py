#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贝叶斯大脑模块
负责概率更新和决策逻辑
专为U盘便携项目优化
"""

import math
from typing import Dict, List, Optional, Any
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BayesianBrain:
    """贝叶斯大脑
    
    实现：
    - 贝叶斯概率更新
    - 主动推理
    - 世界模型构建
    - 信息增益计算
    """
    
    def __init__(self):
        """初始化贝叶斯大脑"""
        # 世界模型 - 存储状态概率
        self.world_model: Dict[str, float] = {}
        # 行动空间
        self.action_space: List[str] = []
        # 历史观测
        self.observations: List[Dict] = []
        # 历史行动
        self.actions: List[str] = []
        # 似然缓存
        self.likelihood_cache: Dict[str, Dict[str, float]] = {}
        # 先验知识
        self.prior_knowledge: Dict[str, float] = {
            "certain": 0.9,
            "likely": 0.7,
            "possible": 0.5,
            "unlikely": 0.3,
            "uncertain": 0.5,
        }
        
        logger.info("BayesianBrain 初始化完成")
    
    def initialize_world_model(self, states: Optional[Dict[str, float]] = None):
        """初始化世界模型
        
        Args:
            states: 初始状态（可选）
        """
        if states:
            self.world_model = states
        else:
            # 默认初始化
            self.world_model = {
                "state_unknown": 1.0,
            }
    
    def update_priors(self, new_evidence: Dict[str, float]):
        """更新先验概率
        
        Args:
            new_evidence: 新的证据，键为状态，值为概率
        """
        for state, probability in new_evidence.items():
            self.world_model[state] = max(0.01, min(0.99, probability))
        
        # 归一化
        self._normalize_world_model()
        
        logger.debug(f"更新了 {len(new_evidence)} 个先验概率")
    
    def bayesian_update(self, observation: Dict) -> Dict[str, float]:
        """执行贝叶斯更新
        
        Args:
            observation: 当前观测
            
        Returns:
            更新后的后验概率
        """
        if not self.world_model:
            self.initialize_world_model()
        
        posterior = {}
        total_prob = 0.0
        
        for state, prior in self.world_model.items():
            # 计算似然
            likelihood = self._calculate_likelihood(state, observation)
            # 计算联合概率
            joint = prior * likelihood
            posterior[state] = joint
            total_prob += joint
        
        # 归一化
        if total_prob > 0:
            for state in posterior:
                posterior[state] /= total_prob
        
        # 更新世界模型
        self.world_model = posterior
        # 记录观测
        self.observations.append({
            "timestamp": datetime.now().isoformat(),
            "observation": observation,
        })
        
        return posterior
    
    def _calculate_likelihood(self, state: str, observation: Dict) -> float:
        """计算似然概率
        
        Args:
            state: 当前状态
            observation: 观测数据
            
        Returns:
            似然概率
        """
        cache_key = f"{state}|{str(observation)}"
        
        if cache_key in self.likelihood_cache:
            return self.likelihood_cache[cache_key]
        
        likelihood = 0.5
        
        # 基于观测数据计算似然
        if "evidence" in observation:
            evidence = observation["evidence"]
            
            if isinstance(evidence, dict):
                # 字典型证据匹配
                match_score = 0
                for key, value in evidence.items():
                    if key in state.lower():
                        match_score += 1
                    if str(value).lower() in state.lower():
                        match_score += 0.5
                
                likelihood += min(0.4, match_score * 0.1)
                
            elif isinstance(evidence, str):
                # 文本证据匹配
                evidence_lower = evidence.lower()
                state_lower = state.lower()
                
                if evidence_lower in state_lower:
                    likelihood += 0.4
                else:
                    # 词重叠
                    evidence_words = set(evidence_lower.split())
                    state_words = set(state_lower.split())
                    overlap = len(evidence_words & state_words)
                    if evidence_words:
                        likelihood += overlap / len(evidence_words) * 0.3
        
        # 确保似然值在合理范围内
        likelihood = max(0.01, min(0.99, likelihood))
        
        # 缓存
        if len(self.likelihood_cache) < 1000:
            self.likelihood_cache[cache_key] = likelihood
        
        return likelihood
    
    def active_inference(self, possible_actions: List[str]) -> str:
        """主动推理选择行动
        
        基于自由能原理，选择能最大化信息增益的行动
        
        Args:
            possible_actions: 可能的行动列表
            
        Returns:
            选择的行动
        """
        if not possible_actions:
            return "no_action"
        
        # 计算每个行动的信息增益
        action_scores = {}
        for action in possible_actions:
            info_gain = self._calculate_information_gain(action)
            expected_value = self._calculate_expected_value(action)
            
            # 综合评分：信息增益为主，预期价值为辅
            action_scores[action] = info_gain * 0.6 + expected_value * 0.4
        
        # 选择评分最高的行动
        best_action = max(action_scores, key=lambda x: action_scores[x])
        
        # 记录行动
        self.actions.append({
            "timestamp": datetime.now().isoformat(),
            "action": best_action,
            "scores": action_scores,
        })
        
        logger.debug(f"主动推理选择: {best_action}, 评分: {action_scores[best_action]:.3f}")
        
        return best_action
    
    def _calculate_expected_value(self, action: str) -> float:
        """计算行动的预期价值
        
        Args:
            action: 行动
            
        Returns:
            预期价值
        """
        value = 0.0
        
        # 基于行动与当前状态的相关性
        action_lower = action.lower()
        
        for state, prob in self.world_model.items():
            state_lower = state.lower()
            
            # 关键词匹配
            if action_lower in state_lower:
                value += prob * 1.5
            elif any(word in state_lower for word in action_lower.split()):
                value += prob * 1.2
            else:
                value += prob * 0.8
        
        # 归一化到[0, 1]
        value = min(1.0, value)
        
        return value
    
    def _calculate_information_gain(self, action: str) -> float:
        """计算行动的预期信息增益
        
        Args:
            action: 行动
            
        Returns:
            预期信息增益
        """
        if not self.world_model:
            return 0.0
        
        # 计算当前熵
        current_entropy = self._calculate_entropy(self.world_model)
        
        # 模拟行动后的状态分布
        predicted_states = self._predict_states_after_action(action)
        
        # 计算预期熵
        expected_entropy = self._calculate_entropy(predicted_states)
        
        # 信息增益 = 当前熵 - 预期熵
        information_gain = current_entropy - expected_entropy
        
        return max(0.0, information_gain)
    
    def _calculate_entropy(self, distribution: Dict[str, float]) -> float:
        """计算概率分布的熵
        
        Args:
            distribution: 概率分布
            
        Returns:
            熵值
        """
        entropy = 0.0
        
        for prob in distribution.values():
            if prob > 0:
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _predict_states_after_action(self, action: str) -> Dict[str, float]:
        """预测行动后的状态分布
        
        Args:
            action: 行动
            
        Returns:
            预测的状态分布
        """
        predicted = {}
        action_lower = action.lower()
        
        for state, prob in self.world_model.items():
            state_lower = state.lower()
            
            # 简单的状态转移模型
            if action_lower in state_lower:
                # 行动与状态相关，增加概率
                predicted[state] = prob * 1.2
            else:
                # 行动与状态无关，略微降低概率
                predicted[state] = prob * 0.9
        
        # 归一化
        total = sum(predicted.values())
        if total > 0:
            for state in predicted:
                predicted[state] /= total
        
        return predicted
    
    def _normalize_world_model(self):
        """归一化世界模型概率"""
        total = sum(self.world_model.values())
        
        if total > 0:
            for state in self.world_model:
                self.world_model[state] /= total
    
    def get_most_probable_state(self) -> tuple[str, float]:
        """获取最可能的状态
        
        Returns:
            (状态, 概率)
        """
        if not self.world_model:
            return ("unknown", 0.0)
        
        best_state = max(self.world_model.keys(), key=lambda k: self.world_model[k])
        return (best_state, self.world_model[best_state])
    
    def get_top_states(self, n: int = 5) -> List[tuple[str, float]]:
        """获取最可能的N个状态
        
        Args:
            n: 数量
            
        Returns:
            [(状态, 概率)] 列表
        """
        sorted_states = sorted(
            self.world_model.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_states[:n]
    
    def get_beliefs(self) -> Dict[str, float]:
        """获取当前信念状态
        
        Returns:
            当前世界模型的概率分布
        """
        return self.world_model.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计信息
        """
        return {
            "num_states": len(self.world_model),
            "num_observations": len(self.observations),
            "num_actions": len(self.actions),
            "entropy": self._calculate_entropy(self.world_model),
            "top_state": self.get_most_probable_state(),
        }
    
    def reset(self):
        """重置贝叶斯大脑"""
        self.world_model = {}
        self.observations = []
        self.actions = []
        self.likelihood_cache = {}
        
        logger.info("BayesianBrain 已重置")


bayesian_brain = BayesianBrain()
