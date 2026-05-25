#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web UI 集成模块
提供简单的Web界面功能
专为U盘便携项目优化
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class UIComponent:
    """UI组件"""
    id: str
    type: str
    title: str
    content: Any
    metadata: Dict[str, Any]


class UIManager:
    """UI管理器
    
    管理多个UI组件
    """
    
    def __init__(self):
        """初始化"""
        self.components: Dict[str, UIComponent] = {}
        self.component_callbacks: Dict[str, Callable] = {}
        
        logger.info("UI管理器初始化完成")
    
    def register_component(self, component: UIComponent):
        """注册组件
        
        Args:
            component: 组件
        """
        self.components[component.id] = component
        logger.debug(f"注册组件: {component.id}")
    
    def get_component(self, component_id: str) -> Optional[UIComponent]:
        """获取组件
        
        Args:
            component_id: 组件ID
            
        Returns:
            组件
        """
        return self.components.get(component_id)
    
    def list_components(self) -> List[UIComponent]:
        """列出所有组件
        
        Returns:
            组件列表
        """
        return list(self.components.values())
    
    def get_dashboard(self) -> List[Dict[str, Any]]:
        """获取仪表板内容
        
        Returns:
            仪表板组件
        """
        # 确保默认组件已创建（懒加载）
        create_default_ui_components()
        
        dashboard_items = []
        
        for comp in self.components.values():
            dashboard_items.append({
                "id": comp.id,
                "type": comp.type,
                "title": comp.title,
                "content": comp.content,
                "metadata": comp.metadata,
            })
        
        return dashboard_items


ui_manager = UIManager()


# 默认组件标记，用于懒加载
_default_ui_created = False


def create_default_ui_components():
    """创建默认UI组件（懒加载）"""
    global _default_ui_created
    if _default_ui_created:
        return
    
    try:
        # 健康组件
        health = UIComponent(
            id="health_status",
            type="status",
            title="系统状态",
            content="运行中",
            metadata={
                "icon": "🚀",
                "updated": datetime.now().isoformat(),
            }
        )
        
        # 统计组件（安全获取）
        stats_content = {}
        try:
            from src.core.cognition import cognition_coordinator
            stats_content = cognition_coordinator.get_statistics()
        except Exception as e:
            logger.debug(f"获取认知统计失败: {e}")
        
        stats = UIComponent(
            id="cogni_stats",
            type="stats",
            title="决策统计",
            content=stats_content,
            metadata={
                "icon": "📊",
            }
        )
        
        ui_manager.register_component(health)
        ui_manager.register_component(stats)
        _default_ui_created = True
        logger.debug("默认UI组件创建完成")
    except Exception as e:
        logger.warning(f"创建默认UI组件失败: {e}")


def render_to_html(content: Any, style: str = "default") -> str:
    """渲染内容为HTML
    
    Args:
        content: 要渲染的内容
        style: 样式类型
        
    Returns:
        HTML字符串
    """
    html = '<div class="cogni-rendered">'
    
    if isinstance(content, dict):
        html += '<div class="dict-content">'
        for key, value in content.items():
            key_str = str(key).replace("_", " ").title()
            html += f'<p><b>{key_str}:</b> {value}</p>'
        html += '</div>'
    
    elif isinstance(content, list):
        html += '<ul>'
        for item in content:
            html += f'<li>{render_to_html(item)}</li>'
        html += '</ul>'
    
    else:
        html += f'<p>{str(content)}</p>'
    
    html += '</div>'
    
    return html


class WebInterface:
    """Web界面简单封装
    
    提供静态页面生成
    """
    
    def __init__(self):
        """初始化"""
        self.pages: Dict[str, Callable] = {}
        self.register_page("dashboard", self.render_dashboard)
        
        logger.info("Web界面初始化完成")
    
    def register_page(self, page_id: str, render_func: Callable):
        """注册页面
        
        Args:
            page_id: 页面ID
            render_func: 渲染函数
        """
        self.pages[page_id] = render_func
    
    def render_page(self, page_id: str = "dashboard") -> str:
        """渲染页面
        
        Args:
            page_id: 页面ID
            
        Returns:
            HTML字符串
        """
        if page_id in self.pages:
            return self.pages[page_id]()
        
        return self.render_not_found()
    
    def render_dashboard(self) -> str:
        """渲染仪表板
        
        Returns:
            HTML字符串
        """
        components = ui_manager.get_dashboard()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>CogniCore Dashboard</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9fafb;
                }
                h1 {
                    color: #1f2937;
                    text-align: center;
                }
                .dashboard-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-top: 30px;
                }
                @media (max-width: 768px) {
                    .dashboard-grid {
                        grid-template-columns: 1fr;
                    }
                }
                .component {
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .component h2 {
                    margin-top: 0;
                    color: #4b5563;
                }
                .status-good {
                    color: green;
                }
                .status-warning {
                    color: orange;
                }
                .status-error {
                    color: red;
                }
            </style>
        </head>
        <body>
            <h1>🚀 CogniCore Dashboard</h1>
            <div class="dashboard-grid">
        """
        
        for comp in components:
            icon = comp.get("metadata", {}).get("icon", "")
            html += f"""
            <div class="component">
                <h2>{icon} {comp.get('title', '')}</h2>
                {render_to_html(comp.get('content'))}
            </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def render_not_found(self) -> str:
        """渲染404
        
        Returns:
            HTML字符串
        """
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Page Not Found</title>
        </head>
        <body>
            <h1>404 - Page Not Found</h1>
        </body>
        </html>
        """


web_interface = WebInterface()

# ============================================
# 模块导出
# ============================================
__all__ = [
    "UIComponent",
    "UIManager",
    "ui_manager",
    "render_to_html",
    "WebInterface",
    "web_interface",
]
