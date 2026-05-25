#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工业级数据管道 - 完整容错体系
包含：重试、幂等性、DLQ、校验、监控
"""

import asyncio
import logging
import json
import uuid
import time
import random
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

# ============================================
# 1. 核心数据模型
# ============================================


class DecisionMode(Enum):
    SYSTEM1 = "system1"
    SYSTEM2 = "system2"
    HYBRID = "hybrid"


class MessageStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    RETRYING = "retrying"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class DecisionEvent:
    event_id: str
    session_id: str
    input_text: str
    output_text: Optional[str]
    confidence: float
    mode: DecisionMode
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    retry_count: int = 0
    max_retries: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "confidence": self.confidence,
            "mode": self.mode.value,
            "metadata": json.dumps(self.metadata, ensure_ascii=False),
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionEvent":
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            session_id=data.get("session_id", ""),
            input_text=data.get("input_text", ""),
            output_text=data.get("output_text"),
            confidence=data.get("confidence", 0.0),
            mode=DecisionMode(data.get("mode", "hybrid")),
            metadata=json.loads(data.get("metadata", "{}")) if isinstance(data.get("metadata"), str) else data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 5)
        )


@dataclass
class ProcessingResult:
    event_id: str
    success: bool
    status: MessageStatus
    message: str
    retry_after_seconds: Optional[float] = None
    error: Optional[Exception] = None


# ============================================
# 2. 重试机制 - 指数退避
# ============================================


class RetryPolicy:
    """指数退避重试策略
    """
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """获取第 N 次重试的延迟时间
        """
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            delay = delay * (0.8 + random.random() * 0.4)
        
        return delay


def with_retry(retry_policy: Optional[RetryPolicy] = None):
    """重试装饰器
    """
    if retry_policy is None:
        retry_policy = RetryPolicy()
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retry_policy.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retry_policy.max_retries:
                        delay = retry_policy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt+1}/{retry_policy.max_retries} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {retry_policy.max_retries} attempts failed")
            raise last_exception
        return wrapper
    return decorator


# ============================================
# 3. 幂等性处理
# ============================================


class IdempotencyManager:
    """幂等性管理器 - 使用 event_id 确保不重复处理
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "pipeline.db"
        self.db_path = db_path
        self._processed_ids: set = set()
        self._cache_initialized = False
    
    async def initialize(self):
        if self._cache_initialized:
            return
        await self._load_processed_ids()
        self._cache_initialized = True
        logger.info(f"Idempotency cache initialized with {len(self._processed_ids)} IDs")
    
    async def _load_processed_ids(self):
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute(
                    "SELECT event_id FROM decision_events WHERE 1=1 LIMIT 10000"
                ) as cursor:
                    async for row in cursor:
                        self._processed_ids.add(row[0])
        except Exception as e:
            logger.warning(f"Could not load processed IDs (will check on write): {e}")
    
    async def is_processed(self, event_id: str) -> bool:
        """检查是否已处理
        """
        if event_id in self._processed_ids:
            return True
        
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute(
                    "SELECT 1 FROM decision_events WHERE event_id = ? LIMIT 1",
                    (event_id,)
                ) as cursor:
                    exists = await cursor.fetchone() is not None
                    if exists:
                        self._processed_ids.add(event_id)
                    return exists
        except Exception as e:
            logger.warning(f"Idempotency check failed: {e}")
            return False
    
    def mark_processed(self, event_id: str):
        """标记为已处理（内存标记）
        """
        self._processed_ids.add(event_id)


# ============================================
# 4. 死信队列 (DLQ)
# ============================================


class DeadLetterQueue:
    """死信队列 - 隔离无法处理的消息
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "pipeline.db"
        self.db_path = db_path
    
    async def initialize(self):
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    original_message TEXT NOT NULL,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            await conn.commit()
        logger.info("Dead Letter Queue initialized")
    
    async def send_to_dlq(self, event: DecisionEvent, error: Exception) -> bool:
        """发送到 DLQ
        """
        try:
            import aiosqlite
            error_msg = f"{type(error).__name__}: {str(error)}"
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO dead_letter_queue 
                    (event_id, original_message, error_message, retry_count)
                    VALUES (?, ?, ?, ?)
                """, (
                    event.event_id,
                    json.dumps(event.to_dict(), ensure_ascii=False),
                    error_msg,
                    event.retry_count
                ))
                await conn.commit()
            
            logger.error(f"Message sent to DLQ: {event.event_id}, error: {error_msg}")
            return True
        except Exception as dlq_error:
            logger.critical(f"Failed to send to DLQ: {dlq_error}")
            return False
    
    async def get_pending_dlq_count(self) -> int:
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT COUNT(*) FROM dead_letter_queue WHERE status = 'pending'") as cursor:
                count = await cursor.fetchone()
                return count[0] if count else 0


# ============================================
# 5. 数据校验层
# ============================================


class SchemaValidator:
    """数据校验器
    """
    
    @staticmethod
    def validate(event: DecisionEvent) -> tuple[bool, List[str]]:
        errors = []
        
        if not event.event_id:
            errors.append("event_id is required")
        
        if not event.session_id:
            errors.append("session_id is required")
        
        if not event.input_text or len(event.input_text.strip()) == 0:
            errors.append("input_text cannot be empty")
        
        if not (0.0 <= event.confidence <= 1.0):
            errors.append("confidence must be between 0.0 and 1.0")
        
        return len(errors) == 0, errors


# ============================================
# 6. 可观测性与监控
# ============================================


class PipelineMetrics:
    """管道监控指标
    """
    
    def __init__(self):
        self.total_messages = 0
        self.success_count = 0
        self.failure_count = 0
        self.retry_count = 0
        self.dead_letter_count = 0
        self.start_time = datetime.now()
        self.processing_times: List[float] = []
        self._lock = asyncio.Lock()
    
    async def record_success(self, processing_time_seconds: float):
        async with self._lock:
            self.total_messages += 1
            self.success_count += 1
            self.processing_times.append(processing_time_seconds)
    
    async def record_failure(self):
        async with self._lock:
            self.total_messages += 1
            self.failure_count += 1
    
    async def record_retry(self):
        async with self._lock:
            self.retry_count += 1
    
    async def record_dead_letter(self):
        async with self._lock:
            self.dead_letter_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        avg_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "total_messages": self.total_messages,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "retry_count": self.retry_count,
            "dead_letter_count": self.dead_letter_count,
            "success_rate": round(self.success_count / self.total_messages * 100, 2) if self.total_messages else 0,
            "avg_processing_time_ms": round(avg_time * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }


# ============================================
# 7. 工业级管道主类
# ============================================


class RobustDataPipeline:
    """工业级数据管道 - 完整容错体系
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.retry_policy = RetryPolicy()
        self.idempotency = IdempotencyManager(db_path)
        self.dlq = DeadLetterQueue(db_path)
        self.metrics = PipelineMetrics()
        self.validator = SchemaValidator()
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        if self._initialized:
            return
        await self._init_db()
        await self.idempotency.initialize()
        await self.dlq.initialize()
        self._initialized = True
        logger.info("🔥 Robust Data Pipeline initialized!")
    
    async def _init_db(self):
        import aiosqlite
        if self.db_path is None:
            self.db_path = Path(__file__).parent / "data" / "pipeline.db"
        self.db_path.parent.mkdir(exist_ok=True)
        async with aiosqlite.connect(self.db_path) as conn:
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
            await conn.commit()
    
    async def process_event(self, event: DecisionEvent) -> ProcessingResult:
        """处理单个事件 - 端到端完整容错流程
        """
        start_time = time.time()
        
        logger.info(f"Processing: {event.event_id} (retry={event.retry_count})")
        
        # Step 1: 数据校验
        is_valid, errors = self.validator.validate(event)
        if not is_valid:
            logger.warning(f"Validation failed: {errors}")
            await self.metrics.record_failure()
            return ProcessingResult(
                event_id=event.event_id,
                success=False,
                status=MessageStatus.FAILED,
                message=f"Validation errors: {', '.join(errors)}"
            )
        
        # Step 2: 幂等性检查
        if await self.idempotency.is_processed(event.event_id):
            logger.info(f"Event already processed (idempotent): {event.event_id}")
            await self.metrics.record_success(time.time() - start_time)
            return ProcessingResult(
                event_id=event.event_id,
                success=True,
                status=MessageStatus.SUCCESS,
                message="Already processed (idempotent skip)"
            )
        
        # Step 3: 处理与重试
        try:
            for attempt in range(self.retry_policy.max_retries + 1):
                try:
                    await self._save_to_storage(event)
                    self.idempotency.mark_processed(event.event_id)
                    processing_time = time.time() - start_time
                    await self.metrics.record_success(processing_time)
                    
                    logger.info(f"Success: {event.event_id} in {processing_time*1000:.2f}ms")
                    return ProcessingResult(
                        event_id=event.event_id,
                        success=True,
                        status=MessageStatus.SUCCESS,
                        message="Processed successfully"
                    )
                except Exception as e:
                    event.retry_count = attempt
                    await self.metrics.record_retry()
                    
                    if attempt < self.retry_policy.max_retries:
                        delay = self.retry_policy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt+1} failed: {e}. Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All retries exhausted for {event.event_id}")
                        raise
        
        except Exception as final_error:
            await self.metrics.record_failure()
            await self.metrics.record_dead_letter()
            await self.dlq.send_to_dlq(event, final_error)
            
            return ProcessingResult(
                event_id=event.event_id,
                success=False,
                status=MessageStatus.DEAD_LETTER,
                message=f"Failed, sent to DLQ: {final_error}",
                error=final_error
            )
    
    @with_retry()
    async def _save_to_storage(self, event: DecisionEvent):
        """带重试的存储操作
        """
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT OR IGNORE INTO decision_events 
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
        logger.debug(f"Saved: {event.event_id}")


# ============================================
# 8. 容错测试套件
# ============================================


async def test_robust_pipeline():
    """工业级管道测试
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("\n" + "="*80)
    print("  🚀 工业级数据管道 - 完整容错体系测试")
    print("="*80)
    
    pipeline = RobustDataPipeline()
    await pipeline.initialize()
    
    session_id = f"test-robust-{uuid.uuid4().hex[:8]}"
    
    # Test 1: 正常处理
    print("\n" + "-"*80)
    print("  🔹 Test 1: 正常事件处理")
    print("-"*80)
    event1 = DecisionEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        input_text="Hello Robust Pipeline!",
        output_text="Success!",
        confidence=0.95,
        mode=DecisionMode.HYBRID
    )
    result1 = await pipeline.process_event(event1)
    print(f"  Result: {result1.status} - {result1.message}")
    
    # Test 2: 幂等性测试（重复 ID）
    print("\n" + "-"*80)
    print("  🔹 Test 2: 幂等性测试（重复处理同一 ID）")
    print("-"*80)
    result2 = await pipeline.process_event(event1)
    print(f"  Result: {result2.status} - {result2.message}")
    
    # Test 3: 校验失败测试
    print("\n" + "-"*80)
    print("  🔹 Test 3: 数据校验失败测试")
    print("-"*80)
    invalid_event = DecisionEvent(
        event_id="",
        session_id="",
        input_text="",
        output_text=None,
        confidence=1.5,
        mode=DecisionMode.HYBRID
    )
    result3 = await pipeline.process_event(invalid_event)
    print(f"  Result: {result3.status} - {result3.message}")
    
    # 统计信息
    print("\n" + "="*80)
    print("  📊 管道监控指标")
    print("="*80)
    stats = pipeline.metrics.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*80)
    print("  🎉 工业级数据管道测试完成！")
    print("="*80)
    
    return stats


if __name__ == "__main__":
    asyncio.run(test_robust_pipeline())
