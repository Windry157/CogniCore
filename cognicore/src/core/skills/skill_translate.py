#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TranslationSkill
支持多语言互译
"""
import logging
from typing import Dict, Any
from .base import BaseSkill

logger = logging.getLogger(__name__)

class TranslateSkill(BaseSkill):
    """TranslationSkill"""
    
    @property
    def name(self) -> str:
        return "translate"
    
    @property
    def description(self) -> str:
        return "多语言TranslationSkill, 支持中文, 英文, 日文, 韩文, 法文, 德文等多种语言的互译"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["auto", "to_en", "to_zh", "to_ja", "to_ko", "to_fr", "to_de"],
                    "description": "Translation方向: auto(自动检测), to_en(Translation成英文), to_zh(Translation成中文), to_ja(日文), to_ko(韩文), to_fr(法文), to_de(德文)"
                },
                "text": {
                    "type": "string",
                    "description": "要Translation的文本"
                },
                "source_lang": {
                    "type": "string",
                    "description": "源语言代码 (可选) , 例如: zh, en, ja, ko, fr, de"
                },
                "target_lang": {
                    "type": "string",
                    "description": "目标语言代码 (可选) , 例如: zh, en, ja, ko, fr, de"
                }
            },
            "required": ["action", "text"]
        }
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Translation操作"""
        try:
            text = params.get("text", "")
            if not text:
                return {
                    "status": "error",
                    "message": "要Translation的文本不能为空"
                }
            
            source_lang = params.get("source_lang", "auto")
            target_lang = params.get("target_lang", "en")
            
            # 根据action设置目标语言
            if action == "auto":
                target_lang = "en"  # 默认Translation成英文
            elif action == "to_en":
                target_lang = "en"
            elif action == "to_zh":
                target_lang = "zh"
            elif action == "to_ja":
                target_lang = "ja"
            elif action == "to_ko":
                target_lang = "ko"
            elif action == "to_fr":
                target_lang = "fr"
            elif action == "to_de":
                target_lang = "de"
            
            # 执行Translation
            translated_text = await self._translate_text(text, source_lang, target_lang)
            
            return {
                "status": "success",
                "message": "Translation successful",
                "original_text": text,
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translation文本"""
        try:
            # 尝试使用 translate 库
            try:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                return translator.translate(text)
            except ImportError:
                logger.info("deep_translator not installed, trying fallback")
                pass
            
            # 备用方案: 使用简单的Translation表Processing常见短语
            return self._fallback_translate(text, source_lang, target_lang)
            
        except Exception as e:
            logger.warning(f"Translation library call failed: {e}")
            return self._fallback_translate(text, source_lang, target_lang)
    
    def _fallback_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """备用Translation方案 - 简单映射"""
        # 常用短语Translation表
        translations = {
            "zh": {
                "你好": "Hello",
                "谢谢": "Thank you",
                "再见": "Goodbye",
                "好的": "Okay",
                "是的": "Yes",
                "不": "No",
                "请": "Please",
                "帮助": "Help",
                "对不起": "Sorry",
                "没关系": "It's okay"
            },
            "en": {
                "Hello": "你好",
                "Thank you": "谢谢",
                "Goodbye": "再见",
                "Okay": "好的",
                "Yes": "是的",
                "No": "不",
                "Please": "请",
                "Help": "帮助",
                "Sorry": "对不起",
                "It's okay": "没关系"
            }
        }
        
        # 检查是否有匹配
        if source_lang == "zh" and target_lang == "en":
            if text in translations["zh"]:
                return translations["zh"][text]
        elif source_lang == "en" and target_lang == "zh":
            if text in translations["en"]:
                return translations["en"][text]
        
        # 如果没有匹配, 提示用户安装Translation库
        return f"[需要Translation] {text}\n\n提示: 请安装 deep_translator 库来获得更好的Translation效果:\npip install deep_translator"
