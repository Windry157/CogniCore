#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket service module
用于实现实时消息传递
"""

import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocketConnect管理器
    """
    
    def __init__(self):
        """
        InitializationConnect管理器
        """
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """
        ConnectWebSocket
        
        Args:
            websocket: WebSocketConnect
        """
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established, Current connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """
        DisconnectWebSocketConnect
        
        Args:
            websocket: WebSocketConnect
        """
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket connection disconnected, Current connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        广播消息给所有Connect
        
        Args:
            message: 消息Content
        """
        async with self.lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Message send failed: {e}")
                await self.disconnect(connection)
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send message
        
        Args:
            message: 消息Content
            websocket: WebSocketConnect
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Send message failed: {e}")
            await self.disconnect(websocket)
    
    def get_connections_count(self) -> int:
        """
        GetCurrent connections
        
        Returns:
            Connect数
        """
        return len(self.active_connections)


class WebSocketService:
    """
    WebSocket service
    """
    
    def __init__(self):
        """
        InitializationWebSocket service
        """
        self.manager = ConnectionManager()
        self.heartbeat_interval = 30  # 心跳间隔 (s) 
        self.heartbeat_tasks = {}  # 存储每 Connect的心跳Task
        logger.info("WebSocket service initialization complete")
    
    async def _heartbeat_task(self, websocket: WebSocket):
        """
        心跳Task - 定期发送ping消息检测ConnectStatus
        
        Args:
            websocket: WebSocketConnect
        """
        while True:
            try:
                await websocket.send_json({"type": "PING", "timestamp": asyncio.get_event_loop().time()})
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.debug(f"Heartbeat send failed, Connectmay be disconnected: {e}")
                break
    
    async def handle_websocket(self, websocket: WebSocket):
        """
        ProcessingWebSocketConnect
        
        Args:
            websocket: WebSocketConnect
        """
        await self.manager.connect(websocket)
        
        # Start心跳Task
        heartbeat_task = asyncio.create_task(self._heartbeat_task(websocket))
        self.heartbeat_tasks[id(websocket)] = heartbeat_task
        
        try:
            while True:
                # 接收客户端消息, 设置超时
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=self.heartbeat_interval * 2)
                except asyncio.TimeoutError:
                    # 超时未Message received, 检查ConnectStatus
                    logger.warning("WebSocket receive timeout")
                    continue
                
                try:
                    message = json.loads(data)
                    logger.debug(f"Message received: {message}")
                    
                    # Process message
                    await self.handle_message(message, websocket)
                except json.JSONDecodeError:
                    logger.error("Message format error")
                    await self.manager.send_personal_message(
                        {"type": "ERROR", "message": "Message format error"}, 
                        websocket
                    )
        except WebSocketDisconnect:
            logger.info("WebSocket client actively disconnected")
        except Exception as e:
            logger.error(f"WebSocketProcessingError: {e}")
        finally:
            # 取消心跳Task
            heartbeat_task.cancel()
            if id(websocket) in self.heartbeat_tasks:
                del self.heartbeat_tasks[id(websocket)]
            await self.manager.disconnect(websocket)
    
    async def handle_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Process message
        
        Args:
            message: 消息Content
            websocket: WebSocketConnect
        """
        message_type = message.get("type")
        
        if message_type == "PING":
            # Processing心跳
            await self.manager.send_personal_message(
                {"type": "PONG"}, 
                websocket
            )
        elif message_type == "SUBSCRIBE":
            # Processing订阅
            topic = message.get("topic")
            logger.info(f"Client subscribed to topic: {topic}")
            await self.manager.send_personal_message(
                {"type": "SUBSCRIBED", "topic": topic}, 
                websocket
            )
        else:
            # 未知消息type
            await self.manager.send_personal_message(
                {"type": "ERROR", "message": "未知消息type"}, 
                websocket
            )
    
    async def send_task_update(self, task_id: str, status: str, data: Dict[str, Any]):
        """
        发送TaskUpdate
        
        Args:
            task_id: TaskID
            status: Task status
            data: Update数据
        """
        message = {
            "type": "TASK_UPDATE",
            "task_id": task_id,
            "status": status,
            "data": data
        }
        await self.manager.broadcast(message)
    
    async def send_agent_message(self, agent_name: str, message: str, level: str = "info"):
        """
        发送Agent消息
        
        Args:
            agent_name: AgentName
            message: 消息Content
            level: 消息级别
        """
        message = {
            "type": "AGENT_MESSAGE",
            "agent_name": agent_name,
            "message": message,
            "level": level
        }
        await self.manager.broadcast(message)
    
    async def send_system_message(self, message: str, level: str = "info"):
        """
        发送系统消息
        
        Args:
            message: 消息Content
            level: 消息级别
        """
        message = {
            "type": "SYSTEM_MESSAGE",
            "message": message,
            "level": level
        }
        await self.manager.broadcast(message)


# 全局WebSocket service实例
websocket_service = None


def get_websocket_service() -> WebSocketService:
    """
    GetWebSocket service实例
    
    Returns:
        WebSocketService实例
    """
    global websocket_service
    if websocket_service is None:
        websocket_service = WebSocketService()
    return websocket_service


def reset_websocket_service():
    """
    重置WebSocket service
    """
    global websocket_service
    websocket_service = None
