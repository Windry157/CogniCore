#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全与伦理层
用于监控和控制Agent的行为, 确保系统的可信赖性
"""

import re
import json
from typing import Dict, Any, List, Optional
import logging
import threading
import time

from src.core.config import config

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    安全监控器
    """
    
    def __init__(self):
        """
        Initialization安全监控器
        """
        self.blocked_patterns = [
            r"(?:hack|crack|exploit|渗透|攻击|入侵|破解|漏洞)",
            r"(?:password|密码|密钥|token|api[_\s]?key)",
            r"(?:credit[_\s]?card|信用卡|银行卡|账户|账号)",
            r"(?:violence|暴力|色情|赌博|毒品|违法|犯罪)",
            r"(?:private|隐私|个人信息|身份信息|身份证)",
            r"(?:system[_\s]?command|系统命令|命令执行|Execute command)",
            r"(?:delete|Delete|rm|rmdir|格式化|format)",
            r"(?:exec|eval|execfile|compile|open|file)",
            r"(?:import|from\s+\w+\s+import)",
            r"(?:__import__|__builtins__)",
        ]
        
        self.sensitive_topics = [
            "政治", "宗教", "种族", "性别", "暴力", "色情", "赌博", "毒品", "违法", "犯罪"
        ]
        
        self.monitoring_history = []
        self.lock = threading.Lock()
        
        logger.info("Security monitor initialization complete")
    
    def check_input(self, input_text: str) -> Dict[str, Any]:
        """
        检查输入是否安全
        
        Args:
            input_text: 输入文本
            
        Returns:
            检查
        """
        result = {
            "safe": True,
            "reason": [],
            "score": 1.0
        }
        
        # 检查敏感模式
        for pattern in self.blocked_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                result["safe"] = False
                result["reason"].append(f"包含敏感模式: {pattern}")
                result["score"] -= 0.2
        
        # 检查敏感主题
        for topic in self.sensitive_topics:
            if topic in input_text:
                result["safe"] = False
                result["reason"].append(f"包含敏感主题: {topic}")
                result["score"] -= 0.1
        
        # 确保分数在0-1之间
        result["score"] = max(0.0, min(1.0, result["score"]))
        
        # 记录监控历史
        self._record_history("input", input_text, result)
        
        return result
    
    def check_output(self, output_text: str) -> Dict[str, Any]:
        """
        检查输出是否安全
        
        Args:
            output_text: 输出文本
            
        Returns:
            检查
        """
        result = {
            "safe": True,
            "reason": [],
            "score": 1.0
        }
        
        # 检查敏感模式
        for pattern in self.blocked_patterns:
            if re.search(pattern, output_text, re.IGNORECASE):
                result["safe"] = False
                result["reason"].append(f"包含敏感模式: {pattern}")
                result["score"] -= 0.2
        
        # 检查敏感主题
        for topic in self.sensitive_topics:
            if topic in output_text:
                result["safe"] = False
                result["reason"].append(f"包含敏感主题: {topic}")
                result["score"] -= 0.1
        
        # 确保分数在0-1之间
        result["score"] = max(0.0, min(1.0, result["score"]))
        
        # 记录监控历史
        self._record_history("output", output_text, result)
        
        return result
    
    def check_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查Tool调用是否安全
        
        Args:
            tool_name: ToolName
            tool_args: Tool参数
            
        Returns:
            检查
        """
        result = {
            "safe": True,
            "reason": [],
            "score": 1.0
        }
        
        # 检查危险Tool
        dangerous_tools = ["execute_command", "eval", "exec"]
        if tool_name in dangerous_tools:
            result["safe"] = False
            result["reason"].append(f"危险Tool调用: {tool_name}")
            result["score"] -= 0.5
        
        # 检查Tool参数
        args_str = json.dumps(tool_args, ensure_ascii=False)
        for pattern in self.blocked_patterns:
            if re.search(pattern, args_str, re.IGNORECASE):
                result["safe"] = False
                result["reason"].append(f"Tool参数包含敏感模式: {pattern}")
                result["score"] -= 0.3
        
        # 确保分数在0-1之间
        result["score"] = max(0.0, min(1.0, result["score"]))
        
        # 记录监控历史
        self._record_history("tool_call", f"{tool_name}: {args_str}", result)
        
        return result
    
    def _record_history(self, event_type: str, content: str, result: Dict[str, Any]):
        """
        记录监控历史
        
        Args:
            event_type: 事件type
            content: Content
            result: 检查
        """
        with self.lock:
            self.monitoring_history.append({
                "timestamp": time.time(),
                "type": event_type,
                "content": content,
                "result": result
            })
            
            # 限制历史记录Length
            if len(self.monitoring_history) > 1000:
                self.monitoring_history = self.monitoring_history[-1000:]
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get监控历史
        
        Args:
            limit: 限制数量
            
        Returns:
            监控历史列表
        """
        with self.lock:
            return self.monitoring_history[-limit:]
    
    def clear_history(self):
        """
        Clear监控历史
        """
        with self.lock:
            self.monitoring_history = []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetStatistics
        
        Returns:
            Statistics
        """
        with self.lock:
            total = len(self.monitoring_history)
            unsafe = sum(1 for item in self.monitoring_history if not item["result"]["safe"])
            
            return {
                "total_events": total,
                "unsafe_events": unsafe,
                "safe_rate": (total - unsafe) / total if total > 0 else 1.0
            }


class EthicsGuardian:
    """
    伦理守护者
    """
    
    def __init__(self):
        """
        Initialization伦理守护者
        """
        self.ethical_principles = [
            "尊重用户隐私",
            "避免偏见和歧视",
            "提供准确信息",
            "避免伤害",
            "保持透明度",
            "尊重知识产权"
        ]
        
        self.violations = []
        self.lock = threading.Lock()
        
        logger.info("Ethics guardian initialization complete")
    
    def check_ethics(self, input_text: str, output_text: str) -> Dict[str, Any]:
        """
        检查伦理合规性
        
        Args:
            input_text: 输入文本
            output_text: 输出文本
            
        Returns:
            检查
        """
        result = {
            "compliant": True,
            "violations": [],
            "score": 1.0
        }
        
        # 检查隐私保护
        if self._check_privacy(output_text):
            result["compliant"] = False
            result["violations"].append("违反隐私保护原则")
            result["score"] -= 0.3
        
        # 检查偏见和歧视
        if self._check_bias(output_text):
            result["compliant"] = False
            result["violations"].append("包含偏见或歧视Content")
            result["score"] -= 0.3
        
        # 检查信息准确性
        if self._check_accuracy(output_text):
            result["compliant"] = False
            result["violations"].append("可能提供不准确信息")
            result["score"] -= 0.2
        
        # 检查有害Content
        if self._check_harm(output_text):
            result["compliant"] = False
            result["violations"].append("包含有害Content")
            result["score"] -= 0.4
        
        # 确保分数在0-1之间
        result["score"] = max(0.0, min(1.0, result["score"]))
        
        # 记录违规
        if not result["compliant"]:
            self._record_violation(input_text, output_text, result["violations"])
        
        return result
    
    def _check_privacy(self, text: str) -> bool:
        """
        检查隐私保护
        
        Args:
            text: 文本
            
        Returns:
            是否违反隐私保护
        """
        # 检查是否包含 人信息
        privacy_patterns = [
            r"\d{11}",  # 手机号 (简化版, 不使用单词边界) 
            r"\b\d{18}\b",  # 身份证号
            r"\b\d{6}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]\b",  # 身份证号
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # 邮箱
        ]
        
        for pattern in privacy_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _check_bias(self, text: str) -> bool:
        """
        检查偏见和歧视
        
        Args:
            text: 文本
            
        Returns:
            是否包含偏见或歧视
        """
        bias_patterns = [
            r"(?:男|女)生就是(?:不行|不如|应该)",
            r"(?:某 种族|某 国家|某 地区)的人就是(?:不好|不行|落后)",
            r"(?:老人|年轻人|小孩)就是(?:不懂|不行|没用)",
            r"(?:残疾人|病人)就是(?:可怜|没用|负担)",
            r"如何歧视",
            r"歧视某 群体",
            r"歧视他们",
        ]
        
        for pattern in bias_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _check_accuracy(self, text: str) -> bool:
        """
        检查信息准确性
        
        Args:
            text: 文本
            
        Returns:
            是否可能提供不准确信息
        """
        uncertainty_patterns = [
            r"(?:据传说|据听说|据猜测|据估计)",
            r"(?:虚假信息|谣言|假的|编造)",
        ]
        
        for pattern in uncertainty_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _check_harm(self, text: str) -> bool:
        """
        检查有害Content
        
        Args:
            text: 文本
            
        Returns:
            是否包含有害Content
        """
        harmful_patterns = [
            r"(?:自杀|自残|自虐)",
            r"(?:暴力|打架|斗殴|杀人|伤害)",
            r"(?:毒品|吸毒|贩毒|制毒)",
            r"(?:赌博|博彩|赌场)",
            r"(?:色情|黄色|淫秽|露骨)",
            r"(?:诈骗|欺诈|骗人|上当)",
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _record_violation(self, input_text: str, output_text: str, violations: List[str]):
        """
        记录违规
        
        Args:
            input_text: 输入文本
            output_text: 输出文本
            violations: 违规列表
        """
        with self.lock:
            self.violations.append({
                "timestamp": time.time(),
                "input": input_text,
                "output": output_text,
                "violations": violations
            })
            
            # 限制违规记录Length
            if len(self.violations) > 1000:
                self.violations = self.violations[-1000:]
    
    def get_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get违规记录
        
        Args:
            limit: 限制数量
            
        Returns:
            违规记录列表
        """
        with self.lock:
            return self.violations[-limit:]
    
    def clear_violations(self):
        """
        Clear违规记录
        """
        with self.lock:
            self.violations = []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetStatistics
        
        Returns:
            Statistics
        """
        with self.lock:
            total_violations = len(self.violations)
            violation_types = {}
            
            for violation in self.violations:
                for v in violation["violations"]:
                    violation_types[v] = violation_types.get(v, 0) + 1
            
            return {
                "total_violations": total_violations,
                "violation_types": violation_types
            }


class GuardrailLayer:
    """
    护栏层
    集成安全监控和伦理检查
    """
    
    def __init__(self):
        """
        Initialization护栏层
        """
        self.security_monitor = SecurityMonitor()
        self.ethics_guardian = EthicsGuardian()
        
        logger.info("Guardrail layer initialization complete")
    
    def check_input(self, input_text: str) -> Dict[str, Any]:
        """
        检查输入
        
        Args:
            input_text: 输入文本
            
        Returns:
            检查
        """
        security_result = self.security_monitor.check_input(input_text)
        
        return {
            "safe": security_result["safe"],
            "reason": security_result["reason"],
            "score": security_result["score"],
            "type": "input"
        }
    
    def check_output(self, output_text: str) -> Dict[str, Any]:
        """
        检查输出
        
        Args:
            output_text: 输出文本
            
        Returns:
            检查
        """
        security_result = self.security_monitor.check_output(output_text)
        
        return {
            "safe": security_result["safe"],
            "reason": security_result["reason"],
            "score": security_result["score"],
            "type": "output"
        }
    
    def check_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查Tool调用
        
        Args:
            tool_name: ToolName
            tool_args: Tool参数
            
        Returns:
            检查
        """
        security_result = self.security_monitor.check_tool_call(tool_name, tool_args)
        
        return {
            "safe": security_result["safe"],
            "reason": security_result["reason"],
            "score": security_result["score"],
            "type": "tool_call"
        }
    
    def check_ethics(self, input_text: str, output_text: str) -> Dict[str, Any]:
        """
        检查伦理合规性
        
        Args:
            input_text: 输入文本
            output_text: 输出文本
            
        Returns:
            检查
        """
        ethics_result = self.ethics_guardian.check_ethics(input_text, output_text)
        
        return {
            "compliant": ethics_result["compliant"],
            "violations": ethics_result["violations"],
            "score": ethics_result["score"],
            "type": "ethics"
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetStatistics
        
        Returns:
            Statistics
        """
        security_stats = self.security_monitor.get_statistics()
        ethics_stats = self.ethics_guardian.get_statistics()
        
        return {
            "security": security_stats,
            "ethics": ethics_stats
        }
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get监控历史
        
        Args:
            limit: 限制数量
            
        Returns:
            监控历史列表
        """
        return self.security_monitor.get_history(limit)
    
    def get_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get违规记录
        
        Args:
            limit: 限制数量
            
        Returns:
            违规记录列表
        """
        return self.ethics_guardian.get_violations(limit)
    
    def clear_history(self):
        """
        Clear历史记录
        """
        self.security_monitor.clear_history()
        self.ethics_guardian.clear_violations()


# 全局护栏层实例
guardrail_layer = None


def get_guardrail_layer() -> GuardrailLayer:
    """
    Get护栏层实例
    
    Returns:
        GuardrailLayer实例
    """
    global guardrail_layer
    if guardrail_layer is None:
        guardrail_layer = GuardrailLayer()
    return guardrail_layer


def reset_guardrail_layer():
    """
    重置护栏层
    """
    global guardrail_layer
    guardrail_layer = None
