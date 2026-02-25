"""
MapToPoster - FastAPI Application

Main API application with modular service architecture.
Supports both Python GUI (Streamlit) and JS Frontend (Vite/React-like).
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import sys
import uuid
import io
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import init_config, get_config
from backend.core.service_registry import ServiceRegistry
from backend.services.geocoding_service import GeocodingService
from backend.services.generator_service import PosterGeneratorService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize configuration
config_manager = init_config()
app_config = config_manager.get_app_config()

# Create FastAPI app
app = FastAPI(
    title=app_config.name,
    version=app_config.version,
    description="Modular map poster generation API",
    docs_url=f"{app_config.api_prefix}/docs",
    redoc_url=f"{app_config.api_prefix}/redoc"
)

# CORS middleware
cors_config = config_manager.get("cors", {})
if cors_config.get("enabled", True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get("origins", ["*"]),
        allow_credentials=True,
        allow_methods=cors_config.get("methods", ["*"]),
        allow_headers=["*"],
    )

# Global service registry
service_registry: Optional[ServiceRegistry] = None

# In-memory poster storage (use Redis in production)
POSTER_STORE: Dict[str, bytes] = {}


# === Dependency Injection ===

def get_service_registry() -> ServiceRegistry:
    """Get service registry instance."""
    if service_registry is None:
        raise HTTPException(status_code=500, detail="Service registry not initialized")
    return service_registry


# === Pydantic Models ===

class GeocodeRequest(BaseModel):
    """Geocoding request."""
    address: str = Field(..., description="Address to geocode")
    use_cache: bool = Field(True, description="Use cached results")


class GeocodeResponse(BaseModel):
    """Geocoding response."""
    latitude: float
    longitude: float
    formatted_address: str


class PosterRequest(BaseModel):
    """Poster generation request."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    city_name: str
    country_name: str = ""
    theme: Optional[str] = None
    custom_theme: Optional[Dict[str, Any]] = None
    distance: int = Field(8000, gt=0)
    paper_size: str = "A4"
    dpi: int = Field(300, ge=72, le=600)
    layers: Optional[Dict[str, bool]] = None
    text_position: Optional[Dict[str, Any]] = None


class PosterResponse(BaseModel):
    """Poster generation response."""
    status: str
    message: str
    poster_id: str
    download_url: Optional[str] = None


class ThemeResponse(BaseModel):
    """Theme information."""
    name: str
    description: str
    colors: Dict[str, str]


class GeocodeSearchResult(BaseModel):
    """Geocoding search result."""
    name: str
    latitude: float
    longitude: float
    display_name: str
    type: str


class ReverseGeocodeResult(BaseModel):
    """Reverse geocoding result."""
    latitude: float
    longitude: float
    display_name: str
    address: Dict[str, str]


class ServiceInfo(BaseModel):
    """Service information."""
    name: str
    version: str
    description: str
    enabled: bool
    status: str
    optional: bool
    dependencies: List[str]


class HealthResponse(BaseModel):
    """Health check response."""
    overall_healthy: bool
    services: Dict[str, Any]


# === Startup & Shutdown ===

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global service_registry
    
    logger.info("Starting MapToPoster API...")
    
    # Create service registry
    service_registry = ServiceRegistry(config_manager.to_dict())
    
    # Register core services
    service_registry.register(GeocodingService)
    service_registry.register(PosterGeneratorService)
    
    # Enable services based on configuration
    for service_name in ["geocoding", "generator"]:
        if config_manager.is_service_enabled(service_name):
            success = await service_registry.enable(service_name)
            if not success:
                logger.error(f"Failed to enable service: {service_name}")
    
    logger.info("MapToPoster API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown services."""
    logger.info("Shutting down MapToPoster API...")
    if service_registry:
        await service_registry.shutdown_all()
    logger.info("MapToPoster API shutdown complete")


# === Routes ===

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": app_config.name,
        "version": app_config.version,
        "status": "running",
        "docs": f"{app_config.api_prefix}/docs"
    }


@app.get(f"{app_config.api_prefix}/health", response_model=HealthResponse)
async def health_check(registry: ServiceRegistry = Depends(get_service_registry)):
    """Health check endpoint."""
    health_status = await registry.health_check_all()
    return health_status


@app.get(f"{app_config.api_prefix}/services", response_model=List[ServiceInfo])
async def list_services(registry: ServiceRegistry = Depends(get_service_registry)):
    """List all registered services."""
    return registry.list_services()


@app.post(f"{app_config.api_prefix}/geocode", response_model=GeocodeResponse)
async def geocode_address(
    request: GeocodeRequest,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Geocode an address to coordinates."""
    geocoding_service = registry.get("geocoding")
    
    if not geocoding_service:
        raise HTTPException(status_code=503, detail="Geocoding service not available")
    
    result = await geocoding_service.geocode(request.address, request.use_cache)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")
    
    lat, lon, formatted = result
    return GeocodeResponse(
        latitude=lat,
        longitude=lon,
        formatted_address=formatted
    )


@app.post(f"{app_config.api_prefix}/posters/generate", response_model=PosterResponse)
async def generate_poster(
    request: PosterRequest,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Generate a map poster."""
    generator_service = registry.get("generator")

    if not generator_service:
        raise HTTPException(status_code=503, detail="Generator service not available")

    try:
        fig = await generator_service.generate_poster(
            lat=request.latitude,
            lon=request.longitude,
            city_name=request.city_name,
            country_name=request.country_name,
            theme=request.theme,
            custom_theme=request.custom_theme,
            distance=request.distance,
            paper_size=request.paper_size,
            dpi=request.dpi,
        )

        # Save poster to memory store
        poster_id = str(uuid.uuid4())
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", pad_inches=0.05)
        buf.seek(0)
        POSTER_STORE[poster_id] = buf.getvalue()
        buf.close()

        return PosterResponse(
            status="success",
            message="Poster generated successfully",
            poster_id=poster_id,
            download_url=f"{app_config.api_prefix}/posters/{poster_id}/download"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating poster: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(f"{app_config.api_prefix}/posters/{{poster_id}}/download")
async def download_poster(
    poster_id: str,
    format: str = Query("png", regex="^(png|svg|pdf)$")
):
    """Download a generated poster."""
    if poster_id not in POSTER_STORE:
        raise HTTPException(status_code=404, detail="Poster not found")

    content_type = {
        "png": "image/png",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }

    return FileResponse(
        io.BytesIO(POSTER_STORE[poster_id]),
        media_type=content_type.get(format, "image/png"),
        filename=f"poster.{format}"
    )


@app.get(f"{app_config.api_prefix}/themes", response_model=List[ThemeResponse])
async def list_themes(registry: ServiceRegistry = Depends(get_service_registry)):
    """List all available themes."""
    generator_service = registry.get("generator")
    if not generator_service:
        return []

    try:
        # Import themes from modules
        from modules.poster_generator import PosterGenerator
        from modules.config import THEMES_DIR
        
        themes = []
        for theme_file in THEMES_DIR.glob("*.json"):
            try:
                import json
                with open(theme_file, "r") as f:
                    theme_data = json.load(f)
                    themes.append(ThemeResponse(
                        name=theme_data.get("name", theme_file.stem),
                        description=theme_data.get("description", ""),
                        colors={k: v for k, v in theme_data.items() if k not in ["name", "description", "custom"]}
                    ))
            except Exception:
                continue
        
        return themes
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        return []


@app.post(f"{app_config.api_prefix}/themes", response_model=ThemeResponse)
async def save_theme(
    theme: Dict[str, Any],
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Save a custom theme."""
    try:
        import json
        from modules.config import THEMES_DIR
        
        name = theme.get("name", "custom_theme")
        colors = theme.get("colors", {})
        
        theme_data = {
            "name": name,
            "description": "Custom theme",
            "custom": True,
            **colors
        }
        
        theme_path = THEMES_DIR / f"{name}.json"
        with open(theme_path, "w") as f:
            json.dump(theme_data, f, indent=2)
        
        return ThemeResponse(
            name=name,
            description="Custom theme",
            colors=colors
        )
    except Exception as e:
        logger.error(f"Error saving theme: {e}")
        raise HTTPException(status_code=500, detail="Failed to save theme")


@app.get(f"{app_config.api_prefix}/geocode/search", response_model=List[GeocodeSearchResult])
async def search_geocode(
    q: str = Query(..., description="Search query"),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Search for locations."""
    geocoding_service = registry.get("geocoding")
    if not geocoding_service:
        raise HTTPException(status_code=503, detail="Geocoding service not available")

    try:
        result = await geocoding_service.geocode(q, use_cache=True)
        if result is None:
            return []
        
        lat, lon, display_name = result
        return [GeocodeSearchResult(
            name=q,
            latitude=lat,
            longitude=lon,
            display_name=display_name,
            type="locality"
        )]
    except Exception as e:
        logger.error(f"Error searching geocode: {e}")
        return []


@app.get(f"{app_config.api_prefix}/geocode/reverse", response_model=ReverseGeocodeResult)
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Reverse geocode coordinates to address."""
    # For now, return basic info - can be enhanced with Nominatim reverse geocoding
    return ReverseGeocodeResult(
        latitude=lat,
        longitude=lon,
        display_name=f"{lat}, {lon}",
        address={}
    )


# === Service Management (Admin) ===

@app.post(f"{app_config.api_prefix}/services/{{service_name}}/enable")
async def enable_service(
    service_name: str,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Enable a service."""
    success = await registry.enable(service_name)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to enable service: {service_name}")
    
    return {"status": "success", "service": service_name, "enabled": True}


@app.post(f"{app_config.api_prefix}/services/{{service_name}}/disable")
async def disable_service(
    service_name: str,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Disable a service."""
    success = await registry.disable(service_name)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to disable service: {service_name}")
    
    return {"status": "success", "service": service_name, "enabled": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=app_config.host,
        port=app_config.port,
        reload=app_config.debug
    )
