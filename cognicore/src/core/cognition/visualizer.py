#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理可视化模块
用于可视化思维链、知识图谱、推理过程
专为U盘便携项目优化
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class VisualizationType(Enum):
    """可视化类型"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    BAYESIAN_BELIEF = "bayesian_belief"
    CONFIDENCE_HISTORY = "confidence_history"


@dataclass
class VisualizationNode:
    """可视化节点"""
    id: str
    label: str
    content: str
    confidence: float
    type: str = "default"


@dataclass
class VisualizationEdge:
    """可视化边"""
    source: str
    target: str
    label: Optional[str]
    weight: float = 1.0


@dataclass
class VisualizationData:
    """可视化数据"""
    type: VisualizationType
    nodes: List[VisualizationNode]
    edges: List[VisualizationEdge]
    metadata: Dict[str, Any]


class ReasoningVisualizer:
    """推理可视化器"""
    
    def __init__(self):
        """初始化"""
        self.colors = {
            "high": "#22c55e",
            "medium": "#eab308",
            "low": "#f97316",
            "very_low": "#ef4444",
            "default": "#3b82f6",
        }
        
        logger.info("ReasoningVisualizer 初始化完成")
    
    def visualize_chain_of_thought(
        self,
        reasoning_chain: List[Any],
        include_confidence: bool = True,
    ) -> VisualizationData:
        """可视化思维链
        
        Args:
            reasoning_chain: 推理链
            include_confidence: 是否包含置信度
            
        Returns:
            可视化数据
        """
        nodes = []
        edges = []
        
        for i, step in enumerate(reasoning_chain):
            node_id = f"step_{i}"
            
            # 提取信息
            thought = getattr(step, "thought", str(step))
            confidence = getattr(step, "confidence", 0.5)
            action = getattr(step, "action", None)
            
            # 创建节点
            node = VisualizationNode(
                id=node_id,
                label=f"步骤 {i + 1}",
                content=thought,
                confidence=confidence,
                type="thought",
            )
            nodes.append(node)
            
            # 创建边
            if i > 0:
                edge = VisualizationEdge(
                    source=f"step_{i - 1}",
                    target=node_id,
                    label=action,
                )
                edges.append(edge)
        
        return VisualizationData(
            type=VisualizationType.CHAIN_OF_THOUGHT,
            nodes=nodes,
            edges=edges,
            metadata={
                "num_steps": len(reasoning_chain),
                "include_confidence": include_confidence,
            },
        )
    
    def visualize_bayesian_belief(
        self,
        world_model: Dict[str, float],
        top_n: int = 10,
    ) -> VisualizationData:
        """可视化贝叶斯信念分布
        
        Args:
            world_model: 世界模型
            top_n: 显示前N个
            
        Returns:
            可视化数据
        """
        nodes = []
        
        # 排序
        sorted_states = sorted(
            world_model.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        for i, (state, prob) in enumerate(sorted_states):
            node = VisualizationNode(
                id=f"state_{i}",
                label=state,
                content=f"{state}: {prob:.3f}",
                confidence=prob,
                type="belief",
            )
            nodes.append(node)
        
        return VisualizationData(
            type=VisualizationType.BAYESIAN_BELIEF,
            nodes=nodes,
            edges=[],
            metadata={
                "num_states": len(nodes),
                "total_states": len(world_model),
            },
        )
    
    def to_ascii_art(self, data: VisualizationData) -> str:
        """转换为ASCII艺术
        
        Args:
            data: 可视化数据
            
        Returns:
            ASCII字符串
        """
        if data.type == VisualizationType.CHAIN_OF_THOUGHT:
            return self._chain_to_ascii(data)
        elif data.type == VisualizationType.BAYESIAN_BELIEF:
            return self._belief_to_ascii(data)
        else:
            return str(data)
    
    def _chain_to_ascii(self, data: VisualizationData) -> str:
        """思维链转ASCII"""
        lines = []
        lines.append("╔" + "═" * 60 + "╗")
        lines.append("║" + " " * 10 + "思维链推理过程" + " " * 34 + "║")
        lines.append("╠" + "═" * 60 + "╣")
        
        for i, node in enumerate(data.nodes):
            bar = self._confidence_bar(node.confidence)
            label = node.label.ljust(10)
            content = node.content[:40] if len(node.content) > 40 else node.content
            
            lines.append(f"║ {label} {bar} {content.ljust(25)} ║")
            
            if i < len(data.edges):
                lines.append("║          ↓                   ║")
        
        lines.append("╚" + "═" * 60 + "╝")
        
        return "\n".join(lines)
    
    def _belief_to_ascii(self, data: VisualizationData) -> str:
        """信念分布转ASCII"""
        lines = []
        lines.append("╔" + "═" * 60 + "╗")
        lines.append("║" + " " * 12 + "贝叶斯信念分布" + " " * 34 + "║")
        lines.append("╠" + "═" * 60 + "╣")
        
        for node in data.nodes:
            bar = self._confidence_bar(node.confidence)
            label = node.label[:15]
            prob = f"{node.confidence:.3f}"
            
            lines.append(f"║ {label.ljust(15)} {bar} {prob.rjust(8)} ║")
        
        lines.append("╚" + "═" * 60 + "╝")
        
        return "\n".join(lines)
    
    def _confidence_bar(self, confidence: float, width: int = 20) -> str:
        """生成置信度条形图
        
        Args:
            confidence: 置信度
            width: 宽度
            
        Returns:
            条形图字符串
        """
        filled = int(confidence * width)
        
        if confidence >= 0.8:
            color = "🟢"
        elif confidence >= 0.6:
            color = "🟡"
        elif confidence >= 0.4:
            color = "🟠"
        else:
            color = "🔴"
        
        return f"{color}[{'█' * filled}{'░' * (width - filled)}]"
    
    def to_html(self, data: VisualizationData) -> str:
        """转换为HTML
        
        Args:
            data: 可视化数据
            
        Returns:
            HTML字符串
        """
        if data.type == VisualizationType.BAYESIAN_BELIEF:
            return self._belief_to_html(data)
        else:
            return self._chain_to_html(data)
    
    def _chain_to_html(self, data: VisualizationData) -> str:
        """思维链转HTML"""
        html_parts = []
        html_parts.append("""
        <div class="cogni-visualization">
            <h3>思维链推理</h3>
            <div class="reasoning-chain">
        """)
        
        for i, node in enumerate(data.nodes):
            color = self._get_confidence_color(node.confidence)
            
            html_parts.append(f"""
                <div class="reasoning-step" style="border-left: 4px solid {color}; padding: 10px; margin: 10px 0;">
                    <div class="step-header">
                        <span style="font-weight: bold;">{node.label}</span>
                        <span style="color: {color}; font-weight: bold;">
                            置信度: {node.confidence:.1%}
                        </span>
                    </div>
                    <div class="step-content">{node.content}</div>
                </div>
            """)
        
        html_parts.append("""
            </div>
        </div>
        """)
        
        return "\n".join(html_parts)
    
    def _belief_to_html(self, data: VisualizationData) -> str:
        """信念分布转HTML"""
        html_parts = []
        html_parts.append("""
        <div class="cogni-visualization">
            <h3>贝叶斯信念分布</h3>
            <div class="belief-bars">
        """)
        
        for node in data.nodes:
            color = self._get_confidence_color(node.confidence)
            width_pct = node.confidence * 100
            
            html_parts.append(f"""
                <div class="belief-item" style="margin: 5px 0;">
                    <div style="font-weight: bold;">{node.label}</div>
                    <div style="background: #f0f0f0; border-radius: 5px; overflow: hidden; height: 25px;">
                        <div style="
                            background: {color};
                            width: {width_pct}%;
                            height: 100%;
                            display: flex;
                            align-items: center;
                            justify-content: flex-end;
                            padding-right: 5px;
                            color: white;
                        ">
                            {node.confidence:.1%}
                        </div>
                    </div>
                </div>
            """)
        
        html_parts.append("""
            </div>
        </div>
        """)
        
        return "\n".join(html_parts)
    
    def _get_confidence_color(self, confidence: float) -> str:
        """获取置信度颜色
        
        Args:
            confidence: 置信度
            
        Returns:
            颜色字符串
        """
        if confidence >= 0.8:
            return "#22c55e"
        elif confidence >= 0.6:
            return "#eab308"
        elif confidence >= 0.4:
            return "#f97316"
        else:
            return "#ef4444"
    
    def to_json(self, data: VisualizationData) -> str:
        """转换为JSON
        
        Args:
            data: 可视化数据
            
        Returns:
            JSON字符串
        """
        dict_data = {
            "type": data.type.value,
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "content": node.content,
                    "confidence": node.confidence,
                    "type": node.type,
                }
                for node in data.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label,
                    "weight": edge.weight,
                }
                for edge in data.edges
            ],
            "metadata": data.metadata,
        }
        
        return json.dumps(dict_data, ensure_ascii=False, indent=2)


reasoning_visualizer = ReasoningVisualizer()
