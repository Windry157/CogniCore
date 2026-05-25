"""CogniCore 12-skill prompt-based tool calling for gemma3:1b fallback"""

import json
import re
import psutil
import os
import platform
import subprocess
from typing import Callable, Dict, Any, Optional
import httpx


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}
        self._schemas: Dict[str, Dict] = {}

    def register(self, name: str, func: Callable, description: str, schema: Dict):
        self._tools[name] = func
        self._descriptions[name] = description
        self._schemas[name] = schema

    def list_tools(self):
        return [{"name": n, "description": self._descriptions[n], "schema": self._schemas[n]}
                for n in self._tools]

    def execute(self, name: str, args):
        if name not in self._tools:
            return {"success": False, "error": f"工具 {name} 不存在"}
        try:
            if isinstance(args, dict):
                res = self._tools[name](**args)
            else:
                res = self._tools[name]()
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": str(e)}


class CogniCoreToolChat:
    def __init__(self, model="gemma3:1b", ollama_url="http://localhost:11434", registry=None):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.registry = registry or ToolRegistry()

    def _build_prompt(self):
        tool_str = "\n".join([f"- {t['name']}: {t['description']}"
                              for t in self.registry.list_tools()])
        return f"""
你是CogniCore随身智能助手。

可用工具列表：
{tool_str}

规则：
1. 日常对话（打招呼、闲聊、问好等）直接回复，不使用工具。
2. 只有用户明确要求执行系统操作时才使用工具。
3. 需要工具时输出JSON：{{"tool":"工具名","args":{{}}}}
4. 禁止编造工具。
"""

    def _extract_json(self, text):
        # Strip markdown code fences first
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```", "", text)
        # Try exact parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fallback: find first JSON object
        match = re.search(r"\{[\s\S]*?\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None

    def chat(self, user_input):
        prompt = self._build_prompt() + f"\n用户：{user_input}"
        try:
            with httpx.Client(timeout=120) as c:
                r = c.post(f"{self.ollama_url}/api/chat", json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                })
                data = r.json()
                if "error" in data:
                    return {"type": "error", "content": f"⚠️ {data['error']}"}
                out = (data.get("message", {}).get("content") or "").strip()
        except Exception as e:
            return {"type": "error", "content": f"模型调用失败: {e}"}

        tool = self._extract_json(out)
        if not tool:
            return {"type": "text", "content": out}

        res = self.registry.execute(tool.get("tool"), tool.get("args", {}))
        if res["success"]:
            return {"type": "tool_result", "tool": tool["tool"], "result": res["result"]}
        return {"type": "tool_error", "error": res["error"]}


def register_cognicore_12_tools(registry: ToolRegistry):
    def sys_basic(**kwargs):
        return f"系统：{platform.system()} {platform.release()}"
    registry.register("sys_basic", sys_basic, "获取系统版本", {})

    def sys_cpu(**kwargs):
        return f"CPU 占用：{psutil.cpu_percent()}%"
    registry.register("sys_cpu", sys_cpu, "查看CPU占用", {})

    def sys_mem(**kwargs):
        mem = psutil.virtual_memory()
        return f"内存：{mem.percent}% 已用"
    registry.register("sys_mem", sys_mem, "查看内存占用", {})

    def sys_disk(**kwargs):
        return "C盘可用：" + str(round(psutil.disk_usage('C:\\').free / 1024 ** 3, 2)) + "GB"
    registry.register("sys_disk", sys_disk, "查看C盘空间", {})

    def proc_list(limit=10):
        return [p.name() for p in psutil.process_iter()][:limit]
    registry.register("proc_list", proc_list, "获取进程列表", {"limit": "int"})

    def proc_kill(pid: int):
        psutil.Process(pid).terminate()
        return f"已结束进程 {pid}"
    registry.register("proc_kill", proc_kill, "结束指定PID进程", {"pid": "int"})

    def file_list(path: str = "."):
        return os.listdir(path)
    registry.register("file_list", file_list, "列出目录文件", {"path": "str"})

    def file_read(path: str = "", **kwargs):
        if not path:
            return "请指定文件路径"
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()[:500]
        except Exception as e:
            return f"读取失败: {e}"
    registry.register("file_read", file_read, "读取文本文件", {"path": "str"})

    def file_write(path: str, content: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "写入成功"
    registry.register("file_write", file_write, "写入文本文件", {"path": "str", "content": "str"})

    def net_status(**kwargs):
        return "网络连通" if psutil.net_connections() else "未检测到连接"
    registry.register("net_status", net_status, "查看网络状态", {})

    def sys_cmd(cmd: str = "", **kwargs):
        allow = ["dir", "echo", "ipconfig", "ping -n 2 127.0.0.1"]
        if cmd not in allow:
            return "命令不被允许"
        return subprocess.getoutput(cmd)[:800]
    registry.register("sys_cmd", sys_cmd, "执行安全系统命令", {"cmd": "str"})

    def calc(a: float, b: float, op: str):
        if op == "add":
            return a + b
        if op == "mul":
            return a * b
        return "不支持"
    registry.register("calc", calc, "基础计算器", {"a": "float", "b": "float", "op": "str"})


_registry = None
_chat_instance = None


def get_prompt_chat(model: str = "gemma3:1b", ollama_url: str = "http://localhost:11434") -> CogniCoreToolChat:
    global _registry, _chat_instance
    if _registry is None:
        _registry = ToolRegistry()
        register_cognicore_12_tools(_registry)
    if _chat_instance is None or _chat_instance.model != model or _chat_instance.ollama_url != ollama_url.rstrip("/"):
        _chat_instance = CogniCoreToolChat(model=model, ollama_url=ollama_url, registry=_registry)
    return _chat_instance


if __name__ == "__main__":
    reg = ToolRegistry()
    register_cognicore_12_tools(reg)
    bot = CogniCoreToolChat(model="gemma3:1b", registry=reg)
    for q in ["查看系统信息", "查看CPU占用", "计算 3+5"]:
        print(f"\n用户：{q}")
        print(json.dumps(bot.chat(q), ensure_ascii=False, indent=2))
