#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Screen capture service
实现屏幕Screenshot, 分析和理解功能
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image
    import base64
    import io
    
    # 检查是否安装了必要的库
    SCREEN_SUPPORT = True
except ImportError:
    logger.warning("Screen capture library not installed, screen capture will be unavailable")
    SCREEN_SUPPORT = False


class ScreenService:
    """
    Screen capture service
    负责屏幕Screenshot, 分析和理解
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        InitializationScreen capture service
        
        参数:
            config: 配置字典
        """
        self.config = config or {}
        self.screen_support = SCREEN_SUPPORT
        
        if self.screen_support:
            logger.info("[OK] Screen capture serviceInitialization successful")
        else:
            logger.warning("[!] Screen capture serviceinitialization failed, missing required library")
    
    async def capture_screen(self, region: Optional[tuple] = None) -> Dict[str, Any]:
        """
        捕获屏幕
        
        参数:
            region: 捕获区域 (x, y, width, height), None 表示整 屏幕
            
        返回:
            屏幕捕获
        """
        if not self.screen_support:
            return {
                "error": "Screen capture library not installed",
                "status": "error"
            }
        
        try:
            logger.info("[screen]  Starting screen capture...")
            
            # 捕获屏幕
            screenshot = pyautogui.screenshot(region=region)
            
            # 转换为RGB格式
            screenshot_rgb = screenshot.convert('RGB')
            
            # 压缩图像
            buffer = io.BytesIO()
            screenshot_rgb.save(buffer, format="JPEG", quality=80)
            screenshot_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Get屏幕信息
            screen_width, screen_height = pyautogui.size()
            
            result = {
                "status": "success",
                "screen_info": {
                    "width": screen_width,
                    "height": screen_height,
                    "region": region
                },
                "screenshot": screenshot_base64,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("[OK] Screen capture complete")
            return result
            
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def analyze_screen_content(self, screenshot_base64: str, llm_service: Any) -> Dict[str, Any]:
        """
        分析屏幕Content
        
        参数:
            screenshot_base64: 屏幕Screenshot的base64编码
            llm_service: LLM服务实例
            
        返回:
            Screen content analysis
        """
        if not self.screen_support:
            return {
                "error": "Screen capture library not installed",
                "status": "error"
            }
        
        try:
            logger.info("[brain] Starting screen content analysis...")
            
            # 准备LLM分析请求
            messages = [
                {
                    "role": "system",
                    "content": "你是一 Screen content analysis专家, 能够根据屏幕Screenshot分析屏幕上的Content, 界面和信息."
                },
                {
                    "role": "user",
                    "content": "请分析以下屏幕Screenshot的Content, 包括界面元素, 文本信息, 正在进行的操作等."
                },
                {
                    "role": "user",
                    "content": f"屏幕Screenshot: <image>{screenshot_base64}</image>"
                }
            ]
            
            # 调用LLM分析
            response = await llm_service.chat_completion(messages)
            analysis = response.choices[0].message.content
            
            result = {
                "status": "success",
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("[OK] Screen content analysis complete")
            return result
            
        except Exception as e:
            logger.error(f"Screen content analysis failed: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def capture_and_analyze(self, llm_service: Any, region: Optional[tuple] = None) -> Dict[str, Any]:
        """
        捕获并分析屏幕
        
        参数:
            llm_service: LLM服务实例
            region: 捕获区域 (x, y, width, height), None 表示整 屏幕
            
        返回:
            屏幕捕获和分析
        """
        # 捕获屏幕
        capture_result = await self.capture_screen(region)
        
        if capture_result.get("status") != "success":
            return capture_result
        
        # 分析屏幕Content
        screenshot_base64 = capture_result.get("screenshot")
        analysis_result = await self.analyze_screen_content(screenshot_base64, llm_service)
        
        if analysis_result.get("status") != "success":
            return analysis_result
        
        # 整合
        result = {
            "status": "success",
            "screen_info": capture_result.get("screen_info"),
            "analysis": analysis_result.get("analysis"),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    async def learn_from_screen(self, llm_service: Any, memory_system: Any, region: Optional[tuple] = None) -> Dict[str, Any]:
        """
        From屏幕中学习
        
        参数:
            llm_service: LLM服务实例
            memory_system:  memories系统实例
            region: 捕获区域 (x, y, width, height), None 表示整 屏幕
            
        返回:
            学习
        """
        # 捕获并分析屏幕
        analysis_result = await self.capture_and_analyze(llm_service, region)
        
        if analysis_result.get("status") != "success":
            return analysis_result
        
        try:
            logger.info("[books] Starting screen learning...")
            
            # 提取屏幕分析
            analysis = analysis_result.get("analysis", "")
            screen_info = analysis_result.get("screen_info", {})
            
            # 存储到 memories系统
            await memory_system.store_experience(
                content=f"Screen content analysis: {analysis}",
                context=f"屏幕信息: {screen_info}",
                importance=0.7,
                tags=['screen', 'learning']
            )
            
            # 提取屏幕中的概念和知识
            await self._extract_concepts_from_screen(analysis, memory_system)
            
            result = {
                "status": "success",
                "message": "Screen learning complete",
                "screen_info": screen_info
            }
            
            logger.info("[OK] Screen learning complete")
            return result
            
        except Exception as e:
            logger.error(f"Screen learning failed: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def _extract_concepts_from_screen(self, analysis: str, memory_system: Any):
        """
        Extracting concepts from screen analysis
        
        参数:
            analysis: 屏幕分析
            memory_system:  memories系统实例
        """
        try:
            # 这里可以使用LLM来Extract concept
            # 暂时简化Processing, 直接存储分析
            logger.info("[search] Extracting concepts from screen analysis...")
            
            # 存储屏幕分析作为语义 memories
            await memory_system.store_concept(
                concept="Screen content analysis",
                description=analysis,
                category="screen",
                tags=['screen', 'analysis']
            )
            
        except Exception as e:
            logger.error(f"Extract concept failed: {e}")
    
    async def shutdown(self):
        """
        Close screen capture service
        """
        logger.info("Close screen capture service")
        # 清理资源
        pass
