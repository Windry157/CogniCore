#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task规划器
负责将复杂目标分解为可执行的子Task
"""

from typing import List, Dict, Any, Optional
import json
import logging

from .interfaces import PlannerInterface

logger = logging.getLogger(__name__)


class TaskPlanner(PlannerInterface):
    """Task规划器"""
    
    def __init__(self, llm_service=None):
        """
        InitializationTask规划器
        
        Args:
            llm_service: LLM服务实例, 用于executing task分解
        """
        self.llm_service = llm_service
        self.task_templates = {
            "travel_planning": [
                {"id": "search_flights", "name": "查询航班", "description": "查询往返航班信息"},
                {"id": "search_hotels", "name": "查询酒店", "description": "查询住宿酒店信息"},
                {"id": "create_itinerary", "name": "生成行程", "description": "根据航班和酒店信息生成详细行程"},
                {"id": "calculate_budget", "name": "估算预算", "description": "根据行程估算总预算"}
            ],
            "research_topic": [
                {"id": "collect_information", "name": "收集信息", "description": "收集相关主题的信息"},
                {"id": "analyze_information", "name": "分析信息", "description": "分析收集到的信息"},
                {"id": "synthesize_findings", "name": "综合发现", "description": "综合分析形成结论"},
                {"id": "present_results", "name": "呈现", "description": "以清晰的方式呈现研究"}
            ]
        }
    
    def decompose_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        将复杂Task分解为子Task
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            子Task列表, 每 子Task包含id, name, description, params等字段
        """
        logger.info(f"Decomposing task: {task}")
        
        # 首先尝试匹配预定义的Task模板
        for template_name, template_tasks in self.task_templates.items():
            if any(keyword in task.lower() for keyword in template_name.split('_')):
                logger.info(f"Matched task template: {template_name}")
                return self._enrich_tasks_with_context(template_tasks, context)
        
        # 如果没有匹配到模板, 使用LLM进行Task分解
        if self.llm_service:
            return self._use_llm_for_decomposition(task, context)
        else:
            # 如果没有LLM服务, 返回默认的通用Task分解
            logger.warning("No LLM service, using default task decomposition")
            return self._default_decomposition(task, context)
    
    def _enrich_tasks_with_context(self, tasks: List[Dict[str, Any]], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据上下文丰富Task信息
        
        Args:
            tasks: Task列表
            context: 上下文信息
            
        Returns:
            丰富后的Task列表
        """
        enriched_tasks = []
        for task in tasks:
            enriched_task = task.copy()
            if context:
                enriched_task['params'] = self._extract_params_for_task(task['id'], context)
            else:
                enriched_task['params'] = {}
            enriched_tasks.append(enriched_task)
        return enriched_tasks
    
    def _extract_params_for_task(self, task_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        为特定Task提取参数
        
        Args:
            task_id: TaskID
            context: 上下文信息
            
        Returns:
            Task参数
        """
        params = {}
        
        if task_id == "search_flights":
            params['origin'] = context.get('origin', '')
            params['destination'] = context.get('destination', '')
            params['departure_date'] = context.get('departure_date', '')
            params['return_date'] = context.get('return_date', '')
        elif task_id == "search_hotels":
            params['location'] = context.get('destination', '')
            params['check_in_date'] = context.get('departure_date', '')
            params['check_out_date'] = context.get('return_date', '')
            params['guests'] = context.get('guests', 1)
        elif task_id == "create_itinerary":
            params['destination'] = context.get('destination', '')
            params['duration'] = context.get('duration', 7)
        elif task_id == "calculate_budget":
            params['destination'] = context.get('destination', '')
            params['duration'] = context.get('duration', 7)
            params['guests'] = context.get('guests', 1)
        
        return params
    
    def _use_llm_for_decomposition(self, task: str, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用LLM进行Task分解
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            子Task列表
        """
        try:
            # 构建提示词
            prompt = self._build_decomposition_prompt(task, context)
            messages = [
                {"role": "system", "content": "你是一 专业的Task规划师, 擅长将复杂Task分解为可执行的子Task."},
                {"role": "user", "content": prompt}
            ]
            
            # 调用LLM服务
            response = self.llm_service.chat(messages)
            
            # 解析Response
            tasks = self._parse_llm_response(response)
            
            # 验证和优化Task列表
            if tasks and self.validate_task_plan(tasks):
                optimized_tasks = self.optimize_task_order(tasks)
                return optimized_tasks
            else:
                logger.warning("LLM-generated task list invalid, using default decomposition")
                return self._default_decomposition(task, context)
        except Exception as e:
            logger.error(f"LLM task decomposition failed: {e}")
            return self._default_decomposition(task, context)
    
    def _build_decomposition_prompt(self, task: str, context: Optional[Dict[str, Any]]) -> str:
        """
        构建Task分解提示词
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            提示词字符串
        """
        prompt = "你是一 专业的Task规划师, 擅长将复杂Task分解为可执行的子Task.以下是一些Task分解的示例: \n\n"
        
        # 示例1: 旅行规划Task
        prompt += "示例1: \n"
        prompt += "Task: 为我规划一 周末去杭州的旅行\n"
        prompt += "上下文信息: {\"budget\": 2000, \"duration\": 2, \"interests\": [\"自然风光\", \"历史文化\", \"美食\"]}\n"
        prompt += "输出: \n"
        prompt += "[\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"search_transport\",\n"
        prompt += "        \"name\": \"查询交通\",\n"
        prompt += "        \"description\": \"查询往返杭州的交通方式和价格\",\n"
        prompt += "        \"params\": {\"destination\": \"杭州\", \"duration\": 2, \"budget\": 2000}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"search_accommodation\",\n"
        prompt += "        \"name\": \"查询住宿\",\n"
        prompt += "        \"description\": \"查询杭州的酒店或民宿\",\n"
        prompt += "        \"params\": {\"destination\": \"杭州\", \"duration\": 2, \"budget\": 1000}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"plan_itinerary\",\n"
        prompt += "        \"name\": \"生成行程\",\n"
        prompt += "        \"description\": \"根据兴趣和时间生成详细行程\",\n"
        prompt += "        \"params\": {\"destination\": \"杭州\", \"duration\": 2, \"interests\": [\"自然风光\", \"历史文化\", \"美食\"]}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"calculate_budget\",\n"
        prompt += "        \"name\": \"计算预算\",\n"
        prompt += "        \"description\": \"计算整 旅行的总预算\",\n"
        prompt += "        \"params\": {\"budget\": 2000, \"duration\": 2}\n"
        prompt += "    }\n"
        prompt += "]\n\n"
        
        # 示例2: 研究Task
        prompt += "示例2: \n"
        prompt += "Task: 研究人工智能在医疗领域的应用\n"
        prompt += "上下文信息: {\"timeframe\": \"过去5年\", \"focus\": \"诊断和治疗\", \"report_format\": \"详细报告\"}\n"
        prompt += "输出: \n"
        prompt += "[\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"collect_information\",\n"
        prompt += "        \"name\": \"收集信息\",\n"
        prompt += "        \"description\": \"收集过去5年人工智能在医疗诊断和治疗领域的应用信息\",\n"
        prompt += "        \"params\": {\"timeframe\": \"过去5年\", \"focus\": \"诊断和治疗\"}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"analyze_information\",\n"
        prompt += "        \"name\": \"分析信息\",\n"
        prompt += "        \"description\": \"分析收集到的信息, 识别主要应用领域和技术趋势\",\n"
        prompt += "        \"params\": {\"focus\": \"诊断和治疗\"}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"synthesize_findings\",\n"
        prompt += "        \"name\": \"综合发现\",\n"
        prompt += "        \"description\": \"综合分析, 形成研究结论\",\n"
        prompt += "        \"params\": {\"report_format\": \"详细报告\"}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"create_report\",\n"
        prompt += "        \"name\": \"生成报告\",\n"
        prompt += "        \"description\": \"根据研究生成详细报告\",\n"
        prompt += "        \"params\": {\"report_format\": \"详细报告\"}\n"
        prompt += "    }\n"
        prompt += "]\n\n"
        
        # 示例3: 项目管理Task
        prompt += "示例3: \n"
        prompt += "Task: 开发一 智能助手应用\n"
        prompt += "上下文信息: {\"team_size\": 5, \"deadline\": \"3 月\", \"tech_stack\": [\"Python\", \"FastAPI\", \"React\"]}\n"
        prompt += "输出: \n"
        prompt += "[\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"define_requirements\",\n"
        prompt += "        \"name\": \"定义需求\",\n"
        prompt += "        \"description\": \"定义智能助手应用的功能需求和技术要求\",\n"
        prompt += "        \"params\": {\"tech_stack\": [\"Python\", \"FastAPI\", \"React\"]}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"design_architecture\",\n"
        prompt += "        \"name\": \"设计架构\",\n"
        prompt += "        \"description\": \"设计应用的系统架构和 module划分\",\n"
        prompt += "        \"params\": {\"team_size\": 5, \"tech_stack\": [\"Python\", \"FastAPI\", \"React\"]}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"implement_backend\",\n"
        prompt += "        \"name\": \"实现后端\",\n"
        prompt += "        \"description\": \"使用FastAPI实现后端服务\",\n"
        prompt += "        \"params\": {\"tech_stack\": [\"Python\", \"FastAPI\"]}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"implement_frontend\",\n"
        prompt += "        \"name\": \"实现前端\",\n"
        prompt += "        \"description\": \"使用React实现前端界面\",\n"
        prompt += "        \"params\": {\"tech_stack\": [\"React\"]}\n"
        prompt += "    },\n"
        prompt += "    {\n"
        prompt += "        \"id\": \"test_and_deploy\",\n"
        prompt += "        \"name\": \"Test和部署\",\n"
        prompt += "        \"description\": \"Test应用功能并部署到生产环境\",\n"
        prompt += "        \"params\": {\"deadline\": \"3 月\"}\n"
        prompt += "    }\n"
        prompt += "]\n\n"
        
        # 实际Task
        prompt += f"现在, 请分解以下Task: \n\nTask: {task}\n"
        
        if context:
            prompt += f"\n上下文信息: {json.dumps(context, ensure_ascii=False)}\n"
        
        prompt += "\n请按照与示例相同的JSON格式输出子Task列表, 确保: \n"
        prompt += "1. 子Task是具体的, 可执行的\n"
        prompt += "2. 子Task之间有合理的执行顺序\n"
        prompt += "3. 每 子Task包含必要的参数\n"
        prompt += "4. 只输出JSON格式, 不要包含其他Content\n"
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析LLM的Response
        
        Args:
            response: LLM的ResponseContent
            
        Returns:
            子Task列表
        """
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                tasks = json.loads(json_match.group(0))
                # 验证Task格式
                for task in tasks:
                    if 'id' not in task:
                        task['id'] = f"task_{tasks.index(task)}"
                    if 'name' not in task:
                        task['name'] = f"Task{tasks.index(task) + 1}"
                    if 'description' not in task:
                        task['description'] = task.get('name', '')
                    if 'params' not in task:
                        task['params'] = {}
                return tasks
            else:
                logger.error("No JSON task list found in LLM response")
                return []
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []
    
    def _default_decomposition(self, task: str, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        默认的Task分解
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            子Task列表
        """
        return [
            {
                "id": "task_1",
                "name": "Analyzing task",
                "description": "Analyzing task需求和目标",
                "params": {}
            },
            {
                "id": "task_2",
                "name": "executing task",
                "description": "执行主要TaskContent",
                "params": {}
            },
            {
                "id": "task_3",
                "name": "验证",
                "description": "Validating task execution result",
                "params": {}
            }
        ]
    
    def validate_task_plan(self, tasks: List[Dict[str, Any]]) -> bool:
        """
        验证Task计划的Effectiveness
        
        Args:
            tasks: Task列表
            
        Returns:
            是否有效
        """
        if not tasks:
            return False
        
        for task in tasks:
            if 'id' not in task or 'name' not in task:
                return False
        
        return True
    
    def optimize_task_order(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        优化Task执行顺序
        
        Args:
            tasks: Task列表
            
        Returns:
            优化后的Task列表
        """
        optimized_tasks = []
        
        for task in tasks:
            if any(keyword in task['name'].lower() for keyword in ['查询', '收集', 'Get', 'search', 'collect', 'fetch']):
                optimized_tasks.append(task)
        
        for task in tasks:
            if task not in optimized_tasks and any(keyword in task['name'].lower() for keyword in ['分析', 'Processing', '生成', 'analyze', 'process', 'generate']):
                optimized_tasks.append(task)
        
        for task in tasks:
            if task not in optimized_tasks:
                optimized_tasks.append(task)
        
        return optimized_tasks
    
    def reflect_on_task(self, task: Dict[str, Any], result: Dict[str, Any], 
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        对Task execution resultperforming reflection
        
        Args:
            task: 执行的Task信息
            result: 执行
            context: 执行上下文
            
        Returns:
            Reflection result, 包含Effectiveness, Efficiency和遗漏点评估
        """
        logger.info(f"For task {task.get('name', 'Unknown')} performing reflection")
        
        reflection = {
            "task_id": task.get('id', ''),
            "task_name": task.get('name', ''),
            "effectiveness": self._evaluate_effectiveness(task, result),
            "efficiency": self._evaluate_efficiency(task, result),
            "blind_spots": self._identify_blind_spots(task, result, context),
            "recommendations": []
        }
        
        reflection["recommendations"] = self._generate_reflection_recommendations(reflection)
        
        logger.info(f"Reflection complete: Effectiveness={reflection['effectiveness']['score']:.2f}, "
                   f"Efficiency={reflection['efficiency']['score']:.2f}, "
                   f"遗漏点={len(reflection['blind_spots'])} ")
        
        return reflection
    
    def _evaluate_effectiveness(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估TaskEffectiveness
        
        Args:
            task: Task信息
            result: 执行
            
        Returns:
            Effectiveness评估
        """
        effectiveness = {
            "score": 1.0,
            "assessment": "",
            "details": []
        }
        
        if result.get('status') != 'SUCCESS':
            effectiveness["score"] = 0.0
            effectiveness["assessment"] = "Taskexecution failed"
            effectiveness["details"].append(f"Error信息: {result.get('message', 'Unknown error')}")
            return effectiveness
        
        task_name = task.get('name', '')
        task_id = task.get('id', '')
        
        if task_id == "search_flights":
            if 'flight_id' not in result or 'price' not in result:
                effectiveness["score"] = 0.7
                effectiveness["assessment"] = "航班信息不完整"
                effectiveness["details"].append("缺少航班ID或价格信息")
        elif task_id == "search_hotels":
            if 'hotel_id' not in result or 'price_per_night' not in result:
                effectiveness["score"] = 0.7
                effectiveness["assessment"] = "酒店信息不完整"
                effectiveness["details"].append("缺少酒店ID或价格信息")
        elif task_id == "create_itinerary":
            if 'itinerary' not in result:
                effectiveness["score"] = 0.7
                effectiveness["assessment"] = "行程信息不完整"
                effectiveness["details"].append("缺少行程安排")
        elif task_id == "calculate_budget":
            if 'budget' not in result or 'total' not in result.get('budget', {}):
                effectiveness["score"] = 0.7
                effectiveness["assessment"] = "预算信息不完整"
                effectiveness["details"].append("缺少总预算信息")
        else:
            effectiveness["score"] = 0.9
            effectiveness["assessment"] = "Task执行 successful"
        
        return effectiveness
    
    def _evaluate_efficiency(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估TaskEfficiency
        
        Args:
            task: Task信息
            result: 执行
            
        Returns:
            Efficiency评估
        """
        efficiency = {
            "score": 1.0,
            "assessment": "",
            "details": []
        }
        
        if result.get('status') != 'SUCCESS':
            efficiency["score"] = 0.0
            efficiency["assessment"] = "Taskexecution failed, 无法评估效率"
            return efficiency
        
        task_name = task.get('name', '')
        
        if any(keyword in task_name for keyword in ['查询', 'Search', 'search', 'fetch']):
            if result.get('response_time', 0) > 5.0:
                efficiency["score"] = 0.7
                efficiency["assessment"] = "查询Response时间较长"
                efficiency["details"].append(f"Response时间: {result.get('response_time', 0):.2f}s")
            else:
                efficiency["score"] = 0.9
                efficiency["assessment"] = "查询效率良好"
        
        elif any(keyword in task_name for keyword in ['分析', 'Processing', 'analyze', 'process']):
            if result.get('processing_time', 0) > 10.0:
                efficiency["score"] = 0.7
                efficiency["assessment"] = "Processing时间较长"
                efficiency["details"].append(f"Processing时间: {result.get('processing_time', 0):.2f}s")
            else:
                efficiency["score"] = 0.9
                efficiency["assessment"] = "Processing效率良好"
        else:
            efficiency["score"] = 0.9
            efficiency["assessment"] = "Task执行效率正常"
        
        return efficiency
    
    def _identify_blind_spots(self, task: Dict[str, Any], result: Dict[str, Any],
                            context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        识别Task执行中的遗漏点
        
        Args:
            task: Task信息
            result: 执行
            context: 执行上下文
            
        Returns:
            遗漏点列表
        """
        blind_spots = []
        
        if result.get('status') != 'SUCCESS':
            blind_spots.append("Taskexecution failed, 需要分析 failedReason")
            return blind_spots
        
        task_id = task.get('id', '')
        task_name = task.get('name', '')
        
        if task_id == "search_flights":
            if not result.get('flight_id'):
                blind_spots.append("未Get航班ID, 可能需要检查APIResponse")
            if not result.get('price'):
                blind_spots.append("未Get航班价格信息")
            if not result.get('duration'):
                blind_spots.append("未Get飞行时长信息")
        
        elif task_id == "search_hotels":
            if not result.get('hotel_id'):
                blind_spots.append("未Get酒店ID")
            if not result.get('rating') and not result.get('reviews'):
                blind_spots.append("未Get酒店评分和评论信息")
            if not result.get('amenities'):
                blind_spots.append("未Get酒店设施信息")
        
        elif task_id == "create_itinerary":
            if not result.get('itinerary') or len(result.get('itinerary', [])) == 0:
                blind_spots.append("行程安排为空")
            if not result.get('highlights'):
                blind_spots.append("未标Register行程亮点")
        
        elif task_id == "calculate_budget":
            if 'budget' not in result:
                blind_spots.append("未生成预算明细")
            elif 'breakdown' not in result.get('budget', {}):
                blind_spots.append("预算缺少分项明细")
        
        if context:
            if context.get('user_requirements'):
                user_req = context.get('user_requirements')
                if isinstance(user_req, dict):
                    for key, value in user_req.items():
                        if key not in result and key not in task.get('params', {}):
                            blind_spots.append(f"用户需求 '{key}' 未被满足")
        
        return blind_spots
    
    def _generate_reflection_recommendations(self, reflection: Dict[str, Any]) -> List[str]:
        """
        基于Reflection result生成建议
        
        Args:
            reflection: Reflection result
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if reflection['effectiveness']['score'] < 0.8:
            recommendations.append("TaskEffectiveness较低, 建议检查Task目标和执行")
            recommendations.append(f"具体问题: {reflection['effectiveness']['assessment']}")
        
        if reflection['efficiency']['score'] < 0.8:
            recommendations.append("Task效率较低, 建议优化执行流程")
            recommendations.append(f"具体问题: {reflection['efficiency']['assessment']}")
        
        if reflection['blind_spots']:
            recommendations.append(f"发现 {len(reflection['blind_spots'])}  遗漏点, 需要关Register")
            for blind_spot in reflection['blind_spots'][:3]:
                recommendations.append(f"- {blind_spot}")
        
        if reflection['effectiveness']['score'] >= 0.8 and reflection['efficiency']['score'] >= 0.8:
            recommendations.append("Task执行良好, 可以继续下一步")
        
        return recommendations
    
    def update_plan_based_on_reflection(self, tasks: List[Dict[str, Any]], 
                                      reflections: List[Dict[str, Any]],
                                      context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Updating task plan based on reflection
        
        Args:
            tasks: 原始Task列表
            reflections: Reflection result列表
            context: 执行上下文
            
        Returns:
            Update后的Task列表
        """
        logger.info("Updating task plan based on reflection")
        
        updated_tasks = []
        
        for i, task in enumerate(tasks):
            task_copy = task.copy()
            
            if i < len(reflections):
                reflection = reflections[i]
                
                if reflection['blind_spots']:
                    task_copy['notes'] = f"遗漏点: {', '.join(reflection['blind_spots'][:2])}"
                
                if reflection['effectiveness']['score'] < 0.7:
                    task_copy['retry'] = True
                    task_copy['retry_reason'] = reflection['effectiveness']['assessment']
                
                if reflection['efficiency']['score'] < 0.7:
                    task_copy['optimize'] = True
            
            updated_tasks.append(task_copy)
        
        for reflection in reflections:
            if reflection['recommendations']:
                for rec in reflection['recommendations']:
                    if 'retry' in rec.lower() or '重新' in rec:
                        pass
            
        logger.info(f"Task plan updated, total {len(updated_tasks)}  tasks")
        return updated_tasks