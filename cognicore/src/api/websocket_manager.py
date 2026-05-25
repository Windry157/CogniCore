#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocketConnect管理 module
"""

import asyncio
import time
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocketConnect管理器"""
    
    def __init__(self):
        # 存储活动的WebSocketConnect
        self.active_connections: Dict[str, Set[asyncio.Queue]] = {}
        # 用于配置变化通知的队列
        self.config_notification_queue = asyncio.Queue()
        # Start配置通知Processor
        self._start_config_notification_handler()
    
    def connect(self, client_id: str, queue: asyncio.Queue):
        """Add新的WebSocketConnect"""
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(queue)
        logger.info(f"WebSocket connection added: {client_id}")
    
    def disconnect(self, client_id: str, queue: asyncio.Queue):
        """移除WebSocketConnect"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(queue)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
            logger.info(f"WebSocket connection removed: {client_id}")
    
    async def send_message(self, client_id: str, message: dict):
        """向特定客户端Send message"""
        if client_id in self.active_connections:
            for queue in self.active_connections[client_id]:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.error(f"Message send failed: {e}")
    
    async def broadcast(self, message: dict):
        """向所有客户端广播消息"""
        for client_id, queues in self.active_connections.items():
            for queue in queues:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.error(f"Broadcast failed: {e}")
    
    async def notify_config_change(self, config_changes: dict):
        """通知配置变化"""
        await self.config_notification_queue.put(config_changes)
    
    async def _start_config_notification_handler(self):
        """Start配置通知Processor"""
        async def handle_config_notifications():
            while True:
                try:
                    config_changes = await self.config_notification_queue.get()
                    # 构建通知消息
                    message = {
                        "type": "config_change",
                        "data": config_changes,
                        "timestamp": time.time()
                    }
                    # 广播给所有客户端
                    await self.broadcast(message)
                    self.config_notification_queue.task_done()
                except Exception as e:
                    logger.error(f"Configuration notification failed: {e}")
        
        # StartProcessing协程
        asyncio.create_task(handle_config_notifications())

# Create全局WebSocket管理器实例
websocket_manager = WebSocketManager()