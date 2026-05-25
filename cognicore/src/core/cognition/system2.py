#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统2模块
负责慢速分析决策，基于逻辑和推理
专为U盘便携项目优化
"""

import time
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReasoningMode(Enum):
    """推理模式"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    ACTIVE_INFERENCE = "active_inference"


@dataclass
class ReasoningStep:
    """推理步骤"""
    step: int
    thought: str
    action: Optional[str]
    observation: Optional[str]
    confidence: float
    timestamp: float


@dataclass
class ThoughtNode:
    """思维节点（用于树搜索）"""
    id: str
    content: str
    confidence: float
    parent_id: Optional[str]
    children: List["ThoughtNode"]
    depth: int


class System2:
    """系统2 - 深度分析决策
    
    特点：
    - 深度分析推理
    - 基于贝叶斯大脑
    - 链式/树形推理
    - 可解释性
    """
    
    def __init__(self, bayesian_brain=None, reasoning_mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT):
        """初始化系统2
        
        Args:
            bayesian_brain: 贝叶斯大脑实例
            reasoning_mode: 推理模式
        """
        self.bayesian_brain = bayesian_brain
        self.reasoning_mode = reasoning_mode
        self.reasoning_depth = 3
        self.max_thought_branches = 3
        self.min_confidence_threshold = 0.3
        
        # 推理历史
        self.reasoning_history: List[List[ReasoningStep]] = []
        
        # 推理模板
        self.thinking_templates = [
            "让我想想这个问题...",
            "首先，我需要明确...",
            "接下来，我应该...",
            "然后，我会...",
            "最后，我认为...",
        ]
        
        logger.info(f"System2 初始化完成，推理模式: {reasoning_mode}")
    
    async def make_decision(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """分析决策
        
        Args:
            situation: 当前情况
            
        Returns:
            决策结果
        """
        start_time = time.time()
        
        try:
            # 构建世界模型
            world_model = self._build_world_model(situation)
            
            # 生成可能的行动
            possible_actions = self._generate_possible_actions(situation, world_model)
            
            # 使用指定模式推理
            if self.reasoning_mode == ReasoningMode.TREE_OF_THOUGHT:
                reasoning_chain, best_action = await self._tree_reasoning(situation, possible_actions)
            elif self.reasoning_mode == ReasoningMode.ACTIVE_INFERENCE:
                reasoning_chain, best_action = await self._active_inference_reasoning(situation, possible_actions)
            else:
                reasoning_chain, best_action = await self._chain_reasoning(situation, possible_actions)
            
            # 评估决策
            evaluation = self._evaluate_decision(situation, best_action, reasoning_chain)
            
            # 记录推理历史
            self.reasoning_history.append(reasoning_chain)
            
            decision_time = time.time() - start_time
            
            return {
                "decision": best_action,
                "confidence": evaluation["confidence"],
                "time_taken": decision_time,
                "system": "System2",
                "reasoning_chain": reasoning_chain,
                "reasoning_mode": self.reasoning_mode.value,
                "world_model": world_model,
                "evaluation": evaluation,
            }
            
        except Exception as e:
            logger.error(f"System2 决策失败: {e}")
            decision_time = time.time() - start_time
            return {
                "decision": "抱歉，我需要更多信息来分析这个问题。",
                "confidence": 0.3,
                "time_taken": decision_time,
                "system": "System2",
                "error": str(e),
            }
    
    def _build_world_model(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """构建世界模型
        
        Args:
            situation: 当前情况
            
        Returns:
            世界模型
        """
        world_model = {
            "states": {},
            "beliefs": {},
            "goals": [],
            "constraints": [],
        }
        
        # 从情况中提取信息
        if "context" in situation:
            world_model["context"] = situation["context"]
        
        if "input" in situation:
            world_model["input"] = situation["input"]
        
        # 生成默认状态
        if self.bayesian_brain:
            world_model["states"] = self.bayesian_brain.world_model
        else:
            # 简单状态
            world_model["states"] = {
                "certainty": 0.5,
                "complexity": self._assess_complexity(situation),
            }
        
        # 提取目标
        if "goals" in situation:
            world_model["goals"] = situation["goals"]
        else:
            world_model["goals"] = ["provide_answer", "be_helpful"]
        
        return world_model
    
    def _assess_complexity(self, situation: Dict[str, Any]) -> float:
        """评估问题复杂度
        
        Args:
            situation: 当前情况
            
        Returns:
            复杂度（0-1）
        """
        input_text = situation.get("input", "")
        complexity = 0.3  # 基础复杂度
        
        # 基于长度
        if len(input_text) > 100:
            complexity += 0.2
        if len(input_text) > 200:
            complexity += 0.15
        
        # 基于关键词
        complex_keywords = ["为什么", "怎么", "如何", "对比", "分析", "总结"]
        for keyword in complex_keywords:
            if keyword in input_text:
                complexity += 0.05
        
        return min(1.0, complexity)
    
    def _generate_possible_actions(self, situation: Dict[str, Any], world_model: Dict[str, Any]) -> List[str]:
        """生成可能的行动
        
        Args:
            situation: 当前情况
            world_model: 世界模型
            
        Returns:
            可能的行动列表
        """
        input_text = situation.get("input", "")
        possible_actions = []
        
        # 从情况中获取
        if "possible_actions" in situation:
            possible_actions.extend(situation["possible_actions"])
        
        # 默认行动
        default_actions = [
            "answer_question",
            "ask_for_clarification",
            "provide_information",
            "suggest_help",
        ]
        
        possible_actions.extend(default_actions)
        
        # 去重
        return list(dict.fromkeys(possible_actions))[:5]  # 保留5个
    
    async def _chain_reasoning(
        self, situation: Dict[str, Any], possible_actions: List[str]
    ) -> tuple[List[ReasoningStep], str]:
        """链式推理
        
        Args:
            situation: 当前情况
            possible_actions: 可能的行动
            
        Returns:
            (推理链, 最佳行动)
        """
        reasoning_chain = []
        current_action = None
        
        for step in range(self.reasoning_depth):
            # 模拟思考过程
            thought = self._generate_thought(step, situation)
            
            # 选择行动
            if step == 0:
                current_action = self._select_best_action(possible_actions, situation)
            else:
                current_action = self._refine_action(current_action, situation)
            
            # 模拟观察
            observation = self._simulate_observation(situation, current_action, step)
            
            # 计算置信度
            confidence = self._calculate_step_confidence(step, situation)
            
            reasoning_chain.append(
                ReasoningStep(
                    step=step + 1,
                    thought=thought,
                    action=current_action,
                    observation=observation,
                    confidence=confidence,
                    timestamp=time.time(),
                )
            )
        
        # 最后一步确定最终行动
        final_action = self._determine_final_action(reasoning_chain)
        
        return reasoning_chain, final_action
    
    async def _tree_reasoning(
        self, situation: Dict[str, Any], possible_actions: List[str]
    ) -> tuple[List[ReasoningStep], str]:
        """树搜索推理
        
        Args:
            situation: 当前情况
            possible_actions: 可能的行动
            
        Returns:
            (推理链, 最佳行动)
        """
        # 简化版树推理
        # 实际实现可以更复杂，包含节点评估、剪枝等
        
        # 先生成几个分支
        branches = []
        for i in range(min(len(possible_actions), self.max_thought_branches)):
            action = possible_actions[i]
            confidence = random.uniform(0.4, 0.8)
            branches.append((action, confidence))
        
        # 选择置信度最高的分支
        best_branch = max(branches, key=lambda x: x[1])
        
        # 对此分支进行深度推理
        reasoning_chain, final_action = await self._chain_reasoning(situation, [best_branch[0]])
        
        return reasoning_chain, final_action
    
    async def _active_inference_reasoning(
        self, situation: Dict[str, Any], possible_actions: List[str]
    ) -> tuple[List[ReasoningStep], str]:
        """主动推理（简化版）
        
        Args:
            situation: 当前情况
            possible_actions: 可能的行动
            
        Returns:
            (推理链, 最佳行动)
        """
        if not self.bayesian_brain:
            # 降级为链式推理
            return await self._chain_reasoning(situation, possible_actions)
        
        # 使用贝叶斯大脑进行主动推理
        try:
            best_action = self.bayesian_brain.active_inference(possible_actions)
        except:
            best_action = possible_actions[0] if possible_actions else "default_action"
        
        # 生成推理链
        reasoning_chain = []
        for step in range(self.reasoning_depth):
            thought = f"基于贝叶斯大脑选择行动: {best_action}"
            observation = f"预期结果: {step + 1}/3"
            confidence = 0.6 + step * 0.1
            
            reasoning_chain.append(
                ReasoningStep(
                    step=step + 1,
                    thought=thought,
                    action=best_action,
                    observation=observation,
                    confidence=min(0.9, confidence),
                    timestamp=time.time(),
                )
            )
        
        return reasoning_chain, best_action
    
    def _generate_thought(self, step: int, situation: Dict[str, Any]) -> str:
        """生成思考内容
        
        Args:
            step: 步骤
            situation: 当前情况
            
        Returns:
            思考内容
        """
        template = self.thinking_templates[step % len(self.thinking_templates)]
        
        input_text = situation.get("input", "")
        if input_text:
            return f"{template} 关于: '{input_text[:30]}...'"
        
        return template
    
    def _select_best_action(self, possible_actions: List[str], situation: Dict[str, Any]) -> str:
        """选择最佳行动
        
        Args:
            possible_actions: 可能的行动
            situation: 当前情况
            
        Returns:
            最佳行动
        """
        if not possible_actions:
            return "default_action"
        
        # 简单的行动选择策略
        input_text = situation.get("input", "").lower()
        
        # 关键词匹配
        if "为什么" in input_text or "怎么" in input_text:
            if "answer_question" in possible_actions:
                return "answer_question"
        if "?" in input_text or "？" in input_text:
            if "provide_information" in possible_actions:
                return "provide_information"
        
        # 默认选择第一个
        return possible_actions[0]
    
    def _refine_action(self, current_action: str, situation: Dict[str, Any]) -> str:
        """细化行动
        
        Args:
            current_action: 当前行动
            situation: 当前情况
            
        Returns:
            细化后的行动
        """
        # 简单实现，保持原行动
        return current_action
    
    def _simulate_observation(self, situation: Dict[str, Any], action: str, step: int) -> str:
        """模拟观察结果
        
        Args:
            situation: 当前情况
            action: 行动
            step: 步骤
            
        Returns:
            观察结果
        """
        return f"执行 {action} 后，观察结果: 状态良好，进展顺利 (步骤 {step + 1})"
    
    def _calculate_step_confidence(self, step: int, situation: Dict[str, Any]) -> float:
        """计算步骤置信度
        
        Args:
            step: 步骤
            situation: 当前情况
            
        Returns:
            置信度
        """
        base_confidence = 0.5
        # 越往后置信度越高（假设进展顺利）
        step_boost = step * 0.1
        
        return min(0.9, base_confidence + step_boost)
    
    def _determine_final_action(self, reasoning_chain: List[ReasoningStep]) -> str:
        """确定最终行动
        
        Args:
            reasoning_chain: 推理链
            
        Returns:
            最终行动
        """
        if not reasoning_chain:
            return "default_action"
        
        # 获取最后一步的行动
        last_step = reasoning_chain[-1]
        return last_step.action if last_step.action else "default_action"
    
    def _evaluate_decision(
        self,
        situation: Dict[str, Any],
        action: str,
        reasoning_chain: List[ReasoningStep],
    ) -> Dict[str, Any]:
        """评估决策
        
        Args:
            situation: 当前情况
            action: 行动
            reasoning_chain: 推理链
            
        Returns:
            评估
        """
        if not reasoning_chain:
            return {
                "confidence": 0.5,
                "value": 5,
                "success_probability": 0.5,
            }
        
        # 计算平均置信度
        confidences = [step.confidence for step in reasoning_chain]
        average_confidence = sum(confidences) / len(confidences)
        
        # 估计价值
        total_value = sum(step.confidence * 10 for step in reasoning_chain)
        
        # 成功概率
        success_probability = min(0.95, average_confidence + 0.1)
        
        return {
            "confidence": average_confidence,
            "value": total_value,
            "success_probability": success_probability,
            "steps_taken": len(reasoning_chain),
        }
    
    def set_reasoning_mode(self, mode: ReasoningMode):
        """设置推理模式
        
        Args:
            mode: 推理模式
        """
        self.reasoning_mode = mode
        logger.info(f"推理模式设置为: {mode}")
    
    def set_reasoning_depth(self, depth: int):
        """设置推理深度
        
        Args:
            depth: 推理深度
        """
        self.reasoning_depth = max(1, min(depth, 10))  # 限制在1-10之间
    
    def get_reasoning_history(self, limit: int = 10) -> List[List[ReasoningStep]]:
        """获取推理历史
        
        Args:
            limit: 限制数量
            
        Returns:
            推理历史
        """
        return self.reasoning_history[-limit:]


system2 = System2()
