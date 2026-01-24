"""
Configuration and constants for CityMaps poster generator.

Centralizes paper sizes, API keys, paths, and default settings.
"""

import os
from pathlib import Path

# ============================================================================
# ENVIRONMENT & PATHS
# ============================================================================

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Directory paths
THEMES_DIR = PROJECT_ROOT / "themes"
FONTS_DIR = PROJECT_ROOT / "fonts"
POSTERS_DIR = PROJECT_ROOT / "posters"
CACHE_DIR = PROJECT_ROOT / "cache"

# Ensure directories exist
for directory in [THEMES_DIR, FONTS_DIR, POSTERS_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# API CONFIGURATION
# ============================================================================

# Google Places API Key - load from environment
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# ============================================================================
# PAPER SIZES (in inches, ISO 216 standard)
# ============================================================================

PAPER_SIZES = {
    "A2": (16.54, 23.39),    # 594 × 841 mm
    "A3": (11.69, 16.54),    # 297 × 420 mm (actually A3 is 2x A4)
    "A4": (8.27, 11.69),     # 210 × 297 mm
    "A5": (5.83, 8.27),      # 148 × 210 mm
}

# Default paper size
DEFAULT_PAPER_SIZE = "A4"

# ============================================================================
# RENDERING CONFIGURATION
# ============================================================================

# Default DPI for preview
PREVIEW_DPI = 150

# Default DPI for final output (600 for highest quality prints)
OUTPUT_DPI = 600

# Default map radius in meters
DEFAULT_DISTANCE = 8000  # 8 km

# Figure background facecolor
DEFAULT_FACECOLOR = "white"

# ============================================================================
# TEXT POSITIONING (normalized 0-1 axes coordinates)
# ============================================================================

DEFAULT_TEXT_POSITION = {
    "x": 0.5,          # Center horizontally
    "y": 0.14,         # Standard position from bottom
    "alignment": "center",
    "show_coords": True,
    "show_country": True,
}

# ============================================================================
# THEME CONFIGURATION
# ============================================================================

# Default theme name
DEFAULT_THEME = "feature_based"

# Theme color keys that must exist in every theme
REQUIRED_THEME_KEYS = [
    "bg",
    "text",
    "gradient_color",
    "water",
    "parks",
    "road_motorway",
    "road_primary",
    "road_secondary",
    "road_tertiary",
    "road_residential",
    "road_default",
]

# ============================================================================
# FONT CONFIGURATION
# ============================================================================

FONT_FILES = {
    "bold": "Roboto-Bold.ttf",
    "regular": "Roboto-Regular.ttf",
    "light": "Roboto-Light.ttf",
}

# Font sizes for typography
FONT_SIZES = {
    "city_name": 60,
    "country": 22,
    "coordinates": 14,
    "attribution": 8,
}

# Dynamic font size scaling for long names
MIN_CITY_FONT_SIZE = 24
LONG_NAME_THRESHOLD = 10  # Characters before scaling kicks in

# ============================================================================
# FONT OPTIONS (User-selectable fonts)
# ============================================================================

FONT_OPTIONS = {
    "roboto": {
        "name": "Roboto",
        "files": {
            "bold": "Roboto-Bold.ttf",
            "regular": "Roboto-Regular.ttf",
            "light": "Roboto-Light.ttf",
        },
        "style": "Modern Sans",
        "google_font": "Roboto:wght@300;400;700",
    },
    "playfair": {
        "name": "Playfair Display",
        "files": {
            "bold": "PlayfairDisplay-Bold.ttf",
            "regular": "PlayfairDisplay-Regular.ttf",
            "light": "PlayfairDisplay-Regular.ttf",
        },
        "style": "Klassisch Seriös",
        "google_font": "Playfair+Display:wght@400;700",
    },
    "courier": {
        "name": "Courier Prime",
        "files": {
            "bold": "CourierPrime-Bold.ttf",
            "regular": "CourierPrime-Regular.ttf",
            "light": "CourierPrime-Regular.ttf",
        },
        "style": "Schreibmaschine",
        "google_font": "Courier+Prime:wght@400;700",
    },
    "dancing": {
        "name": "Dancing Script",
        "files": {
            "bold": "DancingScript-Bold.ttf",
            "regular": "DancingScript-Regular.ttf",
            "light": "DancingScript-Regular.ttf",
        },
        "style": "Handschrift",
        "google_font": "Dancing+Script:wght@400;700",
    },
    "raleway": {
        "name": "Raleway",
        "files": {
            "bold": "Raleway-Bold.ttf",
            "regular": "Raleway-Regular.ttf",
            "light": "Raleway-Light.ttf",
        },
        "style": "Dünn Minimal",
        "google_font": "Raleway:wght@300;400;700",
    },
}

DEFAULT_FONT = "roboto"

# ============================================================================
# FONT SCALING FACTORS (for paper size and zoom level)
# ============================================================================

# Paper size scaling (A4 = reference at 1.0)
PAPER_SCALE_FACTORS = {
    "A2": 1.4,
    "A3": 1.2,
    "A4": 1.0,
    "A5": 0.7,
}

# Zoom/distance scaling (15km+ = reference at 1.0)
# Maps distance in meters to scale factor
ZOOM_SCALE_FACTORS = [
    (500, 0.4),      # Nachbarschaft
    (1000, 0.5),     # Kleines Dorf
    (2000, 0.6),     # Dorf
    (4000, 0.75),    # Kleinstadt
    (8000, 0.9),     # Mittelstadt
    (15000, 1.0),    # Großstadt (reference)
]

# ============================================================================
# DETAIL LAYER CONFIGURATION
# ============================================================================

# Zoom thresholds for automatic layer defaults
LAYER_ZOOM_THRESHOLDS = {
    "all_on": 2000,      # <= 2km: all detail layers ON
    "buildings_only": 8000,  # <= 8km: only buildings ON
    # > 8km: all detail layers OFF
}

# OSM tags for detail layers
DETAIL_LAYER_TAGS = {
    "buildings": {"building": True},
    "paths": {"highway": ["track", "path", "footway", "cycleway", "bridleway"]},
    "landscape": {
        "landuse": ["farmland", "meadow", "orchard", "vineyard", "forest"],
        "natural": ["wood", "scrub", "heath", "grassland"],
    },
    "waterways": {"waterway": ["stream", "river", "canal", "ditch", "drain"]},
    "railways": {"railway": ["rail", "tram", "light_rail", "narrow_gauge"]},
    "hedges": {"barrier": ["hedge", "fence", "wall"]},
    "leisure": {"leisure": ["pitch", "playground", "garden", "sports_centre"]},
    "amenities": {"amenity": ["place_of_worship", "school", "cemetery"]},
}

# Z-order for rendering layers (higher = on top)
LAYER_ZORDER = {
    "landscape": 0,
    "water": 1,
    "waterways": 1.5,
    "parks": 2,
    "leisure": 2.5,
    "amenities": 2.8,
    "buildings": 3,
    "hedges": 3.5,
    "paths": 4,
    "railways": 4.5,
    "roads": 5,
    "gradients": 10,
    "text": 11,
}

# Line widths for detail layers
DETAIL_LAYER_LINEWIDTHS = {
    "paths": 0.3,
    "buildings_edge": 0.2,
    "waterways": 0.5,
    "railways": 0.6,
    "hedges": 0.2,
}

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Cache settings
CACHE_ENABLED = True
CACHE_EXPIRY_DAYS = 365  # Keep cache for 1 year

# ============================================================================
# GEOCODING CONFIGURATION
# ============================================================================

# Rate limiting for geocoding requests (seconds)
GEOCODING_RATE_LIMIT = 1

# Nominatim user agent (required by Nominatim ToS)
NOMINATIM_USER_AGENT = "citymaps-poster-generator/2.0"

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

# Supported output formats
SUPPORTED_FORMATS = ["png", "svg", "pdf"]

# Default output format
DEFAULT_OUTPUT_FORMAT = "png"

# Output filename pattern
OUTPUT_FILENAME_PATTERN = "{city_slug}_{theme_name}_{timestamp}.{format}"

# ============================================================================
# ROAD HIERARCHY (OSM highway tags)
# ============================================================================

ROAD_HIERARCHY = {
    "motorway": ("road_motorway", 1.2),
    "motorway_link": ("road_motorway", 1.2),
    "trunk": ("road_primary", 1.0),
    "primary": ("road_primary", 1.0),
    "secondary": ("road_secondary", 0.8),
    "tertiary": ("road_tertiary", 0.6),
    "residential": ("road_residential", 0.4),
    "living_street": ("road_residential", 0.4),
    "unclassified": ("road_default", 0.4),
}

# ============================================================================
# DEFAULT THEME (fallback if theme JSON not found)
# ============================================================================

DEFAULT_THEME_COLORS = {
    "name": "Default",
    "description": "Built-in default theme",
    "bg": "#FFFFFF",
    "text": "#000000",
    "gradient_color": "#000000",
    "water": "#A8DADC",
    "parks": "#90BE6D",
    "road_motorway": "#F77F00",
    "road_primary": "#F94144",
    "road_secondary": "#F8961E",
    "road_tertiary": "#F9C74F",
    "road_residential": "#90BE6D",
    "road_default": "#CCCCCC",
    # Detail layer colors
    "buildings": "#D0D0D0",
    "buildings_fill": "#E8E8E8",
    "paths": "#B0B0B0",
    "farmland": "#F5F5DC",
    "forest": "#C8E6C9",
    "meadow": "#E8F5E9",
    # New detail layer colors
    "waterways": "#7CB9E8",
    "railways": "#4A4A4A",
    "railways_dash": "#FFFFFF",
    "hedges": "#6B8E23",
    "leisure": "#C5E1A5",
    "amenities": "#E0E0E0",
    "amenities_edge": "#808080",
}
