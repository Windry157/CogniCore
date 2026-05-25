#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CogniCore 使用示例
快速演示项目功能
"""

import asyncio
import logging
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_cognition():
    """演示认知功能"""
    print("\n" + "="*60)
    print("🚀 演示认知功能")
    print("="*60 + "\n")
    
    from src.core.cognition import (
        cognition_coordinator,
        reasoning_visualizer,
    )
    
    # 简单问题
    questions = [
        "你好！",
        "什么是Python？",
        "解释贝叶斯定理",
    ]
    
    for q in questions:
        result = await cognition_coordinator.make_decision({"input": q, "context": {}})
        print(f"👤 问题: {q}")
        print(f"🤖 回答: {result['decision']}")
        print(f"📊 置信度: {result['confidence']:.2f}")
        print(f"⚙️  模式: {result['mode']}")
        print()
    
    # 打印统计
    print("\n📊 决策统计:")
    stats = cognition_coordinator.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return True


async def demo_resilience():
    """演示韧性模块"""
    print("\n" + "="*60)
    print("🔧 演示韧性模块")
    print("="*60 + "\n")
    
    from src.core.resilience import (
        CircuitBreaker,
        circuit_breaker,
        EventBus,
        event_bus,
        DomainEvent,
    )
    
    print("📌 熔断器演示:")
    print(f"当前状态: {circuit_breaker.get_state()}")
    
    print("\n📌 事件总线演示:")
    
    # 订阅事件
    def handler(event):
        print(f"  ✅ 收到事件: {event.id}")
    
    event_bus.subscribe("test_event", handler)
    
    # 发布事件
    test_event = DomainEvent(
        id="test_event",
        source="demo",
        data={"message": "Hello!"},
    )
    await event_bus.publish(test_event)
    
    print()
    return True


async def demo_webui():
    """演示Web UI"""
    print("\n" + "="*60)
    print("🎨 演示Web UI 集成")
    print("="*60 + "\n")
    
    from src.core.webui import web_interface
    
    print("🎨 生成仪表板HTML...")
    html = web_interface.render_page("dashboard")
    print(f"✅ 生成成功，长度: {len(html)} 字符")
    
    # 保存到临时文件
    temp_file = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"📄 仪表板已保存到: {temp_file}")
    
    return True


async def demo_all():
    """运行所有演示"""
    results = []
    
    results.append(("认知功能", await demo_cognition()))
    results.append(("韧性模块", await demo_resilience()))
    results.append(("Web UI", await demo_webui()))
    
    print("\n" + "="*60)
    print("✅ 演示总结")
    print("="*60)
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")
    print("="*60)


def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║              🚀 CogniCore-Portable 演示                    ║
║                  轻量级 AI 助手项目                         ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(demo_all())
        
        print("""
╔═══════════════════════════════════════════════════════════╗
║              🎉 演示完成！                                  ║
║  请查看 src/core/ 了解每个模块的详细使用方式                   ║
╚═══════════════════════════════════════════════════════════╝
        """)
        
        return 0
        
    except Exception as e:
        logger.error(f"演示失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
