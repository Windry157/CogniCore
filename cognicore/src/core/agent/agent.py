#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent主类: 整合规划, 执行和评估功能
"""
from typing import Dict, Any, Optional, AsyncGenerator
from .planner import AgentPlanner
from .executor import AgentExecutor
from .critic import AgentCritic


class IntelligentAgent:
    """Agent主类"""

    def __init__(self, llm, skill_manager=None, memory_system=None, profile=None):
        self.llm = llm
        self.skill_manager = skill_manager
        self.memory_system = memory_system
        self.profile = profile
        
        # 系统提示
        self.system_prompt = profile.system_prompt if profile else "你是一 智能助手"
        
        # Initializationgroups件
        self.planner = AgentPlanner(llm, skill_manager=skill_manager, system_prompt=self.system_prompt)
        self.executor = AgentExecutor(skill_manager, memory_system)
        self.critic = AgentCritic(llm, system_prompt=self.system_prompt)
        
        # 过滤Tool (如果有profile) 
        if profile and profile.tools:
            self._filter_tools(profile.tools)
    
    def _filter_tools(self, allowed_tools: list):
        """
        过滤Tool, 只保留允许使用的Tool
        
        参数:
            allowed_tools: 允许使用的Tool列表
        """
        if self.skill_manager:
            # 这里需要实现Tool过滤逻辑
            # 暂时不做过滤, 使用所有Tool
            pass

    async def run(self, user_goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        运行Agent
        
        Args:
            user_goal: 用户目标
            context: 上下文信息
            
        Returns:
            最终执行
        """
        # Step 1: 规划Task
        plan = await self.planner.plan(user_goal, context)
        
        # Step 2: 执行计划
        execution_result = await self.executor.execute(plan, context)
        
        # Step 3: 评估
        evaluation = await self.critic.evaluate(user_goal, execution_result)
        
        # Step 4: Processing评估
        if evaluation.get("status") == "fail":
            # execution failed, attempting correction
            correction = await self.critic.suggest_correction(user_goal, execution_result)
            
            return {
                "status": "correction_needed",
                "message": "执行未满足目标",
                "evaluation": evaluation,
                "correction": correction,
                "execution_result": execution_result
            }
        else:
            # 执行 successful
            return {
                "status": "success",
                "message": "Task执行 successful",
                "evaluation": evaluation,
                "execution_result": execution_result
            }

    async def process_complex_task(self, user_goal: str, max_retries: int = 3) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Processing复杂Task, 支持重试, 流式输出进度和Step
        
        Args:
            user_goal: 用户目标
            max_retries: 最大重试次数
            
        Yields:
            逐步输出执行进度和最终
        """
        retry_count = 0
        last_result = None
        
        yield {
            "type": "status",
            "content": f"[refresh] 开始Processing复杂Task: {user_goal}\n"
        }
        
        while retry_count < max_retries:
            if retry_count > 0:
                yield {
                    "type": "status",
                    "content": f"[refresh] Round  {retry_count + 1} 次尝试...\n"
                }
            
            # 先规划Task
            plan = await self.planner.plan(user_goal, last_result)
            
            # 执行计划, 逐步输出每 Step
            execution_result = {
                "status": "success",
                "results": []
            }
            
            for step in plan:
                result = await self.executor._execute_step(step, {})
                execution_result["results"].append(result)
                # 流式输出这 Step
                yield {
                    "type": "step",
                    "step": {
                        "step": step["step"],
                        "thought": step["thought"],
                        "tool": step["tool"],
                        "result": result
                    }
                }
            
            # 检查是否有Error
            errors = [r for r in execution_result["results"] if "error" in r]
            if errors:
                execution_result["status"] = "error"
                execution_result["errors"] = errors
            
            # 评估
            evaluation = await self.critic.evaluate(user_goal, execution_result)
            
            if evaluation.get("status") == "success":
                # 执行 successful
                yield {
                    "type": "complete",
                    "result": {
                        "status": "success",
                        "message": "Task执行 successful",
                        "evaluation": evaluation,
                        "execution_result": execution_result
                    }
                }
                return
            
            # execution failed, 需要修正
            retry_count += 1
            if retry_count >= max_retries or not evaluation.get("correction"):
                break
            
            # 准备重试
            last_result = {
                "status": "fail",
                "message": "执行未满足目标",
                "evaluation": evaluation,
                "correction": evaluation.get("correction"),
                "execution_result": execution_result
            }
        
        # Reached max retries
        yield {
            "type": "complete",
            "result": {
                "status": "failed",
                "message": f"Taskexecution failed, already尝试 {retry_count} 次",
                "last_result": last_result
            }
        }
