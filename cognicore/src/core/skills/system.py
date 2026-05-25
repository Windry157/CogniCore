#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import webbrowser
import datetime
import subprocess
import platform
from typing import Dict, Any
from .base import BaseSkill

class SystemControlSkill(BaseSkill):
    """系统控制Skill: 打开网页, 应用, Get时间等"""

    @property
    def name(self) -> str:
        return "system_control"

    @property
    def description(self) -> str:
        return "用于控制计算机系统, 包括打开网页, 打开应用程序, Get当前时间, 系统休眠等."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open_url", "open_app", "get_time", "shutdown"],
                    "description": "要执行的操作"
                },
                "target": {
                    "type": "string",
                    "description": "操作的目标, 例如网址或应用Name"
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "")
        result = {"status": "success", "message": ""}

        try:
            if action == "open_url":
                if not target.startswith("http"):
                    target = "https://" + target
                webbrowser.open(target)
                result["message"] = f"already为您打开网页: {target}"

            elif action == "open_app":
                # 简单的 Windows 应用映射
                app_map = {
                    "计算器": "calc.exe",
                    "记事本": "notepad.exe",
                    "cmd": "cmd.exe",
                    "explorer": "explorer.exe"
                }
                cmd = app_map.get(target, target)
                if cmd in app_map.values() or (cmd.endswith(".exe") and os.path.isfile(cmd)):
                    subprocess.Popen(cmd.split(), shell=False)
                elif cmd in app_map.values():
                    subprocess.Popen(cmd.split(), shell=False)
                else:
                    result = {"success": False, "message": f"Blocked: {target}"}
                    return result
                result["message"] = f"already尝试Start应用: {target}"

            elif action == "get_time":
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                weekday = datetime.datetime.now().strftime("%A")
                result["message"] = f"当前系统时间是: {now} ({weekday})"
            
            elif action == "shutdown":
                # 为了安全, 这里只演示, 不真的关机
                result["message"] = "收到关机指令, 但为了安全起见, 演示模式下already拦截该操作."
                # os.system("shutdown /s /t 60") 

            else:
                result["status"] = "error"
                result["message"] = f"未知的动作: {action}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"执行出错: {str(e)}"

        return result