#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应包装器模块
为LLM响应添加置信度信息和元数据
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class ConfidenceMetadata:
    """置信度元数据"""
    confidence_score: float = 0.5
    confidence_level: str = "medium"
    factor_scores: Dict[str, float] = field(default_factory=dict)
    uncertainty_analysis: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class ResponseMetadata:
    """响应元数据"""
    model: str = ""
    tokens_used: int = 0
    generation_time: float = 0.0
    confidence: Optional[ConfidenceMetadata] = None
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ResponseWrapper:
    """响应包装器
    
    为LLM响应添加置信度信息和元数据
    """
    
    def __init__(self):
        """初始化响应包装器"""
        self.default_level_thresholds = {
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "very_low": 0.2
        }
    
    def wrap(
        self,
        response_text: str,
        confidence_result: Optional[Dict[str, Any]] = None,
        model_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """包装响应
        
        Args:
            response_text: 响应文本
            confidence_result: 置信度结果
            model_info: 模型信息
            
        Returns:
            包装后的响应
        """
        metadata = ResponseMetadata()
        
        if model_info:
            metadata.model = model_info.get("model", "")
            metadata.tokens_used = model_info.get("tokens_used", 0)
            metadata.generation_time = model_info.get("generation_time", 0.0)
        
        if confidence_result:
            metadata.confidence = ConfidenceMetadata(
                confidence_score=confidence_result.get("confidence_score", 0.5),
                confidence_level=confidence_result.get("confidence_level", "medium"),
                factor_scores=confidence_result.get("factor_scores", {}),
                uncertainty_analysis=confidence_result.get("uncertainty_analysis", {}),
                timestamp=confidence_result.get("timestamp", datetime.now().isoformat())
            )
            
            self._add_warnings_and_suggestions(metadata, confidence_result)
        
        wrapped_response = {
            "text": response_text,
            "metadata": asdict(metadata),
            "wrapped_at": datetime.now().isoformat()
        }
        
        return wrapped_response
    
    def wrap_batch(
        self,
        responses: List[Dict[str, Any]],
        confidence_results: List[Dict[str, Any]],
        model_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """批量包装响应
        
        Args:
            responses: 响应列表
            confidence_results: 置信度结果列表
            model_info: 模型信息
            
        Returns:
            包装后的响应列表
        """
        wrapped = []
        for i, (response, confidence) in enumerate(zip(responses, confidence_results)):
            if isinstance(response, str):
                text = response
            else:
                text = response.get("text", str(response))
            
            wrapped.append(self.wrap(text, confidence, model_info))
        
        return wrapped
    
    def _add_warnings_and_suggestions(
        self,
        metadata: ResponseMetadata,
        confidence_result: Dict[str, Any]
    ):
        """添加警告和建议
        
        Args:
            metadata: 响应元数据
            confidence_result: 置信度结果
        """
        level = confidence_result.get("confidence_level", "medium")
        
        if level == "very_low":
            metadata.warnings.append("置信度极低，回答可能不准确")
            metadata.suggestions.append("建议用户提供更多信息或澄清问题")
        elif level == "low":
            metadata.warnings.append("置信度较低，回答可能存在不确定性")
            metadata.suggestions.append("建议结合其他信息源进行验证")
        
        uncertainty = confidence_result.get("uncertainty_analysis", {})
        sources = uncertainty.get("uncertainty_sources", [])
        
        for source in sources:
            if source.get("score", 1.0) < 0.2:
                warning = f"不确定来源: {source.get('description', '未知')}"
                if warning not in metadata.warnings:
                    metadata.warnings.append(warning)
                
                suggestion = source.get("recommendation", "")
                if suggestion and suggestion not in metadata.suggestions:
                    metadata.suggestions.append(suggestion)
    
    def unwrap(self, wrapped_response: Dict[str, Any]) -> str:
        """解包响应
        
        Args:
            wrapped_response: 包装后的响应
            
        Returns:
            原始响应文本
        """
        return wrapped_response.get("text", "")
    
    def extract_confidence(self, wrapped_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取置信度信息
        
        Args:
            wrapped_response: 包装后的响应
            
        Returns:
            置信度信息或 None
        """
        metadata = wrapped_response.get("metadata", {})
        confidence = metadata.get("confidence")
        
        if confidence:
            return {
                "confidence_score": confidence.get("confidence_score"),
                "confidence_level": confidence.get("confidence_level"),
                "factor_scores": confidence.get("factor_scores", {}),
                "uncertainty_analysis": confidence.get("uncertainty_analysis", {})
            }
        
        return None
    
    def format_with_confidence(
        self,
        wrapped_response: Dict[str, Any],
        include_metadata: bool = True
    ) -> str:
        """格式化带置信度的响应
        
        Args:
            wrapped_response: 包装后的响应
            include_metadata: 是否包含元数据
            
        Returns:
            格式化的字符串
        """
        text = wrapped_response.get("text", "")
        
        if not include_metadata:
            return text
        
        lines = []
        lines.append(text)
        lines.append("")
        lines.append("─" * 40)
        
        metadata = wrapped_response.get("metadata", {})
        confidence = metadata.get("confidence")
        
        if confidence:
            score = confidence.get("confidence_score", 0)
            level = confidence.get("confidence_level", "medium")
            
            icon = {"high": "✅", "medium": "⚠️", "low": "⚠️", "very_low": "❌"}.get(level, "❓")
            
            lines.append(f"{icon} 置信度: {score:.1%} ({level.upper()})")
            
            factor_scores = confidence.get("factor_scores", {})
            if factor_scores:
                lines.append("")
                lines.append("因子分析:")
                for name, fscore in factor_scores.items():
                    display_name = name.replace("_", " ").title()
                    bar = "█" * int(fscore * 10) + "░" * (10 - int(fscore * 10))
                    lines.append(f"  {display_name:15}: [{bar}] {fscore:.1%}")
            
            warnings = metadata.get("warnings", [])
            if warnings:
                lines.append("")
                lines.append("⚠️ 警告:")
                for warning in warnings:
                    lines.append(f"  • {warning}")
            
            suggestions = metadata.get("suggestions", [])
            if suggestions:
                lines.append("")
                lines.append("💡 建议:")
                for suggestion in suggestions:
                    lines.append(f"  • {suggestion}")
        else:
            lines.append("ℹ️ 置信度: 未评估")
        
        lines.append("─" * 40)
        
        return "\n".join(lines)


response_wrapper = ResponseWrapper()
