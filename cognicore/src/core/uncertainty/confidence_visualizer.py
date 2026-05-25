#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度可视化模块
提供置信度数据可视化格式化和展示功能
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class ConfidenceFormatter:
    """置信度格式化器"""
    
    @staticmethod
    def format_confidence_bar(confidence_score: float, width: int = 20) -> str:
        """格式化置信度条形图
        
        Args:
            confidence_score: 置信度分数（0-1）
            width: 条形宽度
            
        Returns:
            ASCII 条形图字符串
        """
        filled = int(confidence_score * width)
        empty = width - filled
        
        if confidence_score >= 0.8:
            color = "🟢"
        elif confidence_score >= 0.6:
            color = "🟡"
        elif confidence_score >= 0.4:
            color = "🟠"
        else:
            color = "🔴"
        
        return f"{color}[{'█' * filled}{'░' * empty}] {confidence_score:.1%}"
    
    @staticmethod
    def format_factor_scores(factor_scores: Dict[str, float]) -> str:
        """格式化因子分数
        
        Args:
            factor_scores: 因子分数字典
            
        Returns:
            格式化字符串
        """
        lines = []
        for name, score in factor_scores.items():
            bar = ConfidenceFormatter.format_confidence_bar(score, 10)
            display_name = name.replace("_", " ").title()
            lines.append(f"  {display_name}: {bar}")
        return "\n".join(lines)
    
    @staticmethod
    def format_uncertainty_sources(sources: List[Dict[str, Any]]) -> str:
        """格式化不确定性来源
        
        Args:
            sources: 不确定性来源列表
            
        Returns:
            格式化字符串
        """
        if not sources:
            return "  ✅ 无明显不确定性"
        
        lines = []
        for source in sources:
            icon = "⚠️" if source["score"] < 0.2 else "❓"
            lines.append(f"{icon} {source['description']}")
            if "recommendation" in source:
                lines.append(f"   💡 {source['recommendation']}")
        
        return "\n".join(lines)


class ConfidenceVisualizer:
    """置信度可视化器"""
    
    def __init__(self):
        """初始化可视化器"""
        self.formatter = ConfidenceFormatter()
    
    def visualize_confidence_report(self, confidence_result: Dict[str, Any]) -> str:
        """生成置信度报告可视化
        
        Args:
            confidence_result: 置信度评分结果
            
        Returns:
            格式化的报告字符串
        """
        lines = []
        lines.append("═" * 50)
        lines.append("📊 置信度报告")
        lines.append("═" * 50)
        
        score = confidence_result.get("confidence_score", 0)
        level = confidence_result.get("confidence_level", "unknown")
        lines.append(f"\n总体置信度: {self.formatter.format_confidence_bar(score)}")
        lines.append(f"置信度级别: {level.upper()}")
        
        factor_scores = confidence_result.get("factor_scores", {})
        if factor_scores:
            lines.append("\n📈 因子分析:")
            lines.append(self.formatter.format_factor_scores(factor_scores))
        
        uncertainty = confidence_result.get("uncertainty_analysis", {})
        if uncertainty:
            lines.append("\n🔍 不确定性分析:")
            sources = uncertainty.get("uncertainty_sources", [])
            lines.append(self.formatter.format_uncertainty_sources(sources))
        
        timestamp = confidence_result.get("timestamp", "")
        if timestamp:
            lines.append(f"\n⏰ 时间: {timestamp}")
        
        lines.append("═" * 50)
        
        return "\n".join(lines)
    
    def visualize_comparison(
        self,
        results: List[Dict[str, Any]],
        labels: Optional[List[str]] = None
    ) -> str:
        """生成置信度对比可视化
        
        Args:
            results: 置信度结果列表
            labels: 标签列表
            
        Returns:
            格式化的对比字符串
        """
        if not results:
            return "无数据"
        
        lines = []
        lines.append("═" * 50)
        lines.append("📊 置信度对比")
        lines.append("═" * 50)
        
        for i, result in enumerate(results):
            label = labels[i] if labels and i < len(labels) else f"#{i+1}"
            score = result.get("confidence_score", 0)
            bar = self.formatter.format_confidence_bar(score, 15)
            lines.append(f"\n{label}: {bar}")
            
            factor_scores = result.get("factor_scores", {})
            if factor_scores:
                for name, fscore in factor_scores.items():
                    small_bar = self.formatter.format_confidence_bar(fscore, 8)
                    display_name = name.replace("_", " ")[:12]
                    lines.append(f"  {display_name:12}: {small_bar}")
        
        lines.append("═" * 50)
        
        return "\n".join(lines)
    
    def visualize_trend(self, history: List[Dict[str, Any]], window: int = 10) -> str:
        """生成置信度趋势可视化
        
        Args:
            history: 置信度历史
            window: 窗口大小
            
        Returns:
            格式化的趋势字符串
        """
        if not history:
            return "无历史数据"
        
        recent = history[-window:] if len(history) > window else history
        scores = [h.get("confidence_score", 0.5) for h in recent]
        
        lines = []
        lines.append("═" * 50)
        lines.append("📈 置信度趋势")
        lines.append("═" * 50)
        
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 1
        avg_score = sum(scores) / len(scores) if scores else 0.5
        
        lines.append(f"\n统计:")
        lines.append(f"  平均: {avg_score:.1%}")
        lines.append(f"  最高: {max_score:.1%}")
        lines.append(f"  最低: {min_score:.1%}")
        lines.append(f"  样本: {len(scores)}")
        
        if len(scores) >= 2:
            trend = "📈 上升" if scores[-1] > scores[0] else "📉 下降" if scores[-1] < scores[0] else "➡️ 平稳"
            lines.append(f"  趋势: {trend}")
        
        lines.append("\n最近得分:")
        for i, score in enumerate(scores[-5:], max(0, len(scores) - 4)):
            bar = self.formatter.format_confidence_bar(score, 12)
            lines.append(f"  [{i+1}] {bar}")
        
        lines.append("═" * 50)
        
        return "\n".join(lines)
    
    def generate_html_report(self, confidence_result: Dict[str, Any]) -> str:
        """生成 HTML 置信度报告
        
        Args:
            confidence_result: 置信度评分结果
            
        Returns:
            HTML 字符串
        """
        score = confidence_result.get("confidence_score", 0)
        level = confidence_result.get("confidence_level", "unknown")
        
        color = {
            "high": "#4CAF50",
            "medium": "#FFC107",
            "low": "#FF9800",
            "very_low": "#F44336"
        }.get(level, "#9E9E9E")
        
        html = f"""
        <div class="confidence-report" style="font-family: Arial, sans-serif; padding: 20px;">
            <h3 style="color: #333;">置信度报告</h3>
            <div style="margin: 15px 0;">
                <div style="background: #f0f0f0; border-radius: 10px; height: 30px; width: 100%;">
                    <div style="background: {color}; height: 100%; width: {score*100}%; 
                         border-radius: 10px; display: flex; align-items: center; justify-content: center;
                         color: white; font-weight: bold;">
                        {score:.1%}
                    </div>
                </div>
            </div>
            <p><strong>级别:</strong> <span style="color: {color};">{level.upper()}</span></p>
        """
        
        factor_scores = confidence_result.get("factor_scores", {})
        if factor_scores:
            html += '<h4 style="margin-top: 20px;">因子分析</h4><ul style="list-style: none; padding: 0;">'
            for name, fscore in factor_scores.items():
                bar_width = fscore * 100
                html += f'''
                <li style="margin: 8px 0;">
                    <span style="display: inline-block; width: 120px;">{name.replace('_', ' ').title()}</span>
                    <div style="display: inline-block; width: 150px; background: #f0f0f0; height: 15px; border-radius: 5px;">
                        <div style="background: {color}; width: {bar_width}%; height: 100%; border-radius: 5px;"></div>
                    </div>
                    <span style="margin-left: 10px;">{fscore:.1%}</span>
                </li>
                '''
            html += '</ul>'
        
        html += '</div>'
        return html


confidence_visualizer = ConfidenceVisualizer()
