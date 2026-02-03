"""
MapToPoster - Service Registry

Core service management system for modular plugin architecture.
Services can be dynamically loaded, enabled, disabled, and configured.
"""

from typing import Dict, Any, Optional, Type, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service lifecycle status."""
    DISABLED = "disabled"
    ENABLED = "enabled"
    LOADING = "loading"
    ERROR = "error"


@dataclass
class ServiceMetadata:
    """Metadata for a registered service."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    optional: bool = False
    status: ServiceStatus = ServiceStatus.DISABLED


class BaseService(ABC):
    """
    Base class for all services.
    
    All services must inherit from this class and implement:
    - initialize(): Setup logic when service is enabled
    - shutdown(): Cleanup logic when service is disabled
    - health_check(): Return service health status
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize service with configuration.
        
        Args:
            config: Service-specific configuration dictionary
        """
        self.config = config
        self._initialized = False
        self._metadata: Optional[ServiceMetadata] = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the service.
        
        Called when service is enabled. Should setup resources,
        connections, caches, etc.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the service.
        
        Called when service is disabled. Should cleanup resources,
        close connections, flush caches, etc.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check service health status.
        
        Returns:
            Dictionary with health information:
            {
                "healthy": bool,
                "message": str,
                "details": dict
            }
        """
        pass
    
    @classmethod
    def get_metadata(cls) -> ServiceMetadata:
        """Get service metadata. Override in subclass."""
        return ServiceMetadata(
            name=cls.__name__,
            description="Base service"
        )
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized


class ServiceRegistry:
    """
    Central registry for all services.
    
    Manages service lifecycle (load, enable, disable, unload),
    dependency resolution, and configuration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize service registry.
        
        Args:
            config: Global configuration dictionary
        """
        self.config = config
        self._services: Dict[str, BaseService] = {}
        self._metadata: Dict[str, ServiceMetadata] = {}
        self._enabled: Dict[str, bool] = {}
        logger.info("Service registry initialized")
    
    def register(
        self,
        service_class: Type[BaseService],
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a service class.
        
        Args:
            service_class: Service class (must inherit from BaseService)
            config: Optional service-specific configuration
        
        Returns:
            True if registration successful
        """
        metadata = service_class.get_metadata()
        name = metadata.name
        
        if name in self._services:
            logger.warning(f"Service '{name}' already registered")
            return False
        
        try:
            # Merge global config with service-specific config
            service_config = {
                **(self.config.get("services", {}).get(name, {})),
                **(config or {})
            }
            
            # Instantiate service
            service = service_class(service_config)
            service._metadata = metadata
            
            self._services[name] = service
            self._metadata[name] = metadata
            self._enabled[name] = False
            
            logger.info(f"Service '{name}' registered (v{metadata.version})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service '{name}': {e}")
            return False
    
    async def enable(self, service_name: str) -> bool:
        """
        Enable a service.
        
        Args:
            service_name: Name of the service to enable
        
        Returns:
            True if service enabled successfully
        """
        if service_name not in self._services:
            logger.error(f"Service '{service_name}' not registered")
            return False
        
        if self._enabled.get(service_name, False):
            logger.info(f"Service '{service_name}' already enabled")
            return True
        
        service = self._services[service_name]
        metadata = self._metadata[service_name]
        
        # Check dependencies
        for dep in metadata.dependencies:
            if not self._enabled.get(dep, False):
                logger.error(
                    f"Cannot enable '{service_name}': "
                    f"dependency '{dep}' not enabled"
                )
                return False
        
        try:
            metadata.status = ServiceStatus.LOADING
            success = await service.initialize()
            
            if success:
                self._enabled[service_name] = True
                metadata.status = ServiceStatus.ENABLED
                logger.info(f"Service '{service_name}' enabled")
                return True
            else:
                metadata.status = ServiceStatus.ERROR
                logger.error(f"Service '{service_name}' initialization failed")
                return False
                
        except Exception as e:
            metadata.status = ServiceStatus.ERROR
            logger.error(f"Error enabling service '{service_name}': {e}")
            return False
    
    async def disable(self, service_name: str) -> bool:
        """
        Disable a service.
        
        Args:
            service_name: Name of the service to disable
        
        Returns:
            True if service disabled successfully
        """
        if service_name not in self._services:
            logger.error(f"Service '{service_name}' not registered")
            return False
        
        if not self._enabled.get(service_name, False):
            logger.info(f"Service '{service_name}' already disabled")
            return True
        
        # Check if other enabled services depend on this one
        for name, meta in self._metadata.items():
            if service_name in meta.dependencies and self._enabled.get(name, False):
                logger.error(
                    f"Cannot disable '{service_name}': "
                    f"service '{name}' depends on it"
                )
                return False
        
        service = self._services[service_name]
        metadata = self._metadata[service_name]
        
        try:
            success = await service.shutdown()
            
            if success:
                self._enabled[service_name] = False
                metadata.status = ServiceStatus.DISABLED
                logger.info(f"Service '{service_name}' disabled")
                return True
            else:
                logger.error(f"Service '{service_name}' shutdown failed")
                return False
                
        except Exception as e:
            logger.error(f"Error disabling service '{service_name}': {e}")
            return False
    
    def get(self, service_name: str) -> Optional[BaseService]:
        """
        Get a service instance.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Service instance or None if not found/enabled
        """
        if service_name not in self._services:
            return None
        
        if not self._enabled.get(service_name, False):
            logger.warning(f"Service '{service_name}' is not enabled")
            return None
        
        return self._services[service_name]
    
    def is_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled."""
        return self._enabled.get(service_name, False)
    
    def list_services(self) -> List[Dict[str, Any]]:
        """
        List all registered services.
        
        Returns:
            List of service information dictionaries
        """
        return [
            {
                "name": meta.name,
                "version": meta.version,
                "description": meta.description,
                "enabled": self._enabled.get(meta.name, False),
                "status": meta.status.value,
                "optional": meta.optional,
                "dependencies": meta.dependencies
            }
            for meta in self._metadata.values()
        ]
    
    async def health_check_all(self) -> Dict[str, Any]:
        """
        Run health check on all enabled services.
        
        Returns:
            Dictionary with health status for all services
        """
        results = {}
        
        for name, enabled in self._enabled.items():
            if enabled:
                service = self._services[name]
                try:
                    results[name] = await service.health_check()
                except Exception as e:
                    results[name] = {
                        "healthy": False,
                        "message": f"Health check failed: {e}",
                        "details": {}
                    }
        
        return {
            "overall_healthy": all(r.get("healthy", False) for r in results.values()),
            "services": results
        }
    
    async def shutdown_all(self):
        """Shutdown all enabled services."""
        for name in list(self._enabled.keys()):
            if self._enabled[name]:
                await self.disable(name)
