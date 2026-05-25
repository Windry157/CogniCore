#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证器
负责在执行前后进行安全和伦理校验, 确保决策的可解释性和可信赖性
"""

from typing import Dict, Any, List, Optional
import json
import logging

from .interfaces import ValidatorInterface

logger = logging.getLogger(__name__)


class TaskValidator(ValidatorInterface):
    """Task验证器"""
    
    def __init__(self, llm_service=None):
        """
        InitializationTask验证器
        
        Args:
            llm_service: LLM服务实例, 用于执行复杂的验证和分析
        """
        self.llm_service = llm_service
        self.security_rules = {
            "prohibited_content": ["暴力", "色情", "恐怖主义", "仇恨言论", "违法活动"],
            "privacy_concerns": [" 人信息", "联系方式", "身份证号", "银行卡号"],
            "bias_detection": ["性别歧视", "种族歧视", "年龄歧视", "地域歧视"],
            "permission_boundaries": ["系统权限", "数据访问", "外部API调用"]
        }
        self.permission_scope = {
            "allowed_operations": ["read", "search", "query", "analyze", "generate"],
            "denied_operations": ["delete_system", "modify_security", "access_admin"],
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "max_api_calls_per_minute": 60
        }
    
    def validate_plan(self, plan: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validating execution plan的安全性和可行性
        
        Args:
            plan: 执行计划, 包含多 子Task
            context: Task上下文信息
            
        Returns:
            验证, 包含是否通过, 风险评估和建议
        """
        logger.info("Validating execution plan")
        
        # 检查计划是否为空
        if not plan:
            return {
                "passed": False,
                "reason": "执行计划为空",
                "risks": [],
                "suggestions": ["请生成有效的执行计划"]
            }
        
        # 分析计划Content
        risks = []
        suggestions = []
        
        for i, task in enumerate(plan):
            task_id = task.get('id', f'task_{i}')
            task_name = task.get('name', 'Unknown task')
            task_params = task.get('params', {})
            
            # 检查TaskContent安全性
            content_risks = self._check_content_safety(task_name, task_params)
            if content_risks:
                risks.extend([f"Task {task_name}: {risk}" for risk in content_risks])
            
            # 检查Task参数安全性
            param_risks = self._check_param_safety(task_params)
            if param_risks:
                risks.extend([f"Task {task_name} 参数: {risk}" for risk in param_risks])
        
        # 生成验证
        if risks:
            # 如果有风险, 生成建议
            suggestions = self._generate_suggestions(risks, plan, context)
            
            return {
                "passed": False,
                "reason": "执行计划存在安全风险",
                "risks": risks,
                "suggestions": suggestions
            }
        else:
            return {
                "passed": True,
                "reason": "执行计划安全可行",
                "risks": [],
                "suggestions": ["执行计划already验证, 可安全执行"]
            }
    
    def validate_execution(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validating task execution result的安全性和Effectiveness
        
        Args:
            task: 执行的Task信息
            result: 执行
            
        Returns:
            验证, 包含是否通过, 风险评估和建议
        """
        logger.info(f"Validating task execution result: {task.get('name', 'Unknown task')}")
        
        # 检查执行Status
        if result.get('status') != 'SUCCESS':
            return {
                "passed": False,
                "reason": f"Taskexecution failed: {result.get('message', 'Unknown error')}",
                "risks": [f"Taskexecution failed: {result.get('message', 'Unknown error')}"],
                "suggestions": ["检查Task参数和执行环境"]
            }
        
        # 检查执行Content安全性
        content_risks = self._check_content_safety(result.get('message', ''), result.get('data', {}))
        if content_risks:
            return {
                "passed": False,
                "reason": "执行存在安全风险",
                "risks": content_risks,
                "suggestions": ["检查执行Content", "考虑替代方案"]
            }
        
        # 评估执行的Effectiveness
        effectiveness = self._evaluate_effectiveness(task, result)
        
        return {
            "passed": True,
            "reason": "执行安全有效",
            "risks": [],
            "suggestions": effectiveness.get('suggestions', []),
            "effectiveness": effectiveness
        }
    
    def generate_risk_assessment(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generating risk assessment report
        
        Args:
            task: Task信息
            context: Task上下文信息
            
        Returns:
            风险评估报告
        """
        logger.info(f"Generating risk assessment report: {task.get('name', 'Unknown task')}")
        
        # Analyzing tasktype和参数
        task_type = task.get('id', '')
        task_params = task.get('params', {})
        
        # 评估风险等级
        risk_level = self._assess_risk_level(task_type, task_params)
        
        # 识别潜在风险点
        potential_risks = self._identify_potential_risks(task_type, task_params, context)
        
        # 生成风险缓解建议
        mitigation_strategies = self._generate_mitigation_strategies(potential_risks)
        
        # 构建风险评估报告
        risk_assessment = {
            "task_id": task.get('id', ''),
            "task_name": task.get('name', ''),
            "risk_level": risk_level,
            "potential_risks": potential_risks,
            "mitigation_strategies": mitigation_strategies,
            "timestamp": "2026-04-24",  # 实际应用中应使用当前时间
            "validator_version": "1.0.0"
        }
        
        return risk_assessment
    
    def _check_content_safety(self, content: str, params: Dict[str, Any]) -> List[str]:
        """
        检查Content安全性
        
        Args:
            content: 要检查的Content
            params: Task参数
            
        Returns:
            发现的风险列表
        """
        risks = []
        
        # 检查禁止Content
        for prohibited in self.security_rules["prohibited_content"]:
            if prohibited in content:
                risks.append(f"包含禁止Content: {prohibited}")
        
        # 检查隐私问题
        for privacy in self.security_rules["privacy_concerns"]:
            if privacy in content:
                risks.append(f"涉及隐私问题: {privacy}")
        
        # 检查偏见
        for bias in self.security_rules["bias_detection"]:
            if bias in content:
                risks.append(f"可能存在偏见: {bias}")
        
        return risks
    
    def _check_param_safety(self, params: Dict[str, Any]) -> List[str]:
        """
        检查参数安全性
        
        Args:
            params: Task参数
            
        Returns:
            发现的风险列表
        """
        risks = []
        
        # 检查参数中是否包含敏感信息
        for key, value in params.items():
            value_str = str(value)
            for privacy in self.security_rules["privacy_concerns"]:
                if privacy in value_str:
                    risks.append(f"参数 {key} 可能包含敏感信息: {privacy}")
        
        return risks
    
    def _check_operation_permissions(self, operation: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        检查操作权限
        
        Args:
            operation: 操作Name
            context: 上下文信息
            
        Returns:
            Permission check
        """
        result = {
            "allowed": True,
            "reason": "",
            "warnings": []
        }
        
        if operation in self.permission_scope["denied_operations"]:
            result["allowed"] = False
            result["reason"] = f"操作 {operation} 被明确禁止"
            return result
        
        if operation not in self.permission_scope["allowed_operations"]:
            result["allowed"] = False
            result["reason"] = f"操作 {operation} 不在允许列表中"
            return result
        
        if context:
            if context.get('user_level') == 'guest':
                if operation in ['delete', 'modify', 'execute']:
                    result["allowed"] = False
                    result["reason"] = "访客用户没有权限执行此操作"
                    return result
        
        result["reason"] = "操作权限验证通过"
        return result
    
    def _deep_content_analysis(self, content: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        深层Content分析
        
        Args:
            content: Content
            params: 参数
            
        Returns:
            深层分析
        """
        analysis = {
            "risk_score": 0.0,
            "risk_factors": [],
            "needs_review": False,
            "sanitization_suggestions": []
        }
        
        content_lower = content.lower()
        params_str = str(params).lower()
        
        risk_score = 0.0
        
        if any(word in content_lower for word in ["暴力", "血腥", "残忍"]):
            risk_score += 0.3
            analysis["risk_factors"].append("检测到暴力相关词汇")
        
        if any(word in content_lower for word in ["色情", "裸体", "性感"]):
            risk_score += 0.4
            analysis["risk_factors"].append("检测到敏感Content")
        
        if any(word in content_lower for word in ["恐怖", "爆炸", "袭击"]):
            risk_score += 0.5
            analysis["risk_factors"].append("检测到恐怖主义相关Content")
        
        if any(word in content_lower for word in ["身份证", "护照", "银行卡", "密码"]):
            risk_score += 0.4
            analysis["risk_factors"].append("检测到可能包含 人身份信息")
            analysis["sanitization_suggestions"].append("建议对 人身份信息进行脱敏Processing")
        
        if any(word in content_lower for word in ["歧视", "偏见", "仇恨"]):
            risk_score += 0.3
            analysis["risk_factors"].append("检测到可能存在偏见的Content")
        
        analysis["risk_score"] = min(risk_score, 1.0)
        analysis["needs_review"] = risk_score > 0.3
        
        return analysis
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        数据脱敏
        
        Args:
            data: 原始数据
            
        Returns:
            脱敏后的数据
        """
        sanitized = data.copy()
        
        sensitive_patterns = {
            "phone": r'\d{11}',
            "id_card": r'\d{17}[\dXx]',
            "bank_card": r'\d{16,19}',
            "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "password": r'password["\']?\s*[:=]\s*["\']?[^\s"\']+'
        }
        
        import re
        
        def mask_match(match):
            if re.match(r'\d{11}', match.group()):
                return f"{match.group()[:3]}****{match.group()[-4:]}"
            elif re.match(r'\d{17}[\dXx]', match.group()):
                return match.group()[:6] + "********" + match.group()[-4:]
            elif re.match(r'\d{16,19}', match.group()):
                return f"****{match.group()[-4:]}"
            else:
                return match.group()
        
        data_str = json.dumps(sanitized)
        for pattern_name, pattern in sensitive_patterns.items():
            data_str = re.sub(pattern, mask_match, data_str)
        
        return json.loads(data_str)
    
    def _generate_suggestions(self, risks: List[str], plan: List[Dict[str, Any]], 
                             context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        生成改进建议
        
        Args:
            risks: 发现的风险
            plan: 执行计划
            context: Task上下文信息
            
        Returns:
            改进建议列表
        """
        suggestions = []
        
        # 基于风险type生成建议
        for risk in risks:
            if "禁止Content" in risk:
                suggestions.append("移除或修改包含禁止Content的Task")
            elif "隐私问题" in risk:
                suggestions.append("确保不Processing或存储敏感 人信息")
            elif "偏见" in risk:
                suggestions.append("检查并消除可能的偏见Content")
            elif "权限" in risk:
                suggestions.append("确保Task在授权范围内执行")
        
        # 通用建议
        suggestions.append("审查执行计划, 确保符合安全和伦理标准")
        suggestions.append("考虑使用替代方案以降低风险")
        
        return suggestions
    
    def _evaluate_effectiveness(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估Task执行的Effectiveness
        
        Args:
            task: Task信息
            result: 执行
            
        Returns:
            Effectiveness评估
        """
        effectiveness = {
            "score": 1.0,  # 默认满分
            "suggestions": []
        }
        
        # 检查Task目标是否实现
        task_name = task.get('name', '')
        result_message = result.get('message', '')
        
        # 基于Tasktype评估Effectiveness
        if task_name == "查询航班":
            if "航班" not in result_message and "flight" not in result_message:
                effectiveness["score"] = 0.7
                effectiveness["suggestions"].append("检查航班查询是否包含预期信息")
        elif task_name == "查询酒店":
            if "酒店" not in result_message and "hotel" not in result_message:
                effectiveness["score"] = 0.7
                effectiveness["suggestions"].append("检查酒店查询是否包含预期信息")
        
        return effectiveness
    
    def _assess_risk_level(self, task_type: str, task_params: Dict[str, Any]) -> str:
        """
        评估风险等级
        
        Args:
            task_type: Tasktype
            task_params: Task参数
            
        Returns:
            风险等级: low, medium, high
        """
        # 基于Tasktype和参数评估风险等级
        if any(keyword in task_type for keyword in ["search", "查询", "fetch"]):
            return "low"
        elif any(keyword in task_type for keyword in ["create", "生成", "write"]):
            return "medium"
        elif any(keyword in task_type for keyword in ["delete", "Delete", "execute"]):
            return "high"
        else:
            return "medium"
    
    def _identify_potential_risks(self, task_type: str, task_params: Dict[str, Any], 
                                 context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        识别潜在风险点
        
        Args:
            task_type: Tasktype
            task_params: Task参数
            context: Task上下文信息
            
        Returns:
            潜在风险点列表
        """
        potential_risks = []
        
        # 基于Tasktype识别风险
        if "search" in task_type or "查询" in task_type:
            potential_risks.append("可能访问到敏感信息")
            potential_risks.append("可能触发API速率限制")
        elif "create" in task_type or "生成" in task_type:
            potential_risks.append("可能生成不当Content")
            potential_risks.append("可能违反知识产权")
        elif "execute" in task_type or "执行" in task_type:
            potential_risks.append("可能执行恶意代码")
            potential_risks.append("可能导致系统不稳定")
        
        # 基于参数识别风险
        if "url" in task_params or "website" in task_params:
            potential_risks.append("可能访问不安全的网站")
        if "file" in task_params or "path" in task_params:
            potential_risks.append("可能访问或修改敏感文件")
        
        return potential_risks
    
    def _generate_mitigation_strategies(self, potential_risks: List[str]) -> List[str]:
        """
        生成风险缓解策略
        
        Args:
            potential_risks: 潜在风险点列表
            
        Returns:
            风险缓解策略列表
        """
        mitigation_strategies = []
        
        for risk in potential_risks:
            if "敏感信息" in risk:
                mitigation_strategies.append("实施数据过滤, 避免Processing敏感信息")
            elif "API速率限制" in risk:
                mitigation_strategies.append("实现请求速率控制和重试机制")
            elif "不当Content" in risk:
                mitigation_strategies.append("实施Content审核和过滤机制")
            elif "知识产权" in risk:
                mitigation_strategies.append("确保生成Content符合知识产权法规")
            elif "恶意代码" in risk:
                mitigation_strategies.append("实施代码安全检查和沙箱执行")
            elif "系统不稳定" in risk:
                mitigation_strategies.append("实施资源限制和ErrorProcessing机制")
            elif "不安全的网站" in risk:
                mitigation_strategies.append("实施网站安全检查和访问控制")
            elif "敏感文件" in risk:
                mitigation_strategies.append("实施文件访问权限控制")
        
        return mitigation_strategies
    
    def generate_explanation(self, task: Dict[str, Any], result: Dict[str, Any], 
                           validation: Dict[str, Any]) -> str:
        """
        生成执行解释
        
        Args:
            task: Task信息
            result: 执行
            validation: 验证
            
        Returns:
            执行解释字符串
        """
        explanation = f"\n=== 执行解释 ===\n"
        explanation += f"Task: {task.get('name', 'Unknown')}\n"
        explanation += f"ID: {task.get('id', 'Unknown')}\n"
        
        if task.get('params'):
            explanation += f"参数: {json.dumps(task.get('params'), ensure_ascii=False)}\n"
        
        explanation += f"执行Status: {result.get('status', 'Unknown')}\n"
        
        if result.get('status') == 'SUCCESS':
            explanation += f"执行: {result.get('message', 'Success')}\n"
        else:
            explanation += f"Error信息: {result.get('message', 'Unknown error')}\n"
        
        explanation += f"验证Status: {'通过' if validation.get('passed', False) else '未通过'}\n"
        
        if validation.get('risks'):
            explanation += f"风险评估: {', '.join(validation.get('risks', []))}\n"
        
        if validation.get('suggestions'):
            explanation += f"改进建议: {', '.join(validation.get('suggestions', []))}\n"
        
        if validation.get('effectiveness'):
            effectiveness = validation.get('effectiveness')
            explanation += f"Effectiveness评分: {effectiveness.get('score', 1.0)}\n"
        
        explanation += "=== 解释结束 ==="
        
        return explanation