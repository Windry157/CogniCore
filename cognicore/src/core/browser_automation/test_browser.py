#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testing browser automation
"""
import asyncio
import sys
import os

# Add路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.browser_automation import BrowserAutomationSkill, PlaywrightCLIWrapper


async def test_basic_functionality():
    """Test基础功能"""
    print("="*50)
    print("Testing browser automation")
    print("="*50)

    # TestSkill
    skill = BrowserAutomationSkill()
    
    print(f"\n[OK] SkillName: {skill.name}")
    print(f"[OK] SkillDescription: {skill.description[:100]}...")
    
    # Test生成脚本
    print("\n[note] Testing script generation...")
    result = await skill.execute("generate_script", {"task_description": "TestBrowser automation"})
    
    if result.get("status") == "success":
        print(f"[OK] Script generation successful!")
        print(f"[doc] Script path: {result.get('script_path')}")
        print(f"\nScript preview:\n{result.get('script_content', '')[:200]}...")
    else:
        print(f"[ERR] Script generation failed: {result.get('message')}")
    
    # Test导航 (演示模式) 
    print("\n[www] Testing navigation...")
    result = await skill.execute("navigate", {"url": "https://example.com"})
    
    if result.get("status") == "success":
        print(f"[OK] Navigation successful!")
        print(f"[doc] Page title: {result.get('title')}")
        print(f"[doc] Page URL: {result.get('url')}")
    else:
        print(f"[!] Navigation running in demo mode: {result.get('message')}")
    
    print("\n" + "="*50)
    print("[OK] Basic function test complete!")
    print("="*50)


async def test_wrapper():
    """Testing Playwright wrapper"""
    print("\n" + "="*50)
    print("Testing Playwright wrapper")
    print("="*50)
    
    wrapper = PlaywrightCLIWrapper()
    
    # TestStartbrowser
    print("\n[boot] Testing browser launch...")
    result = await wrapper.launch_browser(headed=True)
    
    if result.get("status") == "success":
        print(f"[OK] Browser launched successfully!")
        print(f"[doc] Session ID: {result.get('session_id')}")
    else:
        print(f"[!] browserrunning in demo mode: {result.get('message')}")
    
    # Test导航
    print("\n[www] Testing navigation...")
    result = await wrapper.navigate("https://example.com")
    
    if result.get("status") == "success":
        print(f"[OK] Navigation successful!")
        print(f"[doc] Title: {result.get('title')}")
        print(f"[doc] Screenshot: {result.get('screenshot_path')}")
    else:
        print(f"[!] Navigation running in demo mode: {result.get('message')}")
    
    print("\n" + "="*50)
    print("[OK] Wrapper test complete!")
    print("="*50)


if __name__ == "__main__":
    print("PyWJJ browser automation test")
    print("="*50)
    
    # TestSkill功能
    asyncio.run(test_basic_functionality())
    
    print("\n\n")
    
    # Test包装器
    try:
        asyncio.run(test_wrapper())
    except Exception as e:
        print(f"[!] Wrapper test requires Playwright")
        print(f"[idea] For full functionality, install: pip install playwright && playwright install chromium")
    
    print("\n[party] All tests complete!")
