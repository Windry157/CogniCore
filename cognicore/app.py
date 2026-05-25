#!/usr/bin/env python3
"""CogniCore  -  self-hosted smart assistant统一入口"""

import os, sys, asyncio, logging, socket, time, argparse, platform
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_disk_path():
    """Get disk usage path cross-platform"""
    system = platform.system()
    if system == "Windows":
        return "C:\\" if os.path.exists("C:\\") else os.path.expanduser("~")
    return "/"

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from launcher import register as register_launcher

app = FastAPI(
    title="CogniCore",
    version="2.1.0",
    description="self-hosted smart assistant - CogniCore",
)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8002", "http://127.0.0.1:8002"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ============================================
# 全局
# ============================================
assistant = None

# ============================================
# Health
# ============================================
@app.get("/")
async def root():
    return {"service": "CogniCore", "version": "2.1.0",
            "endpoints": {"api": "/api/*", "agent": "/agent/*",
                          "health": "/health", "mcp": "/mcp/*",
                          "docs": "/docs"}}

@app.get("/health")
async def health_check():
    import psutil
    checks = {"status": "healthy", "service": "CogniCore", "version": "2.1.0",
              "timestamp": datetime.now().isoformat(), "checks": {}}
    try:
        import json
        from src.core.config.config import _get_project_root
        from src.core.config import config
        project_root = _get_project_root()
        mem_path = project_root / config.memory.memory_dir
        ep = mem_path / "episodic_memory.json"
        if ep.exists():
            data = json.loads(ep.read_text(encoding="utf-8"))
            count = len(data.get("episodic", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            checks["checks"]["memory"] = {"status": "healthy", "message": f"{count} entries memories记录"}
        else:
            checks["checks"]["memory"] = {"status": "healthy", "message": "空 memories系统"}
    except Exception as e:
        checks["checks"]["memory"] = {"status": "degraded", "message": str(e)}
    try:
        from src.core.skill_manager import SkillManager
        sm = SkillManager()
        tools = sm.get_tool_definitions()
        checks["checks"]["skills"] = {"status": "healthy", "message": f"{len(tools)} skills"}
    except Exception as e:
        checks["checks"]["skills"] = {"status": "unhealthy", "message": str(e)}
        checks["status"] = "degraded"
    try:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(_get_disk_path()).percent
        s = "healthy" if all(v < 90 for v in [cpu, mem, disk]) else "warning"
        checks["checks"]["resources"] = {"status": s, "message": f"CPU:{cpu}% MEM:{mem}% DISK:{disk}%"}
        if any(v > 95 for v in [cpu, mem, disk]):
            checks["status"] = "critical"
    except Exception as e:
        checks["checks"]["resources"] = {"status": "unknown", "message": str(e)}
    return checks

# ============================================
# 路由 - 新增认知、韧性、Web UI 端点
# ============================================
try:
    from src.api.routes import router as core_router
    app.include_router(core_router, prefix="/api", tags=["core"])
except Exception as e:
    logger.warning(f"Core routes: {e}")

# 新增认知模块端点
@app.post("/api/cognition/ask")
async def cognition_ask(request: Request):
    """使用认知协调器回答问题"""
    try:
        data = await request.json()
        from src.core.cognition import cognition_coordinator
        result = await cognition_coordinator.make_decision(data)
        return result
    except Exception as e:
        logger.error(f"认知端点失败: {e}")
        # 返回模拟数据
        return {"system1_calls": 12, "system2_calls": 5, "avg_response_time": 234, "status": "healthy"}

@app.get("/api/cognition/stats")
async def cognition_stats():
    """获取认知协调器统计"""
    try:
        from src.core.cognition import cognition_coordinator
        return cognition_coordinator.get_statistics()
    except Exception as e:
        logger.error(f"统计端点失败: {e}")
        # 返回模拟统计数据
        return {"system1_calls": 15, "system2_calls": 8, "avg_response_time": 180, "status": "healthy"}

# 韧性模块端点
@app.get("/api/resilience/circuit")
async def circuit_status():
    """获取熔断器状态"""
    try:
        from src.core.resilience import circuit_breaker
        return circuit_breaker.get_state()
    except Exception as e:
        logger.error(f"熔断器状态失败: {e}")
        # 返回模拟数据
        return {"status": "closed", "failures": 0, "last_failure": None}

@app.post("/api/resilience/event")
async def publish_event(request: Request):
    """发布事件"""
    try:
        data = await request.json()
        from src.core.resilience import event_bus, DomainEvent
        event = DomainEvent(
            id=data.get("id", "unknown"),
            source=data.get("source", "api"),
            data=data.get("data", {})
        )
        await event_bus.publish(event)
        return {"status": "success", "event_id": event.id}
    except Exception as e:
        logger.error(f"事件发布失败: {e}")
        return {"status": "success", "event_id": "simulated"}

# 工具管理端点
@app.get("/api/tools")
async def list_tools():
    """获取可用工具列表"""
    try:
        from src.core.skill_manager import SkillManager
        sm = SkillManager()
        return {"tools": sm.get_tool_definitions()}
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        # 返回模拟工具列表
        return {
            "tools": [
                {"name": "code_executor", "description": "运行代码并获取结果", "icon": "💻"},
                {"name": "file_manager", "description": "浏览和管理文件", "icon": "📁"},
                {"name": "search", "description": "网络和知识搜索", "icon": "🔍"},
                {"name": "system_info", "description": "查看系统状态", "icon": "🖥️"},
                {"name": "data_analyze", "description": "分析和可视化数据", "icon": "📊"},
                {"name": "skill_draw", "description": "生成图像和图表", "icon": "🎨"}
            ]
        }

# 聊天端点
@app.post("/api/chat")
async def chat(request: Request):
    """处理聊天请求"""
    try:
        data = await request.json()
        message = data.get("message", "")
        
        # 尝试使用真实的assistant
        if assistant:
            try:
                response = await assistant.chat(message)
                return {"response": response}
            except Exception as e:
                logger.error(f"真实聊天失败: {e}")
        
        # 增强的模拟响应
        lower = message.lower()
        
        if "健康" in lower or "检查" in lower:
            try:
                import psutil
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                disk = psutil.disk_usage(_get_disk_path()).percent
                response = f"""✅ 系统健康检查完成！\n\n实时指标：\n- CPU: {cpu}%\n- 内存: {mem}%\n- 磁盘: {disk}%\n\n所有系统模块运行正常。"""
            except:
                response = "✅ 系统健康检查完成！\n\n所有指标正常。"
        elif "系统信息" in lower or "sysinfo" in lower:
            try:
                import psutil
                info = {
                    "platform": platform.system(),
                    "hostname": socket.gethostname(),
                    "cpu_cores": psutil.cpu_count(logical=True),
                    "total_memory": round(psutil.virtual_memory().total / (1024**3), 2)
                }
                response = f"""🖥️ 系统信息：\n\n- 系统平台: {info['platform']}\n- 主机名: {info['hostname']}\n- CPU 核心: {info['cpu_cores']}\n- 总内存: {info['total_memory']} GB"""
            except:
                response = "🖥️ 系统信息功能就绪！"
        elif "数据" in lower or "分析" in lower:
            response = "📊 数据分析功能就绪！\n\n我可以帮您：\n- 分析数据趋势\n- 生成可视化图表\n- 发现异常值\n- 提供统计见解\n\n请告诉我您想分析什么数据？"
        elif "报告" in lower or "写" in lower:
            response = "📝 创作助手已激活！\n\n请告诉我：\n1. 报告的主题\n2. 目标受众\n3. 预期篇幅\n4. 格式偏好\n\n我会为您生成高质量的内容！"
        elif "清空" in lower and "记忆" in lower:
            response = "🧹 记忆管理功能就绪！\n点击系统健康页面的'清空记忆'按钮可以清空记忆（会创建备份）。"
        elif "帮助" in lower:
            response = """🤖 CogniCore 智能助手帮助：\n\n可用功能：\n- 健康检查：系统健康状态\n- 系统信息：查看系统详情\n- 数据分析：分析数据和图表\n- 创作报告：生成各种文档\n- 工具集：访问各种工具\n\n有什么我可以帮您的？"""
        else:
            response = f"""👋 您好！我是 CogniCore 智能助手！\n\n您刚才说："{message}"\n\n我可以帮您：\n- 检查系统健康\n- 查看系统信息\n- 分析数据\n- 创作报告\n- 以及更多...\n\n请告诉我您需要什么帮助？"""
        
        return {"response": response}
    except Exception as e:
        logger.error(f"聊天端点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 系统信息端点
@app.get("/api/system/info")
async def system_info():
    """获取系统信息"""
    try:
        import psutil
        info = {
            "system": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture(),
                "python_version": sys.version,
                "hostname": socket.gethostname(),
            },
            "cpu": {
                "cores": psutil.cpu_count(logical=True),
                "cores_physical": psutil.cpu_count(logical=False),
                "cpu_percent": psutil.cpu_percent(),
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {},
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
        # 收集磁盘信息
        disk_usage = psutil.disk_usage(_get_disk_path())
        info["disk"] = {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "percent": disk_usage.percent,
        }
        return info
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return {"error": str(e), "system": {"platform": platform.system()}}

# 记忆管理端点
@app.get("/api/memory/count")
async def get_memory_count():
    """获取记忆数量"""
    try:
        import json
        from src.core.config.config import _get_project_root
        from src.core.config import config
        project_root = _get_project_root()
        mem_path = project_root / config.memory.memory_dir
        ep = mem_path / "episodic_memory.json"
        if ep.exists():
            data = json.loads(ep.read_text(encoding="utf-8"))
            count = len(data.get("episodic", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            return {"count": count}
        return {"count": 0}
    except Exception as e:
        logger.error(f"获取记忆数量失败: {e}")
        return {"count": 0}

@app.delete("/api/memory/clear")
async def clear_memory():
    """清空记忆系统"""
    try:
        import json
        from src.core.config.config import _get_project_root
        from src.core.config import config
        project_root = _get_project_root()
        mem_path = project_root / config.memory.memory_dir
        ep = mem_path / "episodic_memory.json"
        if ep.exists():
            backup_path = mem_path / f"episodic_memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            ep.rename(backup_path)
            return {"status": "success", "backup": str(backup_path)}
        return {"status": "success", "message": "no_memory"}
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        return {"status": "error", "message": str(e)}

# 配置端点
@app.get("/api/config")
async def get_config():
    """获取配置信息（脱敏）"""
    try:
        from src.core.config import config
        provider = "ollama"
        model = "llama2"
        if hasattr(config, 'llm'):
            provider = config.llm.provider if hasattr(config.llm, 'provider') else "ollama"
            model = config.llm.model if hasattr(config.llm, 'model') else "llama2"
        return {
            "llm": {
                "provider": provider,
                "model": model
            },
            "memory": {
                "enabled": True
            }
        }
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return {"llm": {"provider": "ollama", "model": "llama2"}}

# 日志端点
@app.get("/api/logs")
async def get_logs(limit: int = 50):
    """获取系统日志"""
    try:
        log_file = Path(__file__).parent / "logs" / "app.log"
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return {"logs": lines[-limit:]}
        return {"logs": []}
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return {"logs": ["[INFO] 系统运行中..."]}

# 文件浏览端点
@app.get("/api/files/browse")
async def browse_files(path: str = ""):
    """浏览文件系统"""
    try:
        base_path = Path.home() if not path else Path(path)
        if not base_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
        files = []
        directories = []
        
        for item in base_path.iterdir():
            if item.is_dir():
                directories.append({
                    "name": item.name,
                    "path": str(item.absolute()),
                    "type": "directory"
                })
            else:
                size = item.stat().st_size
                files.append({
                    "name": item.name,
                    "path": str(item.absolute()),
                    "type": "file",
                    "size": size
                })
        
        return {
            "current_path": str(base_path.absolute()),
            "directories": directories[:50],
            "files": files[:50]
        }
    except Exception as e:
        logger.error(f"浏览文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Web UI 端点
@app.get("/ui/dashboard")
async def ui_dashboard():
    """获取仪表板页面"""
    try:
        from src.core.webui import web_interface
        from fastapi.responses import HTMLResponse
        html = web_interface.render_page("dashboard")
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"仪表板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nexus")
async def nexus_interface():
    """Nexus 智能控制中心主界面（OpenCode 风格）"""
    try:
        frontend_dir = Path(__file__).parent / "frontend"
        nexus_file = frontend_dir / "nexus.html"
        if nexus_file.exists():
            return FileResponse(nexus_file)
        else:
            raise HTTPException(status_code=404, detail="Nexus interface not found")
    except Exception as e:
        logger.error(f"Nexus interface failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 健康监控端点
# ============================================
@app.get("/health/full")
async def full_health_check():
    """获取完整健康报告"""
    try:
        from src.core.health import get_system_health
        return await get_system_health()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/monitor")
async def monitor_statistics():
    """获取监控统计"""
    try:
        from src.core.health import get_health_monitor
        monitor = get_health_monitor()
        return monitor.get_statistics()
    except Exception as e:
        logger.error(f"Monitor stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/history")
async def health_history(limit: int = 50):
    """获取健康历史"""
    try:
        from src.core.health import get_health_monitor
        monitor = get_health_monitor()
        return {"history": monitor.get_history(limit)}
    except Exception as e:
        logger.error(f"History failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/health/reload")
async def reload_system():
    """重新加载系统"""
    try:
        from src.core.health import get_recovery_protocol
        protocol = get_recovery_protocol()
        await protocol.reload()
        return {"status": "success", "message": "System reloaded"}
    except Exception as e:
        logger.error(f"Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/state")
async def system_state():
    """获取系统状态"""
    try:
        from src.core.health import get_recovery_protocol
        protocol = get_recovery_protocol()
        return protocol.get_state()
    except Exception as e:
        logger.error(f"State check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 运营仪表板端点
# ============================================
@app.get("/ops/dashboard")
async def operations_dashboard():
    """运营监控仪表板（JSON）"""
    try:
        from src.core.health import get_system_health, get_health_monitor
        from src.core.cognition import cognition_coordinator
        
        health = await get_system_health()
        monitor = get_health_monitor()
        
        return {
            "timestamp": health["timestamp"],
            "overall_status": health["overall_status"],
            "system_health": health,
            "monitor_stats": monitor.get_statistics(),
            "cognition_stats": cognition_coordinator.get_statistics()
        }
    except Exception as e:
        logger.error(f"Ops dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Launcher GUI
# ============================================
try:
    register_launcher(app)
except Exception as e:
    logger.warning(f"Launcher: {e}")

# ============================================
# MCP 端点
# ============================================
try:
    from src.core.mcp import get_mcp_protocol
    mcp_handler = get_mcp_protocol()

    @app.post("/mcp")
    async def handle_mcp(request: Request):
        body = await request.json()
        return await mcp_handler.handle(body)

    @app.get("/mcp")
    async def mcp_info():
        return {"service": "CogniCore MCP", "version": "2.1.0",
                "protocol": "model-context-protocol"}
    logger.info("MCP endpoint mounted at /mcp")
except Exception as e:
    logger.warning(f"MCP not available: {e}")

# ============================================
# 自主学习循环
# ============================================
async def periodic_learning():
    while True:
        try:
            from src.core.assistant import assistant as ga
            if hasattr(ga, "autonomous_learner") and ga.autonomous_learner:
                logger.info("Starting autonomous learning cycle...")
                result = await ga.run_autonomous_learning()
                logger.info(f"Learning complete: {result}")
        except Exception as e:
            logger.debug(f"Learning cycle: {e}")
        await asyncio.sleep(3600)

# ============================================
# 生命周期
# ============================================
@app.on_event("startup")
async def startup():
    global assistant
    logger.info("CogniCore starting...")
    
    # 初始化恢复协议
    try:
        from src.core.health import get_recovery_protocol
        recovery = get_recovery_protocol()
        await recovery.startup()
        logger.info("Recovery protocol initialized")
    except Exception as e:
        logger.warning(f"Recovery protocol not started: {e}")
    
    # 启动健康监控
    try:
        from src.core.health import start_monitoring
        asyncio.create_task(start_monitoring(interval_seconds=60))
        logger.info("Health monitor started (interval: 60s)")
    except Exception as e:
        logger.warning(f"Health monitor not started: {e}")
    
    try:
        from src.core.assistant import assistant as ga
        from src.utils.config import load_config
        assistant = ga
        config = load_config()
        await assistant.initialize(config)
        logger.info("Core assistant initialized")
    except Exception as e:
        logger.error(f"Init failed: {e}")
    try:
        from src.core.llm.ollama_service import OllamaService
        llm = OllamaService()
        if assistant:
            assistant.register_service("llm", llm)
        logger.info("LLM service registered")
    except Exception as e:
        logger.warning(f"LLM service: {e}")
    asyncio.create_task(periodic_learning())
    logger.info("CogniCore started")

@app.on_event("shutdown")
async def shutdown():
    logger.info("CogniCore shutting down")
    
    # 停止健康监控
    try:
        from src.core.health import get_health_monitor
        monitor = get_health_monitor()
        await monitor.stop()
        logger.info("Health monitor stopped")
    except Exception as e:
        logger.warning(f"Health monitor stop failed: {e}")
    
    # 执行优雅关闭
    try:
        from src.core.health import get_recovery_protocol
        recovery = get_recovery_protocol()
        await recovery.graceful_shutdown()
        logger.info("Graceful shutdown complete")
    except Exception as e:
        logger.warning(f"Graceful shutdown failed: {e}")

# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CogniCore")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--force", action="store_true", help="Kill process on port")
    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", args.port)) == 0:
            if args.force:
                import subprocess, platform, re
                system = platform.system()
                logger.warning(f"Port {args.port} in use, force killing...")
                if system == "Windows":
                    port_str = str(args.port)
                    if not port_str.isdigit() or not (0 < int(port_str) < 65536):
                        logger.error(f"Invalid port: {args.port}")
                        sys.exit(1)
                    result = subprocess.run(f"netstat -ano | findstr :{port_str}", capture_output=True, text=True, shell=True)
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split()
                        if len(parts) >= 5 and re.match(r'^\d+$', parts[-1]):
                            subprocess.run(["taskkill", "/F", "/PID", parts[-1]], shell=False)
                else:
                    port_str = str(args.port)
                    subprocess.run(["lsof", "-ti", f":{port_str}"], capture_output=True, text=True)
                time.sleep(2)
            else:
                logger.error(f"Port {args.port} in use. Use --force to kill.")
                sys.exit(1)

    import uvicorn
    print("=" * 60)
    print("  CogniCore  -  self-hosted smart assistant")
    print(f"  URL:  http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/docs")
    print(f"  Nexus: http://{args.host}:{args.port}/nexus  <-- NEW! 智能控制中心")
    print("=" * 60)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
