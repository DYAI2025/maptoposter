"""
MapToPoster - FastAPI Application

Main API application with modular service architecture.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import sys
from pathlib import Path

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


@app.post(f"{app_config.api_prefix}/posters/generate")
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
            dpi=request.dpi
        )
        
        # For now, return success
        # TODO: Implement export service to return actual image
        return {
            "status": "success",
            "message": "Poster generated successfully",
            "poster_id": "temp_id"  # TODO: Generate unique ID
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating poster: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
