#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量检索优化 module
为RAG系统提供高质量的向量检索功能
"""

from typing import List, Dict, Optional
import numpy as np
from src.core.memory.memory_vector import VectorMemory
from .reranker import Reranker


class VectorRetriever:
    """向量检索器"""
    
    def __init__(self, vector_memory: VectorMemory, 
                 reranker: Optional[Reranker] = None, 
                 top_k: int = 5, 
                 score_threshold: float = 0.0):
        """
        Initialization向量检索器
        
        参数:
            vector_memory: 向量 memories实例
            reranker:  reranker实例
            top_k: 返回数量
            score_threshold: Score阈值
        """
        self.vector_memory = vector_memory
        self.reranker = reranker
        self.top_k = top_k
        self.score_threshold = score_threshold
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        检索 relevant documents
        
        参数:
            query: 查询文本
            top_k: 返回数量
            
        返回:
            检索列表
        """
        if top_k is None:
            top_k = self.top_k
        
        # From向量 memories中检索
        results = self.vector_memory.search(query, top_k=top_k * 2)  # Get更多用于重排序
        
        # 过滤低Score
        filtered_results = [r for r in results if r.get("similarity", 0) >= self.score_threshold]
        
        # 如果有 reranker, 进行重排序
        if self.reranker and filtered_results:
            # 提取文档Content
            documents = [r["content"] for r in filtered_results]
            # 重排序
            reranked = self.reranker.rank(query, documents)
            # 重建
            reranked_results = []
            for item in reranked:
                original_result = filtered_results[item["index"]]
                reranked_results.append({
                    **original_result,
                    "rerank_score": item["score"],
                    "rank": len(reranked_results) + 1
                })
            return reranked_results[:top_k]
        
        # 为AddRank
        for i, result in enumerate(filtered_results):
            result["rank"] = i + 1
        
        return filtered_results[:top_k]
    
    def retrieve_with_context(self, query: str, context: str = "", top_k: Optional[int] = None) -> List[Dict]:
        """
        带上下文的检索
        
        参数:
            query: 查询文本
            context: 上下文文本
            top_k: 返回数量
            
        返回:
            检索列表
        """
        # groups合查询和上下文
        enhanced_query = f"{context} {query}" if context else query
        return self.retrieve(enhanced_query, top_k)
    
    def batch_retrieve(self, queries: List[str], top_k: Optional[int] = None) -> List[List[Dict]]:
        """
        批量检索
        
        参数:
            queries: 查询列表
            top_k: 返回数量
            
        返回:
            检索列表
        """
        results = []
        for query in queries:
            results.append(self.retrieve(query, top_k))
        return results
    
    def optimize_retrieval_params(self, test_queries: List[str], relevant_docs: List[List[str]]) -> Dict:
        """
        优化检索参数
        
        参数:
            test_queries: Test查询列表
            relevant_docs: 每 查询的 relevant documents列表
            
        返回:
            Optimized parameters
        """
        best_params = {
            "top_k": self.top_k,
            "score_threshold": self.score_threshold,
            "best_score": 0
        }
        
        # Test不同的参数groups合
        top_k_values = [3, 5, 10, 15]
        threshold_values = [0.0, 0.1, 0.2, 0.3]
        
        for top_k in top_k_values:
            for threshold in threshold_values:
                self.top_k = top_k
                self.score_threshold = threshold
                
                # 评估性能
                score = self.evaluate(test_queries, relevant_docs)
                
                if score > best_params["best_score"]:
                    best_params.update({
                        "top_k": top_k,
                        "score_threshold": threshold,
                        "best_score": score
                    })
        
        # 恢复最佳参数
        self.top_k = best_params["top_k"]
        self.score_threshold = best_params["score_threshold"]
        
        return best_params
    
    def evaluate(self, test_queries: List[str], relevant_docs: List[List[str]]) -> float:
        """
        评估检索性能
        
        参数:
            test_queries: Test查询列表
            relevant_docs: 每 查询的 relevant documents列表
            
        返回:
            平均F1分数
        """
        if len(test_queries) != len(relevant_docs):
            raise ValueError("Test查询和 relevant documents列表Length不匹配")
        
        f1_scores = []
        
        for query, relevant in zip(test_queries, relevant_docs):
            results = self.retrieve(query)
            retrieved_docs = [r["content"] for r in results]
            
            # 计算精确率和召回率
            true_positives = len(set(retrieved_docs) & set(relevant))
            precision = true_positives / len(retrieved_docs) if retrieved_docs else 0
            recall = true_positives / len(relevant) if relevant else 0
            
            # 计算F1分数
            if precision + recall > 0:
                f1 = 2 * (precision * recall) / (precision + recall)
            else:
                f1 = 0
            
            f1_scores.append(f1)
        
        return sum(f1_scores) / len(f1_scores) if f1_scores else 0
    
    def get_retrieval_statistics(self, queries: List[str]) -> Dict:
        """
        Get检索Statistics
        
        参数:
            queries: 查询列表
            
        返回:
            Statistics
        """
        total_results = 0
        total_score = 0
        retrieval_times = []
        
        for query in queries:
            import time
            start_time = time.time()
            results = self.retrieve(query)
            end_time = time.time()
            
            retrieval_times.append(end_time - start_time)
            total_results += len(results)
            if results:
                total_score += sum(r.get("similarity", 0) for r in results)
        
        if queries:
            return {
                "average_results_per_query": total_results / len(queries),
                "average_score": total_score / total_results if total_results > 0 else 0,
                "average_retrieval_time": sum(retrieval_times) / len(retrieval_times),
                "total_queries": len(queries)
            }
        else:
            return {
                "average_results_per_query": 0,
                "average_score": 0,
                "average_retrieval_time": 0,
                "total_queries": 0
            }


class HybridRetriever:
    """混合检索器"""
    
    def __init__(self, vector_retriever: VectorRetriever, 
                 keyword_retriever: Optional[Reranker] = None, 
                 vector_weight: float = 0.7):
        """
        Initialization混合检索器
        
        参数:
            vector_retriever: 向量检索器
            keyword_retriever: 关键词检索器 (如BM25) 
            vector_weight: 向量检索的权重
        """
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.vector_weight = vector_weight
        self.keyword_weight = 1.0 - vector_weight
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        混合检索
        
        参数:
            query: 查询文本
            top_k: 返回数量
            
        返回:
            检索列表
        """
        # 向量检索
        vector_results = self.vector_retriever.retrieve(query, top_k=top_k * 2)
        
        # 关键词检索
        if self.keyword_retriever:
            # Get所有文档
            all_docs = [r["content"] for r in vector_results]
            keyword_results = self.keyword_retriever.rank(query, all_docs)
            
            # 构建文档Score映射
            vector_scores = {r["content"]: r.get("similarity", 0) for r in vector_results}
            keyword_scores = {r["content"]: r["score"] for r in keyword_results}
            
            # 归一化Score
            if vector_scores:
                max_vector = max(vector_scores.values())
                min_vector = min(vector_scores.values())
                if max_vector > min_vector:
                    vector_scores = {k: (v - min_vector) / (max_vector - min_vector) for k, v in vector_scores.items()}
                else:
                    vector_scores = {k: 0.5 for k in vector_scores}
            
            if keyword_scores:
                max_keyword = max(keyword_scores.values())
                min_keyword = min(keyword_scores.values())
                if max_keyword > min_keyword:
                    keyword_scores = {k: (v - min_keyword) / (max_keyword - min_keyword) for k, v in keyword_scores.items()}
                else:
                    keyword_scores = {k: 0.5 for k in keyword_scores}
            
            # 计算Hybrid score
            hybrid_scores = {}
            for doc in set(vector_scores.keys()) | set(keyword_scores.keys()):
                vector_score = vector_scores.get(doc, 0)
                keyword_score = keyword_scores.get(doc, 0)
                hybrid_scores[doc] = vector_score * self.vector_weight + keyword_score * self.keyword_weight
            
            # 排序
            sorted_docs = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
            
            # 构建
            results = []
            for doc, score in sorted_docs:
                # Found原始
                original = next((r for r in vector_results if r["content"] == doc), None)
                if original:
                    result = original.copy()
                    result["hybrid_score"] = score
                    result["rank"] = len(results) + 1
                    results.append(result)
            
            return results
        else:
            # 如果没有关键词检索器, 直接返回Vector retrieval results
            return vector_results[:top_k]


if __name__ == "__main__":
    # Test vector retrieval器
    from .reranker import BM25Reranker
    
    # Initialization向量 memories
    vector_memory = VectorMemory(model_name="ollama:nomic-embed-text", vector_db_file="test_vector_retriever.json")
    
    # AddTest数据
    test_docs = [
        "学习效率的提高需要合理的时间管理和专Register度训练.",
        "提高学习效率的方法包括制定学习计划, 保持良好的作息时间.",
        "学习效率是指单位时间内的学习成果, 受到多种因素的影响.",
        "如何提高工作效率?可以通过Task分解和时间管理来实现.",
        "学习效率的提高需要科学的学习方法和良好的学习环境."
    ]
    
    for doc in test_docs:
        vector_memory.add_memory(doc, metadata={"source": "test"})
    
    # Initialization reranker
    bm25_reranker = BM25Reranker()
    
    # Initialization向量检索器
    vector_retriever = VectorRetriever(
        vector_memory=vector_memory,
        reranker=bm25_reranker,
        top_k=3,
        score_threshold=0.0
    )
    
    # Test检索
    test_query = "如何提高学习效率"
    results = vector_retriever.retrieve(test_query)
    
    print("=== Vector retrieval results ===")
    for result in results:
        print(f"Rank: {result['rank']}")
        print(f"Content: {result['content']}")
        print(f"Similarity: {result.get('similarity', 0):.4f}")
        if "rerank_score" in result:
            print(f"Rerank score: {result['rerank_score']:.4f}")
        print()
    
    # Test hybrid retrieval器
    hybrid_retriever = HybridRetriever(
        vector_retriever=vector_retriever,
        keyword_retriever=bm25_reranker,
        vector_weight=0.7
    )
    
    hybrid_results = hybrid_retriever.retrieve(test_query)
    
    print("=== Hybrid retrieval results ===")
    for result in hybrid_results:
        print(f"Rank: {result['rank']}")
        print(f"Content: {result['content']}")
        print(f"Hybrid score: {result.get('hybrid_score', 0):.4f}")
        print()
    
    # Test评估
    test_queries = ["如何提高学习效率", "工作效率"]
    relevant_docs = [
        ["学习效率的提高需要合理的时间管理和专Register度训练.", "提高学习效率的方法包括制定学习计划, 保持良好的作息时间."],
        ["如何提高工作效率?可以通过Task分解和时间管理来实现."]
    ]
    
    score = vector_retriever.evaluate(test_queries, relevant_docs)
    print(f"Evaluation score: {score:.4f}")
    
    # Test参数优化
    optimized_params = vector_retriever.optimize_retrieval_params(test_queries, relevant_docs)
    print(f"Optimized parameters: {optimized_params}")
