#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据层快速启动框架 (Data Layer Quick Start)
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================
# 1. 数据模型定义 (Schema Definition)
# ============================================


class DecisionMode(Enum):
    SYSTEM1 = "system1"
    SYSTEM2 = "system2"
    HYBRID = "hybrid"


@dataclass
class User:
    id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    id: str
    user_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRecord:
    id: str
    session_id: str
    input: str
    output: Optional[str] = None
    confidence: float = 0.0
    mode: DecisionMode = DecisionMode.HYBRID
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AuditLog:
    id: Optional[int] = None
    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================
# 2. 数据访问层 (Repository/DAO Layer)
# ============================================


class BaseRepository:
    """基础 Repository 接口"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent / "data" / "cognicore.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return
        try:
            import aiosqlite
            logger.info(f"Initializing SQLite at: {self.db_path}")
            
            async with aiosqlite.connect(self.db_path) as conn:
                await self._create_tables(conn)
                await conn.commit()
                
            self._initialized = True
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"DB init failed: {e}")
            raise

    async def _create_tables(self, conn):
        """创建核心表结构"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL,
                state TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                input TEXT NOT NULL,
                output TEXT,
                confidence REAL,
                mode TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                before TEXT,
                after TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_session 
            ON decisions(session_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_time 
            ON audit_log(created_at)
        """)
        
        logger.debug("Core tables created/verified")


class UserRepository(BaseRepository):
    """用户数据访问"""
    
    async def create(self, user: User) -> User:
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO users (id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                user.id,
                user.created_at,
                user.updated_at,
                json.dumps(user.metadata, ensure_ascii=False)
            ))
            await conn.commit()
        return user
    
    async def get(self, user_id: str) -> Optional[User]:
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return User(
                        id=row[0],
                        created_at=row[1],
                        updated_at=row[2],
                        metadata=json.loads(row[3]) if row[3] else {}
                    )
        return None


class DecisionRepository(BaseRepository):
    """决策记录数据访问"""
    
    async def create(self, decision: DecisionRecord) -> DecisionRecord:
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO decisions 
                (id, session_id, input, output, confidence, mode, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.id,
                decision.session_id,
                decision.input,
                decision.output,
                decision.confidence,
                decision.mode.value,
                json.dumps(decision.metadata, ensure_ascii=False),
                decision.created_at
            ))
            await conn.commit()
        return decision
    
    async def get_by_session(self, session_id: str, limit: int = 50) -> List[DecisionRecord]:
        import aiosqlite
        results = []
        async with aiosqlite.connect(self.db_path) as conn:
            sql = "SELECT * FROM decisions WHERE session_id = ? ORDER BY created_at DESC LIMIT ?"
            async with conn.execute(sql, (session_id, limit)) as cursor:
                async for row in cursor:
                    results.append(DecisionRecord(
                        id=row[0],
                        session_id=row[1],
                        input=row[2],
                        output=row[3],
                        confidence=row[4] or 0.0,
                        mode=DecisionMode(row[5]) if row[5] else DecisionMode.HYBRID,
                        metadata=json.loads(row[6]) if row[6] else {},
                        created_at=row[7]
                    ))
        return results


class AuditLogRepository(BaseRepository):
    """审计日志数据访问"""
    
    async def create(self, log: AuditLog) -> AuditLog:
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                INSERT INTO audit_log 
                (event_type, entity_type, entity_id, before, after, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log.event_type,
                log.entity_type,
                log.entity_id,
                json.dumps(log.before, ensure_ascii=False) if log.before else None,
                json.dumps(log.after, ensure_ascii=False) if log.after else None,
                json.dumps(log.metadata, ensure_ascii=False) if log.metadata else None,
                log.created_at
            ))
            log.id = cursor.lastrowid
            await conn.commit()
        return log


# ============================================
# 3. 消息队列层 (Redis Streams MQ Layer)
# ============================================


class MessageQueue:
    """基于 Redis Streams 的消息队列"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self._stream_name = "cognicore:events"
        self._group_name = "cognicore:workers"
    
    async def initialize(self):
        """初始化 Redis 连接和 Stream"""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            
            try:
                await self._redis.xgroup_create(
                    self._stream_name,
                    self._group_name,
                    mkstream=True
                )
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"Group create: {e}")
                    
            logger.info("MQ initialized (Redis Streams)")
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
            self._redis = None
            self._fallback_queue = asyncio.Queue()
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        """发布事件到队列"""
        message = {
            "event_type": event_type,
            "data": json.dumps(data, ensure_ascii=False),
            "timestamp": datetime.now().isoformat()
        }
        
        if self._redis:
            await self._redis.xadd(self._stream_name, message)
            logger.debug(f"Event published: {event_type}")
        else:
            await self._fallback_queue.put(message)
    
    async def close(self):
        if self._redis:
            await self._redis.close()


# ============================================
# 4. 数据服务层 (Data Service Layer)
# ============================================


class DataService:
    """统一数据服务层 (门面模式)"""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.decision_repo = DecisionRepository()
        self.audit_repo = AuditLogRepository()
        self.mq = MessageQueue()
        self._initialized = False
    
    async def initialize(self):
        """初始化所有数据服务"""
        if self._initialized:
            return
        await self.user_repo.initialize()
        await self.decision_repo.initialize()
        await self.audit_repo.initialize()
        try:
            await self.mq.initialize()
        except Exception as e:
            logger.warning(f"MQ init skipped (safe): {e}")
        self._initialized = True
        logger.info("Data service layer initialized")
    
    async def record_decision(
        self,
        decision_id: str,
        session_id: str,
        input_str: str,
        output_str: Optional[str],
        confidence: float,
        mode: DecisionMode,
        metadata: Optional[Dict] = None
    ):
        """记录决策（异步 + 持久化）"""
        decision = DecisionRecord(
            id=decision_id,
            session_id=session_id,
            input=input_str,
            output=output_str,
            confidence=confidence,
            mode=mode,
            metadata=metadata or {}
        )
        
        await self.decision_repo.create(decision)
        
        await self.audit_repo.create(AuditLog(
            event_type="decision.created",
            entity_type="decision",
            entity_id=decision_id,
            after=asdict(decision),
            metadata={"source": "data_layer"}
        ))
        
        await self.mq.publish("decision.created", asdict(decision))
        
        logger.debug(f"Decision recorded: {decision_id}")
        return decision


# ============================================
# 5. 快速示例入口 (Quick Start Demo)
# ============================================


async def quick_start_demo():
    """数据层快速演示"""
    print("=" * 60)
    print("  CogniCore 数据层快速演示")
    print("=" * 60)
    
    data_service = DataService()
    await data_service.initialize()
    
    # 1. 创建测试会话
    import uuid
    session_id = str(uuid.uuid4())[:8]
    print(f"\n📝 Session ID: {session_id}")
    
    # 2. 记录测试决策
    decision_id = str(uuid.uuid4())[:8]
    decision = await data_service.record_decision(
        decision_id=decision_id,
        session_id=session_id,
        input_str="测试数据层",
        output_str="数据层工作正常！",
        confidence=0.95,
        mode=DecisionMode.HYBRID,
        metadata={"test": True}
    )
    print(f"✅ 决策记录完成: {decision.id}")
    
    # 3. 查询历史
    history = await data_service.decision_repo.get_by_session(session_id)
    print(f"📊 查询到 {len(history)} 条历史决策")
    
    print("\n🎉 数据层验证成功！")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(quick_start_demo())
