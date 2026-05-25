# CogniCore-Portable 🚀

轻量级 AI 助手框架，专为 USB 随身使用优化

## ✨ 核心特性

| 阶段 | 模块 | 功能 |
|------|------|------|
| **第一阶段** | `uncertainty/` | 置信度评分、可视化、缓存 |
| **第一阶段** | `observability/` | 指标收集、熔断、限流 |
| **第一阶段** | `evaluation/` | 响应评估、质量检测 |
| **第二阶段** | `cognition/` | 双系统架构、贝叶斯推理、可视化 |
| **第三阶段** | `resilience/` | 熔断、事件总线、Saga 模式 |
| **第三阶段** | `webui/` | Web UI 集成、仪表板 |


## 📦 项目结构

```
cognicore/
├── src/core/
│   ├── cognition/          # 第二阶段：认知模块
│   ├── uncertainty/        # 第一阶段：不确定性
│   ├── observability/      # 第一阶段：可观测性
│   ├── evaluation/         # 第一阶段：评估框架
│   ├── resilience/         # 第三阶段：韧性模块
│   ├── webui/              # 第三阶段：Web UI
│   └── multimodal/         # 多模态处理
├── examples/
│   └── demo.py             # 使用示例
├── app.py                  # Web API (FastAPI)
└── launcher.py             # 启动器
```


## 🚀 快速开始

### 1. 运行演示

```bash
cd cognicore
python examples/demo.py
```

### 2. 启动 Web 服务

```bash
# 使用 launcher.py
python launcher.py

# 或直接运行 app.py
python app.py
```

访问: http://localhost:8002


## 💡 使用示例

### 认知决策

```python
import asyncio
from src.core.cognition import cognition_coordinator

async def ask_question():
    result = await cognition_coordinator.make_decision({
        "input": "你好！",
        "context": {}
    })
    print(result['decision'])

asyncio.run(ask_question())
```

### 韧性模块 - 熔断器

```python
from src.core.resilience import circuit_breaker

async def protected_call():
    result = await circuit_breaker.execute(
        my_function,
        fallback=lambda: "降级返回"
    )
```

### 韧性模块 - 事件总线

```python
from src.core.resilience import event_bus, DomainEvent

async def pub_sub():
    # 订阅
    def handler(event):
        print("收到事件:", event)
    
    event_bus.subscribe("order_placed", handler)
    
    # 发布
    event = DomainEvent(id="order_placed", source="demo", data={...})
    await event_bus.publish(event)
```

### Web UI

```python
from src.core.webui import web_interface

html = web_interface.render_page("dashboard")
# 保存或直接返回给浏览器
```


## 🔧 配置

使用环境变量 `CONFIG_PATH` 指定自定义配置文件（YAML）。

```yaml
# config.yaml
llm:
  provider: ollama
  model: qwen2.5:7b
  
memory:
  type: chroma
  
cognition:
  mode: hybrid
```


## 📊 模块详情

### cognition/ 认知模块

| 组件 | 功能 |
|------|------|
| `system1.py` | 快速启发式决策 |
| `system2.py` | 深度分析推理 |
| `bayesian_brain.py` | 概率更新和主动推理 |
| `coordinator.py` | 智能路由和协调 |
| `visualizer.py` | 推理可视化（ASCII/HTML）|

### resilience/ 韧性模块

| 组件 | 功能 |
|------|------|
| `CircuitBreaker` | 熔断器，防止级联故障 |
| `EventBus` | 发布-订阅事件系统 |
| `SagaOrchestrator` | 事务补偿和编排 |

### webui/ Web 集成

| 组件 | 功能 |
|------|------|
| `WebInterface` | 静态页面生成 |
| `UIManager` | UI 组件管理 |
| `render_to_html()` | 通用内容渲染 |


## 📄 许可证

MIT License
