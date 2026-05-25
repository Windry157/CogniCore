#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目验证脚本
检查 CogniCore-Portable 所有模块是否可以正常导入
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("  CogniCore-Portable 项目完整性验证")
print("=" * 70)
print()

results = []


def check_module(name, import_path):
    """检查模块是否可以导入"""
    try:
        __import__(import_path)
        print(f"✅ {name:30s} 导入成功")
        return True
    except Exception as e:
        print(f"❌ {name:30s} 导入失败: {str(e)[:50]}")
        return False


# 检查核心模块
print("-" * 70)
print("  核心模块检查")
print("-" * 70)

results.append(check_module("Config", "src.core.config"))
results.append(check_module("Agent", "src.core.agent"))
results.append(check_module("Memory", "src.core.memory"))
results.append(check_module("LLM", "src.core.llm"))
results.append(check_module("Skills", "src.core.skills"))
results.append(check_module("Tools", "src.core.tools"))

# 检查第一阶段模块
print()
print("-" * 70)
print("  第一阶段模块检查")
print("-" * 70)

results.append(check_module("Uncertainty", "src.core.uncertainty"))
results.append(check_module("Observability", "src.core.observability"))
results.append(check_module("Evaluation", "src.core.evaluation"))

# 检查第二阶段模块
print()
print("-" * 70)
print("  第二阶段模块检查")
print("-" * 70)

results.append(check_module("Cognition", "src.core.cognition"))

# 检查第三阶段模块
print()
print("-" * 70)
print("  第三阶段模块检查")
print("-" * 70)

results.append(check_module("Resilience", "src.core.resilience"))
results.append(check_module("WebUI", "src.core.webui"))
results.append(check_module("Multimodal", "src.core.multimodal"))

# 统计结果
print()
print("=" * 70)
total = len(results)
passed = sum(results)
failed = total - passed

print(f"  总计: {total} 个模块")
print(f"  成功: {passed} 个模块")
print(f"  失败: {failed} 个模块")
print()

if failed == 0:
    print("🎉 所有模块验证成功！项目完整！")
    print("=" * 70)
    sys.exit(0)
else:
    print(f"⚠️ 有 {failed} 个模块导入失败")
    print("=" * 70)
    sys.exit(1)
