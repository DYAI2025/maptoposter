"""
MapToPoster Backend - Core Package

Core infrastructure for modular service architecture.
"""

from backend.core.service_registry import ServiceRegistry, BaseService, ServiceMetadata
from backend.core.config import ConfigManager, get_config, init_config

__version__ = "2.0.0"

__all__ = [
    "ServiceRegistry",
    "BaseService",
    "ServiceMetadata",
    "ConfigManager",
    "get_config",
    "init_config",
]
