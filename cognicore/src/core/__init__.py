#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CogniCore 核心模块
"""

from .agent import (
    AgentCoordinator,
    MultiLayerAgentSystem,
    TaskPlanner,
    TaskExecutor,
    TaskCritic,
    TaskValidator,
)
from .memory import UnifiedMemorySystem
from .llm import LLMFactory, OllamaService, LLMService
from .skill_manager import SkillManager, get_skill_manager
from .skill import SkillManager as EnhancedSkillManager, get_skill_manager as get_enhanced_skill_manager
from .config import config
from .assistant import assistant

try:
    from .uncertainty import (
        confidence_scorer,
        confidence_visualizer,
        confidence_cache,
        confidence_logger,
        response_wrapper,
    )
    _HAS_UNCERTAINTY = True
except ImportError:
    _HAS_UNCERTAINTY = False

try:
    from .observability import (
        metrics_collector,
        service_monitor,
        rate_limiter,
        monitor_latency,
    )
    _HAS_OBSERVABILITY = True
except ImportError:
    _HAS_OBSERVABILITY = False

try:
    from .evaluation import (
        faithfulness_evaluator,
        relevance_evaluator,
        quality_evaluator,
    )
    _HAS_EVALUATION = True
except ImportError:
    _HAS_EVALUATION = False

try:
    from .cognition import (
        system1,
        system2,
        bayesian_brain,
        cognition_coordinator,
        reasoning_visualizer,
    )
    _HAS_COGNITION = True
except ImportError:
    _HAS_COGNITION = False

try:
    from .resilience import (
        circuit_breaker,
        event_bus,
        CircuitBreaker,
        EventBus,
        CircuitBreakerError,
        CircuitState,
        DomainEvent,
        SagaOrchestrator,
        SagaState,
        SagaStep,
    )
    _HAS_RESILIENCE = True
except ImportError:
    _HAS_RESILIENCE = False

try:
    from .webui import (
        ui_manager,
        web_interface,
        UIManager,
        WebInterface,
        render_to_html,
    )
    _HAS_WEBUI = True
except ImportError:
    _HAS_WEBUI = False

try:
    from .health import (
        get_system_health,
        get_health_monitor,
        get_recovery_protocol,
        HealthStatus,
        SystemState
    )
    _HAS_HEALTH = True
except ImportError:
    _HAS_HEALTH = False

__all__ = [
    "AgentCoordinator",
    "MultiLayerAgentSystem",
    "TaskPlanner",
    "TaskExecutor",
    "TaskCritic",
    "TaskValidator",
    "UnifiedMemorySystem",
    "LLMFactory",
    "OllamaService",
    "LLMService",
    "SkillManager",
    "get_skill_manager",
    "EnhancedSkillManager",
    "get_enhanced_skill_manager",
    "config",
    "assistant",
]

if _HAS_UNCERTAINTY:
    __all__.extend([
        "confidence_scorer",
        "confidence_visualizer",
        "confidence_cache",
        "confidence_logger",
        "response_wrapper",
    ])

if _HAS_OBSERVABILITY:
    __all__.extend([
        "metrics_collector",
        "service_monitor",
        "rate_limiter",
        "monitor_latency",
    ])

if _HAS_EVALUATION:
    __all__.extend([
        "faithfulness_evaluator",
        "relevance_evaluator",
        "quality_evaluator",
    ])

if _HAS_COGNITION:
    __all__.extend([
        "system1",
        "system2",
        "bayesian_brain",
        "cognition_coordinator",
        "reasoning_visualizer",
    ])

if _HAS_RESILIENCE:
    __all__.extend([
        "circuit_breaker",
        "event_bus",
        "CircuitBreaker",
        "EventBus",
        "CircuitBreakerError",
        "CircuitState",
        "DomainEvent",
        "SagaOrchestrator",
        "SagaState",
        "SagaStep",
    ])

if _HAS_WEBUI:
    __all__.extend([
        "ui_manager",
        "web_interface",
        "UIManager",
        "WebInterface",
        "render_to_html",
    ])

if _HAS_HEALTH:
    __all__.extend([
        "get_system_health",
        "get_health_monitor",
        "get_recovery_protocol",
        "HealthStatus",
        "SystemState"
    ])
