#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批判器
负责监控Task执行, 识别Error, 并生成修正策略
"""

from typing import Dict, Any, Optional, List
import json
import logging

from .interfaces import CriticInterface

logger = logging.getLogger(__name__)


class TaskCritic(CriticInterface):
    """Task批判器"""
    
    def __init__(self, llm_service=None):
        """
        InitializationTask批判器
        
        Args:
            llm_service: LLM服务实例, 用于执行Error分析和策略生成
        """
        self.llm_service = llm_service
        self.error_patterns = {
            "API_RATE_LIMIT_EXCEEDED": {
                "category": "rate_limit",
                "description": "API速率限制超限",
                "suggestions": ["调整请求频率", "更换时间窗口", "使用备用API"]
            },
            "INPUT_VALIDATION_FAIL": {
                "category": "input_error",
                "description": "输入Parameter validation failed",
                "suggestions": ["修正输入参数", "检查参数格式", "提供默认值"]
            },
            "NETWORK_ERROR": {
                "category": "network",
                "description": "网络ConnectError",
                "suggestions": ["检查网络Connect", "重试操作", "使用代理"]
            },
            "AUTHENTICATION_ERROR": {
                "category": "auth",
                "description": "认证 failed",
                "suggestions": ["检查凭证", "重新登录", "UpdateAPI密钥"]
            },
            "NOT_FOUND": {
                "category": "resource",
                "description": "资源未Found",
                "suggestions": ["检查资源路径", "确认资源存在", "使用备用资源"]
            }
        }
    
    def analyze_error(self, error: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzing error并生成修正策略
        
        Args:
            error: Error信息, 包含status, message, detail等字段
            task:  failed的Task信息
            
        Returns:
            Error analysis result, 包含error type, Reason, 修正策略等
        """
        logger.info(f"Analyzing error: {error.get('message', 'Unknown error')}")
        
        # 提取Error信息
        error_message = error.get('message', 'Unknown error')
        error_detail = error.get('detail', '')
        
        # 识别error type
        error_type = self._identify_error_type(error_message)
        
        # 生成修正策略
        if self.llm_service:
            correction_strategy = self._generate_correction_strategy_with_llm(
                error, task, error_type
            )
        else:
            correction_strategy = self._generate_default_correction_strategy(
                error, task, error_type
            )
        
        # 构建分析
        analysis_result = {
            "error_type": error_type,
            "error_message": error_message,
            "error_detail": error_detail,
            "task_id": task.get('id', ''),
            "task_name": task.get('name', ''),
            "correction_strategy": correction_strategy
        }
        
        logger.info(f"Error analysis result: {json.dumps(analysis_result, ensure_ascii=False)}")
        return analysis_result
    
    def _identify_error_type(self, error_message: str) -> str:
        """
        识别error type
        
        Args:
            error_message: Error消息
            
        Returns:
            error type
        """
        # 首先尝试匹配预定义的Error模式
        for error_pattern, info in self.error_patterns.items():
            if error_pattern in error_message:
                return info['category']
        
        # 根据Error消息Content推断error type
        if any(keyword in error_message.lower() for keyword in ['rate', 'limit', 'quota']):
            return 'rate_limit'
        elif any(keyword in error_message.lower() for keyword in ['input', 'validation', 'parameter']):
            return 'input_error'
        elif any(keyword in error_message.lower() for keyword in ['network', 'connection', 'timeout']):
            return 'network'
        elif any(keyword in error_message.lower() for keyword in ['auth', 'login', 'credential']):
            return 'auth'
        elif any(keyword in error_message.lower() for keyword in ['not found', 'missing', 'does not exist']):
            return 'resource'
        else:
            return 'unknown'
    
    def _generate_correction_strategy_with_llm(self, error: Dict[str, Any], 
                                            task: Dict[str, Any], 
                                            error_type: str) -> Dict[str, Any]:
        """
        使用LLM生成修正策略
        
        Args:
            error: Error信息
            task:  failed的Task信息
            error_type: error type
            
        Returns:
            修正策略
        """
        try:
            prompt = self._build_correction_prompt(error, task, error_type)
            messages = [
                {"role": "system", "content": "你是一 专业的Error分析专家, 擅长Analyzing taskexecution failed的Reason并提供有效的修正策略."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_service.chat(messages)
            strategy = self._parse_llm_strategy(response)
            return strategy
        except Exception as e:
            logger.error(f"LLM correction strategy generation failed: {e}")
            return self._generate_default_correction_strategy(error, task, error_type)
    
    def _build_correction_prompt(self, error: Dict[str, Any], 
                                task: Dict[str, Any], 
                                error_type: str) -> str:
        """
        构建修正策略提示词
        
        Args:
            error: Error信息
            task:  failed的Task信息
            error_type: error type
            
        Returns:
            提示词字符串
        """
        prompt = f"Taskexecution failed, 需要生成修正策略: \n\n"
        prompt += f"Task信息: \n"
        prompt += f"- TaskID: {task.get('id', 'N/A')}\n"
        prompt += f"- TaskName: {task.get('name', 'N/A')}\n"
        prompt += f"- Task参数: {json.dumps(task.get('params', {}), ensure_ascii=False)}\n\n"
        prompt += f"Error信息: \n"
        prompt += f"- ErrorStatus: {error.get('status', 'ERROR')}\n"
        prompt += f"- Error消息: {error.get('message', 'Unknown error')}\n"
        prompt += f"- Error details: {error.get('detail', 'N/A')}\n"
        prompt += f"- error type: {error_type}\n\n"
        
        prompt += "请分析 failedReason, 并生成修正策略.修正策略应该包括: \n"
        prompt += "1.  failedReason分析\n"
        prompt += "2. 具体的修正Step\n"
        prompt += "3. 修正后的Task参数\n"
        prompt += "4. 可能的替代方案\n\n"
        
        prompt += "请按照以下JSON格式输出修正策略: \n"
        prompt += "{\n"
        prompt += "    \"reason\": \" failedReason分析\",\n"
        prompt += "    \"steps\": [\"Step1\", \"Step2\", ...],\n"
        prompt += "    \"corrected_params\": {\"param1\": \"value1\", ...},\n"
        prompt += "    \"alternatives\": [\"方案1\", \"方案2\", ...]\n"
        prompt += "}\n"
        
        prompt += "\n要求: \n"
        prompt += "1. 分析要具体, 准确\n"
        prompt += "2. 修正Step要可执行\n"
        prompt += "3. 修正后的参数要合理\n"
        prompt += "4. 只输出JSON格式, 不要包含其他Content\n"
        
        return prompt
    
    def _parse_llm_strategy(self, response: str) -> Dict[str, Any]:
        """
        解析LLM生成的修正策略
        
        Args:
            response: LLM的ResponseContent
            
        Returns:
            修正策略
        """
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                strategy = json.loads(json_match.group(0))
                # 验证策略格式
                if 'reason' not in strategy:
                    strategy['reason'] = "LLM生成的修正策略"
                if 'steps' not in strategy:
                    strategy['steps'] = []
                if 'corrected_params' not in strategy:
                    strategy['corrected_params'] = {}
                if 'alternatives' not in strategy:
                    strategy['alternatives'] = []
                return strategy
            else:
                logger.error("No JSON correction strategy found in LLM response")
                return self._default_strategy()
        except Exception as e:
            logger.error(f"Failed to parse LLM strategy: {e}")
            return self._default_strategy()
    
    def _generate_default_correction_strategy(self, error: Dict[str, Any], 
                                           task: Dict[str, Any], 
                                           error_type: str) -> Dict[str, Any]:
        """
        生成默认的修正策略
        
        Args:
            error: Error信息
            task:  failed的Task信息
            error_type: error type
            
        Returns:
            修正策略
        """
        strategy = {
            "reason": f"Taskexecution failed, error type: {error_type}",
            "steps": [],
            "corrected_params": task.get('params', {}).copy(),
            "alternatives": []
        }
        
        # 根据error type生成不同的修正策略
        if error_type == 'rate_limit':
            strategy['reason'] = "API速率限制超限, 需要调整请求频率"
            strategy['steps'] = ["Waiting一段时间后重试", "调整请求参数减少API调用", "使用备用API"]
            strategy['alternatives'] = ["更换时间窗口", "使用cache减少重复请求"]
        elif error_type == 'input_error':
            strategy['reason'] = "输入Parameter validation failed, 需要修正参数"
            strategy['steps'] = ["检查输入参数格式", "修正无效参数", "提供默认值"]
            # 尝试修正常见的输入Error
            params = strategy['corrected_params']
            if 'date' in params and '2025-12-25' in params['date']:
                params['date'] = '2025-12-20'  # 修正日期
            elif 'destination' in params and 'Shanghai' == params['destination']:
                params['destination'] = 'New York'  # 修正目的地
        elif error_type == 'network':
            strategy['reason'] = "网络ConnectError, 需要检查网络"
            strategy['steps'] = ["检查网络Connect", "重试操作", "使用代理"]
            strategy['alternatives'] = ["更换网络环境", "使用离线模式"]
        elif error_type == 'auth':
            strategy['reason'] = "认证 failed, 需要检查凭证"
            strategy['steps'] = ["检查认证凭证", "重新登录", "UpdateAPI密钥"]
            strategy['alternatives'] = ["使用其他认证方式", "联系管理员"]
        elif error_type == 'resource':
            strategy['reason'] = "资源未Found, 需要检查资源"
            strategy['steps'] = ["检查资源路径", "确认资源存在", "使用备用资源"]
            strategy['alternatives'] = ["更换资源源", "使用默认资源"]
        else:
            strategy['reason'] = "未知Error, 需要尝试通用修复"
            strategy['steps'] = ["检查Task参数", "重试操作", "查看详细日志"]
            strategy['alternatives'] = ["使用替代方法", "寻求人工帮助"]
        
        return strategy
    
    def _default_strategy(self) -> Dict[str, Any]:
        """
        默认的修正策略
        
        Returns:
            默认修正策略
        """
        return {
            "reason": "无法生成详细的修正策略",
            "steps": ["检查Task参数", "重试操作", "查看详细日志"],
            "corrected_params": {},
            "alternatives": ["使用替代方法", "寻求人工帮助"]
        }
    
    def evaluate_task_result(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估Task execution result
        
        Args:
            task: Task信息
            result: 执行
            
        Returns:
            评估
        """
        evaluation = {
            "task_id": task.get('id', ''),
            "task_name": task.get('name', ''),
            "success": False,
            "score": 0.0,
            "feedback": "",
            "suggestions": []
        }
        
        # 检查执行
        if result.get('status') == 'SUCCESS':
            evaluation['success'] = True
            evaluation['score'] = 1.0
            evaluation['feedback'] = "Task执行 successful"
            evaluation['suggestions'] = ["Task执行良好, 无需修正"]
        else:
            evaluation['success'] = False
            evaluation['score'] = 0.0
            evaluation['feedback'] = f"Taskexecution failed: {result.get('message', 'Unknown error')}"
            # 生成改进建议
            analysis = self.analyze_error(result, task)
            evaluation['suggestions'] = analysis['correction_strategy'].get('steps', [])
        
        return evaluation
    
    def generate_improvement_plan(self, task_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        根据Task历史生成改进计划
        
        Args:
            task_history: Task执行历史
            
        Returns:
            改进计划
        """
        # 分析历史执行情况
        success_count = sum(1 for item in task_history if item.get('evaluation', {}).get('success', False))
        total_count = len(task_history)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        # 分析常见Error
        error_types = {}
        for item in task_history:
            if not item.get('evaluation', {}).get('success', False):
                error_type = item.get('analysis', {}).get('error_type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # 生成改进计划
        improvement_plan = {
            "success_rate": success_rate,
            "total_tasks": total_count,
            "success_tasks": success_count,
            "error_distribution": error_types,
            "recommendations": []
        }
        
        # 根据error type生成建议
        if 'rate_limit' in error_types:
            improvement_plan['recommendations'].append("实现API请求速率限制和重试机制")
        if 'input_error' in error_types:
            improvement_plan['recommendations'].append("增强输入参数验证和修正机制")
        if 'network' in error_types:
            improvement_plan['recommendations'].append("实现网络ErrorProcessing和自动重试")
        if 'auth' in error_types:
            improvement_plan['recommendations'].append("优化认证流程和凭证管理")
        if 'resource' in error_types:
            improvement_plan['recommendations'].append("实现资源存在性检查和备用方案")
        
        # 通用建议
        if success_rate < 0.8:
            improvement_plan['recommendations'].append("增强ErrorProcessing和自我修正能力")
            improvement_plan['recommendations'].append("优化Task参数配置")
        
        return improvement_plan