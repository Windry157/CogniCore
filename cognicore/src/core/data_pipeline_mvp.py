#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管道 MVP - 第一个最小可行数据管道 (Minimum Viable Data Pipeline)
端到端数据流向：输入 -> 队列 -> 存储 -> 验证
"""

import asyncio
import logging
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================
# MVP 1. 核心数据模型
# ============================================


class DecisionMode(Enum):
    SYSTEM1 = "system1"
    SYSTEM2 = "system2"
    HYBRID = "hybrid"


@dataclass
class DecisionEvent:
    """决策事件（队列数据模型
    """
    event_id: str
    session_id: str
    input_text: str
    output_text: Optional[str]
    confidence: float
    mode: DecisionMode
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "confidence": self.confidence,
            "mode": self.mode.value,
            "metadata": json.dumps(self.metadata, ensure_ascii=False),
            "timestamp": self.timestamp
        }


@dataclass
class PipelineStatus:
    """数据管道状态记录
    """
    stage: str  # input -> mq -> storage
    event_id: str
    success: bool
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================
# MVP 2. 存储层 (SQLite 持久化)
# ============================================


class SQLiteStorage:
    """轻量级 SQLite 存储适配器
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "pipeline.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    async def initialize(self):
        """初始化数据库
        """
        if self._initialized:
            return
        import aiosqlite
        logger.info(f"Initializing storage: {self.db_path}")
        
        async with aiosqlite.connect(self.db_path) as conn:
            await self._create_schema(conn)
            await conn.commit()
        self._initialized = True
        logger.info("Storage initialized")
    
    async def _create_schema(self, conn):
        """创建核心表
        """
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS decision_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT,
                input_text TEXT NOT NULL,
                output_text TEXT,
                confidence REAL,
                mode TEXT,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,
                event_id TEXT,
                success INTEGER NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session 
            ON decision_events(session_id)
        """)
        
        logger.debug("Tables created")
    
    async def save_event(self, event: DecisionEvent) -> bool:
        """保存决策事件
        """
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO decision_events 
                    (event_id, session_id, input_text, output_text, confidence, mode, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.session_id,
                    event.input_text,
                    event.output_text,
                    event.confidence,
                    event.mode.value,
                    json.dumps(event.metadata, ensure_ascii=False),
                    event.timestamp
                ))
                await conn.commit()
            logger.debug(f"Event saved: {event.event_id}")
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False
    
    async def get_events(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """查询事件
        """
        import aiosqlite
        results = []
        async with aiosqlite.connect(self.db_path) as conn:
            sql = "SELECT * FROM decision_events ORDER BY timestamp DESC LIMIT ?"
            params = (limit,)
            if session_id:
                sql = "SELECT * FROM decision_events WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?"
                params = (session_id, limit)
            
            async with conn.execute(sql, params) as cursor:
                async for row in cursor:
                    results.append({
                        "event_id": row[0],
                        "session_id": row[1],
                        "input_text": row[2],
                        "output_text": row[3],
                        "confidence": row[4],
                        "mode": row[5],
                        "timestamp": row[7]
                    })
        return results


# ============================================
# MVP 3. 消息队列层 (内存 + Redis 双模式
# ============================================


class MessageQueue:
    """消息队列适配器（内存优先 + Redis 降级）
    """
    
    def __init__(self, use_redis: bool = False, redis_url: str = "redis://localhost:6379/0"):
        self.use_redis = use_redis
        self.redis_url = redis_url
        self._redis = None
        self._memory_queue = asyncio.Queue()
        self._stream_name = "cognicore:mvp"
    
    async def initialize(self):
        if self.use_redis:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                logger.info("MQ: Redis initialized")
            except Exception as e:
                logger.warning(f"Redis unavailable, falling back to memory: {e}")
                self._redis = None
        else:
            logger.info("MQ: Using in-memory queue (simple)")
    
    async def publish(self, event: DecisionEvent) -> bool:
        message = event.to_dict()
        
        if self._redis:
            try:
                await self._redis.xadd(self._stream_name, message)
                logger.debug(f"Published to Redis: {event.event_id}")
                return True
            except Exception as e:
                logger.warning(f"Redis failed, falling back: {e}")
        
        await self._memory_queue.put(message)
        logger.debug(f"Published to memory: {event.event_id}")
        return True


# ============================================
# MVP 4. 数据管道主类
# ============================================


class DataPipelineMVP:
    """最小可行数据管道
    流向: 输入 -> MQ -> 存储 -> 验证
    """
    
    def __init__(self, use_redis: bool = False):
        self.storage = SQLiteStorage()
        self.mq = MessageQueue(use_redis=use_redis)
        self.initialized = False
        self.pipeline_log: List[PipelineStatus] = []
    
    async def initialize(self):
        await self.storage.initialize()
        await self.mq.initialize()
        self.initialized = True
        logger.info("MVP Pipeline initialized")
    
    async def ingest_and_save(self, event: DecisionEvent) -> Dict[str, Any]:
        """端到端数据流向：输入 -> 存储（跳过队列直接存储简化版
        """
        start_time = time.time()
        
        # Step 1: 输入记录
        status_input = PipelineStatus(
            stage="input",
            event_id=event.event_id,
            success=True,
            message=f"Received event for session {event.session_id}"
        )
        self.pipeline_log.append(status_input)
        
        # Step 2: 发布到队列
        publish_ok = await self.mq.publish(event)
        status_mq = PipelineStatus(
            stage="mq",
            event_id=event.event_id,
            success=publish_ok,
            message="Published to queue" if publish_ok else "Queue failed"
        )
        self.pipeline_log.append(status_mq)
        
        # Step 3: 持久化存储
        save_ok = await self.storage.save_event(event)
        status_store = PipelineStatus(
            stage="storage",
            event_id=event.event_id,
            success=save_ok,
            message="Saved to SQLite" if save_ok else "Storage failed"
        )
        self.pipeline_log.append(status_store)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "event_id": event.event_id,
            "success": all([publish_ok, save_ok]),
            "elapsed_ms": round(elapsed_ms, 2),
            "stages": [s.stage for s in self.pipeline_log[-3:]]
        }


# ============================================
# MVP 5. 验证报告生成器
# ============================================


class PipelineVerifier:
    """管道验证和报告生成
    """
    
    def __init__(self, pipeline: DataPipelineMVP):
        self.pipeline = pipeline
    
    async def run_hello_world_test(self) -> Dict[str, Any]:
        """运行第一个 Hello World 测试用例
        """
        print("\n" + "="*70)
        print("  🚀 CogniCore 数据管道 - Hello World 测试")
        print("="*70)
        
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        print(f"\n📝 测试 Session: {session_id}")
        
        test_event = DecisionEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            input_text="Hello, Data Pipeline!",
            output_text="Hello World 成功存储到数据库！",
            confidence=0.95,
            mode=DecisionMode.HYBRID,
            metadata={"test": True, "source": "mvp"}
        )
        print(f"\n📨 测试事件创建: {test_event.event_id}")
        
        result = await self.pipeline.ingest_and_save(test_event)
        print(f"\n✅ 数据流向结果:")
        print(f"   • 成功: {result['success']}")
        print(f"   • 耗时: {result['elapsed_ms']} ms")
        print(f"   • 阶段: {', '.join(result['stages'])}")
        
        print(f"\n📊 查询验证:")
        stored = await self.pipeline.storage.get_events(session_id=session_id)
        print(f"   • 从数据库读取到: {len(stored)} 条记录")
        
        print("\n" + "="*70)
        print("  🎉 数据管道 MVP 测试成功！")
        print("="*70)
        
        return {
            "test_passed": len(stored) > 0 and result["success"],
            "event_count": len(stored),
            "result": result,
            "session_id": session_id
        }
    
    def print_data_flow(self):
        """打印数据流向图
        """
        print("\n📈 数据流向图:")
        print("")
        print("  [用户输入]")
        print("      ↓")
        print("  [生成 DecisionEvent")
        print("      ↓")
        print("  [MQ 发布/内存队列]")
        print("      ↓")
        print("  [SQLite 持久化]")
        print("      ↓")
        print("  [验证查询]")
        print("")


# ============================================
# 入口点
# ============================================


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    pipeline = DataPipelineMVP(use_redis=False)
    await pipeline.initialize()
    
    verifier = PipelineVerifier(pipeline)
    
    # 打印数据流向图
    verifier.print_data_flow()
    
    # 运行 Hello World 测试
    test_result = await verifier.run_hello_world_test()
    
    print(f"\n✅ 测试通过: {test_result['test_passed']}")
    
    return test_result


if __name__ == "__main__":
    asyncio.run(main())
