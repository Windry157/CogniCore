# 🎯 CogniCore-Portable 快速使用指南

**时间：2026-05-23

---

## 🚀 如何启动 CogniCore？

### 方法1：U盘便携启动（推荐！）

1. 插入U盘
2. 进入 `F:\CogniCore-Portable\cognicore` 文件夹
3. **双击** `start_portable.bat`
4. 等待启动完成

### 方法2：查看运行状态

1. 进入 `F:\CogniCore-Portable\cognicore` 文件夹
2. **双击** `start.bat`

---

## 🌐 如何访问Web界面？

### 默认端口：**8002**

启动后，在浏览器中打开：

```
http://localhost:8002/ui/dashboard
```

或

```
http://127.0.0.1:8002/ui/dashboard
```

---

## 📱 主要功能入口

| 功能 | 访问地址 |
|------|----------|
| **Web仪表板** | http://localhost:8002/ui/dashboard |
| **API文档** | http://localhost:8002/docs |
| **健康检查** | http://localhost:8002/health |
| **完整健康报告** | http://localhost:8002/health/full |
| **运营仪表板** | http://localhost:8002/ops/dashboard |
| **认知系统** | http://localhost:8002/api/cognition/ask |
| **认知统计** | http://localhost:8002/api/cognition/stats |
| **熔断器状态** | http://localhost:8002/api/resilience/circuit |
| **系统状态** | http://localhost:8002/health/state |

---

## 🔧 常用操作

### 1. 检查系统是否运行

浏览器打开：http://localhost:8002/health

### 2. 使用API

API文档地址：http://localhost:8002/docs

### 3. 查看日志

日志文件位置：`F:\CogniCore-Portable\cognicore\logs\app.log`

---

## ⚠️ 常见问题

### Q: 端口8002被占用？
A: 修改 `app.py` 中的端口号，或停止占用8002端口的程序。

### Q: 前端无法访问？
A: 确保服务已启动，检查浏览器控制台是否有CORS错误。

### Q: 如何停止服务？
A: 关闭终端窗口，或按 Ctrl+C

---

## 🎯 快速测试流程

1. 双击 `start_portable.bat` 启动
2. 等待显示 "Uvicorn running on http://127.0.0.1:8002"
3. 浏览器打开 http://localhost:8002/ui/dashboard
4. 查看系统状态
5. 尝试发送请求到 /api/cognition/ask
