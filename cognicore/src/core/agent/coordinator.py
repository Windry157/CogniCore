#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent协调器
整合规划器, 执行器, 批判器, 验证器, 形成完整的Agent系统
"""

from typing import Dict, Any, Optional, List
import json
import logging
import asyncio

from .planner import TaskPlanner
from .executor import TaskExecutor
from .critic import TaskCritic
from .validator import TaskValidator
from .interfaces import AgentCoordinatorInterface
from .state_manager import get_task_state_manager
from src.core.utils.logging_utils import get_logger, get_task_logger
from src.core.config import config
from src.core.websocket import get_websocket_service

logger = get_logger(__name__)


class AgentCoordinator(AgentCoordinatorInterface):
    """Agent协调器"""
    
    def __init__(self, skill_manager=None, llm_service=None):
        """
        Initializing agent协调器
        
        Args:
            skill_manager: Skill manager实例
            llm_service: LLM服务实例
        """
        self.skill_manager = skill_manager
        self.llm_service = llm_service
        
        # Initialization各 groups件
        self.planner = TaskPlanner(llm_service)
        self.executor = TaskExecutor(skill_manager, llm_service)
        self.critic = TaskCritic(llm_service)
        self.validator = TaskValidator(llm_service)
        
        # Task执行历史
        self.task_history = []
        
        logger.info("Agent coordinator initialized")
    
    async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processing复杂Task
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            TaskProcessing result
        """
        # CreateTaskID和日志器
        task_id = f"task_{int(asyncio.get_event_loop().time() * 1000)}"
        task_logger = get_task_logger(task_id)
        
        # InitializationTask status
        state_manager = get_task_state_manager()
        task_state = state_manager.create_state(task_id, task, context)
        task_state.add_step("Task分解", "将复杂Task分解为子Task")
        task_state.add_step("Task排序", "优化子Task执行顺序")
        task_state.add_step("计划验证", "Validating execution plan的可行性")
        task_state.add_step("Task执行", "executing task链并ProcessingError")
        task_state.add_step("分析", "生成改进计划并构建最终")
        
        task_logger.progress("开始ProcessingTask", task_description=task, context=context)
        task_state.start()
        
        try:
            # 1. Task分解
            task_state.start_step(0)
            tasks = self.planner.decompose_task(task, context)
            task_state.complete_step(0, tasks)
            task_logger.progress(f"Task分解 complete, Total生成 {len(tasks)}  子Task")
            
            if not tasks:
                error_msg = "Task分解 failed, 无法生成子Task"
                task_state.fail_step(0, error_msg)
                task_state.fail(error_msg)
                state_manager.save_state(task_id)
                task_logger.failure(error_msg)
                return {
                    "status": "ERROR",
                    "message": error_msg,
                    "tasks": [],
                    "task_id": task_id,
                    "status_tracker": task_logger.get_status()
                }
            
            # 2. 优化Task顺序
            task_state.start_step(1)
            optimized_tasks = self.planner.optimize_task_order(tasks)
            task_state.complete_step(1, optimized_tasks)
            task_logger.progress("Task顺序优化 complete")
            
            # 3. Validating execution plan
            task_state.start_step(2)
            plan_validation = self.validator.validate_plan(optimized_tasks, context)
            validation_status = "通过" if plan_validation.get('passed', False) else "未通过"
            task_state.complete_step(2, plan_validation)
            task_logger.progress(f"执行计划验证: {validation_status}")
            
            if not plan_validation.get('passed', False):
                error_msg = "执行计划验证未通过"
                task_state.fail_step(2, error_msg)
                task_state.fail(error_msg)
                state_manager.save_state(task_id)
                task_logger.failure(error_msg)
                return {
                    "status": "ERROR",
                    "message": error_msg,
                    "tasks": optimized_tasks,
                    "validation": plan_validation,
                    "task_id": task_id,
                    "status_tracker": task_logger.get_status()
                }
            
            # 4. executing task链 (带验证) 
            task_state.start_step(3)
            task_logger.progress("开始executing task链")
            result = await self._execute_with_correction_and_validation(optimized_tasks, context, task_logger)
            task_state.complete_step(3, result)
            
            # 5. 记录Task执行历史
            self.task_history.append({
                "task_id": task_id,
                "original_task": task,
                "subtasks": optimized_tasks,
                "result": result,
                "validation": plan_validation,
                "timestamp": asyncio.get_event_loop().time(),
                "status_tracker": task_logger.get_status()
            })
            
            # 6. 生成改进计划
            task_state.start_step(4)
            improvement_plan = self.critic.generate_improvement_plan(
                self.executor.get_task_history()
            )
            
            # 7. 构建最终
            final_result = {
                "status": result.get('status', 'ERROR'),
                "message": result.get('message', 'Taskprocessing complete'),
                "tasks": optimized_tasks,
                "results": result.get('results', []),
                "validations": result.get('validations', []),
                "final_state": self.executor.get_current_state(),
                "improvement_plan": improvement_plan,
                "plan_validation": plan_validation,
                "task_id": task_id,
                "status_tracker": task_logger.get_status(),
                "duration": task_logger.get_duration()
            }
            
            task_state.complete_step(4, final_result)
            task_state.complete(final_result)
            state_manager.save_state(task_id)
            
            if final_result['status'] == 'SUCCESS':
                task_logger.success("Taskprocessing complete")
            else:
                task_logger.failure("TaskProcessing failed")
            
            return final_result
        except Exception as e:
            error_msg = f"ProcessingTask时发生exception: {str(e)}"
            task_state.fail(error_msg)
            state_manager.save_state(task_id)
            task_logger.failure(error_msg)
            return {
                "status": "ERROR",
                "message": error_msg,
                "task_id": task_id,
                "status_tracker": task_logger.get_status()
            }
    
    async def _execute_with_correction_and_validation(self, tasks: List[Dict[str, Any]], 
                                     context: Optional[Dict[str, Any]] = None, 
                                     task_logger: Optional[Any] = None) -> Dict[str, Any]:
        """
        带Error修正和验证的Task执行
        
        Args:
            tasks: Task列表
            context: 上下文信息
            task_logger: Task日志器
            
        Returns:
            执行
        """
        results = []
        validations = []
        explanations = []
        reflections = []
        current_context = context.copy() if context else {}
        
        for i, task in enumerate(tasks):
            task_name = task.get('name', 'Unknown')
            if task_logger:
                task_logger.progress(f"Executing task {i+1}  tasks: {task_name}")
            else:
                logger.info(f"Executing task {i+1}  tasks: {task_name}")
            
            risk_assessment = self.validator.generate_risk_assessment(task, current_context)
            risk_level = risk_assessment.get('risk_level', 'medium')
            if task_logger:
                task_logger.progress(f"Task risk level: {risk_level}")
            else:
                logger.info(f"Task risk level: {risk_level}")
            
            try:
                result = await self.executor.execute_task(task, current_context)
                
                validation = self.validator.validate_execution(task, result)
                validations.append(validation)
                
                explanation = self.validator.generate_explanation(task, result, validation)
                explanations.append(explanation)
                if task_logger:
                    task_logger.progress("Task execution explanation", explanation=explanation[:100] + "...")
                else:
                    logger.info(f"Task execution explanation:\n{explanation}")
                
                results.append(result)
                
                reflection = self.planner.reflect_on_task(task, result, current_context)
                reflections.append(reflection)
                effectiveness = reflection['effectiveness']['score']
                efficiency = reflection['efficiency']['score']
                if task_logger:
                    task_logger.progress(f"Reflection result: Effectiveness={effectiveness:.2f}, Efficiency={efficiency:.2f}")
                else:
                    logger.info(f"Reflection result: Effectiveness={effectiveness:.2f}, Efficiency={efficiency:.2f}")
                
                if result.get('status') != 'SUCCESS':
                    if task_logger:
                        task_logger.progress(f"Task {task_name} execution failed, attempting correction")
                    else:
                        logger.warning(f"Task {task_name} execution failed, attempting correction")
                    
                    analysis = self.critic.analyze_error(result, task)
                    
                    corrected_task = task.copy()
                    corrected_task['params'] = analysis['correction_strategy'].get('corrected_params', {})
                    
                    if task_logger:
                        task_logger.progress("Re-executing task with correction strategy")
                    else:
                        logger.info("Re-executing task with correction strategy")
                    
                    corrected_result = await self.executor.execute_with_retry(corrected_task)
                    
                    corrected_validation = self.validator.validate_execution(corrected_task, corrected_result)
                    validations[-1] = corrected_validation
                    
                    corrected_explanation = self.validator.generate_explanation(corrected_task, corrected_result, corrected_validation)
                    explanations[-1] = corrected_explanation
                    if task_logger:
                        task_logger.progress("Task execution explanation after correction", explanation=corrected_explanation[:100] + "...")
                    else:
                        logger.info(f"Task execution explanation after correction:\n{corrected_explanation}")
                    
                    corrected_reflection = self.planner.reflect_on_task(corrected_task, corrected_result, current_context)
                    reflections[-1] = corrected_reflection
                    
                    if corrected_result.get('status') == 'SUCCESS':
                        if task_logger:
                            task_logger.progress("Task correction successful")
                        else:
                            logger.info("Task correction successful")
                        results[-1] = corrected_result
                        result = corrected_result
                    else:
                        if task_logger:
                            task_logger.failure("Task correction failed, cannot continue")
                        else:
                            logger.error("Task correction failed, cannot continue")
                        return {
                            "status": "ERROR",
                            "message": f"Task {task_name} execution failed, 且修正 failed",
                            "results": results,
                            "validations": validations,
                            "explanations": explanations,
                            "reflections": reflections,
                            "analysis": analysis
                        }
            except Exception as e:
                error_msg = f"Exception during task execution: {e}"
                if task_logger:
                    task_logger.failure(error_msg)
                else:
                    logger.error(error_msg)
                
                error_result = {
                    "status": "ERROR",
                    "message": f"Exception during task execution: {str(e)}",
                    "detail": str(e)
                }
                results.append(error_result)
                
                exception_validation = {
                    "passed": False,
                    "reason": f"Exception during task execution: {str(e)}",
                    "risks": [f"Exception during task execution: {str(e)}"],
                    "suggestions": ["检查Task参数和执行环境"]
                }
                validations.append(exception_validation)
                
                exception_explanation = self.validator.generate_explanation(task, error_result, exception_validation)
                explanations.append(exception_explanation)
                
                exception_reflection = {
                    "task_id": task.get('id', ''),
                    "task_name": task.get('name', ''),
                    "effectiveness": {"score": 0.0, "assessment": "Task执行exception"},
                    "efficiency": {"score": 0.0, "assessment": "无法评估"},
                    "blind_spots": ["Exception during task execution"],
                    "recommendations": ["检查Task参数和执行环境"]
                }
                reflections.append(exception_reflection)
                
                return {
                    "status": "ERROR",
                    "message": f"Exception during task execution",
                    "results": results,
                    "validations": validations,
                    "explanations": explanations,
                    "reflections": reflections,
                    "error": str(e)
                }
            
            current_context.update(result)
            
            # 短暂延迟, 避免API速率限制
            await asyncio.sleep(0.1)  # 减少延迟时间, 提高性能
        
        # 汇总
        summary = {
            "status": "SUCCESS",
            "message": f"Task chain execution complete, Total执行 {len(tasks)}  tasks",
            "results": results,
            "validations": validations,
            "explanations": explanations,
            "final_state": self.executor.get_current_state()
        }
        
        if task_logger:
            task_logger.progress(f"Task chain execution complete, Total执行 {len(tasks)}  tasks")
        
        return summary
    
    async def process_with_reflection(self, task: str, 
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        带反思机制的TaskProcessing
        
        Args:
            task: 复杂TaskDescription
            context: Task上下文信息
            
        Returns:
            TaskProcessing result
        """
        # Round 一次尝试
        first_attempt = await self.process_task(task, context)
        
        # 如果First attempt failed, reflecting and improving
        if first_attempt.get('status') != 'SUCCESS':
            logger.info("First attempt failed, reflecting and improving")
            
            # 生成反思提示词
            reflection_prompt = self._build_reflection_prompt(task, first_attempt)
            
            # 使用LLMperforming reflection
            if self.llm_service:
                messages = [
                    {"role": "system", "content": "你是一 专业的Task分析专家, 擅长Analyzing taskexecution failed的Reason并提供改进方案."},
                    {"role": "user", "content": reflection_prompt}
                ]
                
                try:
                    reflection = self.llm_service.chat(messages)
                    logger.info(f"Reflection result: {reflection}")
                    
                    # 提取改进后的TaskDescription和上下文
                    improved_task, improved_context = self._extract_improvements(reflection, task, context)
                    
                    # Round 二次尝试
                    logger.info("Second attempt based on reflection")
                    second_attempt = await self.process_task(improved_task, improved_context)
                    
                    # 构建最终
                    final_result = {
                        "status": second_attempt.get('status', 'ERROR'),
                        "message": second_attempt.get('message', 'Taskprocessing complete'),
                        "first_attempt": first_attempt,
                        "reflection": reflection,
                        "second_attempt": second_attempt
                    }
                    
                    return final_result
                except Exception as e:
                    logger.error(f"Reflection process failed: {e}")
                    return first_attempt
            else:
                logger.warning("No LLM service available, cannot reflect")
                return first_attempt
        
        return first_attempt
    
    def _build_reflection_prompt(self, task: str, result: Dict[str, Any]) -> str:
        """
        构建反思提示词
        
        Args:
            task: 原始TaskDescription
            result: Round 一次尝试的
            
        Returns:
            反思提示词
        """
        prompt = f"Taskexecution failed, 需要分析Reason并提供改进方案: \n\n"
        prompt += f"原始Task: {task}\n\n"
        prompt += f"执行: {json.dumps(result, ensure_ascii=False)}\n\n"
        
        prompt += "请分析 failedReason, 并提供以下Content: \n"
        prompt += "1.  failed的根本Reason\n"
        prompt += "2. 改进后的TaskDescription\n"
        prompt += "3. 推荐的执行策略\n"
        prompt += "4. 需要补充的上下文信息\n\n"
        
        prompt += "请以清晰, 结构化的方式输出分析."
        
        return prompt
    
    def _extract_improvements(self, reflection: str, task: str, 
                            context: Optional[Dict[str, Any]] = None) -> tuple:
        """
        FromReflection result中提取改进Content
        
        Args:
            reflection: Reflection result
            task: 原始TaskDescription
            context: 原始上下文信息
            
        Returns:
            (改进后的TaskDescription, 改进后的上下文信息)
        """
        # 简单的提取逻辑, 实际项目中可以使用更复杂的NLP技术
        improved_task = task
        improved_context = context.copy() if context else {}
        
        # 尝试提取改进后的TaskDescription
        import re
        task_match = re.search(r'改进后的TaskDescription: (.*?)\n', reflection, re.DOTALL)
        if task_match:
            improved_task = task_match.group(1).strip()
        
        # 尝试提取补充的上下文信息
        context_match = re.search(r'需要补充的上下文信息: (.*?)\n', reflection, re.DOTALL)
        if context_match:
            context_text = context_match.group(1).strip()
            # 简单解析上下文信息
            for line in context_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    improved_context[key.strip()] = value.strip()
        
        return improved_task, improved_context
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        GetTask执行历史
        
        Returns:
            Task执行历史
        """
        return self.task_history
    
    def get_executor_history(self) -> List[Dict[str, Any]]:
        """
        Get执行器的Task执行历史
        
        Returns:
            执行器的Task执行历史
        """
        return self.executor.get_task_history()
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get当前Status
        
        Returns:
            当前Status
        """
        return self.executor.get_current_state()
    
    def reset_state(self):
        """
        重置Status
        """
        self.executor.reset_state()
        logger.info("Agent state has been reset")
    
    def clear_history(self):
        """
        清除历史记录
        """
        self.task_history = []
        self.executor.clear_history()
        logger.info("Agent history has been cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        GetAgent statistics
        
        Returns:
            Statistics
        """
        executor_history = self.executor.get_task_history()
        success_count = sum(1 for item in executor_history if item.get('result', {}).get('status') == 'SUCCESS')
        total_count = len(executor_history)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        return {
            "total_tasks": total_count,
            "success_tasks": success_count,
            "success_rate": success_rate,
            "task_history_count": len(self.task_history)
        }
    
    async def shutdown(self):
        """
        CloseAgent, 清理资源
        """
        logger.info("Closing agent...")
        # 这里可以Add资源清理逻辑
        logger.info("Agent closed")
    
    async def process_with_react(self, task: str, context: Optional[Dict[str, Any]] = None, max_iterations: int = 10) -> Dict[str, Any]:
        """
        使用ReAct模式ProcessingTask
        
        Args:
            task: TaskDescription
            context: 上下文信息
            max_iterations: 最大迭代次数
            
        Returns:
            TaskProcessing result
        """
        # CreateTask日志器
        task_id = f"task_{int(asyncio.get_event_loop().time() * 1000)}"
        task_logger = get_task_logger(task_id)
        
        # GetWebSocket service
        websocket_service = get_websocket_service()
        
        # 发送Task started消息
        await websocket_service.send_task_update(
            task_id=task_id,
            status="STARTED",
            data={
                "task": task,
                "context": context,
                "timestamp": asyncio.get_event_loop().time()
            }
        )
        
        task_logger.progress("开始使用ReAct模式ProcessingTask", task_description=task, context=context)
        
        # InitializationReAct循环
        messages = [
            {
                "role": "system",
                "content": "你是一 智能助手, 使用ReAct模式解决问题.请按照以下格式输出: \n\n思考: [你的思考过程]\n行动: [你要执行的行动]\n参数: [行动的参数]"
            },
            {
                "role": "user",
                "content": f"Task: {task}\n\n上下文: {json.dumps(context, ensure_ascii=False) if context else '无'}"
            }
        ]
        
        # GetTool列表
        from src.core.tools.registry import get_tool_registry
        registry = get_tool_registry()
        tools = registry.get_tools_description()
        
        iteration = 0
        react_history = []
        
        while iteration < max_iterations:
            task_logger.progress(f"ReAct循环迭代 {iteration+1}/{max_iterations}")
            
            # 发送迭代开始消息
            await websocket_service.send_task_update(
                task_id=task_id,
                status="ITERATION_START",
                data={
                    "iteration": iteration + 1,
                    "max_iterations": max_iterations,
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
            
            try:
                # 1. 让LLM生成推理和行动计划
                response = self.llm_service.chat_with_tools(messages, tools)
                
                # 2. 解析LLM的输出
                content = response.get("message", {}).get("content", "")
                tool_calls = response.get("message", {}).get("tool_calls", [])
                
                react_history.append({
                    "iteration": iteration,
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })
                
                # 发送推理
                await websocket_service.send_task_update(
                    task_id=task_id,
                    status="REASONING",
                    data={
                        "iteration": iteration + 1,
                        "content": content,
                        "tool_calls": tool_calls,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                )
                
                # 3. ProcessingTool调用
                if tool_calls:
                    for tool_call in tool_calls:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("arguments", {})
                        
                        task_logger.progress(f"执行Tool调用: {tool_name}", arguments=tool_args)
                        
                        # 发送Tool调用消息
                        await websocket_service.send_task_update(
                            task_id=task_id,
                            status="TOOL_CALL",
                            data={
                                "iteration": iteration + 1,
                                "tool_name": tool_name,
                                "arguments": tool_args,
                                "timestamp": asyncio.get_event_loop().time()
                            }
                        )
                        
                        # 执行Tool
                        tool_result = self.llm_service.execute_tool_call(tool_call, tools)
                        
                        task_logger.progress(f"Tool execution result: {tool_result.get('status')}")
                        
                        # 发送Tool
                        await websocket_service.send_task_update(
                            task_id=task_id,
                            status="TOOL_RESULT",
                            data={
                                "iteration": iteration + 1,
                                "tool_name": tool_name,
                                "result": tool_result,
                                "timestamp": asyncio.get_event_loop().time()
                            }
                        )
                        
                        # 将Tool execution resultAdd到消息历史
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_result, ensure_ascii=False),
                            "tool_call_id": tool_call.get("id"),
                            "name": tool_name
                        })
                        
                        react_history.append({
                            "iteration": iteration,
                            "role": "tool",
                            "content": tool_result
                        })
                else:
                    # 没有Tool调用, Task可能already complete
                    task_logger.progress("没有Tool调用, Task可能already complete")
                    
                    # 发送Task complete消息
                    await websocket_service.send_task_update(
                        task_id=task_id,
                        status="COMPLETED",
                        data={
                            "reason": "没有Tool调用, Task可能already complete",
                            "timestamp": asyncio.get_event_loop().time()
                        }
                    )
                    break
                
                iteration += 1
                
            except Exception as e:
                error_msg = f"ReAct循环execution failed: {e}"
                task_logger.failure(error_msg)
                
                # 发送Error消息
                await websocket_service.send_task_update(
                    task_id=task_id,
                    status="ERROR",
                    data={
                        "message": error_msg,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                )
                
                return {
                    "status": "ERROR",
                    "message": error_msg,
                    "task_id": task_id,
                    "react_history": react_history,
                    "status_tracker": task_logger.get_status()
                }
        
        # 4. 生成最终Answer
        task_logger.progress("生成最终Answer")
        
        # 发送生成最终Answer消息
        await websocket_service.send_task_update(
            task_id=task_id,
            status="GENERATING_FINAL_ANSWER",
            data={
                "timestamp": asyncio.get_event_loop().time()
            }
        )
        
        try:
            final_prompt = f"基于以下对话历史, 总结Task的 complete情况: \n\n"
            for msg in messages:
                if msg["role"] == "user":
                    final_prompt += f"用户: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    final_prompt += f"助手: {msg['content']}\n"
                elif msg["role"] == "tool":
                    final_prompt += f"Tool: {msg['content']}\n"
            
            final_prompt += "\n请提供一 清晰, 全面的总结, 包括Task的 complete情况和获得的."
            
            final_response = self.llm_service.generate(final_prompt)
            
            final_result = {
                "status": "SUCCESS",
                "message": "ReAct模式Taskprocessing complete",
                "final_answer": final_response,
                "task_id": task_id,
                "react_history": react_history,
                "status_tracker": task_logger.get_status(),
                "duration": task_logger.get_duration()
            }
            
            # 发送Task complete消息
            await websocket_service.send_task_update(
                task_id=task_id,
                status="SUCCESS",
                data={
                    "final_answer": final_response,
                    "duration": task_logger.get_duration(),
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
            
            task_logger.success("ReAct模式Taskprocessing complete")
            return final_result
            
        except Exception as e:
            error_msg = f"生成最终Answer failed: {e}"
            task_logger.failure(error_msg)
            
            # 发送Error消息
            await websocket_service.send_task_update(
                task_id=task_id,
                status="ERROR",
                data={
                    "message": error_msg,
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
            
            return {
                "status": "ERROR",
                "message": error_msg,
                "task_id": task_id,
                "react_history": react_history,
                "status_tracker": task_logger.get_status()
            }