#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理类
"""

import yaml
import os
import time
import threading
from typing import Any, Dict
from pathlib import Path

class ConfigManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config_path = Path(os.getenv("CONFIG_PATH", "config.yaml"))
        self.config = self.load_config()
        self.last_modified = os.path.getmtime(self.config_path)
        # 存储上一 有效的配置, 用于回滚
        self.last_valid_config = self.config.copy()
        self._initialized = True
        
        # Start热重载监控线程
        self._start_watcher()
    
    def load_config(self) -> Dict[str, Any]:
        """Load config file"""
        if not self.config_path.exists():
            return self.create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                # 验证配置格式
                if self._validate_config(config):
                    # 配置验证 successful, Updatelast valid config
                    self.last_valid_config = config.copy()
                    return config
                else:
                    print("Config format validation failed, rolling back to last valid config")
                    return self.last_valid_config
        except Exception as e:
            print(f"Load config file failed: {e}")
            print("Load failed, using previous valid config")
            return self.last_valid_config
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置格式"""
        try:
            # 验证必要的配置项
            required_sections = ['app', 'server', 'models']
            for section in required_sections:
                if section not in config:
                    print(f"Config missing required section: {section}")
                    return False
            
            # 验证app部分
            if 'name' not in config.get('app', {}) or 'version' not in config.get('app', {}):
                print("appConfig missing required items")
                return False
            
            # 验证server部分
            server = config.get('server', {})
            if 'host' not in server or 'port' not in server:
                print("serverConfig missing required items")
                return False
            
            # 验证models部分
            models = config.get('models', {})
            if 'default' not in models or 'ollama_url' not in models:
                print("modelsConfig missing required items")
                return False
            
            # 验证端口号
            if not isinstance(server.get('port'), int) or server.get('port') < 1 or server.get('port') > 65535:
                print("Invalid port number configuration")
                return False
            
            return True
        except Exception as e:
            print(f"Error validating configuration: {e}")
            return False
    
    def create_default_config(self):
        """Create默认配置"""
        default_config = {
            'app': {'name': '智能助手', 'version': '0.2.0', 'debug': False},
            'server': {'host': '0.0.0.0', 'port': 8000, 'workers': 4},
            'models': {
                'default': 'minimax-m2.7:cloud',
                'ollama_url': 'http://localhost:11434',
                'refresh_interval': 300
            }
        }
        
        # 确保配置目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True)
        
        return default_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get配置项"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()
    
    def save_config(self):
        """Save配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True)
        # Update最后修改时间
        self.last_modified = os.path.getmtime(self.config_path)
    
    def _start_watcher(self):
        """Start配置监控线程"""
        def watch():
            while True:
                time.sleep(5)  # 每5s检查一次
                try:
                    current_mtime = os.path.getmtime(self.config_path)
                    if current_mtime > self.last_modified:
                        with self._lock:
                            old_config = self.config.copy()
                            self.config = self.load_config()
                            self.last_modified = current_mtime
                            print(f"[ConfigManager] Config hot reloaded: {self.config_path}")
                            
                            # 通知配置变化
                            self._notify_config_change(old_config, self.config)
                except Exception as e:
                    print(f"[ConfigManager] Monitor error: {e}")
        
        thread = threading.Thread(target=watch, daemon=True)
        thread.start()
    
    def _notify_config_change(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """通知配置变化"""
        try:
            # 导入WebSocket管理器 (避免循环导入) 
            from src.api.websocket_manager import websocket_manager
            
            # 计算配置变化
            changes = self._get_config_changes(old_config, new_config)
            
            if changes:
                # 异步通知WebSocket管理器
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(websocket_manager.notify_config_change(changes))
                loop.close()
        except Exception as e:
            print(f"[ConfigManager] Failed to notify config change: {e}")
    
    def _get_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """计算配置变化"""
        changes = {}
        
        # 检查顶层配置项
        all_keys = set(old_config.keys()) | set(new_config.keys())
        
        for key in all_keys:
            old_value = old_config.get(key)
            new_value = new_config.get(key)
            
            if old_value != new_value:
                if isinstance(old_value, dict) and isinstance(new_value, dict):
                    # 递归检查嵌套配置
                    nested_changes = self._get_config_changes(old_value, new_value)
                    if nested_changes:
                        changes[key] = nested_changes
                else:
                    changes[key] = {
                        "old": old_value,
                        "new": new_value
                    }
        
        return changes
    
    def reload(self):
        """手动触发重载"""
        with self._lock:
            self.config = self.load_config()
            self.last_modified = os.path.getmtime(self.config_path)
            print(f"[ConfigManager] Config manually reloaded: {self.config_path}")