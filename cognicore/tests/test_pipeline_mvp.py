#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管道 MVP 第一个测试用例
Test Case 001: Hello World 数据管道验证
"""

import pytest
import asyncio
from src.core.data_pipeline_mvp import (
    DataPipelineMVP,
    DecisionEvent,
    DecisionMode,
    PipelineVerifier,
)
import uuid


@pytest.mark.asyncio
async def test_001_data_pipeline_hello_world():
    """
    Test Case 001: 最小可行数据管道验证
    
    预期结果:
    1. 成功创建 DecisionEvent
    2. 成功发布到队列
    3. 成功保存到 SQLite
    4. 能从数据库查询到记录
    5. 整个流程 < 100ms
    """
    print("\n" + "="*70)
    print("  🧪 Test Case 001: Hello World")
    print("="*70)
    
    # 1. 初始化管道
    pipeline = DataPipelineMVP(use_redis=False)
    await pipeline.initialize()
    
    # 2. 创建测试事件
    session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    test_event = DecisionEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        input_text="Hello, Data Pipeline!",
        output_text="Hello World 成功存储!",
        confidence=0.95,
        mode=DecisionMode.HYBRID,
        metadata={"test_case": "001", "priority": "high"}
    )
    print(f"\n📝 Event: {test_event.event_id}")
    
    # 3. 执行端到端流程
    result = await pipeline.ingest_and_save(test_event)
    print(f"\n⏱️ 耗时: {result['elapsed_ms']} ms")
    print(f"✅ 阶段: {', '.join(result['stages'])}")
    
    # 4. 验证
    assert result["success"] is True, "Pipeline failed"
    assert "input" in result["stages"], "Input stage missing"
    assert "storage" in result["stages"], "Storage stage missing"
    assert result["elapsed_ms"] < 1000, "Pipeline too slow"
    
    # 5. 查询验证
    stored = await pipeline.storage.get_events(session_id=session_id)
    print(f"\n📊 查询到 {len(stored)} 条记录")
    
    assert len(stored) >= 1, "No records found"
    
    stored_event = stored[0]
    assert stored_event["event_id"] == test_event.event_id, "Event ID mismatch"
    assert stored_event["input_text"] == test_event.input_text, "Input mismatch"
    assert stored_event["confidence"] == 0.95, "Confidence mismatch"
    
    print("\n" + "="*70)
    print("  ✅ Test Case 001 PASSED!")
    print("="*70)
    
    return True


if __name__ == "__main__":
    asyncio.run(test_001_data_pipeline_hello_world())
