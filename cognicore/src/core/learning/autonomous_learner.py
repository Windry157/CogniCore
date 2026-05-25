#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自主学习 module
实现自主资料查找, 学习和自我提高能力
"""

import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..memory.unified_memory import UnifiedMemorySystem
from ..llm.openai_service import OpenAILLM
from .active_inference import ActiveInference
from .free_energy import FreeEnergyMinimizer

logger = logging.getLogger(__name__)


class AutonomousLearner:
    """
    自主学习器
    负责自主查找资料, 学习和自我提高
    """
    
    def __init__(self, memory_system: UnifiedMemorySystem, llm_service: OpenAILLM):
        """
        Initialization自主学习器
        
        参数:
            memory_system: 统一 memories系统
            llm_service: LLM服务
        """
        self.memory_system = memory_system
        self.llm_service = llm_service
        self.learning_topics = []
        self.learning_history = []
        
        # Initialization贝叶斯认知Model
        self.free_energy_minimizer = FreeEnergyMinimizer()
        self.active_inference = ActiveInference()
        
        # 设置可能的学习行动
        self.active_inference.set_possible_actions([
            "search_information",
            "learn_from_data",
            "evaluate_progress",
            "adjust_strategy",
            "extract_concepts",
            "store_memory",
            "analyze_video",
            "analyze_screen",
            "enhance_knowledge"
        ])
    
    async def identify_learning_gaps(self) -> List[str]:
        """
        识别知识 gaps
        
        返回:
            学习主题列表
        """
        logger.info("[search] Identifying knowledge gaps...")
        
        # 分析 memories使用情况
        usage_analysis = self.memory_system.analyze_memory_usage()
        
        # 基于 memories分布识别潜在的知识 gaps
        memory_distribution = usage_analysis['memory_distribution']
        
        # 识别知识 gaps 的策略
        gaps = []
        
        # 检查 memoriestype分布是否均衡
        if memory_distribution['episodic'] > 0.7:
            gaps.append("语义知识")
        if memory_distribution['semantic'] < 0.2:
            gaps.append("概念理解")
        if memory_distribution['knowledge_graph'] < 0.1:
            gaps.append("知识结构")
        
        # 基于最近的交互识别 gaps
        # 这里可以Add更复杂的逻辑, 例如分析用户提问的type
        
        logger.info(f"[clipboard] Knowledge gaps identified: {gaps}")
        return gaps
    
    async def search_for_information(self, topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        自主Search信息
        
        参数:
            topic: Search主题
            max_results: 最大数
            
        返回:
            Search列表
        """
        try:
            logger.info(f"[www] Searching for '{topic}'  information...")
            
            # 使用LLM生成Search查询
            search_query = await self._generate_search_query(topic)
            logger.info(f"[search] Generated search query: {search_query}")
            
            # 1. 首先在本地文件系统中查找相关资料
            local_results = await self._search_local_files(topic, max_results=2)
            logger.info(f"[disk] Local search results: {len(local_results)}  entries")
            
            # 2. 然后尝试上网Search (使用模拟数据, 可扩展为真实Search引擎) 
            web_results = self._search_web(topic, max_results=3)
            logger.info(f"[www] Web search results: {len(web_results)}  entries")
            
            # 合并
            all_results = local_results + web_results
            
            # 按相关性排序
            all_results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            
            logger.info(f"[OK] Search complete, Found {len(all_results)}  entries")
            return all_results[:max_results]
        except Exception as e:
            logger.error(f"Information search failed: {e}")
            #  failed时返回模拟数据
            return [
                {
                    "title": f"关于 {topic} 的资料",
                    "content": f"这是关于 {topic} 的详细信息...",
                    "source": "模拟数据",
                    "relevance": 0.9
                }
            ]

    
    async def _search_local_files(self, topic: str, max_results: int = 2) -> List[Dict[str, Any]]:
        """
        在本地文件系统中Search相关资料
        
        参数:
            topic: Search主题
            max_results: 最大数
            
        返回:
            本地文件Search列表
        """
        logger.info(f"[folder] Searching local files for '{topic}'  data...")
        
        # 这里可以集成file_managerTool来Search本地文件
        # 暂时使用模拟数据
        local_results = [
            {
                "title": f"本地资料: {topic} 指南",
                "content": f"这是本地存储的关于 {topic} 的详细指南...",
                "source": "本地文件系统",
                "relevance": 0.85
            },
            {
                "title": f"本地资料: {topic} 案例分析",
                "content": f"这是本地存储的关于 {topic} 的案例分析...",
                "source": "本地文件系统",
                "relevance": 0.75
            }
        ]
        
        logger.info(f"[OK] Local search complete, Found {len(local_results)}  entries")
        return local_results[:max_results]
    
    def _search_web(self, topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        上网Search相关资料
        
        参数:
            topic: Search主题
            max_results: 最大数
            
        返回:
            Web search results列表
        """
        logger.info(f"[globe] Searching web for '{topic}'  data...")
        
        # 这里可以集成真实的Search引擎API
        # 暂时使用模拟数据
        web_results = [
            {
                "title": f"网络资料: {topic} 基础知识",
                "content": f"这是来自网络的关于 {topic} 的基础知识介绍...",
                "source": "互联网",
                "relevance": 0.9
            },
            {
                "title": f"网络资料: {topic} 高级应用",
                "content": f"这是来自网络的关于 {topic} 的高级应用技巧...",
                "source": "互联网",
                "relevance": 0.8
            },
            {
                "title": f"网络资料: {topic} 最新研究",
                "content": f"这是来自网络的关于 {topic} 的最新研究进展...",
                "source": "互联网",
                "relevance": 0.7
            }
        ]
        
        logger.info(f"[OK] Web search complete, Found {len(web_results)}  entries")
        return web_results[:max_results]
    
    async def _generate_search_query(self, topic: str) -> str:
        """
        生成Search查询
        
        参数:
            topic: 主题
            
        返回:
            Search查询字符串
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一 专业的Search查询生成器, 能够将用户的主题转化为有效的Search查询."
                },
                {
                    "role": "user",
                    "content": f"请For topic '{topic}' 生成一 有效的Search查询, 以便Get最相关的信息."
                }
            ]
            
            response = await self.llm_service.chat_completion(messages)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Search query generation failed: {e}")
            #  failed时返回默认Search查询
            return f"{topic} 最新研究 应用 教程"

    
    async def learn_from_information(self, topic: str, information: List[Dict[str, Any]]):
        """
        FromGet的信息中学习
        
        参数:
            topic: 学习主题
            information: 信息列表
        """
        try:
            logger.info(f"[books] Starting learning about '{topic}'  information...")
            
            for info in information:
                try:
                    # 提取关键信息
                    title = info.get('title', '')
                    content = info.get('content', '')
                    source = info.get('source', '')
                    
                    # 构建学习Content
                    learning_content = f"Title: {title}\nContent: {content}\nSource: {source}"
                    
                    # 存储到 memories系统
                    await self.memory_system.store_experience(
                        content=learning_content,
                        context=f"自主学习: {topic}",
                        importance=0.8,
                        tags=['autonomous_learning', topic]
                    )
                    
                    # Extract concept和实体
                    await self._extract_and_store_concepts(content, topic)
                except Exception as e:
                    logger.error(f"Error processing information: {e}")
                    # 继续Processing下一 items
                    continue
            
            # 记录学习历史
            self.learning_history.append({
                'topic': topic,
                'timestamp': datetime.now().isoformat(),
                'sources': len(information)
            })
            
            logger.info(f"[OK] Learning complete, stored {len(information)}  items")
        except Exception as e:
            logger.error(f"Error during learning: {e}")

    
    async def _extract_and_store_concepts(self, content: str, category: str):
        """
        FromContent中Extract concept并存储
        
        参数:
            content: Content
            category: 类别
        """
        # 使用LLMExtract concept
        messages = [
            {
                "role": "system",
                "content": "你是一 概念提取器, 能够From文本中提取重要的概念和实体."
            },
            {
                "role": "user",
                "content": f"请From以下文本中提取重要的概念和实体, 格式为 '概念: Description':\n\n{content}"
            }
        ]
        
        response = await self.llm_service.chat_completion(messages)
        extracted_content = response.choices[0].message.content
        
        # 解析提取的概念
        lines = extracted_content.strip().split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    concept = parts[0].strip()
                    description = parts[1].strip()
                    if concept and description:
                        await self.memory_system.store_concept(
                            concept=concept,
                            description=description,
                            category=category,
                            tags=['extracted', 'autonomous_learning']
                        )
    
    async def evaluate_learning_progress(self) -> Dict[str, Any]:
        """
        评估学习进度
        
        返回:
            学习进度评估
        """
        logger.info("[chart] Evaluating learning progress...")
        
        # 分析 memories系统中的学习 related memories
        search_results = await self.memory_system.retrieve("autonomous_learning", limit=10)
        
        # 计算学习统计
        learning_memories = []
        for key, results in search_results.items():
            for result in results:
                if isinstance(result, dict) and 'tags' in result:
                    if 'autonomous_learning' in result['tags']:
                        learning_memories.append(result)
        
        # 分析学习主题分布
        topic_distribution = {}
        for memory in learning_memories:
            tags = memory.get('tags', [])
            for tag in tags:
                if tag != 'autonomous_learning' and tag != 'extracted':
                    topic_distribution[tag] = topic_distribution.get(tag, 0) + 1
        
        progress = {
            'total_learning_memories': len(learning_memories),
            'topic_distribution': topic_distribution,
            'learning_history_count': len(self.learning_history),
            'last_learning_session': self.learning_history[-1] if self.learning_history else None
        }
        
        logger.info(f"[OK] Learning progress evaluation complete: {progress}")
        return progress
    
    async def self_improve(self):
        """
        自我提高
        分析学习效果并调整学习策略
        """
        logger.info("[boot] Starting self-improvement...")
        
        # 1. 识别知识 gaps
        gaps = await self.identify_learning_gaps()
        
        # 2. 使用主动推理选择最佳学习行动
        for gap in gaps:
            # 构建学习上下文
            context = f"学习主题: {gap}"
            
            # 构建感官输入和内部Model
            sensory_input = np.array([1.0])  # 简化的感官输入
            model = np.array([0.5])  # 简化的内部Model
            
            # 使用主动推理选择最佳行动
            best_action = self.active_inference.select_action(sensory_input, model, context)
            logger.info(f"[target] For topic '{gap}' selecting action: {best_action}")
            
            # 执行选择的行动
            if best_action == "search_information":
                # Search相关信息
                search_results = await self.search_for_information(gap)
                
                # From信息中学习
                await self.learn_from_information(gap, search_results)
            elif best_action == "extract_concepts":
                # Extract concept
                # 这里可以AddFrom memories中Extract concept的逻辑
                pass
            elif best_action == "store_memory":
                # 存储 memories
                # 这里可以Add memories存储的逻辑
                pass
            elif best_action == "analyze_video":
                # 分析视频
                # 这里可以Add视频分析的逻辑
                pass
            elif best_action == "analyze_screen":
                # 分析屏幕
                # 这里可以Add屏幕分析的逻辑
                pass
            elif best_action == "enhance_knowledge":
                # 增强知识
                # 这里可以Add知识增强的逻辑
                pass
        
        # 3. 评估学习效果
        progress = await self.evaluate_learning_progress()
        
        # 4. 调整学习策略
        self._adjust_learning_strategy(progress)
        
        logger.info("[OK] Self-improvement complete")
        return progress
    
    def _adjust_learning_strategy(self, progress: Dict[str, Any]):
        """
        调整学习策略
        
        参数:
            progress: 学习进度
        """
        # 基于学习进度调整策略
        # 这里可以实现更复杂的策略调整逻辑
        logger.info("[target] Adjusting learning strategy...")
        
        # 例如: 如果某 主题的学习 memories较少, 增加该主题的学习权重
        topic_distribution = progress.get('topic_distribution', {})
        if topic_distribution:
            least_learned_topic = min(topic_distribution, key=topic_distribution.get)
            logger.info(f"[pin] Topics needing more learning identified: {least_learned_topic}")
    
    async def learn_from_customer_interaction(self, user_input: str, assistant_response: str, context: str = None):
        """
        From客户交流中学习
        
        参数:
            user_input: 用户输入
            assistant_response: 助手Response
            context: 上下文
        """
        logger.info("[chat] Learning from client interaction...")
        
        # 1. 存储交互 memories
        await self.memory_system.learn_from_interaction(user_input, assistant_response, context)
        
        # 2. 分析交互Content, 提取有价值的信息
        await self._extract_value_from_interaction(user_input, assistant_response, context)
        
        # 3. 识别可能的知识 gaps
        gaps = await self.identify_learning_gaps()
        
        # 4. 如果Identified gaps, 进行针对性学习
        for gap in gaps:
            # Search相关信息
            search_results = await self.search_for_information(gap)
            
            # From信息中学习
            await self.learn_from_information(gap, search_results)
        
        logger.info("[OK] Learning from client interaction complete")
        
        return {
            'status': 'success',
            'gaps_identified': gaps,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _extract_value_from_interaction(self, user_input: str, assistant_response: str, context: str = None):
        """
        From用户交互中提取有价值的信息
        
        参数:
            user_input: 用户输入
            assistant_response: 助手Response
            context: 上下文
        """
        logger.info("[search] Extracting valuable info from interactions...")
        
        # 使用LLM分析交互Content, 提取有价值的信息
        messages = [
            {
                "role": "system",
                "content": "你是一 信息提取器, 能够From用户与助手的对话中提取有价值的信息, 概念和实体."
            },
            {
                "role": "user",
                "content": f"请From以下对话中提取有价值的信息, 概念和实体, 格式为 'type: Content':\n\n用户: {user_input}\n助手: {assistant_response}"
            }
        ]
        
        response = await self.llm_service.chat_completion(messages)
        extracted_content = response.choices[0].message.content
        
        # 解析提取的信息
        lines = extracted_content.strip().split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    info_type = parts[0].strip()
                    info_content = parts[1].strip()
                    if info_type and info_content:
                        # 根据信息type存储到不同的 memories系统
                        if info_type in ['概念', '实体', '知识']:
                            # 尝试Extract concept和Description
                            if ':' in info_content:
                                concept_parts = info_content.split(':', 1)
                                if len(concept_parts) == 2:
                                    concept = concept_parts[0].strip()
                                    description = concept_parts[1].strip()
                                    await self.memory_system.store_concept(
                                        concept=concept,
                                        description=description,
                                        category='interaction',
                                        tags=['extracted', 'interaction']
                                    )
                        elif info_type in [' experiences', '事件', '经历']:
                            # 存储为情景 memories
                            await self.memory_system.store_experience(
                                content=info_content,
                                context=context,
                                importance=0.7,
                                tags=['extracted', 'interaction']
                            )
        
        logger.info("[OK] Info extraction from interactions complete")
    
    async def learn_from_video(self, video_path: str):
        """
        From视频中学习
        
        参数:
            video_path: 视频文件路径
            
        返回:
            学习
        """
        logger.info(f"[video] Starting video learning: {video_path}")
        
        # 检查Video processing service是否可用
        video_service = None
        if hasattr(self, 'video_service'):
            video_service = self.video_service
        elif hasattr(self.memory_system, 'video_service'):
            video_service = self.memory_system.video_service
        
        if not video_service:
            # 尝试From外部Get视频服务
            try:
                from src.services.video.video_service import VideoService
                video_service = VideoService()
            except Exception as e:
                logger.error(f"Video processing service unavailable: {e}")
                return {"error": "Video processing service unavailable"}
        
        # From视频中学习
        try:
            result = await video_service.learn_from_video(
                video_path=video_path,
                llm_service=self.llm_service,
                memory_system=self.memory_system
            )
            
            logger.info("[OK] Video learning complete")
            return result
        except Exception as e:
            logger.error(f"Video learning failed: {e}")
            return {"error": str(e)}
    
    async def learn_from_screen(self, region: tuple = None):
        """
        From屏幕中学习
        
        参数:
            region: 捕获区域 (x, y, width, height), None 表示整 屏幕
            
        返回:
            学习
        """
        logger.info("[screen]  Starting screen learning...")
        
        # 检查Screen capture service是否可用
        screen_service = None
        if hasattr(self, 'screen_service'):
            screen_service = self.screen_service
        elif hasattr(self.memory_system, 'screen_service'):
            screen_service = self.memory_system.screen_service
        
        if not screen_service:
            # 尝试From外部Get屏幕服务
            try:
                from src.services.screen.screen_service import ScreenService
                screen_service = ScreenService()
            except Exception as e:
                logger.error(f"Screen capture service unavailable: {e}")
                return {"error": "Screen capture service unavailable"}
        
        # From屏幕中学习
        try:
            result = await screen_service.learn_from_screen(
                llm_service=self.llm_service,
                memory_system=self.memory_system,
                region=region
            )
            
            logger.info("[OK] Screen learning complete")
            return result
        except Exception as e:
            logger.error(f"Screen learning failed: {e}")
            return {"error": str(e)}
    
    async def run_autonomous_learning_cycle(self):
        """
        运行完整的自主学习周期
        """
        try:
            logger.info("[refresh] Starting autonomous learning cycle...")
            
            # 1. 自我提高
            progress = await self.self_improve()
            
            # 2. 执行 memories系统的自主学习
            memory_learning_result = await self.memory_system.autonomous_learning()
            
            # 3. 整合
            combined_result = {
                'self_improvement': progress,
                'memory_learning': memory_learning_result,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("[OK] Autonomous learning cycle complete")
            return combined_result
        except Exception as e:
            logger.error(f"Autonomous learning cycle failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

