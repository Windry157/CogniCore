#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multimodal processor
用于Processing图像和音频等Multimodal数据
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple

import torch
from transformers import CLIPProcessor, CLIPModel, WhisperProcessor, WhisperForConditionalGeneration
from PIL import Image

from src.core.config import config

logger = logging.getLogger(__name__)


class MultimodalProcessor:
    """
    Multimodal processor
    Processing图像和音频等Multimodal数据
    """
    
    def __init__(self):
        """
        InitializationMultimodal processor
        """
        self.clip_model = None
        self.clip_processor = None
        self.whisper_model = None
        self.whisper_processor = None
        
        try:
            # LoadCLIPModel
            self._load_clip_model()
            logger.info("CLIPModelloaded")
            
            # LoadWhisperModel
            self._load_whisper_model()
            logger.info("WhisperModelloaded")
        except Exception as e:
            logger.error(f"Multimodal processorinitialization failed: {e}")
            raise
    
    def _load_clip_model(self):
        """
        LoadCLIPModel
        """
        model_name = "openai/clip-vit-base-patch32"
        try:
            self.clip_model = CLIPModel.from_pretrained(model_name)
            self.clip_processor = CLIPProcessor.from_pretrained(model_name)
        except Exception as e:
            logger.error(f"CLIPModelLoad failed: {e}")
            raise
    
    def _load_whisper_model(self):
        """
        LoadWhisperModel
        """
        model_name = "openai/whisper-base"
        try:
            self.whisper_model = WhisperForConditionalGeneration.from_pretrained(model_name)
            self.whisper_processor = WhisperProcessor.from_pretrained(model_name)
        except Exception as e:
            logger.error(f"WhisperModelLoad failed: {e}")
            raise
    
    def process_image(self, image_path: str) -> Optional[torch.Tensor]:
        """
        Processing图像并生成嵌入
        
        Args:
            image_path: 图像路径
            
        Returns:
            图像嵌入向量
        """
        try:
            # Load图像
            image = Image.open(image_path)
            
            # 预Processing图像
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            # 生成嵌入
            with torch.no_grad():
                embeddings = self.clip_model.get_image_features(**inputs)
                
            # 归一化
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
            
            return embeddings.squeeze().numpy()
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return None
    
    def process_audio(self, audio_path: str) -> Tuple[Optional[torch.Tensor], Optional[str]]:
        """
        Processing音频并生成嵌入
        
        Args:
            audio_path: 音频路径
            
        Returns:
            (音频嵌入向量, 转录文本)
        """
        try:
            # Load音频
            from datasets import load_dataset
            audio = load_dataset("audiofolder", data_dir=os.path.dirname(audio_path), split="train")[0]
            
            # 预Processing音频
            inputs = self.whisper_processor(audio["audio"]["array"], sampling_rate=audio["audio"]["sampling_rate"], return_tensors="pt")
            
            # 转录音频
            with torch.no_grad():
                generated_ids = self.whisper_model.generate(**inputs)
                transcription = self.whisper_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # 为转录文本生成嵌入
            text_inputs = self.clip_processor(text=transcription, return_tensors="pt")
            with torch.no_grad():
                embeddings = self.clip_model.get_text_features(**text_inputs)
                
            # 归一化
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
            
            return embeddings.squeeze().numpy(), transcription
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return None, None
    
    def process_text(self, text: str) -> Optional[torch.Tensor]:
        """
        Processing文本并生成嵌入
        
        Args:
            text: 文本
            
        Returns:
            文本嵌入向量
        """
        try:
            # 预Processing文本
            inputs = self.clip_processor(text=text, return_tensors="pt")
            
            # 生成嵌入
            with torch.no_grad():
                embeddings = self.clip_model.get_text_features(**inputs)
                
            # 归一化
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
            
            return embeddings.squeeze().numpy()
        except Exception as e:
            logger.error(f"Text processing failed: {e}")
            return None
    
    def add_multimodal_document(self, document: Dict[str, Any]) -> bool:
        """
        AddMultimodal文档到向量存储
        
        Args:
            document: 文档信息, 包含id, type, path/content, metadata
            
        Returns:
            是否Add successful
        """
        try:
            from src.core.vector_store.vector_store import get_vector_store
            vector_store = get_vector_store()
            
            # 根据文档typeProcessing
            if document.get("type") == "image":
                # Processing图像
                embedding = self.process_image(document["path"])
                if embedding is None:
                    return False
                
                content = f"图像: {os.path.basename(document['path'])}"
            
            elif document.get("type") == "audio":
                # Processing音频
                embedding, transcription = self.process_audio(document["path"])
                if embedding is None:
                    return False
                
                content = f"音频: {os.path.basename(document['path'])}\n转录: {transcription}"
                document["transcription"] = transcription
            
            else:
                # Processing文本
                embedding = self.process_text(document["content"])
                if embedding is None:
                    return False
                
                content = document["content"]
            
            # Add到向量存储
            vector_store.add_document({
                "id": document["id"],
                "content": content,
                "embedding": embedding.tolist() if hasattr(embedding, "tolist") else embedding,
                "metadata": document.get("metadata", {})
            })
            
            return True
        except Exception as e:
            logger.error(f"Multimodal document add failed: {e}")
            return False


# 全局Multimodal processor实例
multimodal_processor = None


def get_multimodal_processor() -> MultimodalProcessor:
    """
    GetMultimodal processor实例
    
    Returns:
        MultimodalProcessor实例
    """
    global multimodal_processor
    if multimodal_processor is None:
        multimodal_processor = MultimodalProcessor()
    return multimodal_processor


def reset_multimodal_processor():
    """
    重置Multimodal processor
    """
    global multimodal_processor
    multimodal_processor = None
