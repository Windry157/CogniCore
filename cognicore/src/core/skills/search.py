#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SearchSkill
使用 DuckDuckGo 进行网络Search
"""
import requests
from typing import Dict, Any
from .base import BaseSkill

class SearchSkill(BaseSkill):
    """SearchSkill"""
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return "用于进行网络Search, Get最新的信息, 如新闻, 天气, 股票价格等."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["web_search"],
                    "description": "要执行的操作, 目前只支持 web_search"
                },
                "query": {
                    "type": "string",
                    "description": "Search查询词"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量, 默认5"
                }
            },
            "required": ["action", "query"]
        }
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Search操作"""
        if action == "web_search":
            query = params.get("query", "")
            limit = params.get("limit", 5)

            if not query:
                return {
                    "status": "error",
                    "message": "Search查询词不能为空"
                }

            try:
                # 沙箱安全检查 - 网络访问
                try:
                    from src.core.sandbox import get_sandbox_security
                    sandbox = get_sandbox_security()
                    allowed, reason = sandbox.check_network("api.duckduckgo.com", 443)
                    if not allowed:
                        return {
                            "status": "error",
                            "message": f"网络访问被沙箱策略阻止: {reason}"
                        }
                except ImportError:
                    pass  # 沙箱未安装, skip检查
                except Exception as e:
                    pass  # 检查 failed不影响正常流程

                # 使用 DuckDuckGo API 进行Search
                url = f"https://api.duckduckgo.com/?q={query}&format=json&pretty=1"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # ProcessingSearch
                results = []
                
                # 提取主要信息
                abstract = data.get("Abstract", "")
                abstract_text = data.get("AbstractText", "")
                abstract_url = data.get("AbstractURL", "")
                
                if abstract or abstract_text:
                    results.append({
                        "title": data.get("Heading", "Search"),
                        "content": abstract or abstract_text,
                        "url": abstract_url
                    })
                
                # 提取相关主题
                related_topics = data.get("RelatedTopics", [])
                for topic in related_topics[:limit - len(results)]:
                    if "Text" in topic:
                        results.append({
                            "title": topic.get("Text", ""),
                            "content": topic.get("Text", ""),
                            "url": topic.get("FirstURL", "")
                        })
                
                # 限制数量
                results = results[:limit]
                
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "results": results,
                        "total": len(results)
                    }
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Search failed: {str(e)}"
                }
        else:
            return {
                "status": "error",
                "message": f"不支持的操作: {action}"
            }