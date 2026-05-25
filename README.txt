CogniCore Portable v2.1.0
==========================
随身携带的智能 AI 助手 - 插上 U 盘就能用！

总大小：46 MB（不含 AI 模型）
Python 运行环境已预置，无需安装。

目录结构
--------
  start.bat          - 启动 AI 服务（双击运行）
  stop.bat           - 停止所有服务
  bootstrap.ps1      - 首次运行准备（备用）
  README.txt         - 本文件

  venv\              - Python 虚拟环境（已就绪，34 MB）
  cognicore\         - AI 核心代码（1.3 MB）
  memory\            - 记忆数据（11 MB，1573+165 条）
  config\            - 配置文件
  data\              - 运行时数据
  logs\              - 运行日志
  ollama\            - Ollama 引擎（可选，需手动添加）

快速开始
--------
1. 插入 U 盘，双击 start.bat

2. 浏览器自动打开 http://localhost:8002

3. 看到 {"service":"CogniCore","version":"2.1.0"} 即成功

4. 关闭 start.bat 窗口即可停止服务

12 项技能开箱即用（系统控制、文件管理、搜索、翻译、
数据分析等），无需联网。

启用 AI 对话（可选）
--------------------
AI 对话需要 Ollama 引擎 + 一个 LLM 模型。由于网络原因，
Ollama 未预置，需手动操作：

1. 方法 A（推荐）：访问 https://ollama.com/download/windows
   下载 OllamaSetup.exe，安装后将 ollama.exe 复制到本目录的
   ollama\ 文件夹（约 200 MB）
   或方法 B：从 GitHub Releases 下载 ollama-windows-amd64-rocm.zip
   （约 335 MB，AMD GPU 兼容，解压后复制 ollama.exe 到 ollama\）

2. 双击 start.bat，首次运行时自动下载 AI 模型
   （qwen2.5:1.5b，约 1.1GB，仅需一次）

3. 启动后 Ollama 运行于端口 11434，全自动管理

最低配置
--------
- 系统：Windows 10/11 64位
- 内存：4GB+（推荐 8GB）
- 磁盘：2GB 可用空间（不含 AI 模型）
- CPU：双核以上（推荐 4 核）

技术支持
--------
GitHub: https://github.com/anomalyco/opencode
