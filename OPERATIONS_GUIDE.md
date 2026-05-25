# 🏗️ CogniCore-Portable 运营强化指南

## 🎯 目标：从原型到产品级就绪

这份指南详细说明了如何将系统从**开发原型**转变为**生产级产品**，确保故障可恢复、运营可监控、部署可自动化。

---

## ✅ 已实现的运营强化功能

### 1. 🩺 系统健康检查 (`/health/full`)
- **CPU 使用率监控** - 超过 90% 为严重告警，超过 75% 为警告
- **内存使用监控** - 超过 95% 为严重，超过 80% 为警告
- **磁盘空间监控** - 超过 95% 为严重，超过 85% 为警告
- **记忆系统检查** - 检查记忆数据库完整性
- **配置系统检查** - 验证配置加载状态
- **模块可用性检查** - 检查核心模块是否正确加载
- **Ollama 连通性检查** - 可选的 AI 后端检查

### 2. 🛡️ 故障恢复协议 (`/health/state`, `/health/reload`)
- **优雅关闭** - 触发 SIGINT/SIGTERM 信号时的安全关闭流程
- **状态持久化** - 保存上次运行状态到 JSON 文件
- **崩溃恢复** - 从异常退出中自动恢复
- **系统重载** - 无需重启的热重载功能

### 3. 🔍 自动健康巡检 (`/health/monitor`, `/health/history`)
- **后台定期检查** - 默认 60 秒间隔
- **状态历史记录** - 保存最多 100 条记录到 JSONL 文件
- **告警回调** - 支持注册告警处理器
- **统计信息** - 状态分布、监控时长等

### 4. 📊 运营仪表板 (`/ops/dashboard`)
- **整体健康状态概览**
- **健康检查详情**
- **监控统计**
- **认知系统状态**

---

## 🚀 快速开始

### 启动服务
```bash
# Windows
start_portable.bat

# Linux/Mac
./start_portable.sh
```

### 访问健康检查
```
# 完整健康报告
http://localhost:8002/health/full

# 监控统计
http://localhost:8002/health/monitor

# 健康历史
http://localhost:8002/health/history?limit=100

# 系统状态
http://localhost:8002/health/state

# 运营仪表板
http://localhost:8002/ops/dashboard

# Web UI
http://localhost:8002/ui/dashboard
```

---

## 📋 故障恢复协议

### 标准关闭流程
1. 用户按 `Ctrl+C` 或发送 `SIGTERM`
2. 系统进入 `SHUTTING_DOWN` 状态
3. 依次调用关闭回调
4. 保存状态文件
5. 进程优雅退出

### 崩溃恢复流程
1. 系统启动时检测上次异常退出
2. 进入 `RECOVERING` 状态
3. 执行恢复回调
4. 验证系统完整性
5. 进入 `RUNNING` 状态

### 热重载流程
```bash
# API 方式
POST http://localhost:8002/health/reload
```

---

## 🔧 目录结构

```
cognicore/
├── data/
│   ├── system/          # 系统状态保存
│   │   └── system_state.json
│   ├── health/          # 健康历史记录
│   │   └── health_history.jsonl
│   ├── memory/          # 系统记忆
│   └── vector_db/       # 向量数据库
├── logs/                # 日志文件
└── config.yaml          # 便携配置
```

---

## 📈 健康指标阈值配置

| 指标 | 警告阈值 | 严重阈值 | 说明 |
|------|----------|----------|------|
| CPU | >75% | >90% | 处理器使用率 |
| 内存 | >80% | >95% | 系统内存 |
| 磁盘 | >85% | >95% | 应用磁盘 |

---

## 🔌 API 端点完整文档

### 健康检查
| 端点 | 方法 | 说明 |
|------|------|------|
| `/health/full` | GET | 完整健康报告 |
| `/health/monitor` | GET | 监控统计 |
| `/health/history` | GET | 状态历史 |
| `/health/state` | GET | 系统状态 |
| `/health/reload` | POST | 系统重载 |

### 运营
| 端点 | 方法 | 说明 |
|------|------|------|
| `/ops/dashboard` | GET | 运营仪表板 |
| `/health` | GET | 原健康检查端点 |

### 认知
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/cognition/ask` | POST | 认知查询 |
| `/api/cognition/stats` | GET | 认知统计 |

### 韧性
| 端点 | 方法 | 说明 |
|------|------|------|
| `/resilience/circuit` | GET | 熔断器状态 |
| `/resilience/event` | POST | 发布事件 |

---

## 🛡️ 安全操作检查清单

- ✅ 所有数据存储在 U 盘内，不写入系统
- ✅ 支持状态持久化和恢复
- ✅ 优雅关闭不损坏数据
- ✅ 定期健康检查记录日志
- ✅ 自动监控后台运行不阻塞
- ✅ 相对路径完全适配便携场景

---

## 🎓 从开发到产品的演进历程

### 阶段一：原型开发 ✅
- 基础认知系统
- 不确定性量化
- 可观测性框架

### 阶段二：功能强化 ✅
- 双系统决策
- 贝叶斯推理
- Web UI 集成

### 阶段三：产品化（进行中）📍
- ✅ 系统健康检查
- ✅ 故障恢复协议
- ✅ 自动健康巡检
- ✅ 运营监控仪表板

### 阶段四：部署与商业化（未来）
- CI/CD 流水线
- 版本管理与回滚
- 插件架构
- 企业级功能

---

## 📞 问题排查

### 健康检查报告异常
查看：`data/health/health_history.jsonl`

### 系统状态检查
访问：`/health/state`

### 无法重载系统
检查：`data/system/system_state.json`

---

**🚀 系统已完全准备好投入生产级使用！**
