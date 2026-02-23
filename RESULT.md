# MapToPoster — User Personalization Features (Text/Color)

## Summary

Implemented user personalization features in the Streamlit GUI to allow customization of text (city name, coordinates) and basic color schemes on generated map posters.

## What Was Done

### 1. UI Extension for Text Customization (`gui_app.py`)

Added a new "Text-Anpassung" (Text Customization) section in the **Details** tab with the following features:

- **Custom City Text** - Override the city name displayed on the poster (e.g., "Mein Zuhause")
- **Custom Country Text** - Override the country name (e.g., "Brandenburg")
- **Custom Subtitle** - Add subtitle text below the city name (e.g., "Hier wohne ich")
- **Custom Coordinates Text** - Completely override coordinates with custom text
- **Coordinates Format Selector** - Choose format:
  - Standard (52°31'N 13°24'E)
  - Dezimal (52.52, 13.40)
  - Kompakt (52.52N 13.40E)
  - DMS (52°31'24"N 13°24'00"E)
- **Text Color Picker** - Choose custom text color for all text elements

### 2. Backend Integration

- Updated `generate_poster()` call to pass all personalization parameters
- Synced text_color with custom_theme_colors for theme consistency
- Backend already had full support for these parameters (verified in `backend/main.py` and `modules/poster_generator.py`)

### 3. Existing Color Customization

The color customization was already implemented in the **Theme Designer** tab:
- Background color
- Water features color
- Parks/forest color
- Road colors (motorway, primary, secondary, tertiary, residential)
- Building colors
- Path colors
- Gradient color

Users can create, save, and load custom themes with these colors.

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `gui_app.py` | Modified | Added Text Customization section in Details tab, updated generate_poster() call |

## Commit

- **Commit Hash:** 949ebd9
- **Branch:** main
- **Repository:** https://github.com/DYAI2025/maptoposter

## Note

- Git push failed due to authentication (expected in this environment)
- Changes are committed locally and ready for push when credentials are available
- Backend API already supports all personalization parameters defined in PosterRequest model

## Testing

- Syntax validation: ✓ Passed (`python3 -m py_compile gui_app.py`)
- Backend parameters: ✓ Already implemented in `backend/main.py` and `modules/poster_generator.py`
