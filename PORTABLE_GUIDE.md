# 🚀 CogniCore-Portable U盘即插即用指南

## 💡 简介

CogniCore-Portable 是专为U盘设计的 AI 助手，完全独立运行，**无需安装，即插即用，拔下就走**！

## ⚡ 快速开始

### Windows 用户

1. 将U盘插入电脑
2. 打开U盘目录，找到 **`cognicore/start_portable.bat`**
3. **双击运行**即可！

### Linux / macOS 用户

1. 将U盘插入电脑
2. 打开终端，进入U盘目录
3. 运行命令：
   ```bash
   cd /path/to/usb/cognicore
   chmod +x start_portable.sh
   ./start_portable.sh
   ```

---

## 📋 系统要求

| 项目 | 要求 |
|------|------|
| **Python** | 3.8 或更高 |
| **磁盘空间** | 最小 500MB (取决于模型大小) |
| **内存** | 建议 4GB+ |
| **Ollama (可选)** | 本地运行 LLM 需要 |

---

## 🎯 使用步骤

### 1️⃣ 启动服务

- Windows: 双击 `start_portable.bat`
- Linux/Mac: 运行 `./start_portable.sh`

首次运行会自动创建虚拟环境并安装依赖！

### 2️⃣ 访问界面

浏览器打开: **http://localhost:8002**

### 3️⃣ 开始使用

- 访问 Launcher: http://localhost:8002/launcher
- 或直接使用 API 端点

### 4️⃣ 安全退出

1. 在服务窗口按 **Ctrl+C** 停止服务
2. 等待服务完全停止
3. 安全弹出U盘

---

## 🔧 配置说明

### 配置文件位置

所有配置和数据都在U盘内，**不会写入系统**！

- **配置文件**: `cognicore/config.yaml`
- **数据目录**: `cognicore/data/`
- **日志目录**: `cognicore/logs/`

### 修改配置

编辑 `config.yaml` 即可修改设置，下次启动生效！

---

## 📦 目录结构

```
CogniCore-Portable/
├── cognicore/
│   ├── start_portable.bat    # Windows 一键启动
│   ├── start_portable.sh     # Linux/Mac 一键启动
│   ├── app.py                # 主程序
│   ├── launcher.py           # 启动器
│   ├── config.yaml           # 配置文件
│   ├── requirements.txt      # 依赖列表
│   ├── data/                 # [便携] 数据目录
│   │   ├── memory/
│   │   └── vector_db/
│   ├── logs/                 # [便携] 日志目录
│   ├── frontend/             # 前端界面
│   └── src/                  # 源代码
└── README.md                 # 本文件
```

---

## 🔒 隐私与安全

✅ **完全便携**: 所有数据保存在U盘内  
✅ **无系统修改**: 不修改注册表，不安装系统服务  
✅ **即插即用**: 插上使用，拔下即走  
✅ **零残留**: 不会在主机留下任何数据  

---

## ⚙️ 故障排除

### 问题1: Python 未找到

**解决**: 请先安装 Python 3.8 或更高版本

### 问题2: 端口被占用

**解决**:
- 编辑 `app.py` 中的默认端口
- 或使用命令行参数: `python app.py --port 8003`

### 问题3: 依赖安装失败

**解决**:
1. 删除 `venv` 目录
2. 重新运行启动脚本

### 问题4: 页面无法访问

**解决**:
- 确保服务已启动
- 检查防火墙设置
- 尝试访问 http://127.0.0.1:8002

---

## 💡 高级使用

### 使用自定义模型

1. 确保本地安装了 Ollama
2. 编辑 `config.yaml` 中的模型配置
3. 重启服务

### 备份数据

直接复制整个 `cognicore/data/` 目录即可！

---

## 📞 支持

如有问题，请检查:
1. `logs/app.log` 日志文件
2. 确保 Python 版本符合要求
3. 查看终端错误信息

---

**🎉 享受您的便携 AI 助手吧！**
