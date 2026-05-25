# -*- coding: utf-8 -*-
"""
CogniCore Portable 优化Tool包
包含: 异步I/O, 性能cache, 批ProcessingTool
"""

import json
import hashlib
import time
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from functools import wraps
try:
    import aiofiles
    import aiofiles.os
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False
    aiofiles = None

logger = logging.getLogger(__name__)


# ==================== 异步文件I/O ====================

async def async_load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """异步LoadJSON文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        解析后的JSON对象,  failed返回None
    """
    if not HAS_AIOFILES:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Load file failed {file_path}: {e}")
            return None
    
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)
    except FileNotFoundError:
        logger.warning(f"File does not exist: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Load file failed {file_path}: {e}")
        return None


async def async_save_json(file_path: str, data: Any, indent: int = 2) -> bool:
    """异步SaveJSON文件
    
    Args:
        file_path: 文件路径
        data: 要Save的数据
        indent: 缩进空格数
        
    Returns:
        Save successful返回True
    """
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        if not HAS_AIOFILES:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=indent))
        return True
    except Exception as e:
        logger.error(f"Save file failed {file_path}: {e}")
        return False


async def async_file_exists(file_path: str) -> bool:
    """异步检查文件是否存在"""
    if not HAS_AIOFILES:
        return Path(file_path).exists()
    
    return await aiofiles.os.path.exists(file_path)


async def async_read_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """异步读取文本文件"""
    try:
        if not HAS_AIOFILES:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        
        async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
            return await f.read()
    except Exception as e:
        logger.error(f"Read file failed {file_path}: {e}")
        return None


async def async_write_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """异步写入文本文件"""
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        if not HAS_AIOFILES:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        
        async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
            await f.write(content)
        return True
    except Exception as e:
        logger.error(f"Write file failed {file_path}: {e}")
        return False


async def async_delete_file(file_path: str) -> bool:
    """异步Delete file"""
    try:
        if await async_file_exists(file_path):
            if not HAS_AIOFILES:
                Path(file_path).unlink()
            else:
                await aiofiles.os.remove(file_path)
            logger.info(f"Delete file: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Delete file failed {file_path}: {e}")
        return False


async def async_list_files(directory: str, pattern: str = "*") -> List[str]:
    """异步List目录中的文件"""
    try:
        path = Path(directory)
        if not path.exists():
            return []
        
        files = []
        for file in path.glob(pattern):
            if file.is_file():
                files.append(str(file))
        return files
    except Exception as e:
        logger.error(f"List files failed {directory}: {e}")
        return []


# ==================== 内存cache ====================

class MemoryCache:
    """高性能内存cache
    
    Features:
        - LRU淘汰策略
        - TTL过期机制
        - 访问统计
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """Initializationcache
        
        Args:
            max_size: 最大cache entries目数
            ttl: 默认过期时间 (s) 
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成cache键"""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Getcache值"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry['expires_at']:
                self.hits += 1
                entry['access_count'] += 1
                return entry['value']
            else:
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置cache值"""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        expires_at = time.time() + (ttl or self.default_ttl)
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'access_count': 0,
            'created_at': time.time()
        }
    
    def _evict_lru(self) -> None:
        """LRU淘汰策略"""
        if not self.cache:
            return
        
        lru_key = min(self.cache.keys(), 
                     key=lambda k: (self.cache[k]['access_count'], 
                                   self.cache[k]['created_at']))
        del self.cache[lru_key]
    
    def clear(self) -> None:
        """Clearcache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Getcache统计"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2f}%"
        }


# ==================== 文件cache ====================

class FileCache:
    """文件cache - 自动cache频繁读取的文件
    
    Features:
        - 自动文件读取cache
        - LRU淘汰策略
        - TTL过期机制
    """
    
    def __init__(self, max_size: int = 20, ttl: int = 300):
        """
        Args:
            max_size: 最大cache文件数
            ttl: cache过期时间 (s) 
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.access_count: Dict[str, int] = {}
    
    async def get(self, file_path: str) -> Optional[Any]:
        """Get文件Content (带cache) """
        if file_path in self.cache:
            entry = self.cache[file_path]
            if time.time() < entry['expires_at']:
                self.access_count[file_path] = self.access_count.get(file_path, 0) + 1
                return entry['data']
            else:
                del self.cache[file_path]
                del self.access_count[file_path]
        
        data = await async_load_json(file_path)
        if data is not None:
            self._add_to_cache(file_path, data)
        return data
    
    def _add_to_cache(self, file_path: str, data: Any) -> None:
        """Add到cache"""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[file_path] = {
            'data': data,
            'expires_at': time.time() + self.ttl,
            'created_at': time.time()
        }
        self.access_count[file_path] = 1
    
    def _evict_lru(self) -> None:
        """LRU淘汰"""
        if not self.cache:
            return
        
        lru_key = min(self.access_count.keys(),
                     key=lambda k: self.access_count[k])
        del self.cache[lru_key]
        del self.access_count[lru_key]
    
    def clear(self) -> None:
        """Clearcache"""
        self.cache.clear()
        self.access_count.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Getcache统计"""
        total_access = sum(self.access_count.values())
        return {
            'cached_files': len(self.cache),
            'max_size': self.max_size,
            'total_access': total_access,
            'avg_access': total_access / len(self.cache) if self.cache else 0
        }


# ==================== 批ProcessingTool ====================

class BatchProcessor:
    """批Processor - 合并多次I/O操作减少开销"""
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        """
        Args:
            batch_size: 批次大小
            flush_interval: 刷新间隔 (s) 
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending: List[Dict[str, Any]] = []
        self._last_flush = time.time()
    
    async def add(self, operation: str, data: Any) -> None:
        """Add操作到批次"""
        self.pending.append({
            'operation': operation,
            'data': data,
            'timestamp': time.time()
        })
        
        if len(self.pending) >= self.batch_size:
            await self.flush()
        elif time.time() - self._last_flush >= self.flush_interval:
            await self.flush()
    
    async def flush(self) -> List[Any]:
        """刷新批次并执行"""
        if not self.pending:
            return []
        
        results = []
        for item in self.pending:
            if item['operation'] == 'write':
                if isinstance(item['data'], tuple):
                    results.append(await async_save_json(item['data'][0], item['data'][1]))
                else:
                    results.append(True)
            elif item['operation'] == 'delete':
                results.append(await async_delete_file(item['data']))
        
        self.pending.clear()
        self._last_flush = time.time()
        return results


# ==================== 全局cache实例 ====================

memory_cache = MemoryCache(max_size=100, ttl=300)
file_cache = FileCache(max_size=20, ttl=300)
batch_processor = BatchProcessor(batch_size=50, flush_interval=2.0)


__all__ = [
    'async_load_json',
    'async_save_json',
    'async_file_exists',
    'async_read_file',
    'async_write_file',
    'async_delete_file',
    'async_list_files',
    'MemoryCache',
    'FileCache',
    'BatchProcessor',
    'memory_cache',
    'file_cache',
    'batch_processor',
]
