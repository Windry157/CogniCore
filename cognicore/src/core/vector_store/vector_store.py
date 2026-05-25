#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量存储 module
使用ChromaDB实现向量数据库功能
"""

import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging

from src.core.config import config, _get_project_root
from src.core.llm.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class VectorStore:
    """
    向量存储类
    """
    
    def __init__(self, collection_name: str = "knowledge_base"):
        """
        Initialization向量存储
        
        Args:
            collection_name: CollectionName
        """
        project_root = _get_project_root()
        vector_db_path = project_root / config.memory.vector_db_path
        vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # InitializationChromaDB客户端
        self.client = chromadb.Client(
            Settings(
                persist_directory=vector_db_path,
                anonymized_telemetry=False
            )
        )
        
        # Get或CreateCollection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Knowledge base for RAG"}
        )
        
        # Embedding provider initialization
        self.embedding_provider = config.memory.embedding_provider
        self.embedding_model = None
        self.ollama_service = None
        self.embedding_dim = 0
        
        try:
            if self.embedding_provider == "ollama":
                # Using Ollama as embedding provider
                self.ollama_service = OllamaService(model=config.memory.ollama_embedding_model)
                # TestOllamaConnect
                self.ollama_service.test_connection()
                logger.info(f"OllamaConnectTest successful, Model: {config.memory.ollama_embedding_model}")
                # Test嵌入生成
                test_embedding = self.ollama_service.embed("test")
                logger.info(f"Ollama embedding test: {test_embedding[:5]}... (Length: {len(test_embedding)})")
                self.embedding_dim = len(test_embedding)
                logger.info(f"Using Ollama as embedding provider, Model: {config.memory.ollama_embedding_model}")
            else:
                # Using SentenceTransformers as embedding provider
                model_name = config.memory.sentence_transformers_model
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_dim = 384  # all-MiniLM-L6-v2的嵌入维度
                logger.info(f"Using SentenceTransformers as embedding provider, Model: {model_name}")
        except Exception as e:
            logger.warning(f"Embedding provider initialization failed: {e}, will use SentenceTransformers as fallback")
            # Falling back to SentenceTransformers
            model_name = config.memory.sentence_transformers_model
            try:
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_dim = 384
                self.embedding_provider = "sentence-transformers"
                logger.info(f" fell back to SentenceTransformers, Model: {model_name}")
            except Exception as fallback_error:
                logger.error(f"SentenceTransformersInitialization also  failed: {fallback_error}")
                raise
        
        logger.info(f"Vector store initialization complete, Collection: {collection_name}")
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add文档到向量存储
        
        Args:
            documents: 文档列表, 每 文档包含id, content, metadata等字段
        """
        if not documents:
            return
        
        # 提取文档信息
        ids = []
        texts = []
        metadatas = []
        
        for doc in documents:
            ids.append(doc.get("id"))
            texts.append(doc.get("content"))
            metadatas.append(doc.get("metadata", {}))
        
        # 生成嵌入
        embeddings = self._generate_embeddings(texts)
        
        # Add到Collection
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        logger.info(f"added  {len(documents)}  documents to vector store")
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generating text embedding
        
        Args:
            texts: 文本列表
            
        Returns:
            embeddings向量列表
        """
        try:
            if self.embedding_provider == "ollama" and self.ollama_service:
                # 使用Ollama生成嵌入
                embeddings = []
                for i, text in enumerate(texts):
                    logger.info(f"Generating text embedding {i+1}/{len(texts)}: {text[:50]}...")
                    embedding = self.ollama_service.embed(text)
                    logger.info(f"Embedding: {embedding[:5]}... (Length: {len(embedding)})")
                    if not embedding:
                        logger.error(f"Generated embedding is empty: {text[:50]}...")
                    embeddings.append(embedding)
                return embeddings
            elif self.embedding_model:
                # Using SentenceTransformers to generate嵌入
                logger.info(f"Using SentenceTransformers to generate {len(texts)}  embeddings")
                result = self.embedding_model.encode(texts).tolist()
                logger.info(f"SentenceTransformers embedding: {result[0][:5]}... (Length: {len(result[0])})")
                return result
            else:
                logger.error("No available embedding provider")
                raise ValueError("No available embedding provider")
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # 尝试Falling back to SentenceTransformers
            if not self.embedding_model:
                try:
                    model_name = config.memory.sentence_transformers_model
                    self.embedding_model = SentenceTransformer(model_name)
                    self.embedding_provider = "sentence-transformers"
                    logger.info(f"Falling back to SentenceTransformers, Model: {model_name}")
                    result = self.embedding_model.encode(texts).tolist()
                    logger.info(f"SentenceTransformers fallback : {result[0][:5]}... (Length: {len(result[0])})")
                    return result
                except Exception as fallback_error:
                    logger.error(f"SentenceTransformers fallback also failed: {fallback_error}")
                    raise
            raise
    
    def search(self, query: str, k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search相似文档
        
        Args:
            query: 查询文本
            k: 返回的文档数量
            where: 过滤 entries件
            
        Returns:
            相似文档列表
        """
        # 生成查询嵌入
        query_embedding = self._generate_embeddings([query])[0]
        
        # Search
        return self.search_by_embedding(query_embedding, k, where)
    
    def search_by_embedding(self, embedding: List[float], k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        通过嵌入Vector search相似文档
        
        Args:
            embedding: 查询嵌入向量
            k: 返回的文档数量
            where: 过滤 entries件
            
        Returns:
            相似文档列表
        """
        # Search
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where
        )
        
        # 格式化
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        
        return formatted_results
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get单 文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            文档信息
        """
        results = self.collection.get(ids=[doc_id])
        if results["ids"]:
            return {
                "id": results["ids"][0],
                "content": results["documents"][0],
                "metadata": results["metadatas"][0]
            }
        return None
    
    def delete_document(self, doc_id: str):
        """
        Delete document
        
        Args:
            doc_id: 文档ID
        """
        self.collection.delete(ids=[doc_id])
        logger.info(f"Delete document: {doc_id}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        GetCollectionStatistics
        
        Returns:
            Statistics
        """
        return {
            "collection_name": self.collection.name,
            "document_count": self.collection.count()
        }
    
    def clear_collection(self):
        """
        ClearCollection
        """
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"description": "Knowledge base for RAG"}
        )
        logger.info(f"ClearCollection: {self.collection.name}")


class DocumentChunker:
    """
    文档分Chunk器
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialization文档分Chunk器
        
        Args:
            chunk_size: Chunk大小
            chunk_overlap: Chunk重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        将文档分Chunk
        
        Args:
            content: 文档Content
            metadata: 文档元数据
            
        Returns:
            分Chunk后的文档列表
        """
        chunks = []
        start = 0
        doc_id = metadata.get("id") if metadata else None
        
        while start < len(content):
            end = start + self.chunk_size
            chunk = content[start:end]
            
            # 确保切分不会在单词中间
            if end < len(content):
                last_space = chunk.rfind(' ')
                if last_space > 0:
                    end = start + last_space + 1
                    chunk = content[start:end]
            
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata["chunk_id"] = f"{doc_id}_{start}" if doc_id else f"chunk_{start}"
            chunk_metadata["start_pos"] = start
            chunk_metadata["end_pos"] = end
            
            chunks.append({
                "id": chunk_metadata["chunk_id"],
                "content": chunk,
                "metadata": chunk_metadata
            })
            
            start = end - self.chunk_overlap
        
        return chunks


# 全局向量存储实例
vector_store = None


def get_vector_store(collection_name: str = "knowledge_base") -> VectorStore:
    """
    Get向量存储实例
    
    Args:
        collection_name: CollectionName
        
    Returns:
        向量存储实例
    """
    global vector_store
    if vector_store is None:
        vector_store = VectorStore(collection_name)
    return vector_store


def reset_vector_store():
    """
    重置向量存储
    """
    global vector_store
    vector_store = None