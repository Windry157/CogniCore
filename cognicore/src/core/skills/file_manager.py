#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理Skill: 安全的文件浏览和操作
"""
import os
import shutil
import stat
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from .base import BaseSkill

# 使用 send2trash 移动到回收站, 符合用户规则: Delete file移入回收站保留7天
try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    # 如果没有安装, 降级到直接Delete
    HAS_SEND2TRASH = False


class FileManagerSkill(BaseSkill):
    """文件管理Skill"""

    def __init__(self):
        self.allowed_directories = self._get_allowed_directories()

    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return "安全的文件管理, 包括浏览目录, 查看文件信息, 复制, 移动, Delete file等."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_dir", "get_file_info", "read_file", "copy_file", "move_file", "delete_file", "create_dir"],
                    "description": "要执行的操作"
                },
                "path": {
                    "type": "string",
                    "description": "文件或目录路径"
                },
                "target_path": {
                    "type": "string",
                    "description": "目标路径 (用于复制和移动操作) "
                },
                "max_size": {
                    "type": "integer",
                    "description": "Read file的最大大小 ( bytes) , 默认10MB"
                }
            },
            "required": ["action", "path"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {"status": "success", "data": {}}
        path = params.get("path", "")
        target_path = params.get("target_path", "")

        try:
            if not self._is_path_allowed(path):
                return {"status": "error", "message": "访问被拒绝: 该路径不在允许的目录中"}

            if target_path and not self._is_path_allowed(target_path):
                return {"status": "error", "message": "访问被拒绝: 目标路径不在允许的目录中"}

            # 限制目录列表的大小, 避免Processing过多文件导致卡住
            if action == "list_dir":
                result["data"] = await self._list_directory_with_limit(path)
            elif action == "get_file_info":
                result["data"] = self._get_file_info(path)
            elif action == "read_file":
                max_size = params.get("max_size", 10485760)
                result["data"] = self._read_file(path, max_size)
            elif action == "copy_file":
                result["data"] = self._copy_file(path, target_path)
            elif action == "move_file":
                result["data"] = self._move_file(path, target_path)
            elif action == "delete_file":
                result["data"] = self._delete_file(path)
            elif action == "create_dir":
                result["data"] = self._create_directory(path)
            else:
                result["status"] = "error"
                result["message"] = f"未知的动作: {action}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"执行出错: {str(e)}"

        return result
    
    async def _list_directory_with_limit(self, path: str) -> Dict[str, Any]:
        """List目录Content, 限制返回的文件和目录数量"""
        dir_path = Path(path)
        if not dir_path.exists() or not dir_path.is_dir():
            raise ValueError(f"目录does not exist或不是目录: {path}")

        files = []
        dirs = []
        max_items = 30  # 限制返回的项目数量 (减少以控制大小) 
        item_count = 0

        for item in dir_path.iterdir():
            try:
                if item_count >= max_items:
                    break

                stat_info = item.stat()
                # 简化返回的信息, 减少大小
                info = {
                    "name": item.name,
                    "size": self._format_bytes(stat_info.st_size) if item.is_file() else "<DIR>",
                }

                if item.is_dir():
                    dirs.append(info)
                else:
                    files.append(info)

                item_count += 1
            except (PermissionError, OSError):
                continue

        return {
            "path": str(dir_path.resolve()),
            "directories": dirs,
            "files": files,
            "total_items": len(dirs) + len(files),
            "limited": item_count >= max_items
        }

    def _get_allowed_directories(self) -> List[Path]:
        """Get允许访问的目录列表 (跨平台) """
        home = Path.home()
        allowed = [
            home / "Documents",
            Path(os.getcwd()),
            home / "Downloads",
            home / "Desktop",
        ]
        
        # Windows-specific directories
        import platform
        if platform.system() == "Windows":
            allowed += [
                home / "AppData",
                Path("C:/"),
                Path("D:/"),
                Path("E:/"),
            ]
        
        # Linux-specific directories
        if platform.system() == "Linux":
            allowed += [
                Path("/home"),
                Path("/media"),
                Path("/mnt"),
            ]
        
        allowed = [p for p in allowed if p.exists()]
        return allowed
    
    def _is_path_allowed(self, path: str) -> bool:
        """检查路径是否在允许的目录中 (跨平台) """
        try:
            path_obj = Path(path).resolve()
            
            for allowed_dir in self.allowed_directories:
                if path_obj.is_relative_to(allowed_dir):
                    return True
            
            return path_obj.parent == path_obj  # root directory
        except Exception:
            return False



    def _get_file_info(self, path: str) -> Dict[str, Any]:
        """Get文件信息"""
        file_path = Path(path)
        if not file_path.exists():
            raise ValueError(f"File does not exist: {path}")

        stat_info = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path.resolve()),
            "is_dir": file_path.is_dir(),
            "is_file": file_path.is_file(),
            "size": self._format_bytes(stat_info.st_size),
            "size_bytes": stat_info.st_size,
            "created": datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "modified": datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "permissions": stat.filemode(stat_info.st_mode)
        }

    def _read_file(self, path: str, max_size: int) -> Dict[str, Any]:
        """Read fileContent"""
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"File does not exist或不是文件: {path}")

        stat_info = file_path.stat()
        if stat_info.st_size > max_size:
            raise ValueError(f"文件过大 ({self._format_bytes(stat_info.st_size)}) , 超过限制 ({self._format_bytes(max_size)}) ")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "path": str(file_path.resolve()),
                "size": self._format_bytes(stat_info.st_size),
                "content": content,
                "encoding": "utf-8"
            }
        except UnicodeDecodeError:
            return {
                "path": str(file_path.resolve()),
                "size": self._format_bytes(stat_info.st_size),
                "content": "[二进制文件, 无法以文本形式读取]",
                "encoding": "binary"
            }

    def _copy_file(self, src: str, dst: str) -> Dict[str, Any]:
        """复制文件"""
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            raise ValueError(f"源File does not exist: {src}")
        
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        
        return {
            "source": str(src_path.resolve()),
            "destination": str(dst_path.resolve()),
            "message": "复制 successful"
        }

    def _move_file(self, src: str, dst: str) -> Dict[str, Any]:
        """移动文件"""
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            raise ValueError(f"源File does not exist: {src}")
        
        shutil.move(src_path, dst_path)
        
        return {
            "source": str(src_path.resolve()),
            "destination": str(dst_path.resolve()),
            "message": "移动 successful"
        }

    def _delete_file(self, path: str) -> Dict[str, Any]:
        """Delete file, 移动到回收站 (符合用户规则) """
        file_path = Path(path)
        
        if not file_path.exists():
            raise ValueError(f"File does not exist: {path}")
        
        if HAS_SEND2TRASH:
            # 移动到回收站, 保留7天可恢复
            send2trash(str(file_path))
            message = "already移动到回收站, 可以恢复 (保留7天) "
        else:
            # 如果没有 send2trash, 降级到直接Delete
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            message = "already直接Delete (未安装 send2trash, 无法恢复) "
        
        return {
            "path": str(file_path.resolve()),
            "message": message
        }

    def _create_directory(self, path: str) -> Dict[str, Any]:
        """Create目录"""
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "path": str(dir_path.resolve()),
            "message": "目录Create successful"
        }

    def _format_bytes(self, bytes_value: int) -> str:
        """格式化 bytes数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
