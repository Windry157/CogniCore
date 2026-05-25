#!/usr/bin/env python3
import sys
sys.path.insert(0, "E:/CogniCore-Portable/cognicore")

import asyncio
import traceback

async def test_assistant():
    try:
        print("Importing assistant...")
        from src.core.assistant import assistant as ga
        from src.utils.config import load_config
        
        print("Initializing assistant...")
        config = load_config()
        await ga.initialize(config)
        
        print("Calling chat...")
        response = await ga.chat("你好，做个自我介绍")
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_assistant())
