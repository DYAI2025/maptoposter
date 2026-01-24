# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MapToPoster generates minimalist map posters from OpenStreetMap data. It provides both a CLI (`create_map_poster.py`) and a Streamlit web GUI (`gui_app.py`).

## Commands

### Run the Web GUI
```bash
streamlit run gui_app.py
```

### Generate a Poster via CLI
```bash
python create_map_poster.py -c "Berlin" -C "Germany" -t "noir" -d 12000
python create_map_poster.py --list-themes
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

```
CLI/GUI → geocoding.py → poster_generator.py → text_positioning.py
               ↓                  ↓
          cache/              themes/*.json
```

### Core Modules (`modules/`)

- **config.py** - Constants: paper sizes, font scaling factors, road hierarchy widths, layer zoom thresholds, DPI settings
- **geocoding.py** - Address→coordinates via Nominatim (with Google Places fallback). Uses pickle cache in `cache/`
- **poster_generator.py** - `PosterGenerator` class: fetches OSM data via osmnx, renders layers (water→parks→landscape→buildings→paths→roads→gradients→text)
- **text_positioning.py** - Typography rendering with dynamic font scaling based on paper size × zoom level

### Rendering Z-Order
```
z=11 Text (city, country, coords)
z=10 Gradient fades
z=5  Roads
z=4  Paths (detail layer)
z=3  Buildings (detail layer)
z=2  Parks
z=1  Water
z=0  Landscape/Background
```

### Theme System

30+ themes in `themes/*.json`. Required color keys:
- `bg`, `text`, `gradient_color`, `water`, `parks`
- `road_motorway`, `road_primary`, `road_secondary`, `road_tertiary`, `road_residential`, `road_default`
- Detail layers: `buildings`, `buildings_fill`, `paths`, `farmland`, `forest`

### Font System

5 font families in `fonts/` (Roboto, Playfair, Courier, Dancing, Raleway), each with bold/regular/light weights. Font scaling uses two factors from `config.py`: `PAPER_SCALE_FACTORS` and `ZOOM_SCALE_FACTORS`.

## Key Constants (config.py)

```python
DEFAULT_THEME = "feature_based"
DEFAULT_PAPER_SIZE = "A4"
DEFAULT_DISTANCE = 8000  # meters
PREVIEW_DPI = 150
OUTPUT_DPI = 300
LAYER_ZOOM_THRESHOLDS = {"all_on": 2000, "buildings_only": 8000}
```

## Adding Features

**New map layer:** Fetch via `ox.features_from_point()` in `poster_generator.py`, add to theme JSON with new color key, plot at appropriate z-order.

**New theme:** Create JSON in `themes/` with all required color keys (see existing themes for structure).

**New font:** Add TTF files to `fonts/`, register in `FONTS` dict in `config.py`.
