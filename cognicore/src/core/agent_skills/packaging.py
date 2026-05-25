#!/usr/bin/env python3
"""
Skill 打包/分享机制
支持将Skill导出为独立包, 也可From文件或远程源导入.
"""
import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import zipfile
import io

from .schema import SkillManifest, SkillCategory, SkillVisibility, make_manifest
from .registry import SkillRegistry, get_registry

logger = logging.getLogger("SkillPackaging")

PACKAGE_EXTENSION = ".skill.json"
PACKAGE_FORMAT_VERSION = "1.0"


class SkillPackage:
    """Skill包 - 可分享的独立Skill单元"""

    def __init__(self, manifest: SkillManifest, implementation: Optional[str] = None,
                 dependencies: Optional[List[str]] = None):
        self.manifest = manifest
        self.implementation = implementation or ""
        self.dependencies = dependencies or []
        self.format_version = PACKAGE_FORMAT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format_version": self.format_version,
            "manifest": self.manifest.to_dict(),
            "implementation": self.implementation,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillPackage":
        manifest = SkillManifest.from_dict(data["manifest"])
        return cls(
            manifest=manifest,
            implementation=data.get("implementation", ""),
            dependencies=data.get("dependencies", []),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "SkillPackage":
        return cls.from_dict(json.loads(text))


class PackageManager:
    """Skill包管理器"""

    def __init__(self, registry: Optional[SkillRegistry] = None,
                 package_dir: str = "data/skill_packages"):
        self.registry = registry or get_registry()
        self.package_dir = package_dir
        os.makedirs(package_dir, exist_ok=True)

    # ----- 导出 -----

    def export_skill(self, skill_id: str) -> Optional[SkillPackage]:
        manifest = self.registry.get(skill_id)
        if not manifest:
            return None
        return SkillPackage(manifest=manifest)

    def export_to_file(self, skill_id: str, filepath: str) -> bool:
        pkg = self.export_skill(skill_id)
        if not pkg:
            return False
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(pkg.to_json())
        logger.info(f"Skill package exported: {filepath}")
        return True

    # ----- 导入 -----

    def import_from_file(self, filepath: str) -> Optional[SkillManifest]:
        with open(filepath, "r", encoding="utf-8") as f:
            pkg = SkillPackage.from_json(f.read())
        self.registry.register(pkg.manifest)
        logger.info(f"Skill package imported: {pkg.manifest.id}")
        return pkg.manifest

    def import_from_json(self, text: str) -> Optional[SkillManifest]:
        pkg = SkillPackage.from_json(text)
        self.registry.register(pkg.manifest)
        return pkg.manifest

    # ----- 包枚举 -----

    def list_packages(self) -> List[str]:
        if not os.path.isdir(self.package_dir):
            return []
        return [
            f for f in os.listdir(self.package_dir)
            if f.endswith(PACKAGE_EXTENSION)
        ]

    def install_all(self) -> int:
        count = 0
        for fname in self.list_packages():
            fpath = os.path.join(self.package_dir, fname)
            try:
                self.import_from_file(fpath)
                count += 1
            except Exception as e:
                logger.error(f"Skill package installation failed {fname}: {e}")
        return count
