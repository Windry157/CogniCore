#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别服务 (STT)
使用 SpeechRecognition 库进行语音转文本
支持多种语音识别引擎
"""
from typing import Optional
import os
import tempfile
import speech_recognition as sr
from src.utils.config import load_config

class STTService:
    """语音识别服务类"""
    
    def __init__(self):
        """Initialization STT 服务"""
        config = load_config()
        self.api_key = config.get('LLM_API_KEY')
        self.base_url = config.get('LLM_BASE_URL', 'https://api.openai.com/v1')
        self.recognizer = sr.Recognizer()
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        语音转文本
        
        Args:
            audio_data: 音频数据 (bytes)
            
        Returns:
            识别的文本,  failed则返回 None
        """
        try:
            # Save音频到临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # 使用 SpeechRecognition 进行识别
            text = await self._recognize_audio(temp_file_path)
            
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return text
        except Exception as e:
            print(f"STT recognition failed: {e}")
            # 清理临时文件
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return None
    
    async def transcribe_from_file(self, audio_file: str) -> Optional[str]:
        """
        From文件进行语音转文本
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            识别的文本,  failed则返回 None
        """
        try:
            return await self._recognize_audio(audio_file)
        except Exception as e:
            print(f"STT file recognition failed: {e}")
            return None
    
    async def _recognize_audio(self, audio_file: str) -> Optional[str]:
        """
        Recognize audio文件
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            识别的文本,  failed则返回 None
        """
        try:
            # 使用 SpeechRecognition 进行识别
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
            
            # 尝试使用 Google Web Speech API
            try:
                text = self.recognizer.recognize_google(audio, language="zh-CN")
                return text
            except sr.UnknownValueError:
                print("Google Web Speech API cannot recognize audio")
            except sr.RequestError as e:
                print(f"Google Web Speech API request failed: {e}")
            
            # 尝试使用其他引擎
            try:
                text = self.recognizer.recognize_sphinx(audio)
                return text
            except sr.UnknownValueError:
                print("Sphinx cannot recognize audio")
            except sr.RequestError as e:
                print(f"Sphinx request failed: {e}")
            
            return None
        except Exception as e:
            print(f"Recognize audio failed: {e}")
            return None

# 全局 STT 服务实例
stt_service = STTService()

if __name__ == "__main__":
    """Test STT 服务"""
    import asyncio
    
    async def test_stt():
        # 这里需要一 Test音频文件
        test_file = "test_audio.wav"
        if os.path.exists(test_file):
            text = await stt_service.transcribe_from_file(test_file)
            print(f"Recognition: {text}")
        else:
            print(f"Test file {test_file} does not exist")
    
    asyncio.run(test_stt())
