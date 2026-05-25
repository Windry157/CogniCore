# 🚀 CogniCore-Portable 部署清单与回滚计划

## 📋 文档信息

| 项目 | 内容 |
|------|------|
| **系统名称** | CogniCore-Portable |
| **版本** | 1.0 - Production Release |
| **最后更新** | 2026-05-23 |
| **状态** | ✅ Ready for Deployment |

---

## 🚀 1. 部署前检查清单

### 1.1 环境检查

| 检查项 | 状态 | 说明 | 确认人 |
|--------|------|------|--------|
| Python 3.8+ 已安装 | ☐ | `python --version` | |
| 目标系统有足够磁盘空间 (>100MB) | ☐ | 检查可用空间 | |
| 目标路径有读写权限 | ☐ | 测试创建文件 | |
| 端口 8002 未被占用 | ☐ | `netstat -ano` (Windows) | |

---

### 1.2 工件检查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `cognicore/` 目录完整 | ☐ | 包含所有文件 |
| `data/` 目录可写 | ☐ | 权限检查 |
| 配置文件 `config.yaml` 存在 | ☐ | 便携配置 |
| 依赖已就绪 (aiosqlite) | ☐ | 或使用便携 Python |

---

## 📦 2. 部署步骤（生产环境）

### 2.1 U 盘便携部署（推荐 - 零安装）

**适用场景**：需要在不同机器间移动，无安装权限

```batch
:: Windows 部署步骤
:: ====================================

:: 1. 插入 U 盘，复制 CogniCore-Portable 到 U 盘根目录
::
:: 2. 进入目录
cd E:\CogniCore-Portable\cognicore

:: 3. 双击执行一键启动
start_portable.bat

:: 4. 验证健康检查
:: 浏览器访问: http://localhost:8002/health/full
:: 看到 {"overall_status": "healthy"} 即为成功
```

---

### 2.2 固定机器部署

**适用场景**：服务器或固定工作站

```bash
# 1. 创建部署目录
mkdir -p /opt/cognicore
cd /opt/cognicore

# 2. 复制所有文件到目标目录
# (从 U 盘或其他位置复制)

# 3. 安装依赖
pip install aiosqlite

# 4. 首次健康检查
python -m src.core.robust_data_pipeline

# 5. 启动服务
python app.py
# 或使用 launcher
python launcher.py
```

---

## 🛡️ 3. 回滚计划

### 3.1 回滚触发条件

| 触发条件 | 严重程度 | 自动回滚 |
|----------|----------|----------|
| 健康检查返回 CRITICAL | P0 | ☐ 否 (人工判断) |
| 超过 50% 请求失败 | P0 | ☐ 否 |
| 数据损坏或丢失 | P0 | ☐ 否 |
| 系统无法启动 | P1 | ☐ 否 |
| 性能严重下降 (>2s/请求) | P2 | ☐ 否 |

---

### 3.2 回滚执行步骤

**⚠️ 回滚是最后的手段，请先尝试运维手册中的故障排查**

```batch
:: Windows 回滚流程
:: ====================================

:: 步骤 1: 停止系统 (优雅关闭)
:: 按 Ctrl+C 或在任务管理器结束进程

:: 步骤 2: 备份当前状态（防止回滚失败）
set BACKUP_NAME=failed_state_%date:~0,4%%date:~5,2%%date:~8,2%
xcopy cognicore %BACKUP_NAME% /E /I /H /Y

:: 步骤 3: 找到最近的稳定版本
:: 检查 backup_* 目录，找到最后一次正常运行的版本

:: 步骤 4: 回滚文件
:: 重命名当前版本
ren cognicore cognicore_failed
:: 复制稳定版本
xcopy backup_YYYYMMDD cognicore /E /I /H /Y

:: 步骤 5: 验证回滚
cd cognicore
start_robust_pipeline.bat
:: 检查: http://localhost:8002/health/full

:: 步骤 6: 确认后，可保留失败版本 7 天用于排查
```

---

### 3.3 数据级回滚

如果仅数据损坏，无需回滚整个系统：

```sql
-- SQLite 数据库回滚步骤
-- 1. 关闭应用
-- 2. 替换 pipeline.db 为备份版本
-- 3. 重启应用
```

---

## ✅ 4. 部署后验证清单

### 4.1 功能验证

| 检查项 | 命令/操作 | 预期结果 | 验证人 |
|--------|-----------|----------|--------|
| 服务启动 | `start_robust_pipeline.bat` | 无错误，正常退出测试 | |
| 健康检查 | 访问 `/health/full` | `{"overall_status": "healthy"}` | |
| Web UI | 访问 `/ui/dashboard` | 界面正常显示 | |
| 数据管道 | 运行测试 | 3 个测试项都通过 | |
| 工业级测试 | 运行 `robust_data_pipeline` | 完整容错测试通过 | |

---

### 4.2 容错验证

| 检查项 | 操作 | 预期结果 |
|--------|------|----------|
| 幂等性 | 重复发送相同 event_id | 只处理一次 |
| 重试机制 | 模拟瞬时失败 | 自动重试 |
| DLQ | 发送无效数据 | 进入 DLQ，不阻塞 |

---

## 📊 5. 监控与告警（部署后）

### 5.1 日常健康检查

建议频率：每日一次

检查内容：
1. 健康检查端点：`/health/full`
2. DLQ 数量：`SELECT COUNT(*) FROM dead_letter_queue WHERE status='pending'`
3. 磁盘空间
4. 错误日志扫描

---

## 📝 6. 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0 | 2026-05-23 | 初始生产版本 | - |

---

## 📞 7. 紧急联系

部署期间如遇问题，请按以下顺序查阅：
1. **运维手册 (RUNBOOK.md)** - 第一优先
2. **架构蓝图 (ARCHITECTURE.md)** - 系统理解
3. **项目 README** - 基础信息

---

**部署清单版本 1.0 - 2026-05-23**
