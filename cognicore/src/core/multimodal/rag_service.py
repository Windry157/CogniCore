#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multimodal RAG service
用于Processing跨模态检索和生成
"""

import logging
from typing import Dict, Any, List, Optional

from src.core.llm import LLMFactory
from src.core.multimodal.processor import get_multimodal_processor
from src.core.vector_store.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class MultimodalRAGService:
    """
    Multimodal RAG service
    Processing跨模态检索和生成
    """
    
    def __init__(self):
        """
        InitializationMultimodal RAG service
        """
        self.multimodal_processor = get_multimodal_processor()
        self.vector_store = get_vector_store()
        self.llm_service = LLMFactory.create_service("ollama")
        
        logger.info("Multimodal RAG serviceinitialization complete")
    
    def generate_answer(self, query: str, context: Optional[Dict[str, Any]] = None, k: int = 5) -> Dict[str, Any]:
        """
        生成Multimodal增强的Answer
        
        Args:
            query: 查询文本
            context: 上下文信息
            k: 检索数量
            
        Returns:
            包含Answer和Source的字典
        """
        try:
            # 生成查询嵌入
            query_embedding = self.multimodal_processor.process_text(query)
            if query_embedding is None:
                return {
                    "status": "ERROR",
                    "message": "查询Processing failed"
                }
            
            # 检索 relevant documents
            results = self.vector_store.search_by_embedding(
                query_embedding.tolist() if hasattr(query_embedding, "tolist") else query_embedding,
                k=k
            )
            
            # 构建上下文
            context_text = "\n".join([result["content"] for result in results])
            
            # Generate answer
            prompt = f"基于以下上下文Answer问题: \n\n{context_text}\n\n问题: {query}"
            answer = self.llm_service.generate(prompt)
            
            return {
                "status": "SUCCESS",
                "answer": answer,
                "sources": [result["id"] for result in results],
                "retrieved_docs": results
            }
        except Exception as e:
            logger.error(f"Multimodal RAG generation failed: {e}")
            return {
                "status": "ERROR",
                "message": str(e)
            }
    
    def add_knowledge(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        AddMultimodal知识到knowledge base
        
        Args:
            documents: 文档列表, 每 文档包含id, type, path/content, metadata
            
        Returns:
            Add
        """
        try:
            success_count = 0
            failure_count = 0
            
            for document in documents:
                if self.multimodal_processor.add_multimodal_document(document):
                    success_count += 1
                else:
                    failure_count += 1
            
            return {
                "status": "SUCCESS",
                "message": f" successfulAdd {success_count}  文档,  failed {failure_count}  ",
                "success_count": success_count,
                "failure_count": failure_count
            }
        except Exception as e:
            logger.error(f"Add multimodal knowledge failed: {e}")
            return {
                "status": "ERROR",
                "message": str(e)
            }
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        Getknowledge baseStatistics
        
        Returns:
            Statistics
        """
        try:
            stats = self.vector_store.get_collection_stats()
            return {
                "status": "SUCCESS",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Getknowledge baseStatistics failed: {e}")
            return {
                "status": "ERROR",
                "message": str(e)
            }
    
    def clear_knowledge(self) -> Dict[str, Any]:
        """
        Clearknowledge base
        
        Returns:
            Clear
        """
        try:
            self.vector_store.clear_collection()
            return {
                "status": "SUCCESS",
                "message": "knowledge basecleared"
            }
        except Exception as e:
            logger.error(f"Knowledge base clear failed: {e}")
            return {
                "status": "ERROR",
                "message": str(e)
            }


# 全局Multimodal RAG service实例
multimodal_rag_service = None


def get_multimodal_rag_service() -> MultimodalRAGService:
    """
    GetMultimodal RAG service实例
    
    Returns:
        MultimodalRAGService实例
    """
    global multimodal_rag_service
    if multimodal_rag_service is None:
        multimodal_rag_service = MultimodalRAGService()
    return multimodal_rag_service


def reset_multimodal_rag_service():
    """
    重置Multimodal RAG service
    """
    global multimodal_rag_service
    multimodal_rag_service = None
