#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM服务工厂
用于Create不同type的LLM服务实例
"""

from typing import Dict, Any, Optional
import logging

from .llm_service import LLMService
from .ollama_service import OllamaService

logger = logging.getLogger(__name__)


class LLMFactory:
    """LLM服务工厂"""
    
    @staticmethod
    def create_service(service_type: str, **kwargs) -> Optional[LLMService]:
        """
        CreateLLM服务实例
        
        Args:
            service_type: 服务type, 如 "ollama", "openai", "huggingface" 等
            **kwargs: 服务Initialization参数
            
        Returns:
            LLM服务实例
        """
        if service_type == "ollama":
            return LLMFactory._create_ollama_service(**kwargs)
        elif service_type == "openai":
            return LLMFactory._create_openai_service(**kwargs)
        elif service_type == "huggingface":
            return LLMFactory._create_huggingface_service(**kwargs)
        else:
            logger.error(f"Unsupported LLM service type: {service_type}")
            return None
    
    @staticmethod
    def _create_ollama_service(**kwargs) -> OllamaService:
        """
        CreateOllama服务实例
        
        Args:
            **kwargs: 服务Initialization参数
            
        Returns:
            OllamaService实例
        """
        base_url = kwargs.get("base_url", "http://localhost:11434")
        model = kwargs.get("model", "llama3")
        timeout = kwargs.get("timeout", 30)
        
        service = OllamaService(
            base_url=base_url,
            model=model,
            timeout=timeout
        )
        
        # TestConnect
        if not service.test_connection():
            logger.warning("Ollama service connection test failed, may need to start Ollama")
        
        return service
    
    @staticmethod
    def _create_openai_service(**kwargs) -> Optional[LLMService]:
        """
        CreateOpenAI服务实例
        
        Args:
            **kwargs: 服务Initialization参数
            
        Returns:
            OpenAI服务实例
        """
        try:
            from .openai_service import OpenAIService
            api_key = kwargs.get("api_key")
            model = kwargs.get("model", "gpt-3.5-turbo")
            
            if not api_key:
                logger.error("OpenAI service requires API key")
                return None
            
            return OpenAIService(api_key=api_key, model=model)
        except ImportError:
            logger.error("OpenAI service implementation not found")
            return None
    
    @staticmethod
    def _create_huggingface_service(**kwargs) -> Optional[LLMService]:
        """
        CreateHuggingFace服务实例
        
        Args:
            **kwargs: 服务Initialization参数
            
        Returns:
            HuggingFace服务实例
        """
        try:
            from .huggingface_service import HuggingFaceService
            model_name = kwargs.get("model", "gpt2")
            return HuggingFaceService(model_name=model_name)
        except ImportError:
            logger.error("HuggingFace service implementation not found")
            return None
    
    @staticmethod
    def list_available_services() -> Dict[str, Dict[str, Any]]:
        """
        List可用的LLM服务
        
        Returns:
            服务列表
        """
        services = {
            "ollama": {
                "name": "Ollama",
                "description": "本地开源LLM服务",
                "status": "可用",
                "required_params": ["model"]
            },
            "openai": {
                "name": "OpenAI",
                "description": "OpenAI API服务",
                "status": "需要API密钥",
                "required_params": ["api_key", "model"]
            },
            "huggingface": {
                "name": "HuggingFace",
                "description": "HuggingFace本地Model",
                "status": "需要Model",
                "required_params": ["model"]
            }
        }
        
        return services
    
    @staticmethod
    def test_service(service: LLMService) -> Dict[str, Any]:
        """
        TestLLM服务
        
        Args:
            service: LLM服务实例
            
        Returns:
            Test
        """
        try:
            # Test聊天功能
            test_messages = [
                {"role": "system", "content": "你是一 助手"},
                {"role": "user", "content": "你好, Test消息"}
            ]
            chat_response = service.chat(test_messages)
            
            # Test生 successful能
            test_prompt = "Test生 successful能"
            generate_response = service.generate(test_prompt)
            
            # Test嵌入功能
            test_text = "Test嵌入功能"
            embed_response = service.embed(test_text)
            
            # TestModel信息
            model_info = service.get_model_info()
            
            return {
                "status": "success",
                "chat_test": bool(chat_response),
                "generate_test": bool(generate_response),
                "embed_test": len(embed_response) > 0,
                "model_info": model_info
            }
        except Exception as e:
            logger.error(f"LLM service test failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


class LLMRouter:
    """
    LLM路由器, 根据Task特性选择合适的LLM服务
    """
    
    def __init__(self):
        """
        InitializationLLM路由器
        """
        self.services = {}
        self.service_configs = {
            "ollama": {
                "type": "ollama",
                "models": {
                    "llama3": {"complexity": 0.7, "speed": 0.8, "cost": 0.1},
                    "mistral": {"complexity": 0.6, "speed": 0.9, "cost": 0.1},
                    "gemma": {"complexity": 0.5, "speed": 0.95, "cost": 0.1}
                }
            },
            "openai": {
                "type": "openai",
                "models": {
                    "gpt-4": {"complexity": 0.9, "speed": 0.6, "cost": 0.9},
                    "gpt-3.5-turbo": {"complexity": 0.7, "speed": 0.8, "cost": 0.4}
                }
            }
        }
        
    def register_service(self, service_type: str, service: LLMService):
        """
        Registering LLM service
        
        Args:
            service_type: 服务type
            service: LLM服务实例
        """
        self.services[service_type] = service
        logger.info(f"Registering LLM service: {service_type}")
    
    def analyze_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Analyzing task特性
        
        Args:
            task: TaskDescription
            context: 上下文信息
            
        Returns:
            Task特性分析
        """
        # 简单的Task分析逻辑, 实际项目中可以使用更复杂的NLP技术
        complexity = 0.5  # 默认复杂度
        
        # 基于TaskLength和Content分析复杂度
        task_length = len(task)
        if task_length > 500:
            complexity += 0.2
        elif task_length < 100:
            complexity -= 0.2
        
        # 基于关键词分析复杂度
        complex_keywords = ["分析", "推理", "解决", "优化", "设计", "开发", "实现"]
        for keyword in complex_keywords:
            if keyword in task:
                complexity += 0.1
        
        # 确保复杂度在0-1之间
        complexity = max(0.1, min(1.0, complexity))
        
        return {
            "complexity": complexity,
            "urgency": 0.5,  # 默认紧急度
            "cost_sensitivity": 0.5  # 默认成本敏感度
        }
    
    def select_service(self, task: str, context: Dict[str, Any] = None) -> Optional[LLMService]:
        """
        根据Task特性选择合适的LLM服务
        
        Args:
            task: TaskDescription
            context: 上下文信息
            
        Returns:
            选择的LLM服务实例
        """
        # Analyzing task特性
        task_features = self.analyze_task(task, context)
        
        # 计算每 models的Score
        best_score = -1
        best_service = None
        
        for service_type, config in self.service_configs.items():
            if service_type not in self.services:
                continue
            
            for model_name, model_config in config["models"].items():
                # 计算Score
                score = (
                    model_config["complexity"] * task_features["complexity"] +
                    model_config["speed"] * task_features["urgency"] +
                    (1 - model_config["cost"]) * task_features["cost_sensitivity"]
                )
                
                if score > best_score:
                    best_score = score
                    # Update服务的Model
                    service = self.services[service_type]
                    if hasattr(service, "model"):
                        service.model = model_name
                    best_service = service
        
        if best_service:
            logger.info(f"Selecting LLM service for task: {best_service.__class__.__name__}")
        else:
            logger.warning("No LLM service available")
        
        return best_service
    
    def get_service(self, service_type: str) -> Optional[LLMService]:
        """
        Get指定type的LLM服务
        
        Args:
            service_type: 服务type
            
        Returns:
            LLM服务实例
        """
        return self.services.get(service_type)
    
    def list_services(self) -> Dict[str, Any]:
        """
        List所有可用的LLM服务
        
        Returns:
            服务列表
        """
        return {
            service_type: {
                "class": service.__class__.__name__,
                "model": getattr(service, "model", "unknown")
            }
            for service_type, service in self.services.items()
        }


# 全局LLM路由器实例
llm_router = LLMRouter()


def get_llm_router() -> LLMRouter:
    """
    GetLLM路由器实例
    
    Returns:
        LLMRouter实例
    """
    return llm_router