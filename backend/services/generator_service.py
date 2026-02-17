"""
MapToPoster - Poster Generator Service

Generates map posters using OSMnx and existing modules.
"""

from typing import Dict, Any, Optional
import logging
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

from backend.core.service_registry import BaseService, ServiceMetadata
from modules.poster_generator import PosterGenerator as LegacyPosterGenerator

logger = logging.getLogger(__name__)


class PosterGeneratorService(BaseService):
    """
    Poster generation service.
    
    Wraps the existing PosterGenerator from modules/ to integrate
    with the new service architecture.
    """
    
    @classmethod
    def get_metadata(cls) -> ServiceMetadata:
        return ServiceMetadata(
            name="generator",
            version="1.0.0",
            description="Map poster generation service using OSMnx",
            dependencies=["geocoding"],
            optional=False
        )
    
    async def initialize(self) -> bool:
        """Initialize poster generator."""
        try:
            self.default_theme = self.config.get("default_theme", "feature_based")
            self.max_distance = self.config.get("max_distance", 50000)
            self.default_dpi = self.config.get("default_dpi", 300)
            
            # Test initialization
            test_gen = LegacyPosterGenerator(theme_name=self.default_theme)
            
            self._initialized = True
            logger.info("Poster generator service initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize poster generator: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown poster generator."""
        # Cleanup matplotlib figures
        plt.close('all')
        
        self._initialized = False
        logger.info("Poster generator service shutdown")
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            # Test that we can create a generator instance
            gen = LegacyPosterGenerator(theme_name=self.default_theme)
            
            return {
                "healthy": True,
                "message": "Service operational",
                "details": {
                    "default_theme": self.default_theme,
                    "max_distance": self.max_distance
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {e}",
                "details": {}
            }
    
    async def generate_poster(
        self,
        lat: float,
        lon: float,
        city_name: str,
        country_name: str = "",
        theme: Optional[str] = None,
        custom_theme: Optional[Dict[str, Any]] = None,
        distance: int = 8000,
        paper_size: str = "A4",
        dpi: int = 300,
        # User personalization parameters
        custom_city_text: Optional[str] = None,
        custom_country_text: Optional[str] = None,
        custom_subtitle: Optional[str] = None,
        coords_format: str = "default",
        custom_coords_text: Optional[str] = None,
        text_color: Optional[str] = None,
        # Color customization (overrides specific theme colors)
        bg_color: Optional[str] = None,
        water_color: Optional[str] = None,
        parks_color: Optional[str] = None,
        road_colors: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Generate a map poster.

        Args:
            lat: Latitude
            lon: Longitude
            city_name: City name for poster text
            country_name: Country name for poster text
            theme: Theme name (from themes/)
            custom_theme: Custom theme colors dict
            distance: Map radius in meters
            paper_size: Paper size (A4, A3, A2, etc.)
            dpi: Output DPI
            custom_city_text: Override city name with custom text
            custom_country_text: Override country name with custom text
            custom_subtitle: Add custom subtitle below city name
            coords_format: Format for coordinates ("default", "decimal", "compact", "dms")
            custom_coords_text: Completely override coordinates with custom text
            text_color: Override text color from theme
            bg_color: Override background color
            water_color: Override water features color
            parks_color: Override parks/green spaces color
            road_colors: Dict to override road colors (keys: motorway, primary, secondary, tertiary, residential, default)
            **kwargs: Additional arguments for PosterGenerator

        Returns:
            Matplotlib figure object
        """
        if not self.is_initialized:
            raise RuntimeError("Poster generator service not initialized")

        # Validate distance
        if distance > self.max_distance:
            raise ValueError(
                f"Distance {distance}m exceeds maximum {self.max_distance}m"
            )

        # Use theme or custom theme
        theme_name = theme or self.default_theme

        # Merge custom color overrides with custom_theme
        final_custom_theme = dict(custom_theme) if custom_theme else {}
        if bg_color:
            final_custom_theme['bg'] = bg_color
        if water_color:
            final_custom_theme['water'] = water_color
        if parks_color:
            final_custom_theme['parks'] = parks_color
        if road_colors:
            for key, value in road_colors.items():
                final_custom_theme[f'road_{key}'] = value

        try:
            logger.info(
                f"Generating poster: {city_name}, {country_name} "
                f"({lat:.4f}, {lon:.4f}) - "
                f"theme={theme_name}, distance={distance}m"
            )

            # Create generator
            generator = LegacyPosterGenerator(
                theme_name=theme_name if not final_custom_theme else None,
                custom_theme=final_custom_theme if final_custom_theme else None
            )

            # Generate poster with personalization
            fig = generator.generate_poster(
                lat=lat,
                lon=lon,
                city_name=city_name,
                country_name=country_name,
                paper_size=paper_size,
                distance=distance,
                dpi=dpi,
                custom_city_text=custom_city_text,
                custom_country_text=custom_country_text,
                custom_subtitle=custom_subtitle,
                coords_format=coords_format,
                custom_coords_text=custom_coords_text,
                text_color=text_color,
                **kwargs
            )

            logger.info("Poster generated successfully")
            return fig

        except Exception as e:
            logger.error(f"Error generating poster: {e}")
            raise
