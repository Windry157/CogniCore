#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CogniCore - Claw 系统配置
这是项目的核心配置文件
定义了CogniCore的基本信息和功能 module
"""

from typing import Dict, Any


class CogniCoreConfig:
    """CogniCore配置类"""
    
    # 项目基本信息
    PROJECT_NAME: str = "CogniCore"
    PROJECT_FULL_NAME: str = "CogniCore - Claw"
    VERSION: str = "2.1.0"
    DESCRIPTION: str = "基于贝叶斯推理的Agent认知核心系统"
    
    # 系统架构信息
    ARCHITECTURE: Dict[str, Any] = {
        "memory": "5层 memories架构",
        "learning": "贝叶斯自主学习",
        "agent": "多Agent协作",
        "inference": "主动推理",
        "gpu": "RTX 3080 20GB"
    }
    
    #  module说明
    MODULES: Dict[str, str] = {
        "agent": "Agent系统",
        "learning": "贝叶斯学习",
        "memory": "五层 memories",
        "tools": "系统Tool",
        "api": "API网关",
        "frontend": "React前端"
    }
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """GetSystem Info"""
        return {
            "name": cls.PROJECT_NAME,
            "full_name": cls.PROJECT_FULL_NAME,
            "version": cls.VERSION,
            "description": cls.DESCRIPTION,
            "architecture": cls.ARCHITECTURE,
            "modules": cls.MODULES
        }


def get_cognicore_info() -> Dict[str, Any]:
    """GetCogniCore信息的快捷方式"""
    return CogniCoreConfig.get_info()


if __name__ == "__main__":
    info = get_cognicore_info()
    print(f"[boot] CogniCoreSystem Info: ")
    for key, value in info.items():
        print(f"  - {key}: {value}")
