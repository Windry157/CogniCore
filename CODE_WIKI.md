# CogniCore Portable - Code Wiki 文档

**版本**: 2.1.0
**最后更新**: 2026-05-22

---

## 目录
1. [项目概述](#项目概述)
2. [整体架构](#整体架构)
3. [核心模块详解](#核心模块详解)
4. [API接口文档](#api接口文档)
5. [配置说明](#配置说明)
6. [运行部署](#运行部署)
7. [开发指南](#开发指南)

---

## 项目概述

### 项目简介
CogniCore Portable 是一个随身携带的智能 AI 助手系统，无需复杂安装，插在 U 盘上即可使用。系统整合了多代理协作、内存管理、RAG检索、技能系统等功能，提供了丰富的本地 AI 能力。

### 核心特性
- **多代理协作系统** - 支持多个专业代理协同工作
- **多模态内存** - 包含情景记忆、语义记忆、向量记忆、知识图谱
- **丰富的技能系统** - 内置12+系统控制和实用工具技能
- **本地优先** - 支持本地 Ollama 推理，数据本地存储
- **便携式设计** - 可以直接在 U 盘上运行，无需复杂配置
- **安全沙箱** - 内置 HITL 人机协同审批机制

### 技术栈
| 技术类别 | 选型 |
|---------|------|
| 后端框架 | FastAPI |
| 向量数据库 | ChromaDB |
| LLM引擎 | Ollama (本地) + 云端支持 |
| 数据存储 | JSON 文件 + SQLite |
| 异步处理 | asyncio + httpx |
| 配置管理 | Pydantic Settings + YAML |

---

## 整体架构

### 系统架构图
```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (Web UI)                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Web Server                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   API Router Layer                     │  │
│  │  /health | /api/* | /agent/* | /mcp/* | /ws          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Core Services Layer                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Assistant  │  │   Memory     │  │  Skill Manager   │  │
│  │    Core      │  │   System     │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   LLM        │  │    Agent     │  │   RAG Service    │  │
│  │   Service    │  │  Coordinator │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Feedback   │  │   Sandbox    │  │   Plugin Manager │  │
│  │   Manager    │  │   Security   │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data & Storage Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Memory Files  │  Vector DB  │  Knowledge Graph  │  Logs  │
└─────────────────────────────────────────────────────────────┘
```

### 目录结构
```
CogniCore-Portable/
├── run.py                    # 统一启动入口
├── start.bat                # Windows 快速启动
├── stop.bat                 # 停止服务
├── bootstrap.ps1            # 初始化脚本
├── config/                  # 配置文件目录
│   └── cognicore.yaml       # 主配置文件
├── memory/                  # 记忆数据目录
│   ├── episodic_memory.json # 情景记忆
│   ├── semantic_memory.json # 语义记忆
│   └── knowledge_graph.json # 知识图谱
├── cognicore/               # 核心代码目录
│   ├── app.py              # FastAPI 应用入口
│   ├── launcher.py         # 启动器
│   ├── config.yaml         # 应用配置
│   ├── requirements.txt    # Python 依赖
│   ├── frontend/           # 前端文件
│   ├── logs/               # 日志目录
│   ├── data/               # 运行时数据
│   │   └── memory_store/   # 向量数据库
│   ├── src/
│   │   ├── api/            # API 路由
│   │   │   ├── routes.py   # 核心路由定义
│   │   │   └── websocket_manager.py
│   │   ├── core/           # 核心模块
│   │   │   ├── agent/      # 代理系统
│   │   │   ├── agent_skills/ # 代理技能
│   │   │   ├── config/     # 配置模块
│   │   │   ├── feedback/   # 反馈管理
│   │   │   ├── knowledge/  # 知识库
│   │   │   ├── learning/   # 自主学习
│   │   │   ├── llm/        # LLM 服务
│   │   │   ├── lobster/    # 进化算法
│   │   │   ├── logging/    # 结构化日志
│   │   │   ├── memory/     # 记忆系统
│   │   │   ├── multimodal/ # 多模态处理
│   │   │   ├── plugins/    # 插件系统
│   │   │   ├── rag/        # RAG 检索
│   │   │   ├── sandbox/    # 安全沙箱
│   │   │   ├── skills/     # 技能实现
│   │   │   ├── tools/      # 工具注册
│   │   │   ├── user_profile/ # 用户画像
│   │   │   ├── utils/      # 工具函数
│   │   │   ├── vector_store/ # 向量存储
│   │   │   ├── assistant.py # 智能助手核心
│   │   │   ├── auth.py
│   │   │   ├── base.py
│   │   │   ├── cache.py
│   │   │   ├── cognicore_config.py
│   │   │   ├── security.py
│   │   │   ├── skill_manager.py # 技能管理器
│   │   │   ├── tool_knowledge_ecosystem.py
│   │   │   └── websocket.py
│   │   ├── services/       # 服务层
│   │   │   ├── screen/     # 屏幕服务
│   │   │   ├── video/      # 视频分析
│   │   │   └── voice/      # 语音服务
│   │   └── utils/          # 工具函数
│   └── tests/              # 测试目录
└── venv/                   # Python 虚拟环境
```

---

## 核心模块详解

### 1. Assistant 模块 - 智能助手核心

**文件位置**: [cognicore/src/core/assistant.py](file:///e:/CogniCore-Portable/cognicore/src/core/assistant.py)

#### 主要类

##### ModelManager
模型管理器，负责管理可用的 LLM 模型。

**核心方法**:
- `refresh_from_ollama()` - 从 Ollama 刷新模型列表
- `load_from_config(config)` - 从配置加载模型列表
- `get_model(model_id)` - 获取特定模型信息

**支持的模型**:
- 云端模型: minimax-m2.7, kimi-k2.5, deepseek-v3.1, qwen3-vl
- 本地模型: qwen3-vl, deepseek-r1, gemma3 等（通过 Ollama）

##### Assistant
智能助手主类，是整个系统的协调中心。

**核心属性**:
```python
skill_manager: SkillManager              # 技能管理器
memory_system: UnifiedMemorySystem       # 统一记忆系统
services: Dict[str, Any]                 # 注册的服务
user_contexts: Dict[str, Dict]           # 用户上下文
model_manager: ModelManager              # 模型管理器
plugin_manager: PluginManager            # 插件管理器
autonomous_learner: AutonomousLearner    # 自主学习器
```

**核心方法**:
- `initialize(config)` - 初始化助手系统
- `register_service(name, service)` - 注册服务（如 LLM 服务）
- `stream_process_message(session_id, message, model, images)` - 流式处理用户消息（支持 ReAct 模式）
- `_parse_tool_args(func_name, func_args)` - 解析工具参数
- `_extract_tool_calls_from_text(text)` - 从文本中提取工具调用（适配不支持原生 function calling 的模型）
- `_fix_json_arguments(json_str)` - 修复 JSON 参数格式问题

**工作流程**:
```
用户消息 → 记忆检索 → 构建上下文 → LLM 推理 → 工具调用检测 → 
执行工具 → 结果返回 → 更新记忆 → 自主学习
```

---

### 2. Memory 模块 - 统一记忆系统

**文件位置**: [cognicore/src/core/memory/](file:///e:/CogniCore-Portable/cognicore/src/core/memory/)

#### 架构概览
系统采用**五层记忆架构**:
1. **Short-term Memory (JSON)** - 短期情景记忆
2. **Medium-term Memory (Local Vector)** - 中期向量记忆
3. **Long-term Memory (ChromaDB)** - 长期向量数据库
4. **Knowledge Graph** - 结构化知识图谱
5. **Contextual Memory** - 情境化经验记忆

#### 主要类

##### UnifiedMemorySystem
统一记忆系统，整合所有记忆类型。

**核心属性**:
```python
json_memory: JSONMemory              # JSON 记忆
vector_memory: VectorMemory          # 本地向量记忆
kg_memory: KnowledgeGraphMemory      # 知识图谱记忆
vector_db_memory: ChromaDBMemory     # 向量数据库记忆
contextual_memory: ContextualMemory  # 情境记忆
shared_context: Dict                 # 跨助手共享上下文
conversation_history: List           # 对话历史
event_bus: List                      # 事件总线
```

**核心方法**:
- 记忆存储方法:
  - `store_experience(content, context, importance, tags)` - 存储经历
  - `store_task_memory(task, result, context)` - 存储任务记忆
  - `store_error_memory(error, task, correction_strategy)` - 存储错误记忆
  - `store_strategy_memory(strategy, task_type, success_rate)` - 存储策略记忆
  - `store_concept(concept, description, category, tags)` - 存储概念
  - `store_knowledge(entity_name, entity_type, observations)` - 存储知识
  - `store_contextual_experience(context, task, action, result, importance, tags)` - 存储情境经验

- 记忆检索方法:
  - `retrieve(query, limit)` - 从所有记忆系统检索
  - `search_memory(query, limit)` - 搜索记忆
  - `get_entity(entity_name)` - 获取实体详情
  - `retrieve_task_memories(task_type, status, top_k)` - 检索任务记忆
  - `retrieve_error_memories(error_type, task_type, top_k)` - 检索错误记忆
  - `retrieve_strategy_memories(task_type, min_success_rate, top_k)` - 检索策略记忆
  - `retrieve_contextual_experiences(query_context, task_type, top_k)` - 检索情境经验

- 跨助手协作方法:
  - `add_shared_context(key, value, source_agent, expires_in)` - 添加共享上下文
  - `get_shared_context(key)` - 获取共享上下文
  - `record_conversation(agent_id, user_input, agent_response, context)` - 记录对话
  - `publish_event(event_type, data, source_agent)` - 发布事件
  - `synthesize_knowledge(query, context_limit)` - 综合知识

- 自主学习方法:
  - `autonomous_learning()` - 自主学习主函数
  - `analyze_memory_usage()` - 分析记忆使用模式
  - `identify_important_information(threshold)` - 识别重要信息
  - `forget_outdated_information(days_threshold)` - 遗忘过时信息
  - `improve_retrieval_accuracy()` - 提高检索准确性

- 系统管理方法:
  - `get_statistics()` - 获取完整统计
  - `clear_all()` - 清空所有记忆
  - `format_for_llm(query, limit)` - 格式化为 LLM 可用的上下文

##### JSONMemory
JSON 文件存储的记忆。

**支持的记忆类型**:
- `episodic` - 情景记忆（记录经历）
- `semantic` - 语义记忆（存储概念知识）
- `working` - 工作记忆（临时存储）

##### VectorMemory
本地向量记忆系统，支持语义相似度检索。

##### KnowledgeGraphMemory
知识图谱记忆，支持实体-关系-属性存储。

##### ChromaDBMemory
基于 ChromaDB 的长期向量存储。

##### ContextualMemory
情境化记忆，存储完整的经验流（上下文-任务-行动-结果）。

---

### 3. Skills 模块 - 技能系统

**文件位置**: [cognicore/src/core/skills/](file:///e:/CogniCore-Portable/cognicore/src/core/skills/), [cognicore/src/core/skill_manager.py](file:///e:/CogniCore-Portable/cognicore/src/core/skill_manager.py)

#### SkillManager
技能管理器，负责技能的注册、获取和执行。

**核心方法**:
- `register_skill(skill)` - 注册新技能
- `get_tool_definitions()` - 获取 OpenAI 兼容的工具定义列表
- `execute_tool(tool_name, action, params)` - 执行工具（含安全检查）

#### 内置技能列表

| 技能名称 | 功能描述 | 主要动作 |
|---------|---------|---------|
| `system_control` | 系统控制 | get_time, shutdown, restart, etc. |
| `system_info` | 系统信息 | get_all, cpu, memory, disk, network |
| `file_manager` | 文件管理 | list_dir, read_file, write_file, copy, move, delete, mkdir |
| `process_manager` | 进程管理 | list_processes, get_process, kill_process, get_startup_items |
| `network_diagnostic` | 网络诊断 | get_all, ping, check_port, speed_test |
| `security_monitor` | 安全监控 | get_all, check_ports, scan_vulnerabilities |
| `code_executor` | 代码执行 | execute_python, execute_shell, execute_powershell, write_file |
| `search` | 搜索 | web_search, file_search, etc. |
| `skill_draw` | 绘图 | draw, etc. |
| `skill_translate` | 翻译 | translate, etc. |
| `skill_data_analyze` | 数据分析 | analyze, etc. |
| `browser_automation` | 浏览器自动化（可选） | navigate, click, fill, etc. |

#### 安全机制
技能执行前会经过以下安全检查:
1. **HITL 审批** - 敏感操作需要人工批准
2. **路径访问控制** - 文件操作受限于安全路径
3. **命令白名单** - 可执行命令受白名单限制
4. **资源配额** - 限制执行时间和资源使用

#### 技能开发示例
```python
from .base import BaseSkill

class MyCustomSkill(BaseSkill):
    name = "my_custom_skill"
    description = "我的自定义技能"
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["do_something"]},
            "param1": {"type": "string"}
        },
        "required": ["action"]
    }
    
    async def execute(self, action: str, params: dict):
        if action == "do_something":
            return {"status": "success", "result": "完成"}
        return {"status": "error", "message": "未知动作"}
```

---

### 4. LLM 模块 - 大语言模型服务

**文件位置**: [cognicore/src/core/llm/](file:///e:/CogniCore-Portable/cognicore/src/core/llm/)

#### OllamaService
Ollama LLM 服务实现。

**核心方法**:
- `chat(messages, **kwargs)` - 聊天接口（同步，带重试和缓存）
- `async_chat(messages, **kwargs)` - 异步聊天接口
- `stream_chat(messages, tools, model)` - 流式聊天接口
- `generate(prompt, **kwargs)` - 文本生成接口
- `embed(text, **kwargs)` - 文本嵌入接口
- `list_models()` - 列出可用模型
- `pull_model(model)` - 拉取模型
- `chat_with_tools(messages, tools, **kwargs)` - 带工具调用的聊天
- `execute_tool_call(tool_call, tools)` - 执行工具调用

**配置项**:
```python
base_url: str = "http://localhost:11434"
model: str = "llama3.1:8b"
timeout: int = 30
```

#### LLMFactory
LLM 服务工厂，用于创建不同的 LLM 服务实例。

#### Model Adapters
模型适配器，用于适配不同模型的消息和工具格式:
- `BaseModelAdapter` - 基类适配器
- `OllamaAdapter` - Ollama 适配器
- `KimiAdapter` - Kimi 适配器
- `DeepSeekAdapter` - DeepSeek 适配器

---

### 5. Agent 模块 - 多代理系统

**文件位置**: [cognicore/src/core/agent/](file:///e:/CogniCore-Portable/cognicore/src/core/agent/)

#### AgentCoordinator
代理协调器，负责协调多个代理完成复杂任务。

**核心方法**:
- `process_task(goal, context)` - 处理任务
- `process_with_react(task, context)` - 使用 ReAct 模式处理任务

#### 代理类型
| 代理名称 | 角色 | 职责 |
|---------|------|------|
| `planner` | 规划者 | 制定任务计划 |
| `executor` | 执行者 | 执行具体任务 |
| `critic` | 批评者 | 评估结果质量 |
| `validator` | 验证者 | 验证执行正确性 |
| `multi_layer_agent` | 多层代理 | 复杂任务处理 |

#### AgentProfile
代理配置文件，定义每个代理的:
- 角色描述
- 系统提示词
- 可用工具
- 能力范围

---

### 6. API 路由模块

**文件位置**: [cognicore/src/api/routes.py](file:///e:/CogniCore-Portable/cognicore/src/api/routes.py)

#### 路由分类
| 路由前缀 | 功能 |
|---------|------|
| `/health` | 健康检查 |
| `/api/agent` | 代理任务处理 |
| `/api/memory` | 记忆系统操作 |
| `/api/llm` | LLM 服务 |
| `/api/rag` | RAG 检索 |
| `/api/multimodal/rag` | 多模态 RAG |
| `/api/feedback` | 反馈管理 |
| `/api/tools` | 工具管理 |
| `/api/skills` | 技能管理 |
| `/api/user-profile` | 用户画像 |
| `/api/hitl` | 人机协同审批 |
| `/mcp` | MCP 协议 |
| `/ws` | WebSocket |

---

### 7. 其他核心模块

#### Plugin Manager - 插件系统
**文件**: [cognicore/src/core/plugins/plugin_manager.py](file:///e:/CogniCore-Portable/cognicore/src/core/plugins/plugin_manager.py)

支持动态加载和管理插件。

#### RAG Service - 检索增强生成
**文件**: [cognicore/src/core/rag/rag_service.py](file:///e:/CogniCore-Portable/cognicore/src/core/rag/rag_service.py)

提供知识库的文档添加、检索和问答功能。

#### Feedback Manager - 反馈管理
**文件**: [cognicore/src/core/feedback/feedback_manager.py](file:///e:/CogniCore-Portable/cognicore/src/core/feedback/feedback_manager.py)

收集、存储和分析用户反馈。

#### Sandbox Security - 安全沙箱
**文件**: [cognicore/src/core/sandbox/security.py](file:///e:/CogniCore-Portable/cognicore/src/core/sandbox/security.py)

提供安全检查、HITL 审批、资源限制等功能。

---

## API 接口文档

### 健康检查接口

#### GET /health
健康检查，返回系统状态。

**响应示例**:
```json
{
  "status": "healthy",
  "service": "CogniCore",
  "version": "2.1.0",
  "timestamp": "2026-05-22T10:30:00",
  "checks": {
    "memory": {"status": "healthy", "message": "1573 entries memories记录"},
    "skills": {"status": "healthy", "message": "12 skills"},
    "resources": {"status": "healthy", "message": "CPU:15% MEM:45% DISK:60%"}
  }
}
```

#### GET /health/detailed
详细健康检查，包含告警信息和建议。

---

### 系统信息接口

#### GET /api/info
获取 CogniCore 系统信息。

---

### 代理接口

#### POST /api/agent/task
处理复杂任务（代理编排）。

**请求参数**:
```json
{
  "session_id": "string",
  "goal": "string",
  "context": {},
  "agent": "string (optional)",
  "model": "string (optional)"
}
```

#### POST /api/agent/react
使用 ReAct 模式处理任务。

#### GET /api/agents
列出所有可用代理。

#### GET /api/agents/{agent_name}
获取特定代理详情。

---

### 记忆系统接口

#### POST /api/memory/search
搜索记忆。

**请求参数**:
```json
{
  "session_id": "string",
  "query": "string",
  "limit": 5
}
```

#### POST /api/memory/save
保存记忆。

#### GET /api/memory/statistics
获取记忆系统统计。

#### GET /api/memory/usage
获取记忆使用分析。

#### POST /api/memory/clear
清空所有记忆（谨慎使用）。

#### POST /api/memory/learn
触发自主学习。

---

### LLM 接口

#### POST /api/llm/chat-with-tools
带工具调用的聊天接口。

**请求参数**:
```json
{
  "messages": [{"role": "user", "content": "string"}],
  "tools": []
}
```

#### POST /api/llm/execute-tool
执行工具调用。

#### GET /api/llm/models
列出可用 LLM 模型。

---

### RAG 接口

#### POST /api/rag/query
RAG 查询接口。

#### POST /api/rag/add-documents
添加文档到 RAG 知识库。

#### GET /api/rag/stats
获取 RAG 知识库统计。

#### POST /api/rag/clear
清空 RAG 知识库。

---

### 技能和工具接口

#### GET /api/skills
列出所有技能。

#### GET /api/skills/stats
获取技能统计。

#### GET /api/tools
列出所有工具。

---

### HITL 审批接口

#### GET /api/hitl/tasks
获取所有挂起等待审批的任务。

#### POST /api/hitl/approve/{task_id}
批准挂起的任务。

#### POST /api/hitl/deny/{task_id}
拒绝挂起的任务。

---

## 配置说明

### 主配置文件
**文件位置**: [config/cognicore.yaml](file:///e:/CogniCore-Portable/config/cognicore.yaml), [cognicore/config.yaml](file:///e:/CogniCore-Portable/cognicore/config.yaml)

### 配置项详解

```yaml
app:
  debug: false
  name: "CogniCore Portable"
  version: "2.1.0"

models:
  default: "llama3.1:8b"
  ollama_url: "http://192.168.3.105:11434"
  refresh_interval: 300
  providers:
    ollama:
      enabled: true
      models: []
  assistants:
    enabled: false

server:
  host: "0.0.0.0"
  port: 8002
  workers: 1

knowledge:
  enabled: false

voice:
  enabled: false

memory:
  directory: "data/memory"
  vector_model: "ollama:nomic-embed-text-v2-moe"
  vector_db_path: "data/vector_db"
```

### 环境变量配置
系统也支持通过环境变量配置（使用 Pydantic Settings）:

| 环境变量前缀 | 对应配置 |
|-------------|---------|
| `LLM_*` | LLM 配置 |
| `AGENT_*` | 代理配置 |
| `MEMORY_*` | 记忆配置 |
| `TOOL_*` | 工具配置 |
| `LOGGING_*` | 日志配置 |
| `SYSTEM_*` | 系统配置 |

---

## 运行部署

### 系统要求

| 资源 | 最低配置 | 推荐配置 |
|-----|---------|---------|
| 操作系统 | Windows 10/11 64位 | Windows 10/11 64位 |
| 内存 | 4GB | 8GB+ |
| 磁盘空间 | 2GB（不含模型） | 10GB+ |
| CPU | 双核 | 四核及以上 |

### 快速启动

#### Windows 用户
1. 双击 `start.bat`
2. 浏览器自动打开 http://localhost:8002
3. 看到服务信息即表示成功

#### 手动启动
```bash
# 使用统一启动脚本
python run.py

# 或直接启动应用
cd cognicore
python app.py --port 8002 --host 127.0.0.1
```

### 命令行参数

**run.py 支持的命令**:
```bash
# 启动服务
python run.py

# 停止服务
python run.py --stop

# 检查状态
python run.py --status

# 显示系统信息
python run.py --info
```

**app.py 支持的参数**:
```bash
python app.py --port 8002 --host 127.0.0.1 --force
```

### 启用 Ollama AI 对话

#### 方法 1: 安装 Ollama（推荐）
1. 访问 https://ollama.com/download/windows
2. 下载并安装 Ollama
3. 复制 ollama.exe 到项目的 `ollama/` 目录
4. 双击 `start.bat`，系统会自动下载默认模型（qwen2.5:1.5b）

#### 方法 2: 使用远程 Ollama
修改配置中的 `ollama_url` 指向远程 Ollama 服务。

### 停止服务

#### Windows 用户
双击 `stop.bat`

#### 命令行
```bash
python run.py --stop

# 或在运行窗口按 Ctrl+C
```

---

## 开发指南

### 项目依赖安装

```bash
cd cognicore
pip install -r requirements.txt
```

**主要依赖**:
- fastapi - Web 框架
- uvicorn - ASGI 服务器
- pydantic - 数据验证
- pydantic-settings - 配置管理
- chromadb - 向量数据库
- httpx - HTTP 客户端
- psutil - 系统信息
- python-json-logger - 结构化日志

### 代码风格
项目遵循以下规范:
- 使用 Black 格式化代码
- 使用 Flake8 进行代码检查
- 使用 MyPy 进行类型检查
- 中文注释，清晰的变量命名

### 扩展开发

#### 添加新技能
1. 在 `cognicore/src/core/skills/` 创建新的技能文件
2. 继承 `BaseSkill` 类
3. 在 `SkillManager` 中注册
4. 实现 `execute` 方法

#### 添加新的记忆类型
1. 在 `cognicore/src/core/memory/` 创建新的记忆类
2. 在 `UnifiedMemorySystem` 中集成
3. 实现存储和检索方法

#### 添加新的 LLM 适配器
1. 在 `cognicore/src/core/llm/adapters/` 创建新的适配器
2. 继承 `BaseModelAdapter`
3. 在工厂类中注册

### 测试
```bash
# 运行测试
cd cognicore
pytest
```

### 日志
日志文件位置:
- 主日志: `cognicore/logs/app.log`
- Ollama 日志: `logs/ollama.log`
- 其他运行时日志在相应目录

---

## 附录

### 核心文件索引

以下是对应主要模块的核心文件路径：

#### 启动与配置
- [run.py](file:///e:/CogniCore-Portable/run.py) - 统一启动入口
- [cognicore/app.py](file:///e:/CogniCore-Portable/cognicore/app.py) - FastAPI 应用入口
- [cognicore/launcher.py](file:///e:/CogniCore-Portable/cognicore/launcher.py) - 启动器
- [cognicore/config.yaml](file:///e:/CogniCore-Portable/cognicore/config.yaml) - 应用配置
- [config/cognicore.yaml](file:///e:/CogniCore-Portable/config/cognicore.yaml) - 主配置文件

#### 核心模块
- [cognicore/src/core/assistant.py](file:///e:/CogniCore-Portable/cognicore/src/core/assistant.py) - 智能助手核心
- [cognicore/src/core/skill_manager.py](file:///e:/CogniCore-Portable/cognicore/src/core/skill_manager.py) - 技能管理器
- [cognicore/src/core/config/config.py](file:///e:/CogniCore-Portable/cognicore/src/core/config/config.py) - 配置模块

#### 记忆系统
- [cognicore/src/core/memory/unified_memory.py](file:///e:/CogniCore-Portable/cognicore/src/core/memory/unified_memory.py) - 统一记忆系统
- [cognicore/src/core/memory/memory_json.py](file:///e:/CogniCore-Portable/cognicore/src/core/memory/memory_json.py) - JSON 记忆
- [cognicore/src/core/memory/memory_vector.py](file:///e:/CogniCore-Portable/cognicore/src/core/memory/memory_vector.py) - 向量记忆
- [cognicore/src/core/memory/memory_kg.py](file:///e:/CogniCore-Portable/cognicore/src/core/memory/memory_kg.py) - 知识图谱记忆
- [cognicore/src/core/memory/chromadb_memory.py](file:///e:/CogniCore-Portable/cognicore/src/core/memory/chromadb_memory.py) - ChromaDB 记忆
- [cognicore/src/core/memory/contextual_memory.py](file:///e:/CogniCore-Portable/cognicore/src/core/memory/contextual_memory.py) - 情境记忆

#### LLM 服务
- [cognicore/src/core/llm/ollama_service.py](file:///e:/CogniCore-Portable/cognicore/src/core/llm/ollama_service.py) - Ollama 服务
- [cognicore/src/core/llm/llm_factory.py](file:///e:/CogniCore-Portable/cognicore/src/core/llm/llm_factory.py) - LLM 工厂
- [cognicore/src/core/llm/adapters/base.py](file:///e:/CogniCore-Portable/cognicore/src/core/llm/adapters/base.py) - 模型适配器基类

#### 代理系统
- [cognicore/src/core/agent/agent_coordinator.py](file:///e:/CogniCore-Portable/cognicore/src/core/agent/agent_coordinator.py) - 代理协调器
- [cognicore/src/core/agent/planner.py](file:///e:/CogniCore-Portable/cognicore/src/core/agent/planner.py) - 规划者
- [cognicore/src/core/agent/executor.py](file:///e:/CogniCore-Portable/cognicore/src/core/agent/executor.py) - 执行者
- [cognicore/src/core/agent/critic.py](file:///e:/CogniCore-Portable/cognicore/src/core/agent/critic.py) - 批评者

#### API 路由
- [cognicore/src/api/routes.py](file:///e:/CogniCore-Portable/cognicore/src/api/routes.py) - API 路由
- [cognicore/src/api/websocket_manager.py](file:///e:/CogniCore-Portable/cognicore/src/api/websocket_manager.py) - WebSocket 管理

#### 技能系统
- [cognicore/src/core/skills/base.py](file:///e:/CogniCore-Portable/cognicore/src/core/skills/base.py) - 技能基类
- [cognicore/src/core/skills/system.py](file:///e:/CogniCore-Portable/cognicore/src/core/skills/system.py) - 系统控制技能
- [cognicore/src/core/skills/file_manager.py](file:///e:/CogniCore-Portable/cognicore/src/core/skills/file_manager.py) - 文件管理技能
- [cognicore/src/core/skills/code_executor.py](file:///e:/CogniCore-Portable/cognicore/src/core/skills/code_executor.py) - 代码执行技能

#### RAG 服务
- [cognicore/src/core/rag/rag_service.py](file:///e:/CogniCore-Portable/cognicore/src/core/rag/rag_service.py) - RAG 服务
- [cognicore/src/core/rag/vector_retriever.py](file:///e:/CogniCore-Portable/cognicore/src/core/rag/vector_retriever.py) - 向量检索器
- [cognicore/src/core/rag/reranker.py](file:///e:/CogniCore-Portable/cognicore/src/core/rag/reranker.py) - 重排序器

#### 其他核心模块
- [cognicore/src/core/plugins/plugin_manager.py](file:///e:/CogniCore-Portable/cognicore/src/core/plugins/plugin_manager.py) - 插件管理器
- [cognicore/src/core/feedback/feedback_manager.py](file:///e:/CogniCore-Portable/cognicore/src/core/feedback/feedback_manager.py) - 反馈管理器
- [cognicore/src/core/sandbox/security.py](file:///e:/CogniCore-Portable/cognicore/src/core/sandbox/security.py) - 安全沙箱

#### 工具与实用程序
- [cognicore/src/core/tools/registry.py](file:///e:/CogniCore-Portable/cognicore/src/core/tools/registry.py) - 工具注册表
- [cognicore/src/core/tools/utility_tools.py](file:///e:/CogniCore-Portable/cognicore/src/core/tools/utility_tools.py) - 实用工具
- [cognicore/src/core/utils/logging_utils.py](file:///e:/CogniCore-Portable/cognicore/src/core/utils/logging_utils.py) - 日志工具
- [cognicore/src/core/utils/retry.py](file:///e:/CogniCore-Portable/cognicore/src/core/utils/retry.py) - 重试工具
- [cognicore/src/utils/optimization.py](file:///e:/CogniCore-Portable/cognicore/src/utils/optimization.py) - 优化工具

#### 服务模块
- [cognicore/src/services/voice/stt_service.py](file:///e:/CogniCore-Portable/cognicore/src/services/voice/stt_service.py) - 语音转文字
- [cognicore/src/services/voice/tts_service.py](file:///e:/CogniCore-Portable/cognicore/src/services/voice/tts_service.py) - 文字转语音
- [cognicore/src/services/video/video_service.py](file:///e:/CogniCore-Portable/cognicore/src/services/video/video_service.py) - 视频服务

#### 测试文件
- [tests/test_async_io.py](file:///e:/CogniCore-Portable/tests/test_async_io.py) - 异步 IO 测试
- [tests/test_cache.py](file:///e:/CogniCore-Portable/tests/test_cache.py) - 缓存测试
- [cognicore/tests/test_utils.py](file:///e:/CogniCore-Portable/cognicore/tests/test_utils.py) - 工具测试
- [cognicore/tests/test_calculate.py](file:///e:/CogniCore-Portable/cognicore/tests/test_calculate.py) - 计算测试

### 相关链接
- GitHub: https://github.com/anomalyco/opencode
- Ollama: https://ollama.com

### 版本历史
- **v2.1.0** - 当前版本，完整的多代理、记忆、技能系统
- 早期版本 - 基础功能实现

### 联系方式
如有问题或建议，请通过 GitHub 仓库提交 Issue。

---

**文档结束**
