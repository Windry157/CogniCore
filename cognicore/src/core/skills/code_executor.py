#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码执行Skill: 支持 Python 和其他语言的代码运行
"""
import os
import sys
import subprocess
import tempfile
import json
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from .base import BaseSkill


class CodeExecutorSkill(BaseSkill):
    """代码执行Skill"""

    def __init__(self):
        self.allowed_dirs = [
            Path.home(),
            Path(os.getcwd()),
            Path(tempfile.gettempdir())
        ]

    @property
    def name(self) -> str:
        return "code_executor"

    @property
    def description(self) -> str:
        return "代码执行, 支持运行 Python, Shell, PowerShell 等代码.Register意: 为了安全, 代码在受限环境中执行."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["execute_python", "execute_shell", "execute_powershell", "execute_code", "write_file"],
                    "description": "要执行的操作"
                },
                "code": {
                    "type": "string",
                    "description": "要执行的代码Content"
                },
                "language": {
                    "type": "string",
                    "description": "编程语言 (用于 execute_code) "
                },
                "path": {
                    "type": "string",
                    "description": "文件路径 (用于 write_file) "
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间 (s) , 默认30"
                }
            },
            "required": ["action"]
        }

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {"status": "success", "data": {}}

        try:
            if action == "execute_python":
                code = params.get("code", "")
                if not code:
                    return {"status": "error", "message": "需要提供代码 (code)"}
                timeout = params.get("timeout", 30)
                result["data"] = self._execute_python(code, timeout)
            elif action == "execute_shell":
                code = params.get("code", "")
                if not code:
                    return {"status": "error", "message": "需要提供代码 (code)"}
                timeout = params.get("timeout", 30)
                result["data"] = self._execute_shell(code, timeout)
            elif action == "execute_powershell":
                code = params.get("code", "")
                if not code:
                    return {"status": "error", "message": "需要提供代码 (code)"}
                timeout = params.get("timeout", 30)
                result["data"] = self._execute_powershell(code, timeout)
            elif action == "execute_code":
                code = params.get("code", "")
                language = params.get("language", "")
                if not code or not language:
                    return {"status": "error", "message": "需要提供代码 (code) 和编程语言 (language)"}
                timeout = params.get("timeout", 30)
                result["data"] = self._execute_generic_code(code, language, timeout)
            elif action == "write_file":
                path = params.get("path", "")
                code = params.get("code", "")
                if not path or not code:
                    return {"status": "error", "message": "需要提供路径 (path) 和代码 (code)"}
                result["data"] = self._write_file(path, code)
            else:
                result["status"] = "error"
                result["message"] = f"未知的动作: {action}"

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"执行出错: {str(e)}"

        return result

    def _is_path_safe(self, path: str) -> bool:
        """检查路径是否安全"""
        try:
            target_path = Path(path).resolve()
            for allowed_dir in self.allowed_dirs:
                try:
                    if target_path.is_relative_to(allowed_dir.resolve()):
                        return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def _execute_python(self, code: str, timeout: int) -> Dict[str, Any]:
        """执行 Python 代码"""
        start_time = datetime.now()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return {
                "language": "python",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "execution_time": f"{elapsed:.2f} s"
            }
        except subprocess.TimeoutExpired:
            return {
                "language": "python",
                "error": f"执行超时 (超过 {timeout} s) ",
                "success": False
            }
        finally:
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    def _execute_shell(self, code: str, timeout: int) -> Dict[str, Any]:
        """执行 Shell 命令"""
        start_time = datetime.now()
        
        if os.name == 'nt':
            shell = 'cmd.exe'
            args = [shell, '/c', code]
        else:
            shell = '/bin/bash'
            args = [shell, '-c', code]
        
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return {
                "language": "shell",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "execution_time": f"{elapsed:.2f} s"
            }
        except subprocess.TimeoutExpired:
            return {
                "language": "shell",
                "error": f"执行超时 (超过 {timeout} s) ",
                "success": False
            }

    def _execute_powershell(self, code: str, timeout: int) -> Dict[str, Any]:
        """执行 PowerShell 命令"""
        if os.name != 'nt':
            return {
                "language": "powershell",
                "error": "PowerShell 仅在 Windows 系统上可用",
                "success": False
            }
        
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                ['powershell.exe', '-Command', code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return {
                "language": "powershell",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "execution_time": f"{elapsed:.2f} s"
            }
        except subprocess.TimeoutExpired:
            return {
                "language": "powershell",
                "error": f"执行超时 (超过 {timeout} s) ",
                "success": False
            }

    def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write file"""
        if not self._is_path_safe(path):
            return {
                "path": path,
                "error": "访问被拒绝: 该路径不在允许的目录中",
                "success": False
            }
        
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "path": str(file_path.resolve()),
            "size": self._format_bytes(len(content.encode('utf-8'))),
            "success": True,
            "message": "文件写入 successful"
        }

    def _execute_generic_code(self, code: str, language: str, timeout: int) -> Dict[str, Any]:
        """执行通用代码 (支持多种编程语言) """
        start_time = datetime.now()
        
        # 语言配置映射
        language_config = {
            'python': {'extension': '.py', 'command': [sys.executable]},
            'javascript': {'extension': '.js', 'command': ['node']},
            'typescript': {'extension': '.ts', 'command': ['ts-node']},
            'java': {'extension': '.java', 'command': ['javac', '-d', '.', '{file}', '&&', 'java', '{class_name}']},
            'c': {'extension': '.c', 'command': ['gcc', '{file}', '-o', '{output}', '&&', './{output}']},
            'cpp': {'extension': '.cpp', 'command': ['g++', '{file}', '-o', '{output}', '&&', './{output}']},
            'csharp': {'extension': '.cs', 'command': ['csc', '{file}', '&&', '{output}.exe']},
            'go': {'extension': '.go', 'command': ['go', 'run']},
            'rust': {'extension': '.rs', 'command': ['rustc', '{file}', '&&', './{output}']},
            'php': {'extension': '.php', 'command': ['php']},
            'ruby': {'extension': '.rb', 'command': ['ruby']},
            'perl': {'extension': '.pl', 'command': ['perl']},
            'swift': {'extension': '.swift', 'command': ['swift']},
            'kotlin': {'extension': '.kt', 'command': ['kotlinc', '{file}', '-include-runtime', '-d', '{output}.jar', '&&', 'java', '-jar', '{output}.jar']},
            'scala': {'extension': '.scala', 'command': ['scala']},
            'r': {'extension': '.r', 'command': ['Rscript']},
            'lua': {'extension': '.lua', 'command': ['lua']},
            'bash': {'extension': '.sh', 'command': ['bash']},
            'powershell': {'extension': '.ps1', 'command': ['powershell.exe', '-File']},
            'sql': {'extension': '.sql', 'command': ['sqlite3', ':memory:', '.read', '{file}']},
        }
        
        # 规范化语言Name
        language = language.lower()
        
        # 检查语言是否支持
        if language not in language_config:
            return {
                "language": language,
                "error": f"不支持的编程语言: {language}",
                "success": False
            }
        
        config = language_config[language]
        extension = config['extension']
        command_template = config['command']
        
        # Create临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        output_file = temp_file.replace(extension, '')
        class_name = Path(temp_file).stem
        
        try:
            # 构建命令
            command = []
            for part in command_template:
                if '{file}' in part:
                    command.append(part.replace('{file}', temp_file))
                elif '{output}' in part:
                    command.append(part.replace('{output}', output_file))
                elif '{class_name}' in part:
                    command.append(part.replace('{class_name}', class_name))
                else:
                    command.append(part)
            
            # Execute command
            if '&&' in command:
                # Processing包含多 命令的情况
                shell_command = ' '.join(command)
                if os.name == 'nt':
                    result = subprocess.run(
                        ['cmd.exe', '/c', shell_command],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                else:
                    result = subprocess.run(
                        ['/bin/bash', '-c', shell_command],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
            else:
                # Processing单 命令的情况
                result = subprocess.run(
                    command + [temp_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return {
                "language": language,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "execution_time": f"{elapsed:.2f} s"
            }
        except subprocess.TimeoutExpired:
            return {
                "language": language,
                "error": f"执行超时 (超过 {timeout} s) ",
                "success": False
            }
        except FileNotFoundError as e:
            return {
                "language": language,
                "error": f"执行环境未Found: {str(e)}",
                "success": False
            }
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
                # 清理编译产物
                if os.path.exists(output_file):
                    os.unlink(output_file)
                if os.path.exists(output_file + '.exe'):
                    os.unlink(output_file + '.exe')
                if os.path.exists(output_file + '.jar'):
                    os.unlink(output_file + '.jar')
                if os.path.exists(class_name + '.class'):
                    os.unlink(class_name + '.class')
            except Exception:
                pass

    def _format_bytes(self, bytes_value: int) -> str:
        """格式化 bytes数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
