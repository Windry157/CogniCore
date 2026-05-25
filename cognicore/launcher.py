"""CogniCore Launcher  -  可视化引导与Status监控"""

import os, sys, json, logging, platform
import httpx
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse

router = APIRouter(prefix="/launcher")
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"


def _get_disk_path():
    """Get disk usage path cross-platform"""
    if platform.system() == "Windows":
        return "C:\\" if os.path.exists("C:\\") else os.path.expanduser("~")
    return "/"


_skill_manager_cache = None

def _get_skills_count():
    global _skill_manager_cache
    try:
        if _skill_manager_cache is None:
            from src.core.skill_manager import SkillManager
            _skill_manager_cache = SkillManager()
        return len(_skill_manager_cache.get_tool_definitions())
    except Exception:
        return None

@router.get("/status")
async def system_status():
    try:
        import httpx, fastapi, yaml, psutil
        _runtime_ok = True
    except ImportError:
        _runtime_ok = False
    status = {
        "venv": _runtime_ok,
        "ollama_connected": False,
        "ollama_version": None,
        "model_loaded": False,
        "model_name": None,
        "model_size": None,
        "memory_healthy": False,
        "memory_count": None,
        "skills_count": None,
        "cpu": None,
        "memory": None,
        "disk": None,
    }
    from src.core.config import config
    fallback = "http://localhost:11434"
    base = config.llm.ollama_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{base}/api/tags")
            if r.status_code != 200:
                raise Exception("not ok")
    except Exception:
        base = fallback
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{base}/api/tags")
            if r.status_code == 200:
                status["ollama_connected"] = True
                data = r.json()
                models = data.get("models", [])
                if models:
                    m = models[0]
                    status["model_loaded"] = True
                    status["model_name"] = m.get("name", "?")
                    sz = m.get("size", 0)
                    status["model_size"] = f"{sz/1e9:.1f} GB" if sz else None
                    v = m.get("details", {}).get("parameter_size", "") or m.get("digest", "")[:12]
                    status["ollama_version"] = v
    except Exception as e:
        logger.debug(f"Ollama check: {e}")
    try:
        from src.core.config.config import _get_project_root
        from src.core.config import config
        project_root = _get_project_root()
        mem_dir = project_root / config.memory.memory_dir
        ep_file = mem_dir / "episodic_memory.json"
        if ep_file.exists():
            mem = json.loads(ep_file.read_text(encoding="utf-8"))
            status["memory_healthy"] = True
            status["memory_count"] = len(mem.get("episodic", [])) if isinstance(mem, dict) else len(mem) if isinstance(mem, list) else 0
    except Exception as e:
        logger.debug(f"Memory check: {e}")
    status["skills_count"] = _get_skills_count()
    try:
        import psutil
        status["cpu"] = round(psutil.cpu_percent(interval=0.1))
        status["memory"] = round(psutil.virtual_memory().percent)
        status["disk"] = round(psutil.disk_usage(_get_disk_path()).percent)
    except Exception:
        pass
    return status


# ================================================================
# 提示词降级路径导入（gemma3:1b / qwen2.5:0.5b）
# ================================================================
from prompt_tool_chat import get_prompt_chat


async def _system_info():
    """获取并格式化系统信息"""
    import psutil, platform as pf, socket, datetime
    try:
        boot = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        cpu_pct = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        c_disk = psutil.disk_usage("C:\\")
        d_disk = psutil.disk_usage("D:\\") if os.path.exists("D:\\") else None
        e_disk = psutil.disk_usage("E:\\") if os.path.exists("E:\\") else None
        lines = [
            f"🖥️  CogniCore 系统信息",
            f"━━━━━━━━━━━━━━━━━━",
            f"",
            f"【操作系统】",
            f"  平台: {pf.system()} {pf.version()}",
            f"  架构: {pf.machine()}",
            f"  主机名: {socket.gethostname()}",
            f"  启动时间: {boot}",
            f"",
            f"【CPU】",
            f"  核心: {psutil.cpu_count(logical=True)} 逻辑核 / {psutil.cpu_count(logical=False)} 物理核",
            f"  使用率: {cpu_pct}%",
            f"",
            f"【内存】",
            f"  总量: {mem.total / 1024**3:.1f} GB",
            f"  已用: {mem.used / 1024**3:.1f} GB ({mem.percent}%)",
            f"  可用: {mem.available / 1024**3:.1f} GB",
            f"",
            f"【磁盘】",
            f"  C: {c_disk.used / 1024**3:.1f} GB / {c_disk.total / 1024**3:.1f} GB ({c_disk.percent}%)",
        ]
        if d_disk:
            lines.append(f"  D: {d_disk.used / 1024**3:.1f} GB / {d_disk.total / 1024**3:.1f} GB ({d_disk.percent}%)")
        if e_disk:
            lines.append(f"  E: {e_disk.used / 1024**3:.1f} GB / {e_disk.total / 1024**3:.1f} GB ({e_disk.percent}%)")
        return "\n".join(lines)
    except Exception as e:
        return f"获取系统信息失败: {e}"


def _list_directory(path: str):
    """列出目录内容"""
    from pathlib import Path as PPath
    p = PPath(path)
    if not p.exists():
        return f"路径不存在: {path}"
    if not p.is_dir():
        return f"不是目录: {path}"
    limit = 30
    dirs, files = [], []
    for i, entry in enumerate(p.iterdir()):
        if i >= limit:
            break
        if entry.is_dir():
            dirs.append(f"  📁 {entry.name}/")
        else:
            sz = entry.stat().st_size
            if sz < 1024:
                sz_str = f"{sz} B"
            elif sz < 1024**2:
                sz_str = f"{sz/1024:.1f} KB"
            else:
                sz_str = f"{sz/1024**2:.1f} MB"
            files.append(f"  📄 {entry.name}  ({sz_str})")
    lines = [f"📂 {path}  ({len(dirs) + len(files)} 项)"]
    if dirs:
        lines.append("")
        lines.append("子目录:")
        lines.extend(dirs)
    if files:
        lines.append("")
        lines.append("文件:")
        lines.extend(files)
    return "\n".join(lines)


# ================================================================
# 模型工具调用能力自适应
# ================================================================

_native_fc_cache: dict[str, bool] = {}

def _can_native_fc(model: str, tools: list) -> bool:
    """查缓存，避免每次尝试"""
    return _native_fc_cache.get(model, True)  # 默认信任，遇到错误再降级


async def _native_tool_chat(base, model, system_prompt, msg, images, tools, sm):
    """原生 function calling 路径（gemma4:e4b 等）"""
    ollama_messages = [{"role": "system", "content": system_prompt}]
    user_msg = {"role": "user", "content": msg or "描述这张图片"}
    if images:
        user_msg["images"] = images
    ollama_messages.append(user_msg)

    try:
        async with httpx.AsyncClient(timeout=120) as c:
            for _ in range(5):
                payload = {"model": model, "messages": ollama_messages, "stream": False}
                if tools:
                    payload["tools"] = tools

                r = await c.post(f"{base}/api/chat", json=payload)
                data = r.json()
                if "error" in data:
                    err = data["error"]
                    if "does not support tools" in err or "not support" in err.lower():
                        return {"_fallback": True}
                    return {"response": f"⚠️ {err}"}

                msg_obj = data.get("message", {})
                content = msg_obj.get("content") or ""
                tool_calls = msg_obj.get("tool_calls", [])

                if not tool_calls:
                    return {"response": content or "(无回复)"}

                asst_msg = {"role": "assistant", "content": content if content else None, "tool_calls": tool_calls}
                ollama_messages.append(asst_msg)

                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    tc_id = tc.get("id")
                    raw_args = func.get("arguments", "{}")
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            args = {}
                    else:
                        args = raw_args
                    action = args.pop("action", tool_name)
                    result_str = await sm.execute_tool(tool_name, action, args)
                    tool_result = {"role": "tool", "content": result_str, "name": tool_name}
                    if tc_id:
                        tool_result["tool_call_id"] = tc_id
                    ollama_messages.append(tool_result)

        return {"response": "(工具调用超过最大轮次)"}
    except httpx.HTTPStatusError as e:
        return {"response": f"请求失败: {e}"}
    except Exception as e:
        return {"response": f"请求失败: {e}"}





@router.post("/chat")
async def chat(request: Request):
    body = await request.json()
    msg = body.get("message", "").strip()
    images = body.get("images", [])
    if not msg and not images:
        return {"response": "请输入消息"}
    from src.core.config import config as cfg
    from src.core.skill_manager import get_skill_manager

    # === 系统直处理：仅短命令走此路径（避免对话内容误触发） ===
    import re
    lower = msg.lower().strip()

    # 只有 ≤25 字符的短查询才走关键词直处理
    if len(msg) <= 25:
        if re.search(r'^系统信息$|^系统状态$|^sysinfo$', lower):
            return {"response": await _system_info()}
        if re.search(r'^cpu$|^内存$|^磁盘$|^硬盘$', lower):
            raw = await _system_info()
            if "cpu" in lower:
                seg = re.search(r'【CPU】.*?(?=\n\n)', raw, re.DOTALL)
                return {"response": seg.group(0) if seg else raw}
            if "内存" in lower:
                seg = re.search(r'【内存】.*?(?=\n\n)', raw, re.DOTALL)
                return {"response": seg.group(0) if seg else raw}
            if "磁盘" in lower or "硬盘" in lower:
                seg = re.search(r'【磁盘】.*', raw, re.DOTALL)
                return {"response": seg.group(0) if seg else raw}

    # 路径检测：从消息中提取并验证盘符路径
    path = None
    import os as _os
    raw = msg.replace("\\", "/")
    idx = raw.find(":/")
    if idx > 0 and idx + 2 < len(raw):
        drive = raw[idx - 1:idx + 2].upper()
        rest = raw[idx + 2:]
        segments = re.split(r'[/\\]+', rest)
        candidate = drive.rstrip("/")
        for i, seg in enumerate(segments):
            if not seg:
                continue
            trial = candidate + "/" + seg
            if _os.path.exists(trial):
                candidate = trial
                path = candidate
            elif i == len(segments) - 1:
                # 最后一段：可能是中文文本混入，逐字截短尝试
                for j in range(len(seg), 0, -1):
                    trial = candidate + "/" + seg[:j]
                    if _os.path.exists(trial):
                        path = trial
                        break
                break
            else:
                break
        # drive-only fallback
        if not path:
            trial = drive.rstrip("/")
            if _os.path.exists(trial):
                path = trial

    if path:
        if _os.path.isfile(path):
            ext = _os.path.splitext(path)[1].lower()
            if ext in ('.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.pdf', '.lnk', '.tmp', '.db', '.jpg', '.jpeg', '.png', '.gif', '.bmp'):
                return {"response": f"📄 {path}  ({_os.path.getsize(path)} B)  二进制文件，暂不支持文本预览"}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()[:2000]
                return {"response": f"📄 {path}\n\n{content}"}
            except Exception as e:
                return {"response": f"📄 {path}  ({_os.path.getsize(path)} B)  文件读取失败: {e}"}
        return {"response": _list_directory(path)}

    # === 对话场景：走模型 + 工具调用 ===
    # 自动检测 Ollama 地址：先试配置的，不行就试 localhost
    base = cfg.llm.ollama_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=2) as c:
            await c.get(f"{base}/api/tags")
    except Exception:
        fallback = "http://localhost:11434"
        try:
            async with httpx.AsyncClient(timeout=2) as c:
                await c.get(f"{fallback}/api/tags")
            logger.info(f"Ollama URL auto-detected: {fallback} (config had {base})")
            base = fallback
        except Exception:
            pass
    model = cfg.llm.ollama_model
    system_prompt = body.get("system_prompt") or "你是 CogniCore Portable v2.1.0，一个运行在U盘上的智能助手。总用中文回答。不要说你是其他AI模型。你拥有系统技能，可根据对话内容使用工具。"
    sm = get_skill_manager()
    tools = sm.get_tool_definitions()

    if images:
        return {"response": "当前模型不支持图片识别"}

    # 自适应：先试原生 FC，失败则降级
    if _can_native_fc(model, tools):
        result = await _native_tool_chat(base, model, system_prompt, msg, images, tools, sm)
        # 如果 Ollama 返回"不支持 tools"错误，标记缓存并重试降级
        if result.get("_fallback"):
            _native_fc_cache[model] = False
            logger.info(f"Model {model} doesn't support native FC, falling back to prompt-based")
        else:
            return result

    chat = get_prompt_chat(model, base)
    res = chat.chat(msg)
    if res["type"] == "text":
        return {"response": res["content"]}
    if res["type"] == "tool_result":
        return {"response": f"工具「{res['tool']}」执行结果：\n{res['result']}"}
    if res["type"] == "tool_error":
        return {"response": f"工具调用失败: {res['error']}"}
    return {"response": "未知结果"}

@router.post("/ollama/check")
async def check_ollama():
    from src.core.config import config
    candidates = [config.llm.ollama_base_url.rstrip("/"), "http://localhost:11434", "http://127.0.0.1:11434"]
    seen = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{base}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    models = [m.get("name", "?") for m in data.get("models", [])]
                    return {"connected": True, "url": base, "version": "Ollama", "models": models}
        except Exception:
            continue
    return {"connected": False}


@router.post("/ollama/models")
async def list_ollama_models():
    from src.core.config import config
    candidates = [config.llm.ollama_base_url.rstrip("/"), "http://localhost:11434", "http://127.0.0.1:11434"]
    seen = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{base}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    models = [
                        {"name": m["name"], "size": m.get("size", 0), "details": m.get("details", {})}
                        for m in data.get("models", [])
                    ]
                    return {"models": models}
        except Exception:
            continue
    return {"models": []}

@router.post("/config/model")
async def set_config_model(request: Request):
    body = await request.json()
    model = body.get("model", "").strip()
    if not model:
        return {"ok": False, "error": "模型名不能为空"}
    try:
        import yaml
        from pathlib import Path
        cfg_path = Path(os.getenv("CONFIG_PATH", "config.yaml")).resolve()
        if not cfg_path.exists():
            return {"ok": False, "error": "config.yaml not found"}
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if "models" not in cfg:
            cfg["models"] = {}
        cfg["models"]["default"] = model
        cfg_path.write_text(yaml.dump(cfg, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        from src.core.config.config import reload_config
        reload_config()
        logger.info(f"Config updated + reloaded: default model -> {model}")
        return {"ok": True, "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/ollama/pull")
async def pull_model(request: Request):
    body = await request.json()
    model = body.get("model", "qwen2.5:0.5b")
    from src.core.config import config
    base = config.llm.ollama_base_url.rstrip("/")

    async def stream_pull():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", f"{base}/api/pull",
                                          json={"name": model}) as resp:
                    async for line in resp.aiter_lines():
                        if line.strip():
                            yield f"data: {line}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(stream_pull(), media_type="text/event-stream")


def register(app):
    frontend = FRONTEND_DIR
    if frontend.is_dir():
        @app.get("/launcher", response_class=HTMLResponse, include_in_schema=False)
        async def launcher_page():
            return HTMLResponse((frontend / "index.html").read_text(encoding="utf-8"))
        logger.info(f"Launcher frontend mounted from {frontend}")
    else:
        logger.warning(f"Frontend dir not found: {frontend}")
    app.include_router(router)
    logger.info("Launcher module registered")
