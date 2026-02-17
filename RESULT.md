# MapToPoster - User Personalization Features

## Summary

Implemented user personalization features allowing users to customize text and basic color schemes on their map posters.

## Changes Made

### 1. Text Personalization (`modules/text_positioning.py`)

**New Features:**
- `custom_city_text`: Override the city name with custom text
- `custom_country_text`: Override the country name with custom text
- `custom_subtitle`: Add a custom subtitle below the city name
- `coords_format`: Choose coordinate format ("default", "decimal", "compact", "dms")
- `custom_coords_text`: Completely override coordinates with custom text
- `text_color`: Override the text color from theme

**Modified Functions:**
- `format_coordinates()`: Added `format_type` parameter with support for 4 formats:
  - `"default"`: 48.8566° N / 2.3522° E
  - `"decimal"`: 48.8566, 2.3522
  - `"compact"`: 48.9°N / 2.4°E
  - `"dms"`: 48°51'N / 2°21'E
- `apply_text_overlay()`: Extended to accept all personalization parameters

### 2. Poster Generator (`modules/poster_generator.py`)

**Modified Method:**
- `generate_poster()`: Added personalization parameters and passed them to `apply_text_overlay()`
- Updated all 4 render methods to pass personalization parameters:
  - Standard rendering
  - Night Lights mode (`_render_night_lights`)
  - Holonight mode (`_render_holonight`)
  - Kandincity mode (`_render_kandincity`)

### 3. Backend API (`backend/services/generator_service.py`)

**Enhanced Method:**
- `generate_poster()`: Added text and color customization parameters

**New Color Customization:**
- `bg_color`: Override background color
- `water_color`: Override water features color
- `parks_color`: Override parks/green spaces color
- `road_colors`: Dict to override road colors (keys: motorway, primary, secondary, tertiary, residential, default)

### 4. REST API (`backend/main.py`)

**Updated Models:**
- `PosterRequest`: Added all personalization fields with validation

**Updated Endpoints:**
- `POST /api/v1/posters/generate`: Now accepts personalization parameters

## API Usage Examples

### Text Personalization
```bash
curl -X POST http://localhost:8000/api/v1/posters/generate \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 48.8566,
    "longitude": 2.3522,
    "city_name": "Paris",
    "country_name": "France",
    "custom_city_text": "City of Light",
    "custom_subtitle": "Where Dreams Take Flight",
    "coords_format": "compact"
  }'
```

### Color Customization
```bash
curl -X POST http://localhost:8000/api/v1/posters/generate \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 48.8566,
    "longitude": 2.3522,
    "city_name": "Paris",
    "country_name": "France",
    "bg_color": "#1a1a2e",
    "water_color": "#4a90d9",
    "parks_color": "#2d5a27",
    "road_colors": {
      "motorway": "#ff6b6b",
      "primary": "#feca57",
      "secondary": "#48dbfb"
    }
  }'
```

## Files Modified

| File | Changes |
|------|---------|
| `modules/text_positioning.py` | Extended `format_coordinates()` and `apply_text_overlay()` |
| `modules/poster_generator.py` | Added personalization params to `generate_poster()` and all render methods |
| `backend/services/generator_service.py` | Added text and color customization to `generate_poster()` |
| `backend/main.py` | Updated `PosterRequest` model and API endpoint |

## Git Commit

- **Commit Hash**: `1870b29`
- **Branch**: `main`
- **Message**: Add user personalization features: text customization (custom city/country text, subtitle, coordinates format) and basic color customization (bg, water, parks, road colors)

## Note

Push to GitHub requires authentication. The commit is stored locally and ready to push when credentials are available:

```bash
git push origin main
```
