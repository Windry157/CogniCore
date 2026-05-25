#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音合成服务 (TTS)
使用 edge-tts 提供高质量的语音合成
"""
import asyncio
import edge_tts
from typing import Optional

class TTSService:
    """语音合成服务类"""
    
    def __init__(self):
        """Initialization TTS 服务"""
        self.voice = "zh-CN-YunxiNeural"  # 微软 Edge-TTS 中文语音
        self.rate = "+0%"  # 语速
        self.volume = "+0%"  # 音量
    
    async def synthesize(self, text: str) -> bytes:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            
        Returns:
            合成的音频数据 (bytes)
        """
        try:
            # Create TTS 实例
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume)
            
            # 合成音频
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    audio_data += chunk['data']
            
            return audio_data
        except Exception as e:
            print(f"TTS synthesis failed: {e}")
            return b""
    
    async def synthesize_to_file(self, text: str, output_file: str) -> bool:
        """
        合成语音到文件
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径
            
        Returns:
            是否 successful
        """
        try:
            audio_data = await self.synthesize(text)
            if audio_data:
                with open(output_file, 'wb') as f:
                    f.write(audio_data)
                return True
            return False
        except Exception as e:
            print(f"TTS synthesis to file failed: {e}")
            return False

# 全局 TTS 服务实例
tts_service = TTSService()

if __name__ == "__main__":
    """Test TTS 服务"""
    async def test_tts():
        text = "你好, 我是 PyWJJ 智能助手, 很高兴为您服务."
        audio_data = await tts_service.synthesize(text)
        print(f"Synthesized audio length: {len(audio_data)}  bytes")
        
        # Save to file
        success = await tts_service.synthesize_to_file(text, "test_tts.mp3")
        print(f"Save to file: {' successful' if success else ' failed'}")
    
    asyncio.run(test_tts())
