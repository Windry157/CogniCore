#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG (检索增强生成) 服务 module
"""

from typing import List, Dict, Any, Optional
import logging

from src.core.vector_store import get_vector_store, DocumentChunker
from src.core.llm import LLMFactory
from src.core.config import config

logger = logging.getLogger(__name__)


class RAGService:
    """
     RAG service 类
    """
    
    def __init__(self, llm_service=None, vector_store=None):
        """
        Initialization RAG service 
        
        Args:
            llm_service: LLM服务实例
            vector_store: 向量存储实例
        """
        self.llm_service = llm_service or LLMFactory.create_service("ollama")
        self.vector_store = vector_store or get_vector_store()
        self.chunker = DocumentChunker()
        
        logger.info(" RAG service initialization complete")
    
    def add_knowledge(self, documents: List[Dict[str, Any]]):
        """
        Add知识到向量存储
        
        Args:
            documents: 文档列表
        """
        if not documents:
            return
        
        # 分Chunk并Add到向量存储
        all_chunks = []
        for doc in documents:
            chunks = self.chunker.chunk_document(
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {})
            )
            all_chunks.extend(chunks)
        
        if all_chunks:
            self.vector_store.add_documents(all_chunks)
            logger.info(f"added  {len(all_chunks)}  document chunks to knowledge base")
    
    def retrieve_relevant_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        检索与查询相关的文档
        
        Args:
            query: 查询文本
            k: 返回的文档数量
            
        Returns:
             relevant documents列表
        """
        results = self.vector_store.search(query, k=k)
        logger.info(f"For query  '{query}'  retrieved  {len(results)}   relevant documents")
        return results
    
    def generate_answer(self, query: str, context: Optional[Dict[str, Any]] = None, k: int = 5) -> Dict[str, Any]:
        """
        生成基于检索的Answer
        
        Args:
            query: 用户查询
            context: 上下文信息
            k: 检索的文档数量
            
        Returns:
            Answer
        """
        # 检索 relevant documents
        relevant_docs = self.retrieve_relevant_documents(query, k=k)
        
        # 构建上下文
        context_docs = "\n\n".join([
            f"[文档 {i+1}]\n{doc['content']}"
            for i, doc in enumerate(relevant_docs)
        ])
        
        # 构建提示词
        prompt = f"""你是一 智能助手, 根据提供的上下文信息Answer用户的问题.

上下文信息: 
{context_docs}

用户问题: 
{query}

请基于上下文信息Answer用户的问题, 不要Add上下文之外的信息.如果上下文信息不足以Answer问题, 请明确说明."""
        
        # 调用LLMGenerate answer
        try:
            response = self.llm_service.generate(prompt)
            
            return {
                "status": "SUCCESS",
                "answer": response,
                "relevant_documents": relevant_docs,
                "context_used": context_docs
            }
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "status": "ERROR",
                "error": str(e),
                "relevant_documents": relevant_docs
            }
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        Getknowledge baseStatistics
        
        Returns:
            Statistics
        """
        return self.vector_store.get_collection_stats()
    
    def clear_knowledge(self):
        """
        Clearknowledge base
        """
        self.vector_store.clear_collection()
        logger.info("knowledge basecleared")


class RAGEnhancedLLM:
    """
    RAG增强的LLM服务
    """
    
    def __init__(self, rag_service: RAGService):
        """
        InitializationRAG增强的LLM服务
        
        Args:
            rag_service:  RAG service 实例
        """
        self.rag_service = rag_service
        self.llm_service = rag_service.llm_service
    
    def chat(self, messages: List[Dict[str, Any]], use_rag: bool = True) -> str:
        """
        聊天功能, 可选是否使用RAG
        
        Args:
            messages: 消息列表
            use_rag: 是否使用RAG
            
        Returns:
            Answer
        """
        if not use_rag:
            return self.llm_service.chat(messages)
        
        # 提取用户最新的问题
        user_message = messages[-1] if messages else {"content": ""}
        query = user_message.get("content", "")
        
        # 使用RAGGenerate answer
        result = self.rag_service.generate_answer(query)
        
        if result.get("status") == "SUCCESS":
            return result.get("answer", "")
        else:
            # 如果RAG failed, Falling back to 普通LLM
            return self.llm_service.chat(messages)
    
    def generate(self, prompt: str, use_rag: bool = True) -> str:
        """
        生 successful能, 可选是否使用RAG
        
        Args:
            prompt: 提示词
            use_rag: 是否使用RAG
            
        Returns:
            生成的文本
        """
        if not use_rag:
            return self.llm_service.generate(prompt)
        
        # 使用RAGGenerate answer
        result = self.rag_service.generate_answer(prompt)
        
        if result.get("status") == "SUCCESS":
            return result.get("answer", "")
        else:
            # 如果RAG failed, Falling back to 普通LLM
            return self.llm_service.generate(prompt)


# 全局 RAG service 实例
rag_service = None


def get_rag_service() -> RAGService:
    """
    Get RAG service 实例
    
    Returns:
         RAG service 实例
    """
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service


def reset_rag_service():
    """
    重置 RAG service 
    """
    global rag_service
    rag_service = None