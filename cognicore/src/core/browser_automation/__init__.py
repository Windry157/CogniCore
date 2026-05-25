#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Browser automation module
"""
from .playwright_wrapper import PlaywrightCLIWrapper
from .browser_skill import BrowserAutomationSkill

__all__ = ["PlaywrightCLIWrapper", "BrowserAutomationSkill"]
