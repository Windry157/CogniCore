#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度日志和追踪模块
提供置信度历史的持久化和追踪功能
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfidenceLogger:
    """置信度日志记录器
    
    记录置信度评分历史到文件
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """初始化日志记录器
        
        Args:
            log_dir: 日志目录路径
        """
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path("data/logs")
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self._get_log_filename()
    
    def _get_log_filename(self) -> Path:
        """获取日志文件名"""
        date_str = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"confidence_{date_str}.jsonl"
    
    def _rotate_if_needed(self):
        """检查是否需要轮转日志"""
        new_file = self._get_log_filename()
        if new_file != self.current_log_file:
            self.current_log_file = new_file
            logger.info(f"日志轮转: {self.current_log_file}")
    
    def log(self, record: Dict[str, Any]):
        """记录置信度数据
        
        Args:
            record: 置信度记录
        """
        try:
            self._rotate_if_needed()
            
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
            logger.debug(f"置信度记录已保存: {self.current_log_file}")
            
        except Exception as e:
            logger.error(f"保存置信度记录失败: {e}")
    
    def log_decision(self, decision: Dict[str, Any], confidence_result: Dict[str, Any]):
        """记录决策置信度
        
        Args:
            decision: 决策上下文
            confidence_result: 置信度结果
        """
        record = {
            "type": "decision_confidence",
            "timestamp": datetime.now().isoformat(),
            "input": decision.get("input", "")[:200],
            "confidence_score": confidence_result.get("confidence_score"),
            "confidence_level": confidence_result.get("confidence_level"),
            "factor_scores": confidence_result.get("factor_scores"),
            "uncertainty_analysis": confidence_result.get("uncertainty_analysis", {})
        }
        self.log(record)
    
    def log_text_generation(
        self,
        prompt: str,
        generated_text: str,
        confidence_result: Dict[str, Any]
    ):
        """记录文本生成置信度
        
        Args:
            prompt: 提示词
            generated_text: 生成的文本
            confidence_result: 置信度结果
        """
        record = {
            "type": "text_generation_confidence",
            "timestamp": datetime.now().isoformat(),
            "prompt_length": len(prompt),
            "generated_length": len(generated_text),
            "confidence_score": confidence_result.get("confidence_score"),
            "confidence_level": confidence_result.get("confidence_level"),
            "factor_scores": confidence_result.get("factor_scores")
        }
        self.log(record)
    
    def log_retrieval(
        self,
        query: str,
        retrieved_count: int,
        confidence_result: Dict[str, Any]
    ):
        """记录检索置信度
        
        Args:
            query: 查询文本
            retrieved_count: 检索结果数量
            confidence_result: 置信度结果
        """
        record = {
            "type": "retrieval_confidence",
            "timestamp": datetime.now().isoformat(),
            "query_length": len(query),
            "retrieved_count": retrieved_count,
            "confidence_score": confidence_result.get("confidence_score"),
            "confidence_level": confidence_result.get("confidence_level"),
            "factor_scores": confidence_result.get("factor_scores")
        }
        self.log(record)
    
    def read_logs(
        self,
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """读取日志记录
        
        Args:
            date: 日期字符串（YYYYMMDD），默认为今天
            limit: 返回记录数量限制
            
        Returns:
            日志记录列表
        """
        try:
            if date:
                log_file = self.log_dir / f"confidence_{date}.jsonl"
            else:
                log_file = self.current_log_file
            
            if not log_file.exists():
                logger.warning(f"日志文件不存在: {log_file}")
                return []
            
            records = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if len(records) >= limit:
                        break
                    try:
                        records.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
            
            return records
            
        except Exception as e:
            logger.error(f"读取日志失败: {e}")
            return []
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取统计信息
        
        Args:
            days: 统计天数
            
        Returns:
            统计信息
        """
        try:
            total_records = 0
            total_score = 0.0
            level_counts = {"high": 0, "medium": 0, "low": 0, "very_low": 0}
            
            from datetime import timedelta
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                records = self.read_logs(date, limit=1000)
                
                for record in records:
                    total_records += 1
                    if "confidence_score" in record:
                        total_score += record["confidence_score"]
                    if "confidence_level" in record:
                        level = record["confidence_level"]
                        if level in level_counts:
                            level_counts[level] += 1
            
            if total_records == 0:
                return {
                    "total_records": 0,
                    "avg_confidence": 0,
                    "level_distribution": level_counts
                }
            
            return {
                "total_records": total_records,
                "avg_confidence": round(total_score / total_records, 3),
                "level_distribution": level_counts,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}


confidence_logger = ConfidenceLogger()


class ConfidenceTracer:
    """置信度追踪器
    
    在推理过程中追踪置信度变化
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """初始化追踪器
        
        Args:
            session_id: 会话ID
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trace: List[Dict[str, Any]] = []
    
    def start_span(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """开始一个追踪跨度
        
        Args:
            name: 跨度名称
            metadata: 元数据
            
        Returns:
            跨度ID
        """
        span_id = f"{name}_{len(self.trace)}"
        
        span = {
            "span_id": span_id,
            "name": name,
            "start_time": datetime.now().isoformat(),
            "metadata": metadata or {},
            "events": []
        }
        
        self.trace.append(span)
        return span_id
    
    def add_event(self, span_id: str, event_name: str, data: Optional[Dict[str, Any]] = None):
        """添加跨度事件
        
        Args:
            span_id: 跨度ID
            event_name: 事件名称
            data: 事件数据
        """
        for span in reversed(self.trace):
            if span["span_id"] == span_id:
                span["events"].append({
                    "event_name": event_name,
                    "timestamp": datetime.now().isoformat(),
                    "data": data or {}
                })
                return
        
        logger.warning(f"未找到跨度: {span_id}")
    
    def end_span(self, span_id: str, result: Optional[Dict[str, Any]] = None):
        """结束追踪跨度
        
        Args:
            span_id: 跨度ID
            result: 结果数据
        """
        for span in self.trace:
            if span["span_id"] == span_id:
                span["end_time"] = datetime.now().isoformat()
                if result:
                    span["result"] = result
                return
        
        logger.warning(f"未找到跨度: {span_id}")
    
    def get_trace(self) -> List[Dict[str, Any]]:
        """获取追踪记录
        
        Returns:
            追踪记录列表
        """
        return self.trace
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            追踪数据字典
        """
        return {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "trace": self.trace
        }


def create_tracer(session_id: Optional[str] = None) -> ConfidenceTracer:
    """创建置信度追踪器
    
    Args:
        session_id: 会话ID
        
    Returns:
        置信度追踪器实例
    """
    return ConfidenceTracer(session_id)
