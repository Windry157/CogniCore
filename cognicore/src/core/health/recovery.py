#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障恢复协议模块
提供优雅关闭、故障恢复、状态保存功能
"""

import asyncio
import logging
import json
import signal
import sys
import os
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SystemState:
    """系统状态"""
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    RECOVERING = "recovering"
    ERROR = "error"
    STOPPED = "stopped"


class RecoveryProtocol:
    """故障恢复协议"""

    def __init__(self):
        self.state = SystemState.STOPPED
        self._shutdown_callbacks: list = []
        self._startup_callbacks: list = []
        self._state_file = None
        self._setup_state_file()
        self._setup_signal_handlers()

    def _setup_state_file(self):
        """设置状态保存文件"""
        try:
            from src.core.config.config import _get_project_root
            root = _get_project_root()
            state_dir = root / "data" / "system"
            state_dir.mkdir(parents=True, exist_ok=True)
            self._state_file = state_dir / "system_state.json"
        except Exception as e:
            logger.warning(f"Could not set up state file: {e}")

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            signal.signal(signal.SIGINT, self._handle_shutdown_signal)
            signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
            if sys.platform != "win32":
                signal.signal(signal.SIGHUP, self._handle_reload_signal)
        except Exception as e:
            logger.warning(f"Could not set up signal handlers: {e}")

    def _handle_shutdown_signal(self, sig, frame):
        """处理关闭信号"""
        logger.warning(f"Received shutdown signal {sig}")
        asyncio.create_task(self.graceful_shutdown())

    def _handle_reload_signal(self, sig, frame):
        """处理重载信号"""
        logger.warning(f"Received reload signal {sig}")
        asyncio.create_task(self.reload())

    def register_shutdown_callback(self, callback: Callable):
        """注册关闭回调"""
        self._shutdown_callbacks.append(callback)
        logger.debug(f"Registered shutdown callback: {callback.__name__}")

    def register_startup_callback(self, callback: Callable):
        """注册启动回调"""
        self._startup_callbacks.append(callback)
        logger.debug(f"Registered startup callback: {callback.__name__}")

    async def startup(self):
        """系统启动"""
        logger.info("🚀 System starting up...")
        self.state = SystemState.RUNNING

        for callback in self._startup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                logger.debug(f"Startup callback completed: {callback.__name__}")
            except Exception as e:
                logger.error(f"Startup callback failed: {callback.__name__}, {e}")

        await self._save_state("startup")
        logger.info("✅ System startup complete")

    async def graceful_shutdown(self):
        """优雅关闭"""
        if self.state in [SystemState.SHUTTING_DOWN, SystemState.STOPPED]:
            logger.warning("System already shutting down")
            return

        logger.warning("⚠️  Initiating graceful shutdown...")
        self.state = SystemState.SHUTTING_DOWN

        await self._save_state("shutdown")

        for callback in reversed(self._shutdown_callbacks):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                logger.debug(f"Shutdown callback completed: {callback.__name__}")
            except Exception as e:
                logger.error(f"Shutdown callback failed: {callback.__name__}, {e}")

        self.state = SystemState.STOPPED
        logger.info("✅ System shutdown complete")

    async def reload(self):
        """系统重载"""
        logger.info("🔄 System reloading...")
        self.state = SystemState.RECOVERING

        for callback in reversed(self._shutdown_callbacks):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Pre-reload callback failed: {callback.__name__}, {e}")

        for callback in self._startup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Post-reload callback failed: {callback.__name__}, {e}")

        self.state = SystemState.RUNNING
        await self._save_state("reload")
        logger.info("✅ System reload complete")

    async def recover_from_crash(self):
        """从崩溃中恢复"""
        logger.warning("🆘 Recovering from crash...")
        self.state = SystemState.RECOVERING

        last_state = await self._load_state()
        if last_state:
            logger.info(f"Last known state: {last_state}")

        for callback in self._startup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Recovery callback failed: {callback.__name__}, {e}")

        self.state = SystemState.RUNNING
        await self._save_state("recovery")
        logger.info("✅ System recovery complete")

    async def _save_state(self, event: str):
        """保存系统状态"""
        if not self._state_file:
            return

        try:
            state_data = {
                "state": self.state,
                "event": event,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            }

            self._state_file.write_text(
                json.dumps(state_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.debug(f"State saved: {state_data}")
        except Exception as e:
            logger.warning(f"Could not save state: {e}")

    async def _load_state(self) -> Optional[Dict[str, Any]]:
        """加载上次状态"""
        if not self._state_file or not self._state_file.exists():
            return None

        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
            return None

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "state": self.state,
            "shutdown_callbacks": len(self._shutdown_callbacks),
            "startup_callbacks": len(self._startup_callbacks)
        }


_recovery_protocol = None


def get_recovery_protocol() -> RecoveryProtocol:
    """获取恢复协议单例"""
    global _recovery_protocol
    if _recovery_protocol is None:
        _recovery_protocol = RecoveryProtocol()
    return _recovery_protocol
