# Theme-Preview & Font-Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add visual theme color-bar previews and 5 font options to the CityMaps GUI.

**Architecture:** Extend GUI with auto-generated color strips from theme JSON values, add font selector with live ABC preview using Google Fonts CSS, pass selected font through poster generator to text renderer.

**Tech Stack:** Streamlit, Google Fonts CDN, Matplotlib FontProperties, TTF files

---

## Task 1: Add Font Configuration

**Files:**
- Modify: `modules/config.py`

**Step 1: Add FONT_OPTIONS dict to config.py**

Add after `FONT_FILES` section (~line 106):

```python
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
```

**Step 2: Verify config loads without errors**

Run: `cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter && source venv/bin/activate && python -c "from modules.config import FONT_OPTIONS, DEFAULT_FONT; print(f'Loaded {len(FONT_OPTIONS)} fonts, default: {DEFAULT_FONT}')"`

Expected: `Loaded 5 fonts, default: roboto`

**Step 3: Commit**

```bash
git add modules/config.py
git commit -m "feat: add FONT_OPTIONS configuration for 5 font families"
```

---

## Task 2: Download Font Files

**Files:**
- Create: `fonts/PlayfairDisplay-Regular.ttf`
- Create: `fonts/PlayfairDisplay-Bold.ttf`
- Create: `fonts/CourierPrime-Regular.ttf`
- Create: `fonts/CourierPrime-Bold.ttf`
- Create: `fonts/DancingScript-Regular.ttf`
- Create: `fonts/DancingScript-Bold.ttf`
- Create: `fonts/Raleway-Regular.ttf`
- Create: `fonts/Raleway-Light.ttf`
- Create: `fonts/Raleway-Bold.ttf`

**Step 1: Download fonts from Google Fonts**

```bash
cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter/fonts

# Playfair Display
curl -L "https://github.com/googlefonts/Playfair/raw/main/fonts/ttf/PlayfairDisplay-Regular.ttf" -o PlayfairDisplay-Regular.ttf
curl -L "https://github.com/googlefonts/Playfair/raw/main/fonts/ttf/PlayfairDisplay-Bold.ttf" -o PlayfairDisplay-Bold.ttf

# Courier Prime
curl -L "https://github.com/quoteunquoteapps/CourierPrime/raw/master/fonts/ttf/CourierPrime-Regular.ttf" -o CourierPrime-Regular.ttf
curl -L "https://github.com/quoteunquoteapps/CourierPrime/raw/master/fonts/ttf/CourierPrime-Bold.ttf" -o CourierPrime-Bold.ttf

# Dancing Script
curl -L "https://github.com/impallari/DancingScript/raw/master/fonts/ttf/DancingScript-Regular.ttf" -o DancingScript-Regular.ttf
curl -L "https://github.com/impallari/DancingScript/raw/master/fonts/ttf/DancingScript-Bold.ttf" -o DancingScript-Bold.ttf

# Raleway
curl -L "https://github.com/impallari/Raleway/raw/master/fonts/ttf/Raleway-Regular.ttf" -o Raleway-Regular.ttf
curl -L "https://github.com/impallari/Raleway/raw/master/fonts/ttf/Raleway-Light.ttf" -o Raleway-Light.ttf
curl -L "https://github.com/impallari/Raleway/raw/master/fonts/ttf/Raleway-Bold.ttf" -o Raleway-Bold.ttf
```

**Step 2: Verify fonts exist**

```bash
ls -la /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter/fonts/*.ttf | wc -l
```

Expected: `12` (3 Roboto + 9 new)

**Step 3: Commit**

```bash
git add fonts/*.ttf
git commit -m "feat: add Playfair, Courier Prime, Dancing Script, Raleway fonts"
```

---

## Task 3: Update text_positioning.py for Font Selection

**Files:**
- Modify: `modules/text_positioning.py`

**Step 1: Update load_fonts function to accept font_id**

Replace the existing `load_fonts` function (lines 102-127):

```python
def load_fonts(fonts_dir_path: str, font_id: str = "roboto") -> dict | None:
    """
    Load font files for selected font family.

    Args:
        fonts_dir_path: Path to fonts directory
        font_id: Font family ID from FONT_OPTIONS

    Returns:
        Dict with 'bold', 'regular', 'light' font paths, or None if missing
    """
    from .config import FONT_OPTIONS, DEFAULT_FONT

    if font_id not in FONT_OPTIONS:
        print(f"⚠ Unknown font '{font_id}', using default")
        font_id = DEFAULT_FONT

    font_config = FONT_OPTIONS[font_id]
    font_files = font_config["files"]

    fonts = {
        "bold": str(fonts_dir_path / font_files["bold"]),
        "regular": str(fonts_dir_path / font_files["regular"]),
        "light": str(fonts_dir_path / font_files["light"]),
    }

    # Verify all fonts exist
    for weight, path in fonts.items():
        try:
            with open(path):
                pass
        except FileNotFoundError:
            print(f"⚠ Font not found: {path}")
            return None

    return fonts
```

**Step 2: Verify module loads**

```bash
cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter && source venv/bin/activate && python -c "from modules.text_positioning import load_fonts; from modules.config import FONTS_DIR; print(load_fonts(FONTS_DIR, 'roboto'))"
```

Expected: Dict with 3 font paths

**Step 3: Commit**

```bash
git add modules/text_positioning.py
git commit -m "feat: update load_fonts to support font_id selection"
```

---

## Task 4: Update PosterGenerator for Font Selection

**Files:**
- Modify: `modules/poster_generator.py`

**Step 1: Update __init__ to accept font_id**

Modify `__init__` method (around line 50-59):

```python
def __init__(self, theme_name: str = DEFAULT_THEME, font_id: str = "roboto"):
    """
    Initialize poster generator with a specific theme and font.

    Args:
        theme_name: Name of theme JSON file (without .json extension)
        font_id: Font family ID from FONT_OPTIONS
    """
    self.theme_name = theme_name
    self.theme = self.load_theme(theme_name)
    self.font_id = font_id
    self.fonts = load_fonts(FONTS_DIR, font_id)
```

**Step 2: Update generate_poster to pass font_id**

Modify the `apply_text_overlay` call (around line 620) - the call already uses `self.fonts`, no change needed there. But update the import at top of file to include DEFAULT_FONT:

```python
from .config import (
    THEMES_DIR,
    FONTS_DIR,
    POSTERS_DIR,
    PAPER_SIZES,
    DEFAULT_THEME,
    DEFAULT_FACECOLOR,
    OUTPUT_DPI,
    PREVIEW_DPI,
    DEFAULT_THEME_COLORS,
    ROAD_HIERARCHY,
    DETAIL_LAYER_TAGS,
    LAYER_ZORDER,
    DETAIL_LAYER_LINEWIDTHS,
    LAYER_ZOOM_THRESHOLDS,
    DEFAULT_FONT,
)
```

And update the `__init__` signature default:

```python
def __init__(self, theme_name: str = DEFAULT_THEME, font_id: str = DEFAULT_FONT):
```

**Step 3: Test font selection**

```bash
cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter && source venv/bin/activate && python -c "
from modules.poster_generator import PosterGenerator
gen = PosterGenerator(theme_name='noir', font_id='playfair')
print(f'Font ID: {gen.font_id}')
print(f'Fonts loaded: {gen.fonts is not None}')
"
```

Expected:
```
Font ID: playfair
Fonts loaded: True
```

**Step 4: Commit**

```bash
git add modules/poster_generator.py
git commit -m "feat: add font_id parameter to PosterGenerator"
```

---

## Task 5: Add Theme Color Bar to GUI

**Files:**
- Modify: `gui_app.py`

**Step 1: Add show_theme_color_bar function**

Add after `show_theme_preview` function (around line 260):

```python
def show_theme_color_bar(theme_dict: dict) -> None:
    """Display 6 color swatches as a horizontal bar for theme preview."""
    colors = [
        ("BG", theme_dict.get("bg", "#fff")),
        ("Water", theme_dict.get("water", "#adf")),
        ("Parks", theme_dict.get("parks", "#9c6")),
        ("Main", theme_dict.get("road_motorway", "#f70")),
        ("Side", theme_dict.get("road_residential", "#888")),
        ("Text", theme_dict.get("text", "#000")),
    ]

    html = '''
    <div style="display: flex; gap: 4px; margin: 0.75rem 0; align-items: center;">
    '''
    for label, color in colors:
        html += f'''
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
        ">
            <div style="
                width: 36px;
                height: 36px;
                background-color: {color};
                border: 1px solid rgba(0,0,0,0.2);
                border-radius: 4px;
            " title="{label}: {color}"></div>
            <span style="font-size: 0.65rem; color: #666; margin-top: 2px;">{label}</span>
        </div>
        '''
    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)
```

**Step 2: Replace show_theme_preview call with show_theme_color_bar**

Find (around line 387):
```python
    st.caption("Theme-Farben:")
    show_theme_preview(theme_dict)
```

Replace with:
```python
    show_theme_color_bar(theme_dict)
    if theme_dict.get("description"):
        st.caption(f"_{theme_dict.get('description')}_")
```

**Step 3: Verify GUI loads**

```bash
cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter && source venv/bin/activate && python -c "import gui_app; print('GUI module loads OK')"
```

Expected: `GUI module loads OK`

**Step 4: Commit**

```bash
git add gui_app.py
git commit -m "feat: add theme color bar preview in GUI"
```

---

## Task 6: Add Font Selector to GUI

**Files:**
- Modify: `gui_app.py`

**Step 1: Add import for FONT_OPTIONS**

Update imports (around line 25-31):

```python
from modules.config import (
    PAPER_SIZES,
    DEFAULT_PAPER_SIZE,
    DEFAULT_DISTANCE,
    FONTS_DIR,
    POSTERS_DIR,
    LAYER_ZOOM_THRESHOLDS,
    FONT_OPTIONS,
    DEFAULT_FONT,
)
```

**Step 2: Add Google Fonts CSS loader**

Add after the existing CSS block (after line 190, before ZOOM_PRESETS):

```python
# Load Google Fonts for preview
GOOGLE_FONTS_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Courier+Prime&family=Dancing+Script&family=Playfair+Display&family=Raleway:wght@300&family=Roboto&display=swap" rel="stylesheet">
"""
```

**Step 3: Add font_selector function**

Add after `show_theme_color_bar` function:

```python
def font_selector() -> str:
    """Font selection with ABC preview in each font."""

    # Inject Google Fonts CSS
    st.markdown(GOOGLE_FONTS_CSS, unsafe_allow_html=True)

    st.markdown("**Schriftart:**")

    # Build font preview HTML
    font_html = '<div style="display: flex; flex-direction: column; gap: 8px; margin: 0.5rem 0;">'

    font_css_families = {
        "roboto": "Roboto, sans-serif",
        "playfair": "'Playfair Display', serif",
        "courier": "'Courier Prime', monospace",
        "dancing": "'Dancing Script', cursive",
        "raleway": "Raleway, sans-serif; font-weight: 300",
    }

    for font_id, config in FONT_OPTIONS.items():
        css_family = font_css_families.get(font_id, "sans-serif")
        font_html += f'''
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="
                font-family: {css_family};
                font-size: 1.2rem;
                min-width: 50px;
            ">ABC</span>
            <span style="color: #666; font-size: 0.85rem;">{config["name"]} ({config["style"]})</span>
        </div>
        '''

    font_html += '</div>'
    st.markdown(font_html, unsafe_allow_html=True)

    # Actual selector
    selected_font = st.selectbox(
        "Schriftart auswählen",
        options=list(FONT_OPTIONS.keys()),
        index=list(FONT_OPTIONS.keys()).index(DEFAULT_FONT),
        format_func=lambda x: f"{FONT_OPTIONS[x]['name']} - {FONT_OPTIONS[x]['style']}",
        label_visibility="collapsed",
    )

    return selected_font
```

**Step 4: Add font selector to GUI layout**

Find the theme selection section (around line 378-388) and add font selector after theme color bar:

```python
    # Theme Selection
    generator = PosterGenerator()
    available_themes = generator.get_available_themes()

    theme_name = st.selectbox(
        "Farbthema",
        options=available_themes if available_themes else ["feature_based"],
        help="Wähle das visuelle Theme für die Kartenfarben",
    )

    # Show theme color preview
    theme_dict = get_theme_dict(theme_name)
    show_theme_color_bar(theme_dict)
    if theme_dict.get("description"):
        st.caption(f"_{theme_dict.get('description')}_")

    # Font Selection (NEW)
    st.markdown("")  # Spacer
    selected_font = font_selector()

    st.divider()
```

**Step 5: Pass font to PosterGenerator**

Update the generate poster section (around line 630):

```python
                generator = PosterGenerator(theme_name=theme_name, font_id=selected_font)
```

**Step 6: Commit**

```bash
git add gui_app.py
git commit -m "feat: add font selector with ABC preview to GUI"
```

---

## Task 7: Integration Test

**Step 1: Run full end-to-end test**

```bash
cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter && source venv/bin/activate && python -c "
from modules.poster_generator import PosterGenerator
from modules.config import POSTERS_DIR

# Test each font
fonts_to_test = ['roboto', 'playfair', 'dancing']

for font_id in fonts_to_test:
    print(f'Testing font: {font_id}')
    gen = PosterGenerator(theme_name='noir', font_id=font_id)

    fig = gen.generate_poster(
        lat=52.52,
        lon=13.40,
        city_name='Berlin',
        country_name='Deutschland',
        paper_size='A4',
        distance=8000,
    )

    output_path = POSTERS_DIR / f'test_font_{font_id}.png'
    gen.save_poster(fig, output_path, dpi=100)
    print(f'  Saved: {output_path}')

print('All font tests passed!')
"
```

Expected: 3 test images generated without errors

**Step 2: Launch GUI and verify visually**

```bash
cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/CityMaps/maptoposter && source venv/bin/activate && streamlit run gui_app.py
```

Verify:
- [ ] Theme dropdown shows color bar below
- [ ] Font selector shows ABC in 5 different fonts
- [ ] Generating poster uses selected font

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete theme preview and font selection feature"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Font config | `config.py` |
| 2 | Download fonts | `fonts/*.ttf` |
| 3 | Update text_positioning | `text_positioning.py` |
| 4 | Update PosterGenerator | `poster_generator.py` |
| 5 | Theme color bar | `gui_app.py` |
| 6 | Font selector | `gui_app.py` |
| 7 | Integration test | - |

**Future Enhancement (parked):**
- 🏔️ Terrain/Elevation layer with hillshade rendering
