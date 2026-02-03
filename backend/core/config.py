"""
MapToPoster - Configuration Management

Handles loading and validation of service configurations.
Supports YAML, JSON, and environment variables.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration."""
    name: str = "MapToPoster API"
    version: str = "2.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_minute: int = 60
    burst: int = 10


@dataclass
class CORSConfig:
    """CORS configuration."""
    enabled: bool = True
    origins: list = None
    methods: list = None
    
    def __post_init__(self):
        if self.origins is None:
            self.origins = ["*"]
        if self.methods is None:
            self.methods = ["GET", "POST"]


class ConfigManager:
    """
    Central configuration manager.
    
    Loads configuration from multiple sources in priority order:
    1. Environment variables
    2. config.yaml/config.json
    3. Default values
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path or self._find_config_file()
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in common locations."""
        search_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path("config.json"),
            Path("backend/config.yaml"),
            Path("../config.yaml"),
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"Found config file: {path}")
                return path
        
        logger.warning("No config file found, using defaults")
        return None
    
    def _load_config(self):
        """Load configuration from file."""
        if not self.config_path or not self.config_path.exists():
            self._config = self._get_default_config()
            return
        
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.suffix in ['.yaml', '.yml']:
                    self._config = yaml.safe_load(f) or {}
                elif self.config_path.suffix == '.json':
                    self._config = json.load(f) or {}
                else:
                    logger.error(f"Unsupported config format: {self.config_path.suffix}")
                    self._config = self._get_default_config()
            
            logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._config = self._get_default_config()
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "app": asdict(AppConfig()),
            "rate_limit": asdict(RateLimitConfig()),
            "cors": asdict(CORSConfig()),
            "services": {
                "geocoding": {
                    "enabled": True,
                    "provider": "nominatim",
                    "cache_ttl": 86400
                },
                "generator": {
                    "enabled": True,
                    "default_theme": "feature_based",
                    "max_distance": 50000,
                    "default_dpi": 300
                },
                "themes": {
                    "enabled": True,
                    "allow_custom": True,
                    "max_custom_themes": 10
                },
                "export": {
                    "enabled": True,
                    "formats": ["png", "svg", "pdf"],
                    "max_file_size_mb": 50
                }
            }
        }
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # App settings
        if "APP_DEBUG" in os.environ:
            self._config.setdefault("app", {})["debug"] = \
                os.environ["APP_DEBUG"].lower() == "true"
        
        if "APP_PORT" in os.environ:
            self._config.setdefault("app", {})["port"] = \
                int(os.environ["APP_PORT"])
        
        # Service-specific overrides
        for key, value in os.environ.items():
            if key.startswith("SERVICE_"):
                # SERVICE_CACHE_ENABLED=true
                parts = key.lower().split("_")
                if len(parts) >= 3:
                    service = parts[1]
                    setting = "_".join(parts[2:])
                    
                    self._config.setdefault("services", {}) \
                        .setdefault(service, {})[setting] = self._parse_env_value(value)
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Boolean
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"
        
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        # String
        return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Supports dot notation for nested values:
        config.get("app.debug")
        config.get("services.cache.enabled")
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_app_config(self) -> AppConfig:
        """Get application configuration."""
        app_dict = self.get("app", {})
        return AppConfig(**{
            k: v for k, v in app_dict.items()
            if k in AppConfig.__annotations__
        })
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """
        Get service-specific configuration.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Service configuration dictionary
        """
        return self.get(f"services.{service_name}", {})
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled in config."""
        return self.get(f"services.{service_name}.enabled", False)
    
    def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Get all service configurations."""
        return self.get("services", {})
    
    def reload(self):
        """Reload configuration from file."""
        logger.info("Reloading configuration")
        self._load_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return self._config.copy()


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def init_config(config_path: Optional[Path] = None):
    """
    Initialize global configuration.
    
    Args:
        config_path: Optional path to configuration file
    """
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager
