#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text processing module
实现文本切片和分Chunk功能, 为RAG系统提供高质量的文本片段
"""

import re
from typing import Any, List, Dict, Tuple, Optional


class TextProcessor:
    """Text processing器 - 实现文本切片和分Chunk"""
    
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200, 
                 min_chunk_size: int = 200):
        """
        InitializationText processing器
        
        参数:
            chunk_size: Chunk大小 (字符数) 
            chunk_overlap: Chunk重叠大小 (字符数) 
            min_chunk_size: 最小Chunk大小 (字符数) 
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def split_by_size(self, text: str) -> List[str]:
        """
        按固定大小分割文本
        
        参数:
            text: 原始文本
            
        返回:
            文本Chunk列表
        """
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            # 确保最后一 chunks不会太短
            if end >= text_length:
                end = text_length
            else:
                # 尝试在句子边界分割
                end = self._find_sentence_boundary(text, start, end)
            
            chunk = text[start:end].strip()
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            if start >= text_length:
                break
        
        return chunks
    
    def split_by_paragraphs(self, text: str) -> List[str]:
        """
        按段落分割文本
        
        参数:
            text: 原始文本
            
        返回:
            文本Chunk列表
        """
        # 分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 如果段落太长, 进一步分割
            if len(paragraph) > self.chunk_size:
                sub_chunks = self.split_by_size(paragraph)
                chunks.extend(sub_chunks)
            else:
                chunks.append(paragraph)
        
        return chunks
    
    def split_by_sentences(self, text: str) -> List[str]:
        """
        按句子分割文本
        
        参数:
            text: 原始文本
            
        返回:
            文本Chunk列表
        """
        # 分割句子
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 检查Add当前句子后是否超过Chunk大小
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                # Save当前Chunk
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk)
                # 开始新Chunk
                current_chunk = sentence
        
        # Add最后一 chunks
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk)
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """
        寻找句子边界
        
        参数:
            text: 文本
            start: 起始位置
            end: 结束位置
            
        返回:
            句子边界位置
        """
        # Fromend位置向前Search句子结束符
        sentence_endings = ['.', '!', '?', '.', '!', '?']
        
        # Search范围: Fromend向前Search一段距离
        search_start = max(start, end - 200)
        
        for i in range(end, search_start, -1):
            if i < len(text) and text[i] in sentence_endings:
                return i + 1
        
        # 如果没有Found句子边界, 返回原始end
        return end
    
    def process_document(self, text: str, method: str = "size") -> List[Dict]:
        """
        Processing document, 返回带元数据的文本Chunk
        
        参数:
            text: 文档文本
            method: 分割方法 (size, paragraphs, sentences)
            
        返回:
            带元数据的文本Chunk列表
        """
        if method == "paragraphs":
            chunks = self.split_by_paragraphs(text)
        elif method == "sentences":
            chunks = self.split_by_sentences(text)
        else:
            chunks = self.split_by_size(text)
        
        # Add元数据
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "id": f"chunk_{i}",
                "content": chunk,
                "length": len(chunk),
                "position": i,
                "method": method
            })
        
        return result
    
    def merge_small_chunks(self, chunks: List[str], threshold: int = 300) -> List[str]:
        """
        合并小Chunk文本
        
        参数:
            chunks: 文本Chunk列表
            threshold: 合并阈值
            
        返回:
            合并后的文本Chunk列表
        """
        merged_chunks = []
        current_chunk = ""
        
        for chunk in chunks:
            if len(current_chunk) + len(chunk) + 1 <= threshold:
                if current_chunk:
                    current_chunk += " " + chunk
                else:
                    current_chunk = chunk
            else:
                if current_chunk:
                    merged_chunks.append(current_chunk)
                current_chunk = chunk
        
        if current_chunk:
            merged_chunks.append(current_chunk)
        
        return merged_chunks
    
    def calculate_chunk_statistics(self, chunks: List[str]) -> Dict[str, Any]:
        """
        计算文本ChunkStatistics
        
        参数:
            chunks: 文本Chunk列表
            
        返回:
            Statistics
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "average_length": 0,
                "min_length": 0,
                "max_length": 0,
                "total_length": 0
            }
        
        lengths = [len(chunk) for chunk in chunks]
        return {
            "total_chunks": len(chunks),
            "average_length": sum(lengths) / len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "total_length": sum(lengths)
        }


if __name__ == "__main__":
    # TestText processing器
    test_text = """This is a  Test文本.它包含多 句子和段落.

这 段落是Round 二段落, 用于Test文本分Chunk功能.

这是Round 三段落, 包含更多的Content.在这里, 我们将Test不同的分Chunk方法, 包括Chunk by size, Chunk by paragraph和Chunk by sentence.每 方法都有其优缺点, 我们需要根据具体的应用场景选择合适的方法."""
    
    processor = TextProcessor()
    
    print("=== Chunk by size ===")
    size_chunks = processor.split_by_size(test_text)
    for i, chunk in enumerate(size_chunks):
        print(f"Chunk {i+1}: {chunk}")
    
    print("\n=== Chunk by paragraph ===")
    paragraph_chunks = processor.split_by_paragraphs(test_text)
    for i, chunk in enumerate(paragraph_chunks):
        print(f"Chunk {i+1}: {chunk}")
    
    print("\n=== Chunk by sentence ===")
    sentence_chunks = processor.split_by_sentences(test_text)
    for i, chunk in enumerate(sentence_chunks):
        print(f"Chunk {i+1}: {chunk}")
    
    print("\n=== Processing document ===")
    document_chunks = processor.process_document(test_text)
    for chunk in document_chunks:
        print(f"ID: {chunk['id']}, Length: {chunk['length']}, Content: {chunk['content']}")
    
    print("\n=== Statistics ===")
    stats = processor.calculate_chunk_statistics(size_chunks)
    print(stats)
