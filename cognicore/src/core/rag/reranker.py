#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重排序Model module
为RAG系统提供文档重排序功能
"""

from typing import List, Dict, Optional
import numpy as np


class Reranker:
    """ reranker基类"""
    
    def rank(self, query: str, documents: List[str]) -> List[Dict]:
        """
        对文档进行重排序
        
        参数:
            query: 查询文本
            documents: 文档列表
            
        返回:
            带Score的文档列表
        """
        raise NotImplementedError


class BM25Reranker(Reranker):
    """BM25 reranker"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        InitializationBM25 reranker
        
        参数:
            k1: BM25参数
            b: BM25参数
        """
        self.k1 = k1
        self.b = b
        self.doc_freqs = {}
        self.doc_lengths = []
        self.avg_doc_length = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        import re
        return re.findall(r'\w+', text.lower())
    
    def fit(self, documents: List[str]):
        """
        训练BM25Model
        
        参数:
            documents: 文档列表
        """
        # 计算文档频率和文档Length
        total_terms = 0
        
        for doc in documents:
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))
            total_terms += len(tokens)
            
            # 计算词频
            for token in set(tokens):
                if token not in self.doc_freqs:
                    self.doc_freqs[token] = 0
                self.doc_freqs[token] += 1
        
        # 计算平均文档Length
        if documents:
            self.avg_doc_length = total_terms / len(documents)
    
    def rank(self, query: str, documents: List[str]) -> List[Dict]:
        """
        使用BM25对文档进行重排序
        
        参数:
            query: 查询文本
            documents: 文档列表
            
        返回:
            带Score的文档列表
        """
        if not documents:
            return []
        
        # 如果还没有训练, 先训练
        if not self.doc_freqs:
            self.fit(documents)
        
        scores = []
        query_tokens = self._tokenize(query)
        
        for i, doc in enumerate(documents):
            score = 0
            doc_tokens = self._tokenize(doc)
            doc_length = len(doc_tokens)
            
            # 计算词频
            doc_term_freq = {}
            for token in doc_tokens:
                if token not in doc_term_freq:
                    doc_term_freq[token] = 0
                doc_term_freq[token] += 1
            
            # 计算BM25Score
            for token in query_tokens:
                if token not in self.doc_freqs:
                    continue
                
                tf = doc_term_freq.get(token, 0)
                idf = np.log((len(documents) - self.doc_freqs[token] + 0.5) / (self.doc_freqs[token] + 0.5) + 1)
                
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                
                score += idf * (numerator / denominator)
            
            scores.append({
                "content": doc,
                "score": score,
                "index": i
            })
        
        # 按Score排序
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores


class CrossEncoderReranker(Reranker):
    """Cross-encoder reranker"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        InitializationCross-encoder reranker
        
        参数:
            model_name: ModelName
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """LoadModel"""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        except ImportError:
            print("[!]  Missing transformers library, cannot use CrossEncoderReranker")
    
    def rank(self, query: str, documents: List[str]) -> List[Dict]:
        """
        使用交叉编码器对文档进行重排序
        
        参数:
            query: 查询文本
            documents: 文档列表
            
        返回:
            带Score的文档列表
        """
        if not documents:
            return []
        
        if self.model is None:
            # 如果ModelLoad failed, 返回原始顺序
            return [{
                "content": doc,
                "score": 0.0,
                "index": i
            } for i, doc in enumerate(documents)]
        
        # 准备输入
        inputs = self.tokenizer(
            [[query, doc] for doc in documents],
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        
        # 计算Score
        outputs = self.model(**inputs)
        scores = outputs.logits.squeeze().tolist()
        
        # 构建
        results = []
        for i, (doc, score) in enumerate(zip(documents, scores)):
            results.append({
                "content": doc,
                "score": score,
                "index": i
            })
        
        # 按Score排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results


class LinearCombinationReranker(Reranker):
    """线性groups合 reranker"""
    
    def __init__(self, rerankers: List[Reranker], weights: List[float]):
        """
        Initialization线性groups合 reranker
        
        参数:
            rerankers:  reranker列表
            weights: 权重列表
        """
        self.rerankers = rerankers
        self.weights = weights
    
    def rank(self, query: str, documents: List[str]) -> List[Dict]:
        """
        使用线性groups合对文档进行重排序
        
        参数:
            query: 查询文本
            documents: 文档列表
            
        返回:
            带Score的文档列表
        """
        if not documents:
            return []
        
        # Get每  reranker的Score
        all_scores = []
        for reranker in self.rerankers:
            scores = reranker.rank(query, documents)
            # 归一化Score
            score_values = [s["score"] for s in scores]
            if score_values:
                min_score = min(score_values)
                max_score = max(score_values)
                if max_score > min_score:
                    normalized_scores = [(s - min_score) / (max_score - min_score) for s in score_values]
                else:
                    normalized_scores = [0.5 for _ in score_values]
            else:
                normalized_scores = [0.5 for _ in documents]
            all_scores.append(normalized_scores)
        
        # 计算加权Score
        combined_scores = []
        for i in range(len(documents)):
            score = 0
            for j, weights in enumerate(self.weights):
                score += all_scores[j][i] * weights
            combined_scores.append({
                "content": documents[i],
                "score": score,
                "index": i
            })
        
        # 按Score排序
        combined_scores.sort(key=lambda x: x["score"], reverse=True)
        return combined_scores


class RerankerFactory:
    """ reranker工厂"""
    
    @staticmethod
    def create_reranker(name: str, **kwargs) -> Reranker:
        """
        Create reranker
        
        参数:
            name:  rerankerName
            **kwargs: 额外参数
            
        返回:
             reranker实例
        """
        if name == "bm25":
            return BM25Reranker(**kwargs)
        elif name == "cross-encoder":
            return CrossEncoderReranker(**kwargs)
        elif name == "linear":
            return LinearCombinationReranker(**kwargs)
        else:
            raise ValueError(f"未知的 rerankertype: {name}")


if __name__ == "__main__":
    # Test reranker
    test_query = "如何提高学习效率"
    test_documents = [
        "学习效率的提高需要合理的时间管理和专Register度训练.",
        "提高学习效率的方法包括制定学习计划, 保持良好的作息时间.",
        "学习效率是指单位时间内的学习成果, 受到多种因素的影响.",
        "如何提高工作效率?可以通过Task分解和时间管理来实现.",
        "学习效率的提高需要科学的学习方法和良好的学习环境."
    ]
    
    print("=== TestBM25 reranker ===")
    bm25_reranker = BM25Reranker()
    bm25_results = bm25_reranker.rank(test_query, test_documents)
    for i, result in enumerate(bm25_results):
        print(f"Rank {i+1}: Score {result['score']:.4f}")
        print(f"Content: {result['content']}")
        print()
    
    print("=== TestCross-encoder reranker ===")
    try:
        cross_encoder_reranker = CrossEncoderReranker()
        cross_encoder_results = cross_encoder_reranker.rank(test_query, test_documents)
        for i, result in enumerate(cross_encoder_results):
            print(f"Rank {i+1}: Score {result['score']:.4f}")
            print(f"Content: {result['content']}")
            print()
    except Exception as e:
        print(f"Cross-encoder test failed: {e}")
    
    print("=== Test linear combination reranker ===")
    linear_reranker = LinearCombinationReranker(
        rerankers=[bm25_reranker],
        weights=[1.0]
    )
    linear_results = linear_reranker.rank(test_query, test_documents)
    for i, result in enumerate(linear_results):
        print(f"Rank {i+1}: Score {result['score']:.4f}")
        print(f"Content: {result['content']}")
        print()
