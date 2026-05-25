#!/usr/bin/env python3
"""
将现有 SkillManager 中的 12  skills包装为 Agent Skills 标准格式.
"""
import logging
from typing import Dict, Any, Optional
from .schema import SkillManifest, SkillParameter, SkillCategory, make_manifest
from .registry import SkillRegistry

logger = logging.getLogger("AgentSkillsWrapper")


# 现有Skill定义 (与 SkillManager 中Register的Skill对应) 
EXISTING_SKILL_DEFS = [
    {
        "id": "system_control",
        "name": "系统控制",
        "desc": "控制系统设置, 包括关机, 重启, 音量调节等",
        "category": "system",
        "tags": ["system", "control"],
        "params": [
            {"name": "action", "type": "string", "description": "控制动作", "required": True,
             "enum": ["shutdown", "restart", "volume_up", "volume_down", "lock_screen", "sleep"]},
        ],
    },
    {
        "id": "system_info",
        "name": "System Info",
        "desc": "GetSystem Info, 包括 CPU, 内存, 磁盘, 网络等",
        "category": "system",
        "tags": ["system", "monitor"],
        "params": [
            {"name": "action", "type": "string", "description": "查询type", "required": True,
             "enum": ["cpu", "memory", "disk", "network", "os", "all"]},
        ],
    },
    {
        "id": "file_manager",
        "name": "文件管理",
        "desc": "文件读写, 复制, 移动, Delete, Search, 压缩等操作",
        "category": "file",
        "tags": ["file", "fs"],
        "params": [
            {"name": "action", "type": "string", "description": "文件操作type", "required": True,
             "enum": ["read", "write", "copy", "move", "delete", "list", "search", "compress", "extract"]},
            {"name": "path", "type": "string", "description": "文件路径", "required": True},
        ],
    },
    {
        "id": "process_manager",
        "name": "进程管理",
        "desc": "管理系统进程, 包括查看, Start, 停止进程",
        "category": "system",
        "tags": ["system", "process"],
        "params": [
            {"name": "action", "type": "string", "description": "进程操作", "required": True,
             "enum": ["list", "kill", "start", "info"]},
            {"name": "pid", "type": "integer", "description": "进程 ID"},
            {"name": "name", "type": "string", "description": "进程Name"},
        ],
    },
    {
        "id": "network_diagnostic",
        "name": "网络诊断",
        "desc": "网络Connect诊断, 测速, 路由追踪等",
        "category": "network",
        "tags": ["network", "diagnostic"],
        "params": [
            {"name": "action", "type": "string", "description": "诊断type", "required": True,
             "enum": ["ping", "traceroute", "speedtest", "dns_lookup", "port_check"]},
            {"name": "target", "type": "string", "description": "目标地址"},
        ],
    },
    {
        "id": "security_monitor",
        "name": "安全监控",
        "desc": "安全监控和防护, 包括端口扫描, 文件完整性检查等",
        "category": "security",
        "tags": ["security", "monitor"],
        "params": [
            {"name": "action", "type": "string", "description": "安全操作", "required": True,
             "enum": ["port_scan", "file_integrity", "process_check", "network_connections"]},
        ],
    },
    {
        "id": "code_executor",
        "name": "代码执行",
        "desc": "在沙箱中执行 Python 代码并返回",
        "category": "code",
        "tags": ["code", "python", "sandbox"],
        "params": [
            {"name": "action", "type": "string", "description": "执行动作", "required": True,
             "enum": ["run", "eval"]},
            {"name": "code", "type": "string", "description": "要执行的代码", "required": True},
            {"name": "timeout", "type": "integer", "description": "超时s数"},
        ],
    },
    {
        "id": "search",
        "name": "Search",
        "desc": "在本地文件系统和knowledge base中SearchContent",
        "category": "data",
        "tags": ["search", "knowledge"],
        "params": [
            {"name": "action", "type": "string", "description": "Search范围", "required": True,
             "enum": ["files", "knowledge_base", "web"]},
            {"name": "query", "type": "string", "description": "Search关键词", "required": True},
            {"name": "max_results", "type": "integer", "description": "最大数"},
        ],
    },
    {
        "id": "draw",
        "name": "绘图",
        "desc": "使用代码生成图表和数据可视化",
        "category": "data",
        "tags": ["data", "visualization", "chart"],
        "params": [
            {"name": "chart_type", "type": "string", "description": "图表type", "required": True,
             "enum": ["line", "bar", "pie", "scatter", "histogram", "heatmap"]},
            {"name": "data", "type": "object", "description": "数据", "required": True},
            {"name": "title", "type": "string", "description": "图表Title"},
        ],
    },
    {
        "id": "translate",
        "name": "Translation",
        "desc": "多语言Translation服务",
        "category": "utility",
        "tags": ["translation", "language"],
        "params": [
            {"name": "action", "type": "string", "description": "Translation操作", "required": True,
             "enum": ["translate", "detect"]},
            {"name": "text", "type": "string", "description": "要Translation的文本", "required": True},
            {"name": "target_lang", "type": "string", "description": "目标语言"},
            {"name": "source_lang", "type": "string", "description": "源语言"},
        ],
    },
    {
        "id": "data_analyze",
        "name": "数据分析",
        "desc": "结构化数据分析和统计",
        "category": "data",
        "tags": ["data", "analysis", "statistics"],
        "params": [
            {"name": "action", "type": "string", "description": "分析type", "required": True,
             "enum": ["describe", "correlation", "aggregate", "filter", "plot"]},
            {"name": "data", "type": "object", "description": "数据", "required": True},
        ],
    },
    {
        "id": "browser_automation",
        "name": "Browser automation",
        "desc": "Browser automation操作, 包括网页导航, 表单填写, Screenshot等",
        "category": "automation",
        "tags": ["browser", "automation", "web"],
        "params": [
            {"name": "action", "type": "string", "description": "browser操作", "required": True,
             "enum": ["navigate", "click", "type", "screenshot", "extract", "submit"]},
            {"name": "url", "type": "string", "description": "目标 URL"},
            {"name": "selector", "type": "string", "description": "CSS 选择器"},
        ],
    },
]


def register_existing_skills(registry: SkillRegistry):
    """将 12  现有SkillRegister到 Agent Skills Registry"""
    count = 0
    for defn in EXISTING_SKILL_DEFS:
        params = [SkillParameter(**p) for p in defn.get("params", [])]
        manifest = make_manifest(
            id=defn["id"],
            name=defn["name"],
            desc=defn["desc"],
            params=[p.__dict__ for p in params],
            category=defn.get("category", "utility"),
            tags=defn.get("tags", []),
            version="2.0.0",
        )
        registry.register(manifest)
        count += 1
    logger.info(f"Registered {count} existing skills to Agent Skills standard")
    return count
