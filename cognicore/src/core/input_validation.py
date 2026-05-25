#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入验证中间件
使用 Pydantic 实现严格的输入验证
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, field_validator
from typing import Dict, Any, Optional, List, Union
import json
import logging

logger = logging.getLogger(__name__)

# ==================== 基础验证Model ====================

class ChatRequest(BaseModel):
    """聊天请求验证Model"""
    session_id: str
    message: str
    model: Optional[str] = None
    images: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    
    @field_validator('session_id')
    def session_id_must_not_be_empty(cls, v):
        if not v or not str(v).strip():
            raise ValueError('session_id 不能为空')
        return v
    
    @field_validator('message')
    def message_must_not_be_empty(cls, v):
        if not v or not str(v).strip():
            raise ValueError('message 不能为空')
        if len(str(v)) > 10000:
            raise ValueError('message Length不能超过10000字符')
        return v
    
    @field_validator('model')
    def model_must_be_valid(cls, v):
        if v and not isinstance(v, str):
            raise ValueError('model 必须是字符串')
        return v

class ModelRequest(BaseModel):
    """Model请求验证Model"""
    model_id: str
    
    @field_validator('model_id')
    def model_id_must_not_be_empty(cls, v):
        if not v or not str(v).strip():
            raise ValueError('model_id 不能为空')
        return v

class TaskRequest(BaseModel):
    """Task请求验证Model"""
    task_id: Optional[str] = None
    task_type: str
    params: Optional[Dict[str, Any]] = None
    priority: Optional[int] = 5
    
    @field_validator('task_type')
    def task_type_must_be_valid(cls, v):
        valid_types = ['chat', 'tool', 'learning', 'evolution']
        if v not in valid_types:
            raise ValueError(f'task_type 必须是 {valid_types} 之一')
        return v
    
    @field_validator('priority')
    def priority_must_be_valid(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError('priority 必须在 1-10 之间')
        return v

class EvolutionRequest(BaseModel):
    """进化请求验证Model"""
    focus_area: Optional[str] = None
    
    @field_validator('focus_area')
    def focus_area_must_be_valid(cls, v):
        valid_areas = ['memory', 'knowledge', 'learning', None]
        if v not in valid_areas:
            raise ValueError(f'focus_area 必须是 {[a for a in valid_areas if a]} 之一或为空')
        return v

# ==================== 验证函数 ====================

def validate_chat_request(data: Dict[str, Any]) -> ChatRequest:
    """
    验证聊天请求
    
    参数:
        data: 请求数据
    
    返回:
        验证后的 ChatRequest 对象
    
    抛出:
        HTTPException: validation failed时
    """
    try:
        return ChatRequest(**data)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = '.'.join(str(p) for p in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "输入validation failed", "details": errors}
        )

def validate_model_request(data: Dict[str, Any]) -> ModelRequest:
    """
    验证Model请求
    
    参数:
        data: 请求数据
    
    返回:
        验证后的 ModelRequest 对象
    
    抛出:
        HTTPException: validation failed时
    """
    try:
        return ModelRequest(**data)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = '.'.join(str(p) for p in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "输入validation failed", "details": errors}
        )

def validate_task_request(data: Dict[str, Any]) -> TaskRequest:
    """
    验证Task请求
    
    参数:
        data: 请求数据
    
    返回:
        验证后的 TaskRequest 对象
    
    抛出:
        HTTPException: validation failed时
    """
    try:
        return TaskRequest(**data)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = '.'.join(str(p) for p in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "输入validation failed", "details": errors}
        )

# ==================== 通用验证中间件 ====================

async def validate_request(request: Request, validators: Dict[str, callable]) -> Dict[str, Any]:
    """
    通用请求验证中间件
    
    参数:
        request: FastAPI 请求对象
        validators: 验证器字典, key为请求type, value为验证函数
    
    返回:
        验证后的请求数据
    
    抛出:
        HTTPException: validation failed时
    """
    try:
        content_type = request.headers.get('content-type', '')
        
        if content_type.startswith('application/json'):
            try:
                data = await request.json()
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "请求体不是有效的JSON"}
                )
        elif content_type.startswith('application/x-www-form-urlencoded'):
            data = await request.form()
            data = dict(data)
        else:
            data = {}
        
        # 验证数据type
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "请求体必须是对象type"}
            )
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request validation exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"请求Processing failed: {str(e)}"}
        )

# ==================== 安全检查 ====================

def sanitize_input(input_str: str) -> str:
    """
    清理输入, 防止Register入攻击
    
    参数:
        input_str: 输入字符串
    
    返回:
        清理后的字符串
    """
    if not input_str:
        return input_str
    
    # 移除潜在危险字符
    dangerous_patterns = [
        (r'<script[^>]*>.*?</script>', ''),
        (r'javascript:', ''),
        (r'on\w+\s*=', ''),
    ]
    
    import re
    result = str(input_str)
    for pattern, replacement in dangerous_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result

def validate_file_path(path: str) -> str:
    """
    验证文件路径安全性
    
    参数:
        path: 文件路径
    
    返回:
        验证后的路径
    
    抛出:
        HTTPException: 路径不安全时
    """
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "路径不能为空"}
        )
    
    # 防止路径遍历攻击 (跨平台) 
    dangerous_patterns = ['..', '/etc/', '/usr/', '/var/', '~', 'Windows\\System32', 'WINNT']
    import platform
    if platform.system() == "Windows":
        dangerous_patterns += ['C:\\Windows', 'C:\\Program Files', 'C:\\boot']
    for pattern in dangerous_patterns:
        if pattern in path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "路径包含非法字符"}
            )
    
    return path

# ==================== Response格式化 ====================

def format_error_response(error: Exception, status_code: int = 400) -> JSONResponse:
    """
    格式化ErrorResponse
    
    参数:
        error: exception对象
        status_code: HTTPStatus code
    
    返回:
        JSONResponse对象
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        }
    )

# Add datetime 导入
from datetime import datetime