#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行器
负责执行子Task, 管理Tool调用, ProcessingTask间的数据传递
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
import json
import logging
import asyncio

from .interfaces import ExecutorInterface

logger = logging.getLogger(__name__)


class TaskExecutor(ExecutorInterface):
    """Task执行器"""
    
    def __init__(self, skill_manager=None, llm_service=None):
        """
        InitializationTask执行器
        
        Args:
            skill_manager: Skill manager实例, 用于执行Tool调用
            llm_service: LLM服务实例, 用于Processing复杂逻辑
        """
        self.skill_manager = skill_manager
        self.llm_service = llm_service
        self.task_history = []
        self.state = {}
        self.fallback_cache = {}
        self.degradation_strategies = self._init_degradation_strategies()
    
    def _init_degradation_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialization降级策略
        
        Returns:
            降级策略字典
        """
        return {
            "API_RATE_LIMIT_EXCEEDED": {
                "strategy": "retry_with_delay",
                "fallback_to": "cache",
                "delay": 5.0,
                "max_retries": 3
            },
            "INPUT_VALIDATION_FAIL": {
                "strategy": "correct_and_retry",
                "fallback_to": "default_values",
                "auto_correct": True
            },
            "NETWORK_ERROR": {
                "strategy": "retry_with_backoff",
                "fallback_to": "cache",
                "delay": 3.0,
                "max_retries": 5
            },
            "TIMEOUT": {
                "strategy": "retry_with_longer_timeout",
                "fallback_to": "partial_result",
                "timeout_multiplier": 2.0
            },
            "SERVICE_UNAVAILABLE": {
                "strategy": "wait_and_retry",
                "fallback_to": "alternative_service",
                "wait_time": 10.0
            },
            "UNKNOWN_ERROR": {
                "strategy": "log_and_continue",
                "fallback_to": "default_response"
            }
        }
    
    async def execute_with_degradation(self, task: Dict[str, Any], 
                                     context: Optional[Dict[str, Any]] = None,
                                     error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        带优雅降级的Task执行
        
        Args:
            task: Task信息
            context: 上下文信息
            error: Error信息
            
        Returns:
            执行或降级Response
        """
        error_message = error.get('message', 'UNKNOWN_ERROR') if error else 'UNKNOWN_ERROR'
        
        if error_message not in self.degradation_strategies:
            error_message = 'UNKNOWN_ERROR'
        
        strategy = self.degradation_strategies[error_message]
        logger.info(f"Applying degradation strategy: {strategy['strategy']}, error type: {error_message}")
        
        fallback_strategy = strategy.get('fallback_to', 'default_response')
        
        if fallback_strategy == 'cache':
            cached_result = self._get_from_cache(task.get('id', ''))
            if cached_result:
                logger.info(f"Using cached data as degradation response")
                cached_result['degradation_note'] = f"来自cache的降级Response (原始Error: {error_message}) "
                return cached_result
        
        if fallback_strategy == 'default_values':
            logger.info(f"Using default value as degradation response")
            return self._generate_default_response(task, error_message)
        
        if fallback_strategy == 'default_response':
            logger.info(f"Using default response as degradation response")
            return {
                "status": "DEGRADED",
                "message": f"由于Error '{error_message}', 系统使用了降级Response",
                "degradation": True,
                "error": error_message
            }
        
        if fallback_strategy == 'partial_result':
            partial = self._generate_partial_result(task)
            if partial:
                logger.info(f"Using partial results as degradation response")
                partial['degradation_note'] = f"部分 (原始Error: {error_message}) "
                return partial
        
        return {
            "status": "DEGRADED",
            "message": f"无法ProcessingError '{error_message}'",
            "degradation": True,
            "error": error_message
        }
    
    def _get_from_cache(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Got result from cache
        
        Args:
            task_id: TaskID
            
        Returns:
            cache的, 如果没有则返回None
        """
        if task_id in self.fallback_cache:
            cached = self.fallback_cache[task_id]
            cached['from_cache'] = True
            return cached
        
        for history_item in reversed(self.task_history):
            if history_item.get('task', {}).get('id') == task_id:
                result = history_item.get('result', {})
                if result.get('status') == 'SUCCESS':
                    result['from_cache'] = True
                    return result
        
        return None
    
    def _generate_default_response(self, task: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """
        生成默认Response
        
        Args:
            task: Task信息
            error_message: Error信息
            
        Returns:
            默认Response
        """
        task_id = task.get('id', '')
        
        defaults = {
            "search_flights": {
                "status": "DEGRADED",
                "message": "航班查询暂时不可用, 请稍后再试",
                "flight_id": "FL000",
                "price": 0,
                "duration": "未知"
            },
            "search_hotels": {
                "status": "DEGRADED",
                "message": "酒店查询暂时不可用, 请稍后再试",
                "hotel_id": "HT000",
                "price_per_night": 0
            },
            "create_itinerary": {
                "status": "DEGRADED",
                "message": "行程生成暂时不可用, 请稍后再试",
                "itinerary": []
            },
            "calculate_budget": {
                "status": "DEGRADED",
                "message": "预算计算暂时不可用, 请稍后再试",
                "budget": {"total": 0}
            }
        }
        
        response = defaults.get(task_id, {
            "status": "DEGRADED",
            "message": f"Taskexecution failed: {error_message}",
            "error": error_message
        })
        
        response['degradation_note'] = f"默认值降级Response (原始Error: {error_message}) "
        return response
    
    def _generate_partial_result(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生成部分
        
        Args:
            task: Task信息
            
        Returns:
            部分, 如果没有则返回None
        """
        task_id = task.get('id', '')
        current_state = self.state
        
        partial = None
        
        if task_id == "search_flights" and 'flight_info' in current_state:
            partial = current_state['flight_info'].copy()
            partial['status'] = "PARTIAL"
            partial['degradation_note'] = "部分航班信息"
        elif task_id == "search_hotels" and 'hotel_info' in current_state:
            partial = current_state['hotel_info'].copy()
            partial['status'] = "PARTIAL"
            partial['degradation_note'] = "部分酒店信息"
        elif task_id == "calculate_budget" and 'budget' in current_state:
            partial = current_state['budget'].copy()
            partial['status'] = "PARTIAL"
            partial['degradation_note'] = "基于历史数据的预算"
        
        return partial
    
    def _store_in_cache(self, task_id: str, result: Dict[str, Any]):
        """
        存储到cache
        
        Args:
            task_id: TaskID
            result: 执行
        """
        if result.get('status') == 'SUCCESS':
            self.fallback_cache[task_id] = result.copy()
            logger.info(f"Result cached for degradation strategy")
    
    async def execute_task(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行单 tasks
        
        Args:
            task: Task信息, 包含id, name, description, params等字段
            context: Task上下文信息
            
        Returns:
            执行
        """
        logger.info(f"executing task: {task.get('name', 'Unknown task')}")
        
        # 准备Task参数
        params = task.get('params', {}).copy()
        
        # From上下文和Status中Get必要的参数
        if context:
            for key, value in context.items():
                if key not in params:
                    params[key] = value
        
        # FromStatus中Get参数
        for key, value in self.state.items():
            if key not in params:
                params[key] = value
        
        # executing task
        try:
            # 首先尝试Using skill管理器executing task
            if self.skill_manager:
                result = await self._execute_with_skill_manager(task, params)
            else:
                # 如果没有Skill manager, 使用模拟执行
                result = self._execute_with_mock(task, params)
            
            # UpdateStatus
            self._update_state(task, result)
            
            # 记录Task执行历史
            self.task_history.append({
                "task": task,
                "params": params,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            logger.info(f"Task execution complete: {task.get('name', 'Unknown task')}, Status: {result.get('status', 'Unknown')}")
            return result
        except Exception as e:
            logger.error(f"Taskexecution failed: {e}")
            error_result = {
                "status": "ERROR",
                "message": str(e),
                "detail": f"executing task {task.get('name', 'Unknown')} 时发生Error"
            }
            # 记录 failed的Task
            self.task_history.append({
                "task": task,
                "params": params,
                "result": error_result,
                "timestamp": asyncio.get_event_loop().time()
            })
            return error_result
    
    async def _execute_with_skill_manager(self, task: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Using skill管理器executing task
        
        Args:
            task: Task信息
            params: Task参数
            
        Returns:
            执行
        """
        # 映射Task到Skill
        skill_map = {
            "search_flights": ("network_diagnostic", "ping"),
            "search_hotels": ("file_manager", "list_dir"),
            "create_itinerary": ("code_executor", "execute_python"),
            "calculate_budget": ("code_executor", "execute_python"),
            "collect_information": ("search", "search"),
            "analyze_information": ("code_executor", "execute_python"),
            "synthesize_findings": ("code_executor", "execute_python"),
            "present_results": ("file_manager", "write_file")
        }
        
        task_id = task.get('id', '')
        if task_id in skill_map:
            skill_name, action = skill_map[task_id]
            if skill_name in self.skill_manager.skills:
                logger.info(f"Using skill {skill_name}.{action} executing task")
                result = await self.skill_manager.execute_tool(skill_name, action, params)
                return self._normalize_result(result)
        
        # 如果没有匹配的Skill, 使用默认执行
        return self._execute_with_default(task, params)
    
    def _execute_with_mock(self, task: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用模拟executing task
        
        Args:
            task: Task信息
            params: Task参数
            
        Returns:
            模拟执行
        """
        task_id = task.get('id', '')
        
        # 模拟航班查询
        if task_id == "search_flights":
            origin = params.get('origin', 'Tokyo')
            destination = params.get('destination', 'New York')
            date = params.get('date', '2025-12-25')
            
            # 模拟Error情况
            if "2025-12-25" in date:
                return {
                    "status": "ERROR",
                    "message": "API_RATE_LIMIT_EXCEEDED",
                    "detail": "该日期流量超限, 请尝试调整日期."
                }
            elif "New York" not in destination:
                return {
                    "status": "ERROR",
                    "message": "INPUT_VALIDATION_FAIL",
                    "detail": "目的地必须是国际大城市."
                }
            else:
                import random
                price = random.randint(500, 1500)
                return {
                    "status": "SUCCESS",
                    "flight_id": f"FL{random.randint(100, 999)}",
                    "price": price,
                    "duration": "8h",
                    "origin": origin,
                    "destination": destination,
                    "date": date
                }
        
        # 模拟酒店查询
        elif task_id == "search_hotels":
            location = params.get('location', 'New York')
            check_in = params.get('check_in_date', '2025-12-20')
            check_out = params.get('check_out_date', '2025-12-27')
            
            import random
            price = random.randint(200, 800)
            return {
                "status": "SUCCESS",
                "hotel_id": f"HT{random.randint(100, 999)}",
                "name": f"{location} Grand Hotel",
                "price_per_night": price,
                "total_price": price * 7,
                "location": location,
                "check_in": check_in,
                "check_out": check_out
            }
        
        # 模拟生成行程
        elif task_id == "create_itinerary":
            destination = params.get('destination', 'New York')
            duration = params.get('duration', 7)
            
            itinerary = []
            for day in range(1, duration + 1):
                itinerary.append({
                    "day": day,
                    "activities": [
                        f"上午: 参观{destination}景点",
                        f"下午: 购物",
                        f"晚上: 品尝当地美食"
                    ]
                })
            
            return {
                "status": "SUCCESS",
                "itinerary": itinerary,
                "destination": destination,
                "duration": duration
            }
        
        # 模拟估算预算
        elif task_id == "calculate_budget":
            destination = params.get('destination', 'New York')
            duration = params.get('duration', 7)
            guests = params.get('guests', 1)
            
            # 基础预算
            flight_cost = 1000 * guests
            hotel_cost = 300 * duration * guests
            food_cost = 100 * duration * guests
            activities_cost = 200 * duration * guests
            total_cost = flight_cost + hotel_cost + food_cost + activities_cost
            
            return {
                "status": "SUCCESS",
                "budget": {
                    "flight": flight_cost,
                    "hotel": hotel_cost,
                    "food": food_cost,
                    "activities": activities_cost,
                    "total": total_cost
                },
                "destination": destination,
                "duration": duration,
                "guests": guests
            }
        
        # 默认 successful
        else:
            return {
                "status": "SUCCESS",
                "message": f"Task {task.get('name', 'Unknown')} 执行 successful",
                "data": params
            }
    
    def _execute_with_default(self, task: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        默认executing task
        
        Args:
            task: Task信息
            params: Task参数
            
        Returns:
            执行
        """
        return {
            "status": "SUCCESS",
            "message": f"Task {task.get('name', 'Unknown')} 执行 successful",
            "data": params
        }
    
    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        """
        标准化执行
        
        Args:
            result: 原始执行
            
        Returns:
            标准化的执行
        """
        if isinstance(result, dict):
            if 'status' not in result:
                result['status'] = 'SUCCESS'
            return result
        elif isinstance(result, str):
            return {
                "status": "SUCCESS",
                "message": result
            }
        else:
            return {
                "status": "SUCCESS",
                "message": str(result)
            }
    
    def _update_state(self, task: Dict[str, Any], result: Dict[str, Any]):
        """
        根据Task execution resultUpdateStatus
        
        Args:
            task: Task信息
            result: 执行
        """
        if result.get('status') == 'SUCCESS':
            task_id = task.get('id', '')
            
            # 根据TasktypeUpdate不同的Status
            if task_id == "search_flights":
                self.state['flight_info'] = result
                self.state['flight_price'] = result.get('price')
            elif task_id == "search_hotels":
                self.state['hotel_info'] = result
                self.state['hotel_price'] = result.get('total_price')
            elif task_id == "create_itinerary":
                self.state['itinerary'] = result.get('itinerary')
            elif task_id == "calculate_budget":
                self.state['budget'] = result.get('budget')
                self.state['total_budget'] = result.get('budget', {}).get('total')
            
            # 提取通用Status
            for key, value in result.items():
                if key not in ['status', 'message', 'detail']:
                    self.state[key] = value
    
    def _analyze_task_dependencies(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Analyzing task之间的依赖关系
        
        Args:
            tasks: Task列表
            
        Returns:
            依赖关系字典, 键为TaskID, 值为依赖的TaskID列表
        """
        dependencies = {}
        
        # 基于Tasktype和Name分析依赖关系
        for task in tasks:
            task_id = task.get('id', '')
            task_name = task.get('name', '').lower()
            dependencies[task_id] = []
            
            # 分析依赖关系
            if any(keyword in task_name for keyword in ['生成', '计算', '分析', 'Processing', 'synthesize', 'analyze', 'process', 'calculate']):
                # 这些Task通常依赖于前面的查询/收集Task
                for prev_task in tasks:
                    prev_task_id = prev_task.get('id', '')
                    prev_task_name = prev_task.get('name', '').lower()
                    if any(keyword in prev_task_name for keyword in ['查询', '收集', 'Get', 'search', 'collect', 'fetch', 'get']):
                        dependencies[task_id].append(prev_task_id)
            
            # 特殊依赖关系
            if task_id == "create_itinerary":
                # 生成行程依赖于航班和酒店查询
                for prev_task in tasks:
                    prev_task_id = prev_task.get('id', '')
                    if prev_task_id in ["search_flights", "search_hotels"]:
                        dependencies[task_id].append(prev_task_id)
            elif task_id == "calculate_budget":
                # 计算预算依赖于行程生成
                for prev_task in tasks:
                    prev_task_id = prev_task.get('id', '')
                    if prev_task_id == "create_itinerary":
                        dependencies[task_id].append(prev_task_id)
        
        return dependencies
    
    def _group_tasks_by_dependencies(self, tasks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        根据依赖关系For task进行分groups, 同一groups的Task可以并行执行
        
        Args:
            tasks: Task列表
            
        Returns:
            Taskgroups列表, 同一groups的Task可以并行执行
        """
        dependencies = self._analyze_task_dependencies(tasks)
        task_map = {task.get('id', ''): task for task in tasks}
        
        # 计算每 tasks的依赖深度
        task_depth = {}
        for task_id in dependencies:
            depth = 0
            for dep_id in dependencies[task_id]:
                if dep_id in task_depth:
                    depth = max(depth, task_depth[dep_id] + 1)
            task_depth[task_id] = depth
        
        # 根据深度分groups
        groups = {}
        for task_id, depth in task_depth.items():
            if depth not in groups:
                groups[depth] = []
            if task_id in task_map:
                groups[depth].append(task_map[task_id])
        
        # 按深度排序返回
        return [groups[depth] for depth in sorted(groups.keys())]
    
    async def execute_parallel_tasks(self, tasks: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        并行executing task
        
        Args:
            tasks: Task列表
            context: 上下文信息
            
        Returns:
            执行列表
        """
        if not tasks:
            return []
        
        # CreateTask执行协程
        coroutines = []
        for task in tasks:
            coroutine = self.execute_task(task, context)
            coroutines.append(coroutine)
        
        # 并行执行
        results = await asyncio.gather(*coroutines)
        return results
    
    async def execute_task_chain(self, tasks: List[Dict[str, Any]], 
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        executing task链 (支持并行执行) 
        
        Args:
            tasks: Task列表
            context: 初始上下文信息
            
        Returns:
            执行汇总
        """
        results = []
        current_context = context.copy() if context else {}
        
        # Analyzing task依赖关系并分groups
        task_groups = self._group_tasks_by_dependencies(tasks)
        logger.info(f"Task grouping complete, total {len(task_groups)} groups")
        
        for group_idx, task_group in enumerate(task_groups):
            logger.info(f"Executing task {group_idx+1} task groups, Total {len(task_group)}  tasks")
            
            # 并行执行当前groups的Task
            group_results = await self.execute_parallel_tasks(task_group, current_context)
            results.extend(group_results)
            
            # 检查执行
            for task, result in zip(task_group, group_results):
                if result.get('status') != 'SUCCESS':
                    logger.error(f"Task {task.get('name', 'Unknown')} execution failed, stopping task chain")
                    return {
                        "status": "ERROR",
                        "message": f"Task {task.get('name', 'Unknown')} execution failed",
                        "results": results
                    }
                
                # Update上下文
                current_context.update(result)
            
            # 短暂延迟, 避免API速率限制
            await asyncio.sleep(0.5)
        
        # 汇总
        summary = {
            "status": "SUCCESS",
            "message": f"Task chain execution complete, Total执行 {len(tasks)}  tasks",
            "results": results,
            "final_state": self.state.copy(),
            "parallel_execution": True,
            "task_groups": len(task_groups)
        }
        
        logger.info(f"Task chain execution complete: {summary['message']}")
        return summary
    
    async def execute_with_retry(self, task: Dict[str, Any], 
                               max_retries: int = 3, 
                               retry_delay: float = 1.0) -> Dict[str, Any]:
        """
        带重试机制的Task执行
        
        Args:
            task: Task信息
            max_retries: 最大重试次数
            retry_delay: 重试延迟 (s) 
            
        Returns:
            执行
        """
        for attempt in range(max_retries):
            try:
                result = await self.execute_task(task)
                if result.get('status') == 'SUCCESS':
                    return result
                
                logger.warning(f"Task execution failed, attempt {attempt+1} retrying...")
                # 指数退避, 增加随机因素避免重试风暴
                delay = retry_delay * (attempt + 1) + (0.1 * attempt)
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Exception during task execution: {e}")
                # 发生exception时也进行重试
                if attempt < max_retries - 1:
                    logger.warning(f"Exception occurred, attempt {attempt+1} retrying...")
                    delay = retry_delay * (attempt + 1)
                    await asyncio.sleep(delay)
                else:
                    return {
                        "status": "ERROR",
                        "message": f"Exception during task execution: {str(e)}",
                        "detail": str(e)
                    }
        
        logger.error(f"Task execution failed, max retries reached {max_retries}")
        return result
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        GetTask执行历史
        
        Returns:
            Task执行历史
        """
        return self.task_history
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get当前Status
        
        Returns:
            当前Status
        """
        return self.state.copy()
    
    def reset_state(self):
        """
        重置Status
        """
        self.state = {}
        logger.info("Executor state reset")
    
    def clear_history(self):
        """
        清除Task执行历史
        """
        self.task_history = []
        logger.info("Task execution history cleared")