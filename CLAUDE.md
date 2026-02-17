# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MapToPoster generates minimalist map posters from OpenStreetMap data using a layered rendering approach. Supports 30+ themes, 5 font families, multiple paper sizes, and detail layers (buildings, paths, landscape features). Provides both CLI and Streamlit GUI interfaces.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Web GUI
streamlit run gui_app.py

# CLI - Generate a poster
python create_map_poster.py -c "Berlin" -C "Germany" -t "noir" -d 12000

# List all available themes
python create_map_poster.py --list-themes
```

### Testing
```bash
# Basic Streamlit test
python -m streamlit run test_app.py
```

## Architecture

The system follows a linear pipeline: geocoding → OSM data fetching → multi-layer rendering → text overlay.

```
CLI/GUI → geocoding.py → poster_generator.py → text_positioning.py
              ↓                  ↓                      ↓
          cache/            themes/*.json         fonts/
                          (colors & styles)
```

### Core Modules (`modules/`)

- **config.py** - All constants: paper sizes, DPI, font scaling (PAPER_SCALE_FACTORS, ZOOM_SCALE_FACTORS), layer z-orders, road hierarchy, detail layer tags, geocoding rate limits
- **geocoding.py** - Address→lat/lon via Nominatim (with Google Places fallback). Caches results as pickle in `cache/` with 1-year expiry (CACHE_EXPIRY_DAYS)
- **poster_generator.py** - `PosterGenerator` class orchestrates the entire render pipeline: fetches road network via osmnx, adds layers in z-order (landscape→water→parks→buildings→paths→roads→gradients→text), applies theme colors
- **text_positioning.py** - Typography system: renders city/country/coordinates with font scaling based on paper size (PAPER_SCALE_FACTORS) and zoom level (ZOOM_SCALE_FACTORS). Supports 5 font families with dynamic size constraints

### Rendering Pipeline

**Z-Order Stack (lowest to highest):**
```
z=0   Landscape/background color
z=1   Water bodies
z=2   Parks & leisure areas
z=3   Buildings (when visible by zoom)
z=4   Paths & small roads (detail layer)
z=5   Road network (by hierarchy)
z=10  Gradient fade overlays (top/bottom)
z=11  Text labels (city, country, coordinates)
```

### Theme System Architecture

Each theme is a JSON file in `themes/` with color mappings for:
- Base: `bg`, `text`, `gradient_color`
- Water features: `water`, `waterways`
- Vegetation: `parks`, `leisure`, `farmland`, `forest`, `meadow`
- Road hierarchy: `road_motorway` (1.2px), `road_primary` (1.0px), `road_secondary` (0.8px), `road_tertiary` (0.6px), `road_residential` (0.4px), `road_default`
- Detail layers: `buildings`, `buildings_fill`, `paths`, `railways`, `hedges`, `amenities`

**Theme Validation:** `REQUIRED_THEME_KEYS` in config.py. Falls back to `DEFAULT_THEME_COLORS` if keys missing.

### Font System Architecture

Five font families in `fonts/`: Roboto (default), Playfair Display, Courier Prime, Dancing Script, Raleway. Each has regular/bold/light weights via TTF files.

**Dynamic Sizing:** Two-factor scaling system applies:
1. Paper size factor (PAPER_SCALE_FACTORS: A2=1.4, A3=1.2, A4=1.0, A5=0.7)
2. Zoom factor (ZOOM_SCALE_FACTORS: maps distance in meters to 0.4-1.0 scale)

Long names (>10 chars) trigger MIN_CITY_FONT_SIZE constraint (24pt minimum).

### Detail Layers

Controlled by `LAYER_ZOOM_THRESHOLDS`:
- Distance ≤ 2km: All layers enabled
- Distance ≤ 8km: Only buildings shown
- Distance > 8km: All detail layers off

Each layer defined in `DETAIL_LAYER_TAGS` with OSM query parameters. Rendered at layer-specific z-orders and line widths (DETAIL_LAYER_LINEWIDTHS).

## Key Configuration Constants

Located in `modules/config.py`:

```python
# Paper/Output
PAPER_SIZES = {"A2": (16.54, 23.39), "A3": (11.69, 16.54), "A4": (8.27, 11.69), "A5": (5.83, 8.27)}
PREVIEW_DPI = 150    # For GUI preview
OUTPUT_DPI = 600     # For final poster
DEFAULT_PAPER_SIZE = "A4"

# Geocoding
NOMINATIM_USER_AGENT = "citymaps-poster-generator/2.0"
GEOCODING_RATE_LIMIT = 1  # seconds between requests
CACHE_ENABLED = True
CACHE_EXPIRY_DAYS = 365

# Rendering
DEFAULT_DISTANCE = 8000  # meters (map radius)
LAYER_ZOOM_THRESHOLDS = {"all_on": 2000, "buildings_only": 8000}
DEFAULT_THEME = "feature_based"
DEFAULT_FONT = "roboto"
```

## Extending the System

### Adding a New Theme

1. Create `themes/my_theme.json` with all keys from `REQUIRED_THEME_KEYS` plus optional detail layer colors
2. Theme is auto-discovered; appears in `--list-themes` and GUI dropdowns
3. Example structure: see `themes/feature_based.json`

### Adding a New Map Layer

1. Define OSM tags in `DETAIL_LAYER_TAGS` (config.py) with `{'osm_key': 'osm_value(s)'}`
2. Add color keys to all theme JSON files (or DEFAULT_THEME_COLORS fallback)
3. Add z-order in `LAYER_ZORDER` and line width in `DETAIL_LAYER_LINEWIDTHS`
4. In `poster_generator.py`: fetch layer via `ox.features_from_point()`, then plot with appropriate styling
5. Conditionally render based on distance threshold in `LAYER_ZOOM_THRESHOLDS`

### Adding a New Font

1. Add TTF files to `fonts/` (bold, regular, light variants needed)
2. Register in `FONT_OPTIONS` dict (config.py) with Google Fonts reference and style name
3. Font is auto-discovered in GUI font selector

## Common Modification Points

- **Road styling:** `ROAD_HIERARCHY` in config.py (color + width per highway type)
- **Font sizing:** `FONT_SIZES` and scaling factors (PAPER_SCALE_FACTORS, ZOOM_SCALE_FACTORS)
- **Layer visibility:** `LAYER_ZOOM_THRESHOLDS` for distance-based toggling
- **Geocoding provider:** Switch Nominatim/Google Places logic in `geocoding.py`
- **Output quality:** Adjust `PREVIEW_DPI` and `OUTPUT_DPI`

## External Dependencies

Key libraries:
- **osmnx** (v2.0.7) - OpenStreetMap data fetching and graph manipulation
- **matplotlib** (v3.10) - Rendering engine; requires backend fix via `fix_matplotlib_backend.py` on macOS
- **streamlit** (v1.30) - GUI framework
- **geopandas** - Spatial data handling for OSM features
