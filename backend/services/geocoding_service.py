"""
MapToPoster - Geocoding Service

Converts addresses to coordinates using multiple providers
with fallback support and caching.
"""

from typing import Tuple, Optional, Dict, Any
from abc import ABC, abstractmethod
import logging

from geopy.geocoders import Nominatim, GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from backend.core.service_registry import BaseService, ServiceMetadata

logger = logging.getLogger(__name__)


class GeocodingProvider(ABC):
    """Base class for geocoding providers."""
    
    @abstractmethod
    async def geocode(self, address: str) -> Optional[Tuple[float, float, str]]:
        """
        Geocode an address.
        
        Args:
            address: Address string to geocode
        
        Returns:
            Tuple of (latitude, longitude, formatted_address) or None
        """
        pass


class NominatimProvider(GeocodingProvider):
    """OpenStreetMap Nominatim geocoding provider."""
    
    def __init__(self, user_agent: str = "MapToPoster/2.0"):
        self.geocoder = Nominatim(user_agent=user_agent)
    
    async def geocode(self, address: str) -> Optional[Tuple[float, float, str]]:
        """Geocode using Nominatim."""
        try:
            location = self.geocoder.geocode(address, timeout=10)
            if location:
                return (
                    location.latitude,
                    location.longitude,
                    location.address
                )
            return None
        
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Nominatim geocoding failed: {e}")
            return None


class GooglePlacesProvider(GeocodingProvider):
    """Google Places geocoding provider (fallback)."""
    
    def __init__(self, api_key: str):
        self.geocoder = GoogleV3(api_key=api_key)
    
    async def geocode(self, address: str) -> Optional[Tuple[float, float, str]]:
        """Geocode using Google Places."""
        try:
            location = self.geocoder.geocode(address, timeout=10)
            if location:
                return (
                    location.latitude,
                    location.longitude,
                    location.address
                )
            return None
        
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Google Places geocoding failed: {e}")
            return None


class GeocodingService(BaseService):
    """
    Geocoding service with multi-provider support and caching.
    
    Providers:
    - Nominatim (primary, free)
    - Google Places (fallback, requires API key)
    
    Features:
    - Automatic fallback between providers
    - In-memory caching (optional Redis cache via CacheService)
    - Configurable timeouts and retry logic
    """
    
    @classmethod
    def get_metadata(cls) -> ServiceMetadata:
        return ServiceMetadata(
            name="geocoding",
            version="1.0.0",
            description="Geocoding service with multi-provider support",
            dependencies=[],
            optional=False
        )
    
    async def initialize(self) -> bool:
        """Initialize geocoding providers."""
        try:
            # Primary provider
            self.primary_provider = NominatimProvider(
                user_agent=self.config.get(
                    "user_agent",
                    "MapToPoster/2.0"
                )
            )
            
            # Fallback provider (optional)
            self.fallback_provider = None
            google_api_key = self.config.get("google_api_key")
            if google_api_key:
                self.fallback_provider = GooglePlacesProvider(google_api_key)
                logger.info("Google Places fallback enabled")
            
            # Simple in-memory cache
            self._cache: Dict[str, Tuple[float, float, str]] = {}
            self.cache_ttl = self.config.get("cache_ttl", 86400)
            
            self._initialized = True
            logger.info("Geocoding service initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize geocoding service: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown geocoding service."""
        self._cache.clear()
        self._initialized = False
        logger.info("Geocoding service shutdown")
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            # Test geocoding with a known address
            result = await self.geocode("Berlin, Germany")
            
            return {
                "healthy": result is not None,
                "message": "Service operational",
                "details": {
                    "cache_size": len(self._cache),
                    "fallback_enabled": self.fallback_provider is not None
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {e}",
                "details": {}
            }
    
    async def geocode(
        self,
        address: str,
        use_cache: bool = True
    ) -> Optional[Tuple[float, float, str]]:
        """
        Geocode an address to coordinates.
        
        Args:
            address: Address string (e.g., "Berlin, Germany")
            use_cache: Whether to use cached results
        
        Returns:
            Tuple of (latitude, longitude, formatted_address) or None
        """
        if not self.is_initialized:
            raise RuntimeError("Geocoding service not initialized")
        
        # Check cache
        if use_cache and address in self._cache:
            logger.debug(f"Cache hit for address: {address}")
            return self._cache[address]
        
logger.info(f"Geocoding address: {address}")
        
        # Try primary provider
        result = await self.primary_provider.geocode(address)
        
        # Try fallback if primary failed
        if result is None and self.fallback_provider:
            logger.info("Trying fallback provider")
            result = await self.fallback_provider.geocode(address)
        
        # Cache result
        if result and use_cache:
            self._cache[address] = result
        
        return result
    
    def clear_cache(self):
        """Clear geocoding cache."""
        self._cache.clear()
        logger.info("Cache cleared")
