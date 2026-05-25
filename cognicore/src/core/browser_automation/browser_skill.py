#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Browser automationSkill
集成到PyWJJ Skill系统
"""
from typing import Dict, Any
import sys
import os

# Add路径以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入BaseSkill
from ..skills.base import BaseSkill
from .playwright_wrapper import PlaywrightCLIWrapper
import logging

logger = logging.getLogger(__name__)


class BrowserAutomationSkill(BaseSkill):
    """Browser automationSkill"""

    def __init__(self):
        self.wrapper = PlaywrightCLIWrapper()

    @property
    def name(self) -> str:
        return "browser_automation"

    @property
    def description(self) -> str:
        return """
Browser automation操作, 支持: 
- Start/Closebrowser (持久化Cookie) 
- 导航到URL
- 点击元素
- 填写表单
- Get文本
- 滚动Page
- 执行JavaScript
- 自动生成可独立运行的脚本 (0Token模式) 
"""

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作type: launch, navigate, click, fill, get_text, scroll, execute_script, close, generate_script",
                    "enum": ["launch", "navigate", "click", "fill", "get_text", "scroll", "execute_script", "close", "generate_script"]
                },
                "url": {
                    "type": "string",
                    "description": "导航URL (navigate时必填) "
                },
                "selector": {
                    "type": "string",
                    "description": "CSS选择器 (click, fill, get_text时必填) "
                },
                "value": {
                    "type": "string",
                    "description": "填写的值 (fill时必填) "
                },
                "direction": {
                    "type": "string",
                    "description": "滚动方向 (up/down, scroll时用) ",
                    "default": "down"
                },
                "amount": {
                    "type": "integer",
                    "description": "滚动量 (像素, scroll时用) ",
                    "default": 500
                },
                "script": {
                    "type": "string",
                    "description": "JavaScript代码 (execute_script时必填) "
                },
                "headed": {
                    "type": "boolean",
                    "description": "是否有头模式 (launch时用) ",
                    "default": True
                },
                "browser": {
                    "type": "string",
                    "description": "browsertype (chromium, firefox, webkit) ",
                    "default": "chromium"
                },
                "task_description": {
                    "type": "string",
                    "description": "TaskDescription (generate_script时用) "
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Browser automation操作
        
        Args:
            action: 操作type
            params: 参数字典
        
        Returns:
            操作
        """
        logger.info(f"Browser automation: {action}")

        try:
            if action == "launch":
                headed = params.get("headed", True)
                browser = params.get("browser", "chromium")
                return await self.wrapper.launch_browser(headed=headed, browser=browser)

            elif action == "navigate":
                url = params.get("url")
                if not url:
                    return {"status": "error", "message": "navigate需要url参数"}
                return await self.wrapper.navigate(url)

            elif action == "click":
                selector = params.get("selector")
                if not selector:
                    return {"status": "error", "message": "click需要selector参数"}
                return await self.wrapper.click(selector)

            elif action == "fill":
                selector = params.get("selector")
                value = params.get("value")
                if not selector or not value:
                    return {"status": "error", "message": "fill需要selector和value参数"}
                return await self.wrapper.fill(selector, value)

            elif action == "get_text":
                selector = params.get("selector")
                if not selector:
                    return {"status": "error", "message": "get_text需要selector参数"}
                return await self.wrapper.get_text(selector)

            elif action == "scroll":
                direction = params.get("direction", "down")
                amount = params.get("amount", 500)
                return await self.wrapper.scroll(direction, amount)

            elif action == "execute_script":
                script = params.get("script")
                if not script:
                    return {"status": "error", "message": "execute_script需要script参数"}
                return await self.wrapper.execute_script(script)

            elif action == "close":
                return await self.wrapper.close_browser()

            elif action == "generate_script":
                task_desc = params.get("task_description", "")
                return await self._generate_script(task_desc)

            else:
                return {
                    "status": "error",
                    "message": f"未知的操作type: {action}"
                }

        except Exception as e:
            logger.error(f"Browser automation error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _generate_script(self, task_description: str) -> Dict[str, Any]:
        """
        生成可独立运行的Python脚本 (0Token模式) 
        
        Args:
            task_description: TaskDescription
        
        Returns:
            脚本Content
        """
        script_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyWJJBrowser automation脚本
自动生成, 可独立运行 (0Token模式) 
Task: {task_description}
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path


async def main():
    # 配置
    user_data_dir = str(Path.home() / ".pywjj" / "browser_data")
    screenshot_dir = str(Path.home() / ".pywjj" / "screenshots")
    os.makedirs(user_data_dir, exist_ok=True)
    os.makedirs(screenshot_dir, exist_ok=True)
    
    print("[boot] Starting browser...")
    async with async_playwright() as p:
        # Start持久化browser (保持登录态) 
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False
        )
        page = await browser.new_page()
        
        # ========================
        # 在此Add你的自动化Step
        # ========================
        # 示例:
        # await page.goto("https://example.com")
        # await page.fill("#username", "your_username")
        # await page.click("#login-button")
        # await page.wait_for_load_state("networkidle")
        # ========================
        
        print("[OK] Task complete! Browser stays open...")
        input("按Enter键Closebrowser...")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
'''
        # Save脚本
        script_path = os.path.join(os.path.expanduser("~"), ".pywjj", "auto_scripts", "browser_task.py")
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        return {
            "status": "success",
            "message": "脚本already生成",
            "script_path": script_path,
            "script_content": script_content,
            "instructions": "编辑脚本文件Add你的自动化Step, 然后运行即可!"
        }
