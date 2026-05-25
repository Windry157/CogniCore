#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析Skill
支持数据统计, 趋势分析, Description性统计等功能
"""
import os
import json
import logging
from typing import Dict, Any, List, Union
from datetime import datetime
from .base import BaseSkill

logger = logging.getLogger(__name__)

class DataAnalyzeSkill(BaseSkill):
    """数据分析Skill"""
    
    @property
    def name(self) -> str:
        return "data_analyze"
    
    @property
    def description(self) -> str:
        return "数据分析Skill, 支持数据统计, Description性统计, 趋势分析, 数据可视化建议等功能"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["describe", "stats", "trend", "correlation", "visualize"],
                    "description": "分析type: describe(Description性统计), stats(基础统计), trend(趋势分析), correlation(相关性), visualize(可视化建议)"
                },
                "data": {
                    "type": "any",
                    "description": "要分析的数据: 可以是列表, 数groups或对象数groups"
                },
                "file_path": {
                    "type": "string",
                    "description": "数据文件路径 (可选) , 支持 CSV, JSON, Excel 格式"
                },
                "column": {
                    "type": "string",
                    "description": "要分析的列名 (可选) "
                },
                "columns": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "要分析的列名列表 (可选) "
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据分析操作"""
        try:
            data = params.get("data", None)
            file_path = params.get("file_path", None)
            
            # 如果提供了文件路径, Load file数据
            if file_path and not data:
                data = await self._load_file(file_path)
            
            if data is None:
                return {
                    "status": "error",
                    "message": "请提供数据或文件路径"
                }
            
            # 根据action执行分析
            if action == "describe":
                result = await self._analyze_describe(data, params)
            elif action == "stats":
                result = await self._analyze_stats(data, params)
            elif action == "trend":
                result = await self._analyze_trend(data, params)
            elif action == "correlation":
                result = await self._analyze_correlation(data, params)
            elif action == "visualize":
                result = await self._suggest_visualize(data, params)
            else:
                return {
                    "status": "error",
                    "message": f"不支持的分析type: {action}"
                }
            
            return result
            
        except ImportError:
            return {
                "status": "error",
                "message": "需要安装数据分析库: pip install pandas numpy"
            }
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _load_file(self, file_path: str) -> Any:
        """Load数据文件"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".csv":
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                return df.to_dict('records')
            except ImportError:
                logger.warning("pandas not installed, trying simple load")
                with open(file_path, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f]
        elif ext == ".json":
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif ext in [".xlsx", ".xls"]:
            try:
                import pandas as pd
                df = pd.read_excel(file_path)
                return df.to_dict('records')
            except ImportError:
                return {
                    "status": "error",
                    "message": "需要安装 openpyxl 来读取 Excel 文件: pip install openpyxl"
                }
        else:
            return {
                "status": "error",
                "message": f"不支持的文件格式: {ext}"
            }
    
    async def _analyze_describe(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Description性统计分析"""
        column = params.get("column", None)
        
        # 提取数值数据
        numeric_data = self._extract_numeric_data(data, column)
        
        if not numeric_data:
            return {
                "status": "error",
                "message": "没有Found数值数据"
            }
        
        try:
            import numpy as np
            
            arr = np.array(numeric_data)
            
            # 计算统计指标
            stats = {
                "count": len(arr),
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std": float(np.std(arr)),
                "var": float(np.var(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "q25": float(np.percentile(arr, 25)),
                "q75": float(np.percentile(arr, 75))
            }
            
            return {
                "status": "success",
                "message": "Description性统计Analysis complete",
                "type": "describe",
                "data": stats
            }
        except ImportError:
            return self._fallback_describe(numeric_data)
    
    def _fallback_describe(self, data: List[Union[int, float]]) -> Dict[str, Any]:
        """备用方案 - 不使用 numpy 的简单统计"""
        if not data:
            return {
                "status": "error",
                "message": "数据为空"
            }
        
        n = len(data)
        mean = sum(data) / n
        sorted_data = sorted(data)
        median = sorted_data[n//2] if n % 2 == 1 else (sorted_data[n//2-1] + sorted_data[n//2]) / 2
        var = sum((x - mean) ** 2 for x in data) / n
        std = var ** 0.5
        
        stats = {
            "count": n,
            "mean": mean,
            "median": median,
            "std": std,
            "var": var,
            "min": min(data),
            "max": max(data),
            "q25": sorted_data[int(n*0.25)],
            "q75": sorted_data[int(n*0.75)]
        }
        
        return {
            "status": "success",
            "message": "Description性统计Analysis complete (简单模式) ",
            "type": "describe",
            "data": stats
        }
    
    async def _analyze_stats(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """基础统计分析"""
        result = await self._analyze_describe(data, params)
        
        # Add数据type信息
        data_type = "unknown"
        if isinstance(data, list):
            data_type = f"list (length={len(data)})"
        elif isinstance(data, dict):
            data_type = f"dict (keys={list(data.keys())})"
        
        if result["status"] == "success":
            result["data_type"] = data_type
        
        return result
    
    async def _analyze_trend(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """趋势分析"""
        column = params.get("column", None)
        numeric_data = self._extract_numeric_data(data, column)
        
        if len(numeric_data) < 3:
            return {
                "status": "error",
                "message": "数据点太少, 无法分析趋势"
            }
        
        try:
            import numpy as np
            
            x = np.arange(len(numeric_data))
            y = np.array(numeric_data)
            
            # 简单线性回归
            slope, intercept = np.polyfit(x, y, 1)
            
            # 计算趋势方向
            trend = "上升" if slope > 0 else "下降" if slope < 0 else "平稳"
            
            # 计算变化率
            first = numeric_data[0]
            last = numeric_data[-1]
            change_rate = (last - first) / first * 100 if first != 0 else 0
            
            return {
                "status": "success",
                "message": "趋势Analysis complete",
                "type": "trend",
                "data": {
                    "trend": trend,
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "change_rate": float(change_rate),
                    "first_value": first,
                    "last_value": last,
                    "data_points": len(numeric_data)
                }
            }
        except ImportError:
            # 备用方案
            first = numeric_data[0]
            last = numeric_data[-1]
            trend = "上升" if last > first else "下降" if last < first else "平稳"
            
            return {
                "status": "success",
                "message": "趋势Analysis complete (简单模式) ",
                "type": "trend",
                "data": {
                    "trend": trend,
                    "first_value": first,
                    "last_value": last,
                    "data_points": len(numeric_data)
                }
            }
    
    async def _analyze_correlation(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """相关性分析"""
        columns = params.get("columns", [])
        
        if not isinstance(data, list) or not all(isinstance(d, dict) for d in data):
            return {
                "status": "error",
                "message": "相关性分析需要对象数groups数据"
            }
        
        if len(columns) < 2:
            return {
                "status": "error",
                "message": "相关性分析需要至少两 列"
            }
        
        try:
            import numpy as np
            
            # 提取数据
            data_dict = {}
            for col in columns:
                col_data = [float(d.get(col, 0)) for d in data if d.get(col) is not None]
                data_dict[col] = col_data
            
            # 计算相关性矩阵
            n = len(columns)
            corr_matrix = np.zeros((n, n))
            
            for i in range(n):
                for j in range(n):
                    if i == j:
                        corr_matrix[i][j] = 1.0
                    else:
                        x = data_dict[columns[i]]
                        y = data_dict[columns[j]]
                        corr_matrix[i][j] = np.corrcoef(x, y)[0][1]
            
            return {
                "status": "success",
                "message": "相关性Analysis complete",
                "type": "correlation",
                "data": {
                    "columns": columns,
                    "correlation_matrix": corr_matrix.tolist()
                }
            }
        except ImportError:
            return {
                "status": "success",
                "message": "相关性分析需要 numpy 库",
                "type": "correlation",
                "data": {
                    "message": "请安装 numpy: pip install numpy"
                }
            }
    
    async def _suggest_visualize(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """可视化建议"""
        suggestions = []
        
        # analyzing data特征, 给出可视化建议
        if isinstance(data, list):
            n = len(data)
            
            if n == 0:
                suggestions.append("数据为空, 无法可视化")
            elif all(isinstance(x, (int, float)) for x in data):
                suggestions.append({
                    "type": "line",
                    "description": "折线图 - 展示数据趋势"
                })
                suggestions.append({
                    "type": "histogram",
                    "description": "直方图 - 展示数据分布"
                })
            elif all(isinstance(x, dict) for x in data):
                suggestions.append({
                    "type": "bar",
                    "description": "柱状图 - 比较各分类数据"
                })
                suggestions.append({
                    "type": "scatter",
                    "description": "散点图 - 展示两 变量关系"
                })
        
        return {
            "status": "success",
            "message": "可视化建议already生成",
            "type": "visualize",
            "data": {
                "suggestions": suggestions,
                "data_type": str(type(data)),
                "data_points": n if isinstance(data, list) else "N/A"
            }
        }
    
    def _extract_numeric_data(self, data: Any, column: str = None) -> List[Union[int, float]]:
        """提取数值数据"""
        result = []
        
        if isinstance(data, list):
            if column:
                for item in data:
                    if isinstance(item, dict):
                        val = item.get(column)
                        if isinstance(val, (int, float)):
                            result.append(val)
            else:
                for item in data:
                    if isinstance(item, (int, float)):
                        result.append(item)
        elif isinstance(data, (int, float)):
            result = [data]
        
        return result
