#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由 module
定义所有的RESTful API端点
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import time
import logging
import asyncio

from src.core.agent import AgentCoordinator, MultiLayerAgentSystem
from src.core.agent.orchestration import get_agent_orchestrator
from src.core.agent.initialization import initialize_agents, run_agent
from src.core.llm import LLMFactory
from src.core.memory import UnifiedMemorySystem
from src.core.feedback import get_feedback_manager, FeedbackType
from src.core.user_profile import get_user_profile_service
from src.core.skill import get_skill_manager
from src.core.skill_manager import SkillManager
from src.core.mcp import get_mcp_protocol
from src.core.rag import get_rag_service
from src.core.multimodal.rag_service import get_multimodal_rag_service
from src.core.security import get_guardrail_layer
from src.core.websocket import get_websocket_service
from src.core.config import config
from src.utils.config import load_config
from src.core.cognicore_config import get_cognicore_info

logger = logging.getLogger(__name__)

# Create路由器
router = APIRouter()

# 全局实例
_agent_coordinator = None
_memory_system = None
_feedback_manager = None
_ollama_service = None


def get_ollama_service():
    """
    GetOllama服务单例

    Returns:
        OllamaService实例
    """
    global _ollama_service
    if _ollama_service is None:
        from src.core.llm.ollama_service import OllamaService
        _ollama_service = OllamaService()
    return _ollama_service


def get_agent_coordinator(model: Optional[str] = None):
    """
    GetAgent协调器实例
    
    Args:
        model: ModelName
        
    Returns:
        Agent协调器实例
    """
    # 每次都Create新的实例, 以支持不同的Model
    # CreateLLM服务
    llm_service = LLMFactory.create_service("ollama", model=model or config.llm.ollama_model)
    return AgentCoordinator(llm_service=llm_service)


def get_memory_system():
    """
    Get memories系统实例
    """
    global _memory_system
    if _memory_system is None:
        _memory_system = UnifiedMemorySystem(
            memory_dir=config.memory.memory_dir
        )
    return _memory_system


def get_feedback_manager_instance():
    """
    Get反馈管理器实例
    """
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = get_feedback_manager()
    return _feedback_manager


# 请求Model
class TaskRequest(BaseModel):
    """Task请求Model"""
    session_id: str
    goal: str
    context: Optional[Dict[str, Any]] = None
    agent: Optional[str] = None
    model: Optional[str] = None


class FeedbackRequest(BaseModel):
    """反馈请求Model"""
    user_id: str
    session_id: str
    task_id: Optional[str] = None
    type: str
    content: str
    rating: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryRequest(BaseModel):
    """ memories请求Model"""
    session_id: str
    query: str
    limit: Optional[int] = 5


class MemorySaveRequest(BaseModel):
    """ memoriesSave请求Model"""
    session_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class RAGQueryRequest(BaseModel):
    """RAG查询请求Model"""
    query: str
    k: Optional[int] = 5
    context: Optional[Dict[str, Any]] = None


class RAGAddDocumentRequest(BaseModel):
    """RAGAdd文档请求Model"""
    documents: List[Dict[str, Any]]


class FunctionCallingRequest(BaseModel):
    """Function Calling请求Model"""
    messages: List[Dict[str, str]]
    tools: Optional[List[Dict[str, Any]]] = None


class ToolExecutionRequest(BaseModel):
    """Tool执行请求Model"""
    tool_call: Dict[str, Any]
    tools: List[Dict[str, Any]]


# CogniCoreSystem Info
@router.get("/info")
async def cognicore_info():
    """CogniCoreSystem Info端点"""
    try:
        info = get_cognicore_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 健康检查
@router.get("/health")
async def health_check():
    """健康检查端点 - 全面检查系统Status"""
    import psutil
    from src.core.llm.ollama_service import OllamaService
    
    checks = {
        "service": "CogniCore Assistant API",
        "version": "2.1.0",
        "timestamp": time.time(),
        "status": "ok",
        "checks": {}
    }
    
    # 检查内存系统
    try:
        memory_system = get_memory_system()
        checks["checks"]["memory_system"] = {
            "status": "healthy",
            "message": "内存系统正常"
        }
    except Exception as e:
        checks["checks"]["memory_system"] = {
            "status": "unhealthy",
            "message": f"内存系统exception: {str(e)}"
        }
        checks["status"] = "degraded"
    
    # 检查LLM服务 (使用全局单例避免重复CreateConnect) 
    try:
        ollama_service = get_ollama_service()
        models = await ollama_service.async_list_models()
        checks["checks"]["llm_service"] = {
            "status": "healthy",
            "message": f"LLM服务正常, 可用Model数: {len(models)}"
        }
    except Exception as e:
        checks["checks"]["llm_service"] = {
            "status": "unhealthy",
            "message": f"LLM服务exception: {str(e)}"
        }
        checks["status"] = "degraded"
    
    # 检查Skill系统 (使用全局单例避免重复Initialization) 
    try:
        from src.core.skill_manager import get_skill_manager as get_system_skill_manager
        skill_manager = get_system_skill_manager()
        tools = skill_manager.get_tool_definitions()
        checks["checks"]["skill_system"] = {
            "status": "healthy",
            "message": f"Skill系统正常, alreadyRegistering skill数: {len(tools)}"
        }
    except Exception as e:
        checks["checks"]["skill_system"] = {
            "status": "unhealthy",
            "message": f"Skill系统exception: {str(e)}"
        }
        checks["status"] = "degraded"
    
    # 检查系统资源
    try:
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        checks["checks"]["system_resources"] = {
            "status": "healthy" if all(v < 90 for v in [cpu_usage, memory_usage, disk_usage]) else "warning",
            "message": f"CPU: {cpu_usage}%, 内存: {memory_usage}%, 磁盘: {disk_usage}%"
        }
        
        if any(v > 95 for v in [cpu_usage, memory_usage, disk_usage]):
            checks["status"] = "critical"
    except Exception as e:
        checks["checks"]["system_resources"] = {
            "status": "unknown",
            "message": f"资源检查 failed: {str(e)}"
        }
    
    return checks


# 详细健康检查 (包含告警信息) 
@router.get("/health/detailed")
async def health_check_detailed():
    """详细健康检查 - 包含告警信息和建议"""
    try:
        health = await health_check()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    alerts = []
    
    # 检查告警 entries件
    for check_name, check_result in health["checks"].items():
        if check_result["status"] == "unhealthy":
            alerts.append({
                "level": "CRITICAL",
                "component": check_name,
                "message": check_result["message"],
                "suggestion": _get_suggestion(check_name)
            })
        elif check_result["status"] == "warning":
            alerts.append({
                "level": "WARNING",
                "component": check_name,
                "message": check_result["message"],
                "suggestion": _get_suggestion(check_name)
            })
    
    return {
        **health,
        "alerts": alerts,
        "alert_count": len(alerts),
        "recommendations": _generate_recommendations(health)
    }


def _get_suggestion(component: str) -> str:
    """Getgroups件exception的建议"""
    suggestions = {
        "memory_system": "请检查内存目录权限和磁盘空间, 尝试重启服务",
        "llm_service": "请检查Ollama服务是否正常运行, 确认网络Connect",
        "skill_system": "请检查SkillRegister配置, 确保所有依赖installed",
        "system_resources": "请释放系统资源, 考虑扩展硬件或优化服务配置"
    }
    return suggestions.get(component, "请检查相关日志Get更多信息")


def _generate_recommendations(health: dict) -> list:
    """生成优化建议"""
    recommendations = []
    
    if health["status"] == "critical":
        recommendations.append("系统处于严重Status, 请立即检查告警信息并采取措施")
    elif health["status"] == "degraded":
        recommendations.append("系统部分groups件exception, 建议尽快排查")
    
    # 基于资源使用的建议
    resources = health["checks"].get("system_resources", {})
    if resources.get("status") == "warning":
        recommendations.append("系统资源使用率较高, 建议监控并优化")
    
    return recommendations


# AgentTaskProcessing
@router.post("/agent/task")
async def process_task(request: TaskRequest):
    """
    Processing复杂Task (Agent编排) 
    
    Args:
        request: Task请求
        
    Returns:
        Task execution result
    """
    try:
        # 安全检查
        guardrail = get_guardrail_layer()
        input_check = guardrail.check_input(request.goal)
        if not input_check["safe"]:
            raise HTTPException(status_code=400, detail=f"输入不安全: {input_check['reason']}")
        
        coordinator = get_agent_coordinator()
        result = await coordinator.process_task(request.goal, request.context)
        
        # 安全检查输出
        output_check = guardrail.check_output(str(result))
        if not output_check["safe"]:
            return {
                "status": "ERROR",
                "message": f"输出不安全: {output_check['reason']}",
                "safety_check": output_check
            }
        
        # 伦理检查
        ethics_check = guardrail.check_ethics(request.goal, str(result))
        if not ethics_check["compliant"]:
            return {
                "status": "ERROR",
                "message": f"伦理检查未通过: {ethics_check['violations']}",
                "ethics_check": ethics_check
            }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


#  memories系统接口
@router.get("/memory/statistics")
async def get_memory_statistics():
    """
    Get完整的 memories系统Statistics

    Returns:
         memories系统Statistics
    """
    try:
        memory = get_memory_system()
        stats = memory.get_statistics()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get memory statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/usage")
async def get_memory_usage():
    """
    GetMemory usage analysis

    Returns:
        Memory usage analysis
    """
    try:
        memory = get_memory_system()
        usage = memory.analyze_memory_usage()
        return {
            "status": "success",
            "data": usage
        }
    except Exception as e:
        logger.error(f"Failed to get memory usage analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/entity/{entity_name}")
async def get_entity_info(entity_name: str):
    """
    Get知识图谱实体信息

    Args:
        entity_name: 实体Name

    Returns:
        实体信息
    """
    try:
        memory = get_memory_system()
        entity = memory.get_entity(entity_name)
        return {
            "status": "success",
            "data": entity
        }
    except Exception as e:
        logger.error(f"Failed to get entity info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/clear")
async def clear_all_memory():
    """
    Clear所有 memories (谨慎使用) 

    Returns:
        操作
    """
    try:
        memory = get_memory_system()
        memory.clear_all()
        return {
            "status": "success",
            "message": "All memories cleared"
        }
    except Exception as e:
        logger.error(f"Failed to clear memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/learn")
async def trigger_autonomous_learning():
    """
    触发自主学习

    Returns:
        学习
    """
    try:
        memory = get_memory_system()
        learning_result = await memory.autonomous_learning()
        return {
            "status": "success",
            "data": learning_result
        }
    except Exception as e:
        logger.error(f"Autonomous learning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/search")
async def search_memory(request: MemoryRequest):
    """
    Search memories
    
    Args:
        request: Search请求
        
    Returns:
        Search
    """
    try:
        memory = get_memory_system()
        results = memory.search_memory(request.query, limit=request.limit)
        return {
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/save")
async def save_memory(request: MemorySaveRequest):
    """
    Save memories
    
    Args:
        request: Save请求
        
    Returns:
        Save
    """
    try:
        memory = get_memory_system()
        memory.save_memory(
            session_id=request.session_id,
            content=request.content,
            metadata=request.metadata
        )
        return {
            "status": "success",
            "message": " memoriesSave successful"
        }
    except Exception as e:
        logger.error(f"Memory save failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))





#  RAG service 接口
@router.post("/rag/query")
async def rag_query(request: RAGQueryRequest):
    """
    RAG查询接口
    
    Args:
        request: RAG查询请求
        
    Returns:
        查询
    """
    try:
        # 安全检查
        guardrail = get_guardrail_layer()
        input_check = guardrail.check_input(request.query)
        if not input_check["safe"]:
            raise HTTPException(status_code=400, detail=f"输入不安全: {input_check['reason']}")
        
        rag_service = get_rag_service()
        result = rag_service.generate_answer(
            query=request.query,
            context=request.context,
            k=request.k
        )
        
        # 安全检查输出
        output_check = guardrail.check_output(str(result))
        if not output_check["safe"]:
            return {
                "status": "ERROR",
                "message": f"输出不安全: {output_check['reason']}",
                "safety_check": output_check
            }
        
        # 伦理检查
        ethics_check = guardrail.check_ethics(request.query, str(result))
        if not ethics_check["compliant"]:
            return {
                "status": "ERROR",
                "message": f"伦理检查未通过: {ethics_check['violations']}",
                "ethics_check": ethics_check
            }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAGquery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/add-documents")
async def rag_add_documents(request: RAGAddDocumentRequest):
    """
    Add文档到RAGknowledge base
    
    Args:
        request: Add文档请求
        
    Returns:
        Add
    """
    try:
        rag_service = get_rag_service()
        rag_service.add_knowledge(request.documents)
        return {
            "status": "success",
            "message": f" successfulAdd {len(request.documents)}  文档到knowledge base"
        }
    except Exception as e:
        logger.error(f"Document add failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/stats")
async def rag_stats():
    """
    GetRAGknowledge baseStatistics
    
    Returns:
        Statistics
    """
    try:
        rag_service = get_rag_service()
        stats = rag_service.get_knowledge_stats()
        return stats
    except Exception as e:
        logger.error(f"GetRAGStatistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/clear")
async def rag_clear():
    """
    ClearRAGknowledge base
    
    Returns:
        Clear
    """
    try:
        rag_service = get_rag_service()
        rag_service.clear_knowledge()
        return {
            "status": "success",
            "message": "RAGknowledge basecleared"
        }
    except Exception as e:
        logger.error(f"ClearRAGknowledge base failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Multimodal RAG service接口
@router.post("/multimodal/rag/query")
async def multimodal_rag_query(request: RAGQueryRequest):
    """
    MultimodalRAG查询接口
    
    Args:
        request: RAG查询请求
        
    Returns:
        查询
    """
    try:
        # 安全检查
        guardrail = get_guardrail_layer()
        input_check = guardrail.check_input(request.query)
        if not input_check["safe"]:
            raise HTTPException(status_code=400, detail=f"输入不安全: {input_check['reason']}")
        
        multimodal_rag_service = get_multimodal_rag_service()
        result = multimodal_rag_service.generate_answer(
            query=request.query,
            context=request.context,
            k=request.k
        )
        
        # 安全检查输出
        output_check = guardrail.check_output(str(result))
        if not output_check["safe"]:
            return {
                "status": "ERROR",
                "message": f"输出不安全: {output_check['reason']}",
                "safety_check": output_check
            }
        
        # 伦理检查
        ethics_check = guardrail.check_ethics(request.query, str(result))
        if not ethics_check["compliant"]:
            return {
                "status": "ERROR",
                "message": f"伦理检查未通过: {ethics_check['violations']}",
                "ethics_check": ethics_check
            }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MultimodalRAGquery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multimodal/rag/add-documents")
async def multimodal_rag_add_documents(request: RAGAddDocumentRequest):
    """
    AddMultimodal文档到RAGknowledge base
    
    Args:
        request: Add文档请求
        
    Returns:
        Add
    """
    try:
        multimodal_rag_service = get_multimodal_rag_service()
        result = multimodal_rag_service.add_knowledge(request.documents)
        return result
    except Exception as e:
        logger.error(f"Multimodal document add failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/multimodal/rag/stats")
async def multimodal_rag_stats():
    """
    GetMultimodalRAGknowledge baseStatistics
    
    Returns:
        Statistics
    """
    try:
        multimodal_rag_service = get_multimodal_rag_service()
        stats = multimodal_rag_service.get_knowledge_stats()
        return stats
    except Exception as e:
        logger.error(f"GetMultimodalRAGStatistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multimodal/rag/clear")
async def multimodal_rag_clear():
    """
    ClearMultimodalRAGknowledge base
    
    Returns:
        Clear
    """
    try:
        multimodal_rag_service = get_multimodal_rag_service()
        result = multimodal_rag_service.clear_knowledge()
        return result
    except Exception as e:
        logger.error(f"ClearMultimodalRAGknowledge base failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Function Calling接口
@router.post("/llm/chat-with-tools")
async def chat_with_tools(request: FunctionCallingRequest):
    """
    带Tool调用的聊天接口
    
    Args:
        request: Function Calling请求
        
    Returns:
        聊天, 可能包含Tool调用信息
    """
    try:
        llm_service = LLMFactory.create_service("ollama")
        result = llm_service.chat_with_tools(
            messages=request.messages,
            tools=request.tools or []
        )
        return result
    except Exception as e:
        logger.error(f"Chat with tool calls failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/execute-tool")
async def execute_tool(request: ToolExecutionRequest):
    """
    执行Tool调用
    
    Args:
        request: Tool执行请求
        
    Returns:
        Tool execution result
    """
    try:
        llm_service = LLMFactory.create_service("ollama")
        result = llm_service.execute_tool_call(
            tool_call=request.tool_call,
            tools=request.tools
        )
        return result
    except Exception as e:
        logger.error(f"Tool call execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ReAct模式接口
@router.post("/agent/react")
async def process_with_react(request: TaskRequest):
    """
    使用ReAct模式ProcessingTask
    
    Args:
        request: Task请求
        
    Returns:
        TaskProcessing result
    """
    try:
        # 安全检查
        guardrail = get_guardrail_layer()
        input_check = guardrail.check_input(request.goal)
        if not input_check["safe"]:
            raise HTTPException(status_code=400, detail=f"输入不安全: {input_check['reason']}")
        
        coordinator = get_agent_coordinator(model=request.model)
        result = await coordinator.process_with_react(
            task=request.goal,
            context=request.context
        )
        
        # 安全检查输出
        output_check = guardrail.check_output(str(result))
        if not output_check["safe"]:
            return {
                "status": "ERROR",
                "message": f"输出不安全: {output_check['reason']}",
                "safety_check": output_check,
                "react_history": result.get("react_history", [])
            }
        
        # 伦理检查
        ethics_check = guardrail.check_ethics(request.goal, str(result))
        if not ethics_check["compliant"]:
            return {
                "status": "ERROR",
                "message": f"伦理检查未通过: {ethics_check['violations']}",
                "ethics_check": ethics_check,
                "react_history": result.get("react_history", [])
            }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ReActmode task processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 反馈管理接口
@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    提交用户反馈
    
    Args:
        request: 反馈请求
        
    Returns:
        反馈提交
    """
    try:
        feedback_manager = get_feedback_manager_instance()
        feedback_id = feedback_manager.collect_feedback(
            user_id=request.user_id,
            session_id=request.session_id,
            task_id=request.task_id,
            feedback_type=request.type,
            content=request.content,
            rating=request.rating,
            metadata=request.metadata
        )
        return {
            "status": "success",
            "message": "反馈提交 successful",
            "feedback_id": feedback_id
        }
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{feedback_id}")
async def get_feedback(feedback_id: str):
    """
    Get反馈详情
    
    Args:
        feedback_id: 反馈ID
        
    Returns:
        反馈详情
    """
    try:
        feedback_manager = get_feedback_manager_instance()
        feedback = feedback_manager.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="反馈does not exist")
        return feedback.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feedback details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback")
async def list_feedback(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    task_id: Optional[str] = None
):
    """
    List反馈
    
    Args:
        status: 反馈Status
        user_id: 用户ID
        task_id: TaskID
        
    Returns:
        反馈列表
    """
    try:
        feedback_manager = get_feedback_manager_instance()
        
        if task_id:
            feedbacks = feedback_manager.get_feedback_by_task(task_id)
        elif user_id:
            feedbacks = feedback_manager.get_feedback_by_user(user_id)
        elif status:
            feedbacks = feedback_manager.get_feedback_by_status(status)
        else:
            # Get所有反馈
            feedbacks = list(feedback_manager.feedback_data.values())
        
        return {
            "feedbacks": [f.to_dict() for f in feedbacks],
            "count": len(feedbacks)
        }
    except Exception as e:
        logger.error(f"Failed to list feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/analysis/summary")
async def get_feedback_summary():
    """
    Get反馈摘要
    
    Returns:
        反馈摘要
    """
    try:
        feedback_manager = get_feedback_manager_instance()
        summary = feedback_manager.generate_feedback_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get feedback summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent生态系统接口
@router.get("/agents")
async def list_agents():
    """
    List所有Agent
    
    Returns:
        Agent列表
    """
    try:
        from src.core.agent.profiles import get_all_agent_profiles
        profiles = get_all_agent_profiles()
        agents = [{
            "name": name,
            "role": profile.role,
            "description": profile.description,
            "tools": profile.tools
        } for name, profile in profiles.items()]
        return {
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# LLMModel接口
@router.get("/llm/models")
async def list_llm_models():
    """
    List可用的LLMModel
    
    Returns:
        Model列表
    """
    try:
        # CreateOllama服务实例
        ollama_service = LLMFactory.create_service("ollama")
        # Get model list
        models = await ollama_service.async_list_models()
        return {
            "status": "SUCCESS",
            "models": models
        }
    except Exception as e:
        logger.error(f"ListLLMModel failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent编排接口
@router.post("/agents/initialize")
async def initialize_agent_system():
    """
    InitializationAgent系统
    
    Returns:
        Initialization
    """
    try:
        initialize_agents()
        return {
            "status": "success",
            "message": "Agent系统initialization complete"
        }
    except Exception as e:
        logger.error(f"Agent system initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/run")
async def run_single_agent(agent_name: str, task: str):
    """
    运行单 Agentexecuting task
    
    Args:
        agent_name: AgentName
        task: TaskDescription
        
    Returns:
        执行
    """
    try:
        # 安全检查
        guardrail = get_guardrail_layer()
        input_check = guardrail.check_input(task)
        if not input_check["safe"]:
            raise HTTPException(status_code=400, detail=f"输入不安全: {input_check['reason']}")
        
        result = await run_agent(agent_name, task)
        
        # 安全检查输出
        output_check = guardrail.check_output(str(result))
        if not output_check["safe"]:
            return {
                "status": "ERROR",
                "message": f"输出不安全: {output_check['reason']}",
                "safety_check": output_check
            }
        
        # 伦理检查
        ethics_check = guardrail.check_ethics(task, str(result))
        if not ethics_check["compliant"]:
            return {
                "status": "ERROR",
                "message": f"伦理检查未通过: {ethics_check['violations']}",
                "ethics_check": ethics_check
            }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/orchestrate")
async def orchestrate_agents(task: str):
    """
    多Agent协同工作
    
    Args:
        task: TaskDescription
        
    Returns:
        Processing result
    """
    try:
        # 安全检查
        guardrail = get_guardrail_layer()
        input_check = guardrail.check_input(task)
        if not input_check["safe"]:
            raise HTTPException(status_code=400, detail=f"输入不安全: {input_check['reason']}")
        
        orchestrator = get_agent_orchestrator()
        result = await orchestrator.process_task(task)
        
        # 安全检查输出
        output_check = guardrail.check_output(str(result))
        if not output_check["safe"]:
            return {
                "status": "ERROR",
                "message": f"输出不安全: {output_check['reason']}",
                "safety_check": output_check
            }
        
        # 伦理检查
        ethics_check = guardrail.check_ethics(task, str(result))
        if not ethics_check["compliant"]:
            return {
                "status": "ERROR",
                "message": f"伦理检查未通过: {ethics_check['violations']}",
                "ethics_check": ethics_check
            }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-agent collaboration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """
    GetAgent详情
    
    Args:
        agent_name: AgentName
        
    Returns:
        Agent详情
    """
    try:
        from src.core.agent.profiles import get_agent_profile
        profile = get_agent_profile(agent_name)
        if not profile:
            raise HTTPException(status_code=404, detail="Agentdoes not exist")
        return {
            "name": profile.name,
            "role": profile.role,
            "description": profile.description,
            "system_prompt": profile.system_prompt,
            "tools": profile.tools
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 系统配置接口
@router.get("/config")
async def get_config():
    """
    Get系统配置
    
    Returns:
        系统配置
    """
    try:
        return {
            "llm": {
                "ollama_base_url": config.llm.ollama_base_url,
                "ollama_model": config.llm.ollama_model,
                "ollama_timeout": config.llm.ollama_timeout
            },
            "memory": {
                "memory_dir": config.memory.memory_dir,
                "ltm_enabled": config.memory.ltm_enabled,
                "ltm_max_size": config.memory.ltm_max_size,
                "wm_max_size": config.memory.wm_max_size,
                "stm_max_size": config.memory.stm_max_size,
                "vector_enabled": config.memory.vector_enabled
            },
            "system": {
                "system_name": config.system.system_name,
                "system_version": config.system.system_version,
                "data_dir": config.system.data_dir
            }
        }
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Tool系统接口
@router.get("/tools")
async def list_tools():
    """
    List所有Tool
    
    Returns:
        Tool列表
    """
    try:
        from src.core.tools.registry import get_tool_registry
        registry = get_tool_registry()
        tools = registry.get_tools_description()
        return {
            "tools": tools,
            "count": len(tools)
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """
    GetTool详情

    Args:
        tool_name: ToolName

    Returns:
        Tool详情
    """
    try:
        from src.core.tools.registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail="Tooldoes not exist")
        return tool
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# user profiles接口
@router.get("/user-profile/{user_id}")
async def get_user_profile(user_id: str):
    """
    Getuser profiles

    Args:
        user_id: 用户ID

    Returns:
        user profiles
    """
    try:
        profile_service = get_user_profile_service()
        profile = profile_service.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="user profilesdoes not exist")
        return profile.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-profile/{user_id}")
async def create_or_update_user_profile(user_id: str):
    """
    Create或Updateuser profiles

    Args:
        user_id: 用户ID

    Returns:
        user profiles
    """
    try:
        profile_service = get_user_profile_service()
        profile = profile_service.create_profile(user_id)
        return profile.to_dict()
    except Exception as e:
        logger.error(f"Failed to create user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-profile/{user_id}/summary")
async def get_user_profile_summary(user_id: str):
    """
    Getuser profiles摘要

    Args:
        user_id: 用户ID

    Returns:
        user profiles摘要
    """
    try:
        profile_service = get_user_profile_service()
        summary = profile_service.get_user_summary(user_id)
        return summary
    except Exception as e:
        logger.error(f"Failed to get user profile summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-profile/{user_id}/recall")
async def recall_user_info(user_id: str, query: str):
    """
    召回用户相关信息

    Args:
        user_id: 用户ID
        query: 查询字符串

    Returns:
        召回的信息
    """
    try:
        profile_service = get_user_profile_service()
        result = profile_service.recall_relevant_info(user_id, query)
        return result
    except Exception as e:
        logger.error(f"User info recall failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Skill管理接口
@router.get("/skills")
async def list_skills():
    """
    List所有Skill

    Returns:
        Skill列表
    """
    try:
        skill_manager = get_skill_manager()
        skills = skill_manager.get_all_skills()
        return {
            "skills": [s.to_dict() for s in skills],
            "count": len(skills)
        }
    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/stats")
async def get_skill_stats():
    """
    GetSkillStatistics

    Returns:
        SkillStatistics
    """
    try:
        skill_manager = get_skill_manager()
        stats = skill_manager.get_skill_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get skill statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    """
    GetSkill详情

    Args:
        skill_id: SkillID

    Returns:
        Skill详情
    """
    try:
        skill_manager = get_skill_manager()
        skill = skill_manager.get_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skilldoes not exist")
        return skill.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get skill details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skills")
async def create_skill(
    name: str,
    description: str,
    category: str,
    prompts: Optional[List[str]] = None,
    tools: Optional[List[str]] = None
):
    """
    Creating new skill

    Args:
        name: SkillName
        description: SkillDescription
        category: Skill类别
        prompts: 提示词列表
        tools: Tool列表

    Returns:
        Create的Skill
    """
    try:
        skill_manager = get_skill_manager()
        skill = skill_manager.create_skill(
            name=name,
            description=description,
            category=category,
            prompts=prompts,
            tools=tools
        )
        return skill.to_dict()
    except Exception as e:
        logger.error(f"Failed to create skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# HITL人机协同审批接口
@router.get("/hitl/tasks")
async def get_suspended_tasks():
    """Get所有挂起Waiting审批的Task"""
    try:
        from src.core.sandbox import get_sandbox_security
        sandbox = get_sandbox_security()
        tasks = sandbox.get_suspended_tasks()
        return {
            "status": "success",
            "tasks": tasks,
            "count": len(tasks)
        }
    except Exception as e:
        logger.error(f"Failed to get pending tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hitl/approve/{task_id}")
async def approve_hitl_task(task_id: str):
    """批准挂起的Task"""
    try:
        from src.core.sandbox import get_sandbox_security
        sandbox = get_sandbox_security()
        
        if sandbox.approve_task(task_id):
            return {
                "status": "success",
                "task_id": task_id,
                "message": "Taskalready批准"
            }
        else:
            raise HTTPException(status_code=404, detail="Taskdoes not exist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task approval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hitl/deny/{task_id}")
async def deny_hitl_task(task_id: str):
    """拒绝挂起的Task"""
    try:
        from src.core.sandbox import get_sandbox_security
        sandbox = get_sandbox_security()
        
        if sandbox.deny_task(task_id):
            return {
                "status": "success",
                "task_id": task_id,
                "message": "Taskalready拒绝"
            }
        else:
            raise HTTPException(status_code=404, detail="Taskdoes not exist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task rejection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MCP接口
@router.get("/mcp/tools")
async def list_mcp_tools():
    """
    List所有MCPTool

    Returns:
        MCPTool列表
    """
    try:
        mcp_protocol = get_mcp_protocol()
        tools = list(mcp_protocol.tools.values())
        return {
            "tools": [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in tools],
            "count": len(tools)
        }
    except Exception as e:
        logger.error(f"Failed to list MCP tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/resources")
async def list_mcp_resources():
    """
    List所有MCP资源

    Returns:
        MCP资源列表
    """
    try:
        mcp_protocol = get_mcp_protocol()
        resources = list(mcp_protocol.resources.values())
        return {
            "resources": [{"uri": r.uri, "name": r.name, "description": r.description} for r in resources],
            "count": len(resources)
        }
    except Exception as e:
        logger.error(f"Failed to list MCP resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/prompts")
async def list_mcp_prompts():
    """
    List所有MCP提示词

    Returns:
        MCP提示词列表
    """
    try:
        mcp_protocol = get_mcp_protocol()
        prompts = list(mcp_protocol.prompts.values())
        return {
            "prompts": [{"name": p.name, "description": p.description, "arguments": p.arguments} for p in prompts],
            "count": len(prompts)
        }
    except Exception as e:
        logger.error(f"Failed to list MCP prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket接口
@router.websocket("/ws")
async def websocket_endpoint(websocket):
    """
    WebSocket端点
    用于实时消息传递
    """
    try:
        websocket_service = get_websocket_service()
        await websocket_service.handle_websocket(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
