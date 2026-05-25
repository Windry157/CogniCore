#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态处理模块
专为U盘便携项目优化，提供降级模式
"""

from .rag_service import MultimodalRAGService, get_multimodal_rag_service

# 尝试导入并创建处理器，但如果失败则提供降级模式
try:
    from .processor import MultimodalProcessor
    multimodal_processor = None
    
    def get_multimodal_processor():
        """获取多模态处理器，安全加载"""
        global multimodal_processor
        if multimodal_processor is None:
            try:
                multimodal_processor = MultimodalProcessor()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"加载完整多模态处理器失败，使用降级模式: {e}")
                multimodal_processor = _get_fallback_processor()
        return multimodal_processor
    
    def _get_fallback_processor():
        """获取降级的简单多模态处理器"""
        class FallbackProcessor:
            """简单的降级多模态处理器"""
            def process_text(self, text: str):
                """简单处理文本，返回占位嵌入"""
                return None
            def process_image(self, path: str):
                """简单处理图像，返回None"""
                return None
            def process_audio(self, path: str):
                """简单处理音频，返回None"""
                return None, None
        return FallbackProcessor()
        
except ImportError:
    # 降级模式
    class MultimodalProcessor:
        """简单的降级多模态处理器"""
        def process_text(self, text: str):
            return None
        def process_image(self, path: str):
            return None
        def process_audio(self, path: str):
            return None, None
    
    def get_multimodal_processor():
        return MultimodalProcessor()


__all__ = [
    "MultimodalRAGService",
    "get_multimodal_rag_service",
    "MultimodalProcessor",
    "get_multimodal_processor",
]
