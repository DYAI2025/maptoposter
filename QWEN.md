# CityMaps / MapToPoster - Project Context

## Project Overview

**CityMaps/MapToPoster** is a map poster generation system that creates beautiful, minimalist map posters for any city worldwide using OpenStreetMap data. The project offers multiple interfaces:

- **CLI** - Command-line interface for batch generation
- **Streamlit GUI** - Interactive web interface with theme gallery and custom theme designer
- **FastAPI Backend** - REST API for web widget integration and programmatic access

### Core Technologies

| Component | Technology |
|-----------|------------|
| Map Data | OpenStreetMap via OSMnx |
| Geocoding | Nominatim (primary), Google Places (optional fallback) |
| Rendering | Matplotlib, GeoPandas |
| CLI | argparse |
| GUI | Streamlit |
| API | FastAPI |
| Deployment | Docker, docker-compose |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
├─────────────────┬───────────────────────┬───────────────────────┤
│   CLI           │   Streamlit GUI       │   FastAPI + Widget    │
│   (argparse)    │   (web interface)     │   (REST API)          │
└────────┬────────┴───────────┬───────────┴───────────┬───────────┘
         │                    │                       │
         └────────────────────┼───────────────────────┘
                              │
         ┌────────────────────▼────────────────────┐
         │         Core Modules                    │
         │  - geocoding.py    (Nominatim/Google)   │
         │  - poster_generator.py (OSMnx rendering)│
         │  - text_positioning.py                  │
         │  - config.py                            │
         └────────────────────┬────────────────────┘
                              │
         ┌────────────────────▼────────────────────┐
         │         Backend Services                │
         │  - geocoding_service.py                 │
         │  - generator_service.py                 │
         │  - service_registry.py (plugin system)  │
         └─────────────────────────────────────────┘
```

## Project Structure

```
maptoposter/
├── create_map_poster.py          # CLI entry point
├── gui_app.py                     # Streamlit GUI (1156 lines)
├── fix_matplotlib_backend.py      # Matplotlib backend configuration
├── generate_theme_previews.py     # Theme preview generator
├── test_app.py                    # Test suite
│
├── backend/                       # FastAPI REST API
│   ├── main.py                    # API application
│   ├── core/
│   │   ├── config.py              # Configuration management
│   │   └── service_registry.py    # Plugin system
│   ├── services/
│   │   ├── geocoding_service.py   # Geocoding wrapper
│   │   └── generator_service.py   # Poster generator wrapper
│   └── requirements.txt
│
├── modules/                       # Core Python modules
│   ├── config.py                  # Constants, defaults, zoom thresholds
│   ├── geocoding.py               # Address geocoding with caching
│   ├── poster_generator.py        # Main rendering engine (1832 lines)
│   └── text_positioning.py        # Typography positioning
│
├── themes/                        # Theme JSON definitions (17 themes)
│   ├── noir.json                  # Black background, white roads
│   ├── feature_based.json         # Default theme
│   ├── midnight_blue.json         # Navy with gold
│   ├── blueprint.json             # Architectural style
│   ├── neon_cyberpunk.json        # Dark with pink/cyan
│   └── ...
│
├── fonts/                         # Roboto font files
├── posters/                       # Generated poster output
├── theme_previews/                # Theme preview images
├── custom_themes/                 # User-created themes
│
├── frontend/widget/               # Web embed widget
│   ├── src/widget.js              # Vanilla JS widget
│   └── demo.html                  # Demo page
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE_MODULAR.md    # Modular architecture details
│   └── SETUP_MODULAR.md           # Setup guide
│
├── config.yaml                    # Service configuration
├── .env.example                   # Environment template
├── docker-compose.yml             # Docker orchestration
├── Dockerfile                     # Backend container
└── requirements.txt               # Python dependencies
```

## Building and Running

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# For backend API
pip install -r backend/requirements.txt
```

### CLI Usage

```bash
# Basic usage
python create_map_poster.py --city "Berlin" --country "Germany"

# With theme and distance
python create_map_poster.py -c "Tokyo" -C "Japan" -t midnight_blue -d 15000

# List available themes
python create_map_poster.py --list-themes

# Show help
python create_map_poster.py --help
```

### Streamlit GUI

```bash
streamlit run gui_app.py
```

Features:
- Theme gallery with visual previews
- Custom theme designer with color pickers
- Zoom presets (200m - 30km radius)
- Detail layer controls (buildings, paths, railways, etc.)
- Font selection with preview
- Multiple export formats (PNG, SVG, PDF)

### FastAPI Backend

```bash
# Start the API server
python backend/main.py

# Or with uvicorn directly
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API Endpoints:
- `GET /` - Root endpoint with API info
- `GET /api/v1/health` - Health check
- `GET /api/v1/services` - List services
- `POST /api/v1/geocode` - Geocode address
- `POST /api/v1/posters/generate` - Generate poster
- `POST /api/v1/services/{name}/enable` - Enable service
- `POST /api/v1/services/{name}/disable` - Disable service

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# Access points
# API: http://localhost:8000
# API Docs: http://localhost:8000/api/v1/docs
# Widget Demo: http://localhost:8080
```

## Key Components

### PosterGenerator (modules/poster_generator.py)

Main rendering engine with 1832 lines. Key features:

**Rendering Layers (z-order):**
```
z=15  Radial vignette (holonight mode)
z=12  Horizon glow
z=11  Text labels
z=10  Gradient fades
z=9   Intersection glows
z=8   Window lights
z=5-7 Road glow effects
z=3   Roads (via ox.plot_graph)
z=2   Parks, buildings, landscape
z=1   Water
z=0   Background
```

**Special Modes:**
- **Night Lights** - Realistic glow effects with color temperature variation
- **Holonight** - Intense neon glow with white-hot center, intersection glows
- **Kandinsky** - Building blocks as colored geometric shapes

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `generate_poster()` | Main rendering pipeline |
| `get_edge_colors_by_type()` | Road color by OSM highway tag |
| `get_edge_widths_by_type()` | Road width by importance |
| `create_gradient_fade()` | Top/bottom fade effect |
| `fetch_graph()` | OSMnx graph fetching with caching |
| `fetch_features()` | Water, parks, buildings fetching |

### Geocoding (modules/geocoding.py)

Multi-provider geocoding with caching:

```python
# Primary: Nominatim (OpenStreetMap)
# Optional: Google Places API (requires GOOGLE_PLACES_API_KEY)
# Cache: Local pickle files in cache/ directory
```

### Service Registry (backend/core/service_registry.py)

Plugin-based service architecture:

```python
# Services can be enabled/disabled dynamically
# Core services: geocoding, generator
# Optional services: cache, storage, payment, print, analytics
```

### Themes

17 pre-built themes in `themes/` directory:

| Theme | Style |
|-------|-------|
| `feature_based` | Classic black & white with road hierarchy |
| `noir` | Pure black background, white roads |
| `midnight_blue` | Navy background with gold roads |
| `blueprint` | Architectural blueprint aesthetic |
| `neon_cyberpunk` | Dark with electric pink/cyan |
| `warm_beige` | Vintage sepia tones |
| `pastel_dream` | Soft muted pastels |
| `japanese_ink` | Minimalist ink wash style |
| `forest` | Deep greens and sage |
| `ocean` | Blues and teals for coastal cities |
| `terracotta` | Mediterranean warmth |
| `sunset` | Warm oranges and pinks |
| `autumn` | Seasonal burnt oranges and reds |
| `copper_patina` | Oxidized copper aesthetic |
| `monochrome_blue` | Single blue color family |
| `gradient_roads` | Smooth gradient shading |
| `contrast_zones` | High contrast urban density |

**Custom Theme Format:**
```json
{
  "name": "My Theme",
  "description": "Description",
  "bg": "#FFFFFF",
  "text": "#000000",
  "gradient_color": "#FFFFFF",
  "water": "#C0C0C0",
  "parks": "#F0F0F0",
  "road_motorway": "#0A0A0A",
  "road_primary": "#1A1A1A",
  "road_secondary": "#2A2A2A",
  "road_tertiary": "#3A3A3A",
  "road_residential": "#4A4A4A",
  "road_default": "#3A3A3A"
}
```

## Configuration

### config.yaml

Service configuration with plugin system:

```yaml
services:
  geocoding:
    enabled: true
    provider: "nominatim"
  
  generator:
    enabled: true
    default_theme: "feature_based"
    max_distance: 50000
  
  cache:
    enabled: false
    provider: "redis"
  
  storage:
    enabled: false
    provider: "s3"
```

### Environment Variables (.env)

```bash
GOOGLE_PLACES_API_KEY=     # Optional geocoding fallback
CACHE_DIR=cache            # Cache directory
POSTERS_DIR=posters        # Output directory
```

## Development Conventions

### Code Style

- **Type hints** - Used throughout modules
- **Docstrings** - Google-style docstrings for all public functions
- **Error handling** - Try/except with graceful fallbacks
- **Logging** - Structured logging in backend services

### Testing Practices

- Test file: `test_app.py`
- Manual testing via demo pages
- API testing via Swagger UI (`/api/v1/docs`)

### Adding New Features

**New theme:**
1. Create JSON file in `themes/`
2. Run `generate_theme_previews.py` for gallery image

**New detail layer:**
1. Add to `DETAIL_LAYER_TAGS` in `modules/config.py`
2. Add fetch method in `PosterGenerator`
3. Add rendering logic with z-order

**New backend service:**
1. Create class inheriting from `BaseService`
2. Implement `get_metadata()`, `initialize()`, `shutdown()`, `health_check()`
3. Register in `backend/main.py`
4. Configure in `config.yaml`

## Performance Tips

| Tip | Impact |
|-----|--------|
| Use `network_type='drive'` instead of `'all'` | Faster graph downloads |
| Cache directory for OSM data | Avoid repeated API calls |
| Reduce DPI from 300 to 150 for previews | 4x faster rendering |
| Distance >20km = slow + memory heavy | Use 8-15km for quick tests |
| Redis cache for production | Geocoding/poster caching |

## Common Commands

```bash
# Quick test poster
python create_map_poster.py -c "Berlin" -C "Germany" -t noir -d 8000

# Generate theme previews
python generate_theme_previews.py

# Run tests
python test_app.py

# Check matplotlib backend
python fix_matplotlib_backend.py

# Start API with hot reload
uvicorn backend.main:app --reload

# Docker rebuild
docker-compose up -d --build
```

## Output Format

Posters saved to `posters/` with naming convention:
```
{city}_{theme}_{YYYYMMDD_HHMMSS}.{png|svg|pdf}
```

Example: `berlin_noir_20260217_143022.png`

## Distance Guide

| Distance | Best For |
|----------|----------|
| 200-500m | Single property, neighborhood |
| 1000-2000m | Village, district |
| 4000-6000m | Small city center, dense areas |
| 8000-12000m | Medium cities (Paris, Barcelona) |
| 15000-20000m | Large metros (Tokyo, Mumbai) |
| 30000m+ | Full metropolitan region |

## Related Documentation

- `README.md` - User-facing documentation with examples
- `IMPLEMENTATION_STATUS.md` - Modular web integration status (German)
- `docs/ARCHITECTURE_MODULAR.md` - Detailed architecture
- `docs/SETUP_MODULAR.md` - Setup guide for modular deployment
