# 🏥 CogniCore-Portable 运维手册 (Runbook)

## 📋 文档信息

| 项目 | 内容 |
|------|------|
| **系统名称** | CogniCore-Portable |
| **版本** | 1.0 - Production Ready |
| **最后更新** | 2026-05-23 |
| **维护状态** | ✅ Active |

---

## 🎯 目录

1. [系统概述](#1-系统概述)
2. [快速启动](#2-快速启动)
3. [故障排查指南](#3-故障排查指南)
4. [健康检查与监控](#4-健康检查与监控)
5. [数据备份与恢复](#5-数据备份与恢复)
6. [常见问题 (FAQ)](#6-常见问题-faq)

---

## 1. 系统概述

### 1.1 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户接入层 (API)                            │
│                      FastAPI + 前端界面                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐ ┌──────▼───────┐ ┌──────▼───────┐
│  业务逻辑层    │ │  数据管道层   │ │  健康监控层   │
│ (认知系统)     │ │ (容错体系)    │ │ (指标/告警)  │
└───────┬────────┘ └──────┬───────┘ └──────┬───────┘
        │                 │                  │
┌───────▼──────────────────▼──────────────────▼───────┐
│                  数据持久化层                        │
│  SQLite (主数据) + DuckDB (分析) + Redis (可选)     │
└─────────────────────────────────────────────────────┘
```

### 1.2 关键特性

| 特性 | 实现 | 说明 |
|------|------|------|
| ✅ 工业级容错 | 重试、幂等、DLQ | `robust_data_pipeline.py` |
| ✅ 系统健康检查 | CPU、内存、磁盘、业务 | `health/` |
| ✅ 故障恢复 | 优雅关闭、状态持久化 | `recovery.py` |
| ✅ U盘便携 | 相对路径、零配置 | 完整支持 |

---

## 2. 快速启动

### 2.1 Windows 一键启动（推荐）

```cmd
cd cognicore
start_robust_pipeline.bat
```

### 2.2 手动启动

```bash
# 1. 确保 Python 3.8+
python --version

# 2. 安装依赖
pip install aiosqlite

# 3. 启动完整系统
python -m src.core.robust_data_pipeline
# 或启动 Web UI
python app.py
```

### 2.3 验证启动成功

启动后访问以下端点验证：

| 端点 | 验证内容 |
|------|----------|
| `http://localhost:8002/health/full` | 完整健康检查 |
| `http://localhost:8002/health/state` | 系统状态 |
| `http://localhost:8002/ops/dashboard` | 运营仪表板 |

---

## 3. 故障排查指南

### 3.1 数据库连接失败

**症状**：
```
ERROR - Could not connect to database
```

**排查步骤**：
1. 检查 `data/` 目录是否存在且可写
2. 检查磁盘空间：`dir cognicore\data`
3. 检查文件权限
4. 查看日志：`logs/` 目录

**恢复流程**：
1. 停止系统
2. 备份现有数据库文件（如有）
3. 删除损坏的 `pipeline.db`
4. 重启系统，自动重建
5. 从备份恢复数据（如需要）

---

### 3.2 消息堆积过高

**症状**：
- 健康检查显示 DLQ 数量 > 0
- 处理延迟持续上升

**排查步骤**：
1. 检查 DLQ 表：
   ```sql
   SELECT * FROM dead_letter_queue WHERE status = 'pending';
   ```
2. 查看错误信息
3. 确认是数据问题还是系统问题

**恢复流程**：
1. 如果是数据问题：修复数据后手动重新入队
2. 如果是系统问题：重启消费者
3. 监控处理速率

---

### 3.3 系统响应慢/超时

**症状**：
- API 响应时间 > 5s
- 健康检查警告 CPU/内存

**排查步骤**：
1. 检查任务管理器 → 进程 → Python CPU/内存
2. 查看日志文件 `logs/cognicore.log`
3. 检查健康指标：`http://localhost:8002/health/full`

**恢复流程**：
1. 如内存泄漏 → 优雅重启
2. 如 CPU 过高 → 检查是否有循环任务
3. 启动时使用 `start_portable.bat` 安全模式

---

### 3.4 优雅关闭失败

**症状**：
- Ctrl+C 后进程仍在运行
- 状态文件显示异常

**恢复流程**：
1. Windows：打开任务管理器 → 结束 Python 进程
2. Linux/Mac：`pkill -f "python.*cognicore"`
3. 检查状态文件：`data/system/system_state.json`
4. 删除状态文件 → 正常重启

---

## 4. 健康检查与监控

### 4.1 完整健康检查

访问：`http://localhost:8002/health/full`

检查项：
| 指标 | 警告阈值 | 严重阈值 |
|------|----------|----------|
| CPU 使用率 | >75% | >90% |
| 内存使用率 | >80% | >95% |
| 磁盘使用率 | >85% | >95% |

### 4.2 关键日志位置

| 日志类型 | 位置 |
|----------|------|
| 应用日志 | `logs/cognicore.log` |
| 健康历史 | `data/health/health_history.jsonl` |
| 审计日志 | SQLite 数据库 `audit_log` 表 |
| 死信队列 | SQLite 数据库 `dead_letter_queue` 表 |

---

## 5. 数据备份与恢复

### 5.1 备份策略

#### 每日自动备份（推荐）

由于是 U 盘便携系统，建议：
- 每日结束时，将整个 `cognicore/` 目录复制到备份位置
- 保留最近 7 天的备份

#### 手动备份命令（Windows）

```cmd
:: 备份命令 - 复制到 backup_YYYYMMDD
set BACKUP_NAME=backup_%date:~0,4%%date:~5,2%%date:~8,2%
xcopy cognicore %BACKUP_NAME% /E /I /H /Y
echo Backup complete: %BACKUP_NAME%
```

### 5.2 恢复流程

1. 停止系统
2. 重命名当前 `cognicore` 目录 → `cognicore_old`
3. 从备份复制到 `cognicore`
4. 启动系统
5. 验证完整性

---

## 6. 常见问题 (FAQ)

### Q1: 系统可以离线运行吗？

A: 可以！CogniCore-Portable 是完全离线设计，除了可选的 Ollama AI 后端连接。

### Q2: 如何判断当前是 U 盘模式？

A: 所有路径都是相对路径，配置在 `config.yaml` 中。系统自动适配。

### Q3: DLQ 里的消息如何重新处理？

A: 查看 `dead_letter_queue` 表，修复数据后，手动调用数据管道重新入队。

### Q4: 如何设置监控告警？

A: 查看健康检查端点，设置阈值后使用 Prometheus/Grafana 或简单的脚本告警。

---

## 🆘 紧急联系

如需技术支持，查看项目文档：
- 项目 README：[README.md](file:///E:/CogniCore-Portable/README.md)
- 运营指南：[OPERATIONS_GUIDE.md](file:///E:/CogniCore-Portable/OPERATIONS_GUIDE.md)
- 架构文档：[DATA_PIPELINE_DESIGN.md](file:///E:/CogniCore-Portable/DATA_PIPELINE_DESIGN.md)

---

**运维手册版本 1.0 - 2026-05-23**
