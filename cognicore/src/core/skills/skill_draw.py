#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DrawingSkill
支持多种图表type: 折线图, 柱状图, 饼图, 散点图等
"""
import os
import base64
import logging
from typing import Dict, Any
from datetime import datetime
from .base import BaseSkill

logger = logging.getLogger(__name__)

class DrawSkill(BaseSkill):
    """DrawingSkill"""
    
    @property
    def name(self) -> str:
        return "draw"
    
    @property
    def description(self) -> str:
        return "Drawing和数据可视化Skill, 支持多种图表type: 折线图, 柱状图, 饼图, 散点图等"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["line", "bar", "pie", "scatter", "histogram"],
                    "description": "图表type: 折线图(line), 柱状图(bar), 饼图(pie), 散点图(scatter), 直方图(histogram)"
                },
                "title": {
                    "type": "string",
                    "description": "图表Title"
                },
                "data": {
                    "type": "object",
                    "description": "图表数据: {x: [1,2,3], y: [10,20,30]} 或 {labels: ['A','B'], values: [50,50]}"
                },
                "x_label": {
                    "type": "string",
                    "description": "X轴标签"
                },
                "y_label": {
                    "type": "string",
                    "description": "Y轴标签"
                },
                "save_path": {
                    "type": "string",
                    "description": "Save路径 (可选) , 默认Save到 ./output/images/"
                }
            },
            "required": ["action", "data"]
        }
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Drawing操作"""
        try:
            # Create输出目录
            output_dir = params.get("save_path", "./output/images")
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{action}_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)
            
            # 根据图表typeDrawing
            if action == "line":
                result = await self._draw_line_chart(params, filepath)
            elif action == "bar":
                result = await self._draw_bar_chart(params, filepath)
            elif action == "pie":
                result = await self._draw_pie_chart(params, filepath)
            elif action == "scatter":
                result = await self._draw_scatter_chart(params, filepath)
            elif action == "histogram":
                result = await self._draw_histogram(params, filepath)
            else:
                return {
                    "status": "error",
                    "message": f"不支持的图表type: {action}"
                }
            
            result["file_path"] = filepath
            result["file_name"] = filename
            
            return result
            
        except ImportError:
            return {
                "status": "error",
                "message": "matplotlib 未安装, 请运行: pip install matplotlib"
            }
        except Exception as e:
            logger.error(f"Drawing failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _draw_line_chart(self, params: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """绘制折线图"""
        import matplotlib.pyplot as plt
        
        data = params.get("data", {})
        title = params.get("title", "折线图")
        x_label = params.get("x_label", "X")
        y_label = params.get("y_label", "Y")
        
        x = data.get("x", [])
        y = data.get("y", [])
        
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, marker='o', linewidth=2)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            "status": "success",
            "message": "折线图绘制 successful",
            "type": "line"
        }
    
    async def _draw_bar_chart(self, params: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """绘制柱状图"""
        import matplotlib.pyplot as plt
        
        data = params.get("data", {})
        title = params.get("title", "柱状图")
        x_label = params.get("x_label", "X")
        y_label = params.get("y_label", "Y")
        
        x = data.get("x", [])
        y = data.get("y", [])
        
        plt.figure(figsize=(10, 6))
        plt.bar(x, y, alpha=0.7)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            "status": "success",
            "message": "柱状图绘制 successful",
            "type": "bar"
        }
    
    async def _draw_pie_chart(self, params: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """绘制饼图"""
        import matplotlib.pyplot as plt
        
        data = params.get("data", {})
        title = params.get("title", "饼图")
        
        labels = data.get("labels", [])
        values = data.get("values", [])
        
        plt.figure(figsize=(10, 8))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.axis('equal')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            "status": "success",
            "message": "饼图绘制 successful",
            "type": "pie"
        }
    
    async def _draw_scatter_chart(self, params: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """绘制散点图"""
        import matplotlib.pyplot as plt
        
        data = params.get("data", {})
        title = params.get("title", "散点图")
        x_label = params.get("x_label", "X")
        y_label = params.get("y_label", "Y")
        
        x = data.get("x", [])
        y = data.get("y", [])
        
        plt.figure(figsize=(10, 6))
        plt.scatter(x, y, alpha=0.6, s=100)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            "status": "success",
            "message": "散点图绘制 successful",
            "type": "scatter"
        }
    
    async def _draw_histogram(self, params: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """绘制直方图"""
        import matplotlib.pyplot as plt
        import numpy as np
        
        data = params.get("data", {})
        title = params.get("title", "直方图")
        x_label = params.get("x_label", "值")
        y_label = params.get("y_label", "频数")
        
        values = data.get("values", [])
        bins = data.get("bins", 10)
        
        plt.figure(figsize=(10, 6))
        plt.hist(values, bins=bins, alpha=0.7, edgecolor='black')
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            "status": "success",
            "message": "直方图绘制 successful",
            "type": "histogram"
        }
