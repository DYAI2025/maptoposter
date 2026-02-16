"""
CityMaps Poster Generator - Streamlit GUI

A beautiful, refined web interface for generating map posters with custom
themes, text positioning, and multiple export formats.

Features:
- Theme gallery with visual previews
- Custom theme designer with color pickers
- Save/load custom themes
- Multiple zoom presets
- Detail layer controls
"""

import os
import io
import json
from pathlib import Path
from datetime import datetime

# Setup matplotlib backend before importing pyplot
import fix_matplotlib_backend
import matplotlib.pyplot as plt
import streamlit as st
from PIL import Image

# Import modules
from modules.geocoding import geocode_address
from modules.poster_generator import PosterGenerator
from modules.text_positioning import slider_to_axes_coords, load_fonts
from modules.config import (
    PAPER_SIZES,
    DEFAULT_PAPER_SIZE,
    DEFAULT_DISTANCE,
    FONTS_DIR,
    POSTERS_DIR,
    LAYER_ZOOM_THRESHOLDS,
    FONT_OPTIONS,
    DEFAULT_FONT,
    THEMES_DIR,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

PREVIEW_DIR = Path(__file__).parent / "theme_previews"
CUSTOM_THEMES_DIR = Path(__file__).parent / "custom_themes"
CUSTOM_THEMES_DIR.mkdir(exist_ok=True)

# ============================================================================
# PAGE CONFIGURATION & STYLING
# ============================================================================

st.set_page_config(
    page_title="CityMaps Poster Generator",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Editorial Cartography Aesthetic - CSS Styling
st.html(
    """
    <style>
    /* Overall page styling */
    :root {
        --primary-blue: #1a3a52;
        --accent-gold: #d4a574;
        --earth-tan: #8b7355;
        --bg-cream: #f5f3f0;
        --text-dark: #2c2c2c;
    }

    /* Remove default margins */
    .main {
        padding: 0;
    }

    /* Main content area */
    .stColumn {
        padding: 1.5rem 1rem;
    }

    /* Headings with serif styling */
    h1, h2, h3 {
        font-family: Georgia, serif;
        color: var(--primary-blue);
        font-weight: 600;
    }

    h2 {
        border-bottom: 2px solid var(--accent-gold);
        padding-bottom: 0.5rem;
        margin-top: 1rem;
        margin-bottom: 0.75rem;
    }

    /* Input labels */
    label {
        font-weight: 600;
        color: var(--text-dark);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
    }

    /* Text input styling */
    .stTextInput > div > div > input {
        font-size: 1rem !important;
        padding: 0.75rem !important;
        border: 2px solid #d0d0d0 !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--primary-blue) !important;
        box-shadow: 0 0 0 3px rgba(26, 58, 82, 0.1) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #999 !important;
        font-size: 0.95rem !important;
    }

    /* Selectbox styling */
    .stSelectbox > div > div > select,
    .stSelectbox > div > div > div {
        font-size: 1rem !important;
        padding: 0.75rem !important;
        border-radius: 6px !important;
    }

    /* Number input styling */
    .stNumberInput > div > div > input {
        font-size: 1rem !important;
        padding: 0.75rem !important;
        border-radius: 6px !important;
    }

    /* Button styling */
    .stButton > button {
        background-color: var(--primary-blue);
        color: white;
        font-weight: 600;
        font-size: 1rem;
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 0.25rem;
        transition: all 0.3s ease;
        font-family: Georgia, serif;
    }

    .stButton > button:hover {
        background-color: var(--earth-tan);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Divider styling */
    hr {
        border: 1px solid var(--accent-gold);
        margin: 1rem 0;
    }

    /* Theme gallery grid */
    .theme-card {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        background: white;
    }

    .theme-card:hover {
        border-color: var(--accent-gold);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .theme-card.selected {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(26, 58, 82, 0.2);
    }

    .theme-card img {
        width: 100%;
        border-radius: 4px;
    }

    .theme-card-name {
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
        margin-top: 4px;
        color: var(--text-dark);
    }

    /* Color picker grid */
    .color-picker-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin: 1rem 0;
    }

    .color-picker-item {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Google Maps link button */
    .gmaps-link {
        display: inline-block;
        background-color: #4285f4;
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }

    .gmaps-link:hover {
        background-color: #3367d6;
        text-decoration: none;
    }

    /* Tab styling improvements */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        font-weight: 600;
        font-size: 0.95rem;
    }

    /* Slider styling */
    .stSlider > div > div > div {
        padding: 1rem 0.5rem;
    }

    /* Color picker styling */
    .stColorPicker > div > div > div > input {
        height: 48px !important;
        border-radius: 6px !important;
        border: 2px solid #d0d0d0 !important;
        cursor: pointer !important;
    }

    .stColorPicker > div > div > div > input:hover {
        border-color: var(--primary-blue) !important;
    }

    /* Checkbox and Radio styling */
    .stCheckbox > label, .stRadio > label {
        font-size: 0.95rem !important;
        padding: 0.25rem 0 !important;
    }

    /* Improve spacing for form groups */
    .stTextInput, .stSelectbox, .stNumberInput, .stSlider {
        margin-bottom: 1.25rem;
    }

    /* Search input specific styling */
    .stTextInput[data-testid*="search"] input {
        background-color: #fafafa !important;
    }
    </style>
    """
)

# Load Google Fonts for font preview
GOOGLE_FONTS_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Courier+Prime&family=Dancing+Script&family=Playfair+Display&family=Raleway:wght@300&family=Roboto&display=swap" rel="stylesheet">
"""

# ============================================================================
# ZOOM PRESETS
# ============================================================================

ZOOM_PRESETS = {
    "Grundstück / Haus": {"distance": 200, "desc": "Einzelnes Gebäude oder Grundstück"},
    "Nachbarschaft": {"distance": 500, "desc": "Unmittelbare Umgebung"},
    "Kleines Dorf": {"distance": 1000, "desc": "z.B. Wettmar, kleine Ortschaft"},
    "Dorf / Ortsteil": {"distance": 2000, "desc": "z.B. Isernhagen, größeres Dorf"},
    "Kleinstadt": {"distance": 4000, "desc": "Kleine Stadt oder Stadtteil"},
    "Mittelstadt": {"distance": 8000, "desc": "Mittelgroße Stadt"},
    "Großstadt": {"distance": 15000, "desc": "Große Stadt (Berlin, München)"},
    "Metropolregion": {"distance": 30000, "desc": "Gesamte Metropole mit Umland"},
    "Benutzerdefiniert": {"distance": None, "desc": "Eigenen Radius eingeben"},
}


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "generated_figure" not in st.session_state:
    st.session_state.generated_figure = None

if "generation_history" not in st.session_state:
    st.session_state.generation_history = []

if "current_config" not in st.session_state:
    st.session_state.current_config = None

if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "feature_based"

if "custom_theme_colors" not in st.session_state:
    st.session_state.custom_theme_colors = {
        "bg": "#FFFFFF",
        "text": "#1A1A1A",
        "water": "#A8DADC",
        "parks": "#90BE6D",
        "road_motorway": "#F77F00",
        "road_primary": "#F94144",
        "road_secondary": "#F8961E",
        "road_tertiary": "#F9C74F",
        "road_residential": "#90BE6D",
        "road_default": "#CCCCCC",
        "buildings": "#D0D0D0",
        "buildings_fill": "#E8E8E8",
        "paths": "#B0B0B0",
        "gradient_color": "#FFFFFF",
    }

if "use_custom_theme" not in st.session_state:
    st.session_state.use_custom_theme = False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_theme_preview_path(theme_name: str) -> Path | None:
    """Get path to theme preview image if it exists."""
    preview_path = PREVIEW_DIR / f"{theme_name}.png"
    if preview_path.exists():
        return preview_path
    return None


def get_all_themes() -> list[str]:
    """Get list of all available standard themes."""
    themes_path = Path(THEMES_DIR)
    if not themes_path.exists():
        return ["feature_based"]
    return sorted([f.stem for f in themes_path.glob("*.json")])


def get_custom_themes() -> list[str]:
    """Get list of all custom themes."""
    if not CUSTOM_THEMES_DIR.exists():
        return []
    return sorted([f.stem for f in CUSTOM_THEMES_DIR.glob("*.json")])


def load_custom_theme(theme_name: str) -> dict | None:
    """Load a custom theme from file."""
    theme_path = CUSTOM_THEMES_DIR / f"{theme_name}.json"
    if theme_path.exists():
        with open(theme_path, "r") as f:
            return json.load(f)
    return None


def save_custom_theme(theme_name: str, colors: dict) -> bool:
    """Save a custom theme to file."""
    try:
        theme_data = {
            "name": theme_name,
            "description": f"Custom theme created on {datetime.now().strftime('%Y-%m-%d')}",
            "custom": True,
            **colors,
        }
        theme_path = CUSTOM_THEMES_DIR / f"{theme_name}.json"
        with open(theme_path, "w") as f:
            json.dump(theme_data, f, indent=2)
        return True
    except Exception:
        return False


def delete_custom_theme(theme_name: str) -> bool:
    """Delete a custom theme."""
    try:
        theme_path = CUSTOM_THEMES_DIR / f"{theme_name}.json"
        if theme_path.exists():
            theme_path.unlink()
            return True
    except Exception:
        pass
    return False


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
    <div style="display: flex; gap: 8px; margin: 0.75rem 0; align-items: flex-start; flex-wrap: wrap;">
    '''
    for label, color in colors:
        html += f'''
        <div style="display: flex; flex-direction: column; align-items: center; min-width: 50px;">
            <div style="
                width: 44px;
                height: 44px;
                background-color: {color};
                border: 2px solid rgba(0,0,0,0.15);
                border-radius: 6px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            " title="{label}: {color}"></div>
            <span style="
                font-size: 0.7rem; 
                color: #555; 
                margin-top: 4px; 
                font-weight: 500;
                text-align: center;
                white-space: nowrap;
                max-width: 50px;
                overflow: hidden;
                text-overflow: ellipsis;
            ">{label}</span>
        </div>
        '''
    html += '</div>'
    st.html(html)


def font_selector() -> str:
    """Font selection with ABC preview in each font."""
    st.html(GOOGLE_FONTS_CSS)

    font_css_families = {
        "roboto": "Roboto, sans-serif",
        "playfair": "'Playfair Display', serif",
        "courier": "'Courier Prime', monospace",
        "dancing": "'Dancing Script', cursive",
        "raleway": "Raleway, sans-serif; font-weight: 300",
    }

    font_html = '<div style="display: flex; flex-direction: column; gap: 6px; margin: 0.5rem 0;">'
    for font_id, config in FONT_OPTIONS.items():
        css_family = font_css_families.get(font_id, "sans-serif")
        font_html += f'''
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-family: {css_family}; font-size: 1.1rem; min-width: 45px;">ABC</span>
            <span style="color: #666; font-size: 0.8rem;">{config["name"]}</span>
        </div>
        '''
    font_html += '</div>'
    st.html(font_html)

    selected_font = st.selectbox(
        "Schriftart auswählen",
        options=list(FONT_OPTIONS.keys()),
        index=list(FONT_OPTIONS.keys()).index(DEFAULT_FONT),
        format_func=lambda x: f"{FONT_OPTIONS[x]['name']} - {FONT_OPTIONS[x]['style']}",
        label_visibility="collapsed",
    )
    return selected_font


def get_theme_dict(theme_name: str, custom_colors: dict = None) -> dict:
    """Load theme from file or return custom colors."""
    if custom_colors:
        return custom_colors
    generator = PosterGenerator(theme_name)
    return generator.theme


def download_button(fig, format_type: str, filename: str) -> bytes:
    """Generate downloadable bytes from figure."""
    buf = io.BytesIO()
    if format_type == "png":
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", pad_inches=0.05)
    elif format_type == "svg":
        fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.05)
    elif format_type == "pdf":
        fig.savefig(buf, format="pdf", bbox_inches="tight", pad_inches=0.05)
    buf.seek(0)
    return buf.getvalue()


def add_to_history(config: dict, fig) -> None:
    """Add generated poster to history."""
    thumb_buf = io.BytesIO()
    fig.savefig(thumb_buf, format="png", dpi=60, bbox_inches="tight", pad_inches=0.05)
    thumb_buf.seek(0)
    thumb_img = Image.open(thumb_buf)

    history_item = {
        "id": len(st.session_state.generation_history),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "city": config.get("city", "Unknown"),
        "theme": config.get("theme", "Unknown"),
        "thumbnail": thumb_img,
        "config": config,
    }
    st.session_state.generation_history.append(history_item)


def get_layer_defaults(distance_m: int) -> dict:
    """Get default layer visibility based on zoom level."""
    all_layers = {
        "buildings": False, "paths": False, "landscape": False, "waterways": False,
        "railways": False, "hedges": False, "leisure": False, "amenities": False,
    }

    if distance_m <= LAYER_ZOOM_THRESHOLDS["all_on"]:
        return {k: True for k in all_layers}
    elif distance_m <= LAYER_ZOOM_THRESHOLDS["buildings_only"]:
        all_layers["buildings"] = True
        all_layers["waterways"] = True
        all_layers["railways"] = True
        return all_layers
    else:
        return all_layers


def parse_coordinates(coord_string: str) -> tuple[float, float] | None:
    """Parse coordinates from various formats."""
    coord_string = coord_string.strip()

    if "," in coord_string:
        parts = coord_string.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass

    parts = coord_string.split()
    if len(parts) == 2:
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except ValueError:
            pass

    return None


def render_theme_gallery(themes: list[str], cols_per_row: int = 4, is_custom: bool = False) -> str | None:
    """Render a visual theme gallery with preview images."""
    selected = None

    # Create rows of theme cards
    for row_start in range(0, len(themes), cols_per_row):
        row_themes = themes[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)

        for idx, theme in enumerate(row_themes):
            with cols[idx]:
                preview_path = get_theme_preview_path(theme)
                is_selected = (st.session_state.selected_theme == theme and
                              st.session_state.use_custom_theme == is_custom)

                # Container with border
                border_color = "#1a3a52" if is_selected else "#e0e0e0"
                border_width = "3px" if is_selected else "1px"

                if preview_path:
                    img = Image.open(preview_path)
                    st.image(img, use_container_width=True)
                else:
                    # Show color bar as fallback
                    theme_dict = get_theme_dict(theme) if not is_custom else load_custom_theme(theme)
                    if theme_dict:
                        show_theme_color_bar(theme_dict)
                    else:
                        st.caption("Keine Vorschau")

                # Theme name and select button
                if st.button(
                    theme.replace("_", " ").title(),
                    key=f"theme_btn_{theme}_{is_custom}",
                    use_container_width=True,
                ):
                    st.session_state.selected_theme = theme
                    st.session_state.use_custom_theme = is_custom
                    selected = theme

    return selected


# ============================================================================
# PAGE HEADER
# ============================================================================

st.html(
    """
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">CityMaps</h1>
        <p style="font-size: 1rem; color: #666; font-style: italic;">
            Beautiful map posters crafted from OpenStreetMap data
        </p>
    </div>
    """
)

# ============================================================================
# MAIN LAYOUT: 3 COLUMNS
# ============================================================================

col_input, col_preview, col_history = st.columns([1.2, 2, 0.8], gap="medium")

# ============================================================================
# COLUMN 1: INPUT PANEL WITH TABS
# ============================================================================

with col_input:
    # Main tabs for organization
    tab_theme, tab_location, tab_details = st.tabs(["🎨 Theme", "📍 Standort", "⚙️ Details"])

    # ========================================================================
    # TAB 1: THEME SELECTION
    # ========================================================================
    with tab_theme:
        # Sub-tabs for theme types
        theme_subtab1, theme_subtab2, theme_subtab3 = st.tabs([
            "Vorgefertigte Themes", "Custom Themes", "Theme Designer"
        ])

        # ----- Standard Themes Gallery -----
        with theme_subtab1:
            st.markdown("##### Theme-Galerie")

            all_themes = get_all_themes()

            # Search/filter
            theme_search = st.text_input(
                "Theme suchen",
                placeholder="z.B. noir, ocean...",
                key="theme_search"
            )

            if theme_search:
                filtered_themes = [t for t in all_themes if theme_search.lower() in t.lower()]
            else:
                filtered_themes = all_themes

            if filtered_themes:
                selected = render_theme_gallery(filtered_themes, cols_per_row=2)
                if selected:
                    st.rerun()
            else:
                st.info("Keine Themes gefunden")

            # Show selected theme info
            if not st.session_state.use_custom_theme:
                st.divider()
                theme_dict = get_theme_dict(st.session_state.selected_theme)
                st.markdown(f"**Ausgewählt:** {st.session_state.selected_theme.replace('_', ' ').title()}")
                show_theme_color_bar(theme_dict)
                if theme_dict.get("description"):
                    st.caption(f"_{theme_dict.get('description')}_")

        # ----- Custom Themes -----
        with theme_subtab2:
            st.markdown("##### Gespeicherte Custom Themes")

            custom_themes = get_custom_themes()

            if custom_themes:
                selected = render_theme_gallery(custom_themes, cols_per_row=2, is_custom=True)
                if selected:
                    st.rerun()

                st.divider()

                # Delete custom theme
                theme_to_delete = st.selectbox(
                    "Theme zum Löschen auswählen",
                    options=[""] + custom_themes,
                    format_func=lambda x: "-- Auswählen --" if x == "" else x
                )
                if theme_to_delete and st.button("🗑️ Löschen", type="secondary"):
                    if delete_custom_theme(theme_to_delete):
                        st.success(f"'{theme_to_delete}' gelöscht!")
                        st.rerun()
                    else:
                        st.error("Fehler beim Löschen")
            else:
                st.info("Keine Custom Themes vorhanden. Erstelle eines im 'Theme Designer' Tab.")

        # ----- Custom Theme Designer -----
        with theme_subtab3:
            st.markdown("##### Custom Theme Designer")
            st.caption("Erstelle dein eigenes Farbschema")

            # Load existing theme as starting point
            col_load1, col_load2 = st.columns(2)
            with col_load1:
                base_theme = st.selectbox(
                    "Basis-Theme laden",
                    options=[""] + get_all_themes(),
                    format_func=lambda x: "-- Eigene Farben --" if x == "" else x,
                    key="base_theme_select"
                )
            with col_load2:
                if base_theme and st.button("Farben laden"):
                    loaded_theme = get_theme_dict(base_theme)
                    for key in st.session_state.custom_theme_colors.keys():
                        if key in loaded_theme:
                            st.session_state.custom_theme_colors[key] = loaded_theme[key]
                    st.rerun()

            st.divider()

            # Color pickers organized by category
            st.markdown("**Hintergrund & Text**")
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.custom_theme_colors["bg"] = st.color_picker(
                    "Hintergrund", st.session_state.custom_theme_colors["bg"], key="cp_bg"
                )
            with col2:
                st.session_state.custom_theme_colors["text"] = st.color_picker(
                    "Text", st.session_state.custom_theme_colors["text"], key="cp_text"
                )

            st.markdown("**Natur**")
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.custom_theme_colors["water"] = st.color_picker(
                    "Gewässer", st.session_state.custom_theme_colors["water"], key="cp_water"
                )
            with col2:
                st.session_state.custom_theme_colors["parks"] = st.color_picker(
                    "Parks/Wald", st.session_state.custom_theme_colors["parks"], key="cp_parks"
                )

            st.markdown("**Straßen**")
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.custom_theme_colors["road_motorway"] = st.color_picker(
                    "Autobahn", st.session_state.custom_theme_colors["road_motorway"], key="cp_motorway"
                )
                st.session_state.custom_theme_colors["road_secondary"] = st.color_picker(
                    "Nebenstraße", st.session_state.custom_theme_colors["road_secondary"], key="cp_secondary"
                )
                st.session_state.custom_theme_colors["road_residential"] = st.color_picker(
                    "Wohnstraße", st.session_state.custom_theme_colors["road_residential"], key="cp_residential"
                )
            with col2:
                st.session_state.custom_theme_colors["road_primary"] = st.color_picker(
                    "Hauptstraße", st.session_state.custom_theme_colors["road_primary"], key="cp_primary"
                )
                st.session_state.custom_theme_colors["road_tertiary"] = st.color_picker(
                    "Kleine Straße", st.session_state.custom_theme_colors["road_tertiary"], key="cp_tertiary"
                )
                st.session_state.custom_theme_colors["road_default"] = st.color_picker(
                    "Sonstige", st.session_state.custom_theme_colors["road_default"], key="cp_default"
                )

            st.markdown("**Gebäude & Wege**")
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.custom_theme_colors["buildings"] = st.color_picker(
                    "Gebäude (Umriss)", st.session_state.custom_theme_colors["buildings"], key="cp_buildings"
                )
                st.session_state.custom_theme_colors["paths"] = st.color_picker(
                    "Gehwege", st.session_state.custom_theme_colors["paths"], key="cp_paths"
                )
            with col2:
                st.session_state.custom_theme_colors["buildings_fill"] = st.color_picker(
                    "Gebäude (Füllung)", st.session_state.custom_theme_colors["buildings_fill"], key="cp_buildings_fill"
                )
                st.session_state.custom_theme_colors["gradient_color"] = st.color_picker(
                    "Gradient", st.session_state.custom_theme_colors["gradient_color"], key="cp_gradient"
                )

            st.divider()

            # Preview current custom colors
            st.markdown("**Vorschau:**")
            show_theme_color_bar(st.session_state.custom_theme_colors)

            # Use custom theme toggle
            use_custom = st.checkbox(
                "Custom Theme verwenden",
                value=st.session_state.use_custom_theme,
                key="use_custom_checkbox"
            )
            if use_custom != st.session_state.use_custom_theme:
                st.session_state.use_custom_theme = use_custom
                st.rerun()

            st.divider()

            # Save custom theme
            st.markdown("**Theme speichern**")
            custom_name = st.text_input(
                "Theme-Name",
                placeholder="z.B. mein_theme",
                key="custom_theme_name"
            )
            if st.button("💾 Theme speichern", disabled=not custom_name):
                # Sanitize name
                safe_name = "".join(c for c in custom_name if c.isalnum() or c in "_-").lower()
                if safe_name:
                    if save_custom_theme(safe_name, st.session_state.custom_theme_colors):
                        st.success(f"Theme '{safe_name}' gespeichert!")
                        st.rerun()
                    else:
                        st.error("Fehler beim Speichern")
                else:
                    st.error("Ungültiger Name")

    # ========================================================================
    # TAB 2: LOCATION INPUT
    # ========================================================================
    with tab_location:
        input_mode = st.radio(
            "Eingabemethode",
            options=["Adresse / Ortsname", "Direkte Koordinaten"],
            horizontal=True,
            help="Koordinaten ermöglichen präzise Positionierung",
        )

        lat, lon, location_name, country_name = None, None, None, None

        if input_mode == "Adresse / Ortsname":
            address = st.text_input(
                "Adresse",
                placeholder="z.B. Berlin, Deutschland",
                help="Stadt, Dorf oder Adresse eingeben",
            )
        else:
            st.html(
                '<a href="https://www.google.com/maps" target="_blank" class="gmaps-link">🌍 Google Maps öffnen</a>'
            )

            with st.expander("📖 Anleitung", expanded=False):
                st.markdown("""
                1. Öffne [Google Maps](https://www.google.com/maps)
                2. **Rechtsklick** auf den gewünschten Ort
                3. Klicke auf die Koordinaten (erste Zeile)
                4. Füge sie hier ein: `52.5174, 13.3951`
                """)

            coordinates_input = st.text_input(
                "Koordinaten (Lat, Lon)",
                placeholder="52.5174, 13.3951",
            )

            if coordinates_input:
                parsed = parse_coordinates(coordinates_input)
                if parsed:
                    lat, lon = parsed
                    st.success(f"✅ {lat:.6f}, {lon:.6f}")
                else:
                    st.error("❌ Ungültiges Format")

            location_name = st.text_input("Ortsname (für Poster)", placeholder="z.B. Mein Zuhause")
            country_name = st.text_input("Land (optional)", placeholder="z.B. Deutschland")

        st.divider()

        # Zoom selection
        st.markdown("##### Maßstab / Zoom")
        zoom_preset = st.selectbox(
            "Zoom-Stufe",
            options=list(ZOOM_PRESETS.keys()),
            index=5,
            help="Wähle passend zur Ortsgröße",
        )

        preset_info = ZOOM_PRESETS[zoom_preset]
        st.caption(f"💡 {preset_info['desc']}")

        if zoom_preset == "Benutzerdefiniert":
            distance_m = st.number_input(
                "Radius in Metern",
                min_value=100, max_value=50000, value=5000, step=100,
            )
        else:
            distance_m = preset_info["distance"]
            if distance_m >= 1000:
                st.caption(f"📏 Kartenradius: {distance_m/1000:.1f} km")
            else:
                st.caption(f"📏 Kartenradius: {distance_m} m")

    # ========================================================================
    # TAB 3: DETAILS & OPTIONS
    # ========================================================================
    with tab_details:
        # Paper format
        paper_format = st.selectbox(
            "Papierformat",
            options=list(PAPER_SIZES.keys()),
            index=list(PAPER_SIZES.keys()).index(DEFAULT_PAPER_SIZE),
            help="ISO 216 Standard",
        )

        st.divider()

        # Font selection
        st.markdown("##### Schriftart")
        selected_font = font_selector()

        st.divider()

        # Detail layers
        st.markdown("##### Detail-Layer")
        layer_defaults = get_layer_defaults(distance_m)
        st.caption("💡 Voreinstellungen basieren auf Zoom")

        col_layer1, col_layer2 = st.columns(2)
        with col_layer1:
            show_buildings = st.checkbox("Gebäude", value=layer_defaults.get("buildings", False))
            show_paths = st.checkbox("Wege", value=layer_defaults.get("paths", False))
            show_landscape = st.checkbox("Landschaft", value=layer_defaults.get("landscape", False))
            show_waterways = st.checkbox("Gewässer", value=layer_defaults.get("waterways", False))

        with col_layer2:
            show_railways = st.checkbox("Bahngleise", value=layer_defaults.get("railways", False))
            show_hedges = st.checkbox("Hecken", value=layer_defaults.get("hedges", False))
            show_leisure = st.checkbox("Freizeit", value=layer_defaults.get("leisure", False))
            show_amenities = st.checkbox("Gebäude+", value=layer_defaults.get("amenities", False))

        active_layers = sum([show_buildings, show_paths, show_landscape, show_waterways,
                           show_railways, show_hedges, show_leisure, show_amenities])

        if distance_m > 4000 and active_layers > 2:
            st.warning("⚠️ Viele Layer bei großem Maßstab = langsam", icon="⏳")

        st.divider()

        # Text positioning
        st.markdown("##### Text-Positionierung")
        col_x, col_y = st.columns(2)
        with col_x:
            text_x = st.slider("Horizontal", 0, 100, 50, 5)
        with col_y:
            text_y = st.slider("Vertikal", 0, 100, 14, 2)

        col_opts_1, col_opts_2 = st.columns(2)
        with col_opts_1:
            show_country = st.checkbox("Land anzeigen", value=True)
        with col_opts_2:
            show_coords = st.checkbox("Koordinaten anzeigen", value=True)

    # ========================================================================
    # GENERATE BUTTON (Outside tabs, always visible)
    # ========================================================================
    st.divider()

    if st.button("🎨 Poster generieren", type="primary", use_container_width=True):
        # Validate input
        if input_mode == "Adresse / Ortsname":
            if not address:
                st.error("Bitte eine Adresse eingeben.")
                st.stop()

            with st.spinner("🌍 Geocoding..."):
                try:
                    lat, lon, formatted_address = geocode_address(address)
                    location_name = formatted_address.split(",")[0].strip()
                    country_name = formatted_address.split(",")[-1].strip()
                except Exception as e:
                    st.error(f"Geocoding fehlgeschlagen: {e}")
                    st.stop()
        else:
            if lat is None or lon is None:
                st.error("Bitte gültige Koordinaten eingeben.")
                st.stop()
            if not location_name:
                location_name = "Custom Location"
            if not country_name:
                country_name = ""

        # Determine theme to use
        if st.session_state.use_custom_theme:
            theme_name = "__custom__"
            theme_colors = st.session_state.custom_theme_colors.copy()
        else:
            theme_name = st.session_state.selected_theme
            # Check if it's a custom saved theme
            if theme_name in get_custom_themes():
                theme_colors = load_custom_theme(theme_name)
            else:
                theme_colors = None

        # Generate poster
        with st.spinner("🗺️ Karte wird generiert..."):
            try:
                if theme_colors:
                    generator = PosterGenerator(theme_name="feature_based", font_id=selected_font)
                    generator.theme = theme_colors
                else:
                    generator = PosterGenerator(theme_name=theme_name, font_id=selected_font)

                text_x_coord, text_y_coord = slider_to_axes_coords(text_x, text_y)
                text_config = {
                    "x": text_x_coord,
                    "y": text_y_coord,
                    "alignment": "center",
                    "show_coords": show_coords,
                    "show_country": show_country and bool(country_name),
                }

                layer_config = {
                    "buildings": show_buildings,
                    "paths": show_paths,
                    "landscape": show_landscape,
                    "waterways": show_waterways,
                    "railways": show_railways,
                    "hedges": show_hedges,
                    "leisure": show_leisure,
                    "amenities": show_amenities,
                }

                fig = generator.generate_poster(
                    lat=lat,
                    lon=lon,
                    city_name=location_name,
                    country_name=country_name or "",
                    paper_size=paper_format,
                    distance=distance_m,
                    text_position=text_config,
                    layers=layer_config,
                )

                st.session_state.generated_figure = fig
                st.session_state.current_config = {
                    "city": location_name,
                    "country": country_name or "",
                    "theme": theme_name if not st.session_state.use_custom_theme else "Custom",
                    "paper_format": paper_format,
                    "distance_m": distance_m,
                    "lat": lat,
                    "lon": lon,
                    "layers": layer_config,
                }

                add_to_history(st.session_state.current_config, fig)
                st.success("✅ Poster generiert!")
                st.rerun()

            except Exception as e:
                st.error(f"Generierung fehlgeschlagen: {e}")

# ============================================================================
# COLUMN 2: PREVIEW AREA
# ============================================================================

with col_preview:
    st.markdown("### Vorschau")

    if st.session_state.generated_figure is not None:
        buf = io.BytesIO()
        st.session_state.generated_figure.savefig(buf, format="png", bbox_inches='tight', dpi=150)
        buf.seek(0)
        img = Image.open(buf)
        st.image(img, use_container_width=True)
        buf.close()

        if st.session_state.current_config:
            cfg = st.session_state.current_config
            dist = cfg.get("distance_m", 0)
            dist_str = f"{dist/1000:.1f} km" if dist >= 1000 else f"{dist} m"
            st.caption(f"📍 {cfg.get('city', '')} | 🎨 {cfg.get('theme', '')} | 📏 {dist_str}")

        st.markdown("#### Download")
        col_dl1, col_dl2, col_dl3 = st.columns(3)

        with col_dl1:
            png_data = download_button(st.session_state.generated_figure, "png", "poster.png")
            st.download_button("📥 PNG (300 DPI)", data=png_data, file_name="poster.png",
                             mime="image/png", use_container_width=True)

        with col_dl2:
            svg_data = download_button(st.session_state.generated_figure, "svg", "poster.svg")
            st.download_button("📥 SVG Vektor", data=svg_data, file_name="poster.svg",
                             mime="image/svg+xml", use_container_width=True)

        with col_dl3:
            pdf_data = download_button(st.session_state.generated_figure, "pdf", "poster.pdf")
            st.download_button("📥 PDF", data=pdf_data, file_name="poster.pdf",
                             mime="application/pdf", use_container_width=True)
    else:
        st.info("Konfiguriere die Einstellungen und klicke '🎨 Poster generieren'", icon="ℹ️")

        with st.expander("💡 Schnellstart", expanded=True):
            st.markdown("""
            **1. Theme wählen** - Klicke auf ein Theme in der Galerie

            **2. Standort eingeben** - Stadt/Adresse oder GPS-Koordinaten

            **3. Zoom einstellen** - Von Haus (200m) bis Metropole (30km)

            **4. Generieren** - Klicke den Button!
            """)

# ============================================================================
# COLUMN 3: HISTORY & INFO
# ============================================================================

with col_history:
    st.markdown("### Verlauf")

    if st.session_state.generation_history:
        st.caption(f"Erstellt: {len(st.session_state.generation_history)}")

        for item in reversed(st.session_state.generation_history[-5:]):
            with st.expander(f"📍 {item['city']}", expanded=False):
                st.image(item["thumbnail"])
                st.caption(f"{item['timestamp']} | {item['theme']}")

                if st.button("🔄 Laden", key=f"reload_{item['id']}"):
                    config = item["config"]
                    st.session_state.current_config = config
                    st.info("Konfiguration geladen!")
    else:
        st.info("Deine Poster erscheinen hier.", icon="ℹ️")

    st.divider()

    st.markdown("#### Zoom-Referenz")
    st.caption("""
    • **200m** - Gebäude
    • **500m** - Nachbarschaft
    • **1km** - Kleines Dorf
    • **2km** - Dorf
    • **4km** - Kleinstadt
    • **8km** - Mittelstadt
    • **15km** - Großstadt
    • **30km** - Metropole
    """)
