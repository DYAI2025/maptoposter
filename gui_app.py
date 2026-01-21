"""
CityMaps Poster Generator - Streamlit GUI

A beautiful, refined web interface for generating map posters with custom
themes, text positioning, and multiple export formats.

Supports both address geocoding AND direct coordinate input for precise
location control - perfect for villages, neighborhoods, or any exact spot.
"""

import os
import io
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
import matplotlib.pyplot as plt
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
)


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
st.markdown(
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
        padding: 2rem 1.5rem;
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
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Input labels */
    label {
        font-weight: 600;
        color: var(--text-dark);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
        margin: 1.5rem 0;
    }

    /* Info boxes */
    .stInfo {
        background-color: #f0f8fa;
        border-left: 4px solid var(--primary-blue);
        padding: 1rem;
        border-radius: 0.25rem;
    }

    .stSuccess {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
    }

    .stWarning {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
    }

    /* Slider styling */
    .stSlider {
        padding: 0.5rem 0;
    }

    .stSlider > div > div > div {
        color: var(--primary-blue);
    }

    /* Preview frame */
    .preview-frame {
        border: 2px solid var(--accent-gold);
        padding: 1rem;
        background-color: white;
        border-radius: 0.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f0f8fa;
        border-left: 4px solid var(--primary-blue);
    }

    .streamlit-expanderHeader:hover {
        background-color: #e0f2f7;
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

    /* Zoom preset badges */
    .zoom-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Load Google Fonts for font preview
GOOGLE_FONTS_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Courier+Prime&family=Dancing+Script&family=Playfair+Display&family=Raleway:wght@300&family=Roboto&display=swap" rel="stylesheet">
"""

# ============================================================================
# ZOOM PRESETS - From village to metropolis
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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


def get_theme_dict(theme_name: str) -> dict:
    """Load theme from file or return default."""
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
    # Create thumbnail
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
    if distance_m <= LAYER_ZOOM_THRESHOLDS["all_on"]:
        # Village zoom: all layers on
        return {"buildings": True, "paths": True, "landscape": True}
    elif distance_m <= LAYER_ZOOM_THRESHOLDS["buildings_only"]:
        # Town zoom: only buildings
        return {"buildings": True, "paths": False, "landscape": False}
    else:
        # City zoom: no detail layers
        return {"buildings": False, "paths": False, "landscape": False}


def parse_coordinates(coord_string: str) -> tuple[float, float] | None:
    """Parse coordinates from various formats."""
    coord_string = coord_string.strip()

    # Try to parse "lat, lon" format
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

    # Try to parse "lat lon" format (space separated)
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


# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">🗺️ CityMaps</h1>
        <p style="font-size: 1.1rem; color: #666; font-style: italic;">
            Beautiful map posters crafted from OpenStreetMap data
        </p>
        <p style="font-size: 0.9rem; color: #888;">
            Von der Metropole bis zum kleinsten Dorf – immer hochauflösend
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# MAIN LAYOUT: 3 COLUMNS
# ============================================================================

col_input, col_preview, col_history = st.columns([1, 2, 1], gap="medium")

# ============================================================================
# COLUMN 1: INPUT PANEL
# ============================================================================

with col_input:
    st.markdown("### 🎨 Konfiguration")

    # Paper Format Selection
    paper_format = st.selectbox(
        "Papierformat",
        options=list(PAPER_SIZES.keys()),
        index=list(PAPER_SIZES.keys()).index(DEFAULT_PAPER_SIZE),
        help="Wähle die Poster-Dimensionen (ISO 216 Standard)",
    )

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

    # Font Selection
    st.markdown("")  # Spacer
    selected_font = font_selector()

    st.divider()

    # ========================================================================
    # LOCATION INPUT - Two modes
    # ========================================================================

    st.markdown("### 📍 Standort")

    input_mode = st.radio(
        "Eingabemethode",
        options=["Adresse / Ortsname", "Direkte Koordinaten"],
        horizontal=True,
        help="Koordinaten ermöglichen präzise Positionierung für jeden Ort der Welt",
    )

    lat, lon, location_name, country_name = None, None, None, None

    if input_mode == "Adresse / Ortsname":
        # Address mode (existing)
        address = st.text_input(
            "Adresse",
            placeholder="z.B. Isernhagen, Deutschland",
            help="Stadt, Dorf oder Adresse eingeben",
        )

    else:
        # Direct coordinates mode (NEW!)
        st.markdown(
            """
            <a href="https://www.google.com/maps" target="_blank" class="gmaps-link">
                🌍 Google Maps öffnen
            </a>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("📖 Anleitung: Koordinaten aus Google Maps", expanded=False):
            st.markdown("""
            **So findest du die Koordinaten:**

            1. Öffne [Google Maps](https://www.google.com/maps)
            2. Navigiere zu deinem gewünschten Ort
            3. **Rechtsklick** auf die exakte Position
            4. Klicke auf die Koordinaten (erste Zeile im Menü)
            5. Die Koordinaten werden kopiert!
            6. Füge sie hier ein (Format: `52.5174, 13.3951`)

            **Tipp:** Zoome nah heran für präzise Positionierung!
            """)

        coordinates_input = st.text_input(
            "Koordinaten (Lat, Lon)",
            placeholder="52.5174, 13.3951",
            help="Aus Google Maps kopieren: Rechtsklick → Koordinaten klicken",
        )

        # Parse coordinates
        if coordinates_input:
            parsed = parse_coordinates(coordinates_input)
            if parsed:
                lat, lon = parsed
                st.success(f"✅ Koordinaten erkannt: {lat:.6f}, {lon:.6f}")
            else:
                st.error("❌ Ungültiges Format. Bitte 'Lat, Lon' eingeben (z.B. 52.5174, 13.3951)")

        # Custom location name for coordinates
        location_name = st.text_input(
            "Ortsname (für Poster)",
            placeholder="z.B. Mein Zuhause, Wettmar, etc.",
            help="Dieser Name erscheint auf dem Poster",
        )

        country_name = st.text_input(
            "Land / Region (optional)",
            placeholder="z.B. Deutschland, Niedersachsen, etc.",
            help="Erscheint unter dem Ortsnamen",
        )

    st.divider()

    # ========================================================================
    # ZOOM / SCALE CONTROL
    # ========================================================================

    st.markdown("### 🔍 Maßstab / Zoom")

    zoom_preset = st.selectbox(
        "Zoom-Stufe",
        options=list(ZOOM_PRESETS.keys()),
        index=5,  # Default: Mittelstadt
        help="Wähle passend zur Ortsgröße",
    )

    # Show preset description
    preset_info = ZOOM_PRESETS[zoom_preset]
    st.caption(f"💡 {preset_info['desc']}")

    # Custom distance input or use preset
    if zoom_preset == "Benutzerdefiniert":
        distance_m = st.number_input(
            "Radius in Metern",
            min_value=100,
            max_value=50000,
            value=5000,
            step=100,
            help="100m (Haus) bis 50km (Region)",
        )
    else:
        distance_m = preset_info["distance"]
        # Show the actual distance
        if distance_m >= 1000:
            st.caption(f"📏 Kartenradius: {distance_m/1000:.1f} km")
        else:
            st.caption(f"📏 Kartenradius: {distance_m} m")

    st.divider()

    # ========================================================================
    # DETAIL LAYERS
    # ========================================================================

    st.markdown("### 🏘️ Detail-Layer")

    # Get recommended defaults based on zoom level
    layer_defaults = get_layer_defaults(distance_m)

    st.caption("💡 Voreinstellungen basieren auf der gewählten Zoom-Stufe")

    col_layer1, col_layer2 = st.columns(2)

    with col_layer1:
        show_buildings = st.checkbox(
            "🏠 Gebäude",
            value=layer_defaults["buildings"],
            help="Gebäudeumrisse anzeigen",
        )
        show_paths = st.checkbox(
            "🚶 Feldwege / Pfade",
            value=layer_defaults["paths"],
            help="Wanderwege, Radwege, Feldwege",
        )

    with col_layer2:
        show_landscape = st.checkbox(
            "🌾 Landschaft",
            value=layer_defaults["landscape"],
            help="Felder, Wiesen, Wälder",
        )

    # Warning for large zoom with detail layers
    if distance_m > 4000 and (show_buildings or show_paths or show_landscape):
        st.warning(
            "⚠️ Detail-Layer bei großem Maßstab können die Generierung verlangsamen.",
            icon="⏳"
        )

    st.divider()

    # ========================================================================
    # TEXT POSITIONING
    # ========================================================================

    st.markdown("### 📝 Text-Positionierung")

    # Text Position Sliders
    col_x, col_y = st.columns(2)

    with col_x:
        text_x = st.slider(
            "Horizontal",
            min_value=0,
            max_value=100,
            value=50,
            step=5,
            help="0 = links, 50 = mitte, 100 = rechts",
        )

    with col_y:
        text_y = st.slider(
            "Vertikal",
            min_value=0,
            max_value=100,
            value=14,
            step=2,
            help="0 = unten, 50 = mitte, 100 = oben",
        )

    st.caption(f"Position: ({text_x}%, {text_y}%)")

    # Text Options
    col_opts_1, col_opts_2 = st.columns(2)
    with col_opts_1:
        show_country = st.checkbox("Land anzeigen", value=True)
    with col_opts_2:
        show_coords = st.checkbox("Koordinaten anzeigen", value=True)

    st.divider()

    # ========================================================================
    # GENERATE BUTTON
    # ========================================================================

    if st.button("🎨 Poster generieren", type="primary", use_container_width=True):

        # Validate input based on mode
        if input_mode == "Adresse / Ortsname":
            if not address:
                st.error("Bitte eine Adresse eingeben.")
                st.stop()

            with st.spinner("🌍 Geocoding Adresse..."):
                try:
                    lat, lon, formatted_address = geocode_address(address)
                    location_name = formatted_address.split(",")[0].strip()
                    country_name = formatted_address.split(",")[-1].strip()
                except Exception as e:
                    st.error(f"Geocoding fehlgeschlagen: {e}")
                    st.stop()

        else:  # Coordinates mode
            if lat is None or lon is None:
                st.error("Bitte gültige Koordinaten eingeben.")
                st.stop()

            if not location_name:
                st.warning("Kein Ortsname angegeben - verwende 'Custom Location'")
                location_name = "Custom Location"

            if not country_name:
                country_name = ""

        # Generate poster
        with st.spinner("🗺️ Karte wird generiert..."):
            try:
                generator = PosterGenerator(theme_name=theme_name, font_id=selected_font)

                # Convert slider to axes coords
                text_x_coord, text_y_coord = slider_to_axes_coords(text_x, text_y)

                text_config = {
                    "x": text_x_coord,
                    "y": text_y_coord,
                    "alignment": "center",
                    "show_coords": show_coords,
                    "show_country": show_country and bool(country_name),
                }

                # Layer visibility settings
                layer_config = {
                    "buildings": show_buildings,
                    "paths": show_paths,
                    "landscape": show_landscape,
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
                    "theme": theme_name,
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
    st.markdown("### 🖼️ Vorschau")

    if st.session_state.generated_figure is not None:
        # Display figure
        st.markdown('<div class="preview-frame">', unsafe_allow_html=True)
        st.pyplot(st.session_state.generated_figure, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Show current config
        if st.session_state.current_config:
            cfg = st.session_state.current_config
            dist = cfg.get("distance_m", 0)
            dist_str = f"{dist/1000:.1f} km" if dist >= 1000 else f"{dist} m"
            st.caption(
                f"📍 {cfg.get('city', '')} | "
                f"🎨 {cfg.get('theme', '')} | "
                f"📏 {dist_str}"
            )

        # Download buttons
        st.markdown("#### Download-Optionen")

        col_dl1, col_dl2, col_dl3 = st.columns(3)

        with col_dl1:
            png_data = download_button(
                st.session_state.generated_figure,
                "png",
                "poster.png",
            )
            st.download_button(
                "📥 PNG (300 DPI)",
                data=png_data,
                file_name="poster.png",
                mime="image/png",
                use_container_width=True,
            )

        with col_dl2:
            svg_data = download_button(
                st.session_state.generated_figure,
                "svg",
                "poster.svg",
            )
            st.download_button(
                "📥 SVG Vektor",
                data=svg_data,
                file_name="poster.svg",
                mime="image/svg+xml",
                use_container_width=True,
            )

        with col_dl3:
            pdf_data = download_button(
                st.session_state.generated_figure,
                "pdf",
                "poster.pdf",
            )
            st.download_button(
                "📥 PDF",
                data=pdf_data,
                file_name="poster.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    else:
        st.info(
            "Konfiguriere die Einstellungen und klicke '🎨 Poster generieren'",
            icon="ℹ️",
        )

        # Show example workflow
        with st.expander("💡 Beispiel-Workflow", expanded=True):
            st.markdown("""
            **Für eine Großstadt (z.B. Berlin):**
            1. Wähle "Adresse / Ortsname"
            2. Eingabe: `Berlin, Deutschland`
            3. Zoom: `Großstadt` (15 km)

            **Für ein kleines Dorf (z.B. Wettmar):**
            1. Wähle "Adresse / Ortsname"
            2. Eingabe: `Wettmar, Deutschland`
            3. Zoom: `Kleines Dorf` (1 km)

            **Für einen exakten Ort (z.B. dein Haus):**
            1. Wähle "Direkte Koordinaten"
            2. Öffne Google Maps, Rechtsklick → Koordinaten
            3. Füge ein: `52.1234, 9.5678`
            4. Zoom: `Nachbarschaft` (500 m)
            """)

# ============================================================================
# COLUMN 3: HISTORY & CONTROLS
# ============================================================================

with col_history:
    st.markdown("### 📊 Verlauf")

    if st.session_state.generation_history:
        st.caption(f"Generierte Poster: {len(st.session_state.generation_history)}")

        for item in reversed(st.session_state.generation_history[-5:]):
            with st.expander(
                f"📍 {item['city']} — {item['timestamp']}",
                expanded=False,
            ):
                st.image(item["thumbnail"])

                col_reload, col_info = st.columns(2)

                with col_reload:
                    if st.button("🔄 Laden", key=f"reload_{item['id']}"):
                        config = item["config"]
                        st.session_state.current_config = config
                        st.info("Konfiguration geladen!")

                with col_info:
                    st.caption(f"Theme: {item['theme']}")

    else:
        st.info(
            "Deine generierten Poster erscheinen hier.",
            icon="ℹ️",
        )

    st.divider()

    # Quick Stats
    st.markdown("#### Statistiken")
    st.metric("Poster erstellt", len(st.session_state.generation_history))

    st.divider()

    st.markdown("#### Zoom-Referenz")
    st.caption("""
    • **200m** - Einzelnes Gebäude
    • **500m** - Nachbarschaft
    • **1km** - Kleines Dorf
    • **2km** - Größeres Dorf
    • **4km** - Kleinstadt
    • **8km** - Mittelstadt
    • **15km** - Großstadt
    • **30km** - Metropolregion
    """)

    st.markdown("#### Info")
    st.caption(
        "CityMaps nutzt OpenStreetMap-Daten. "
        "Alle Karten sind vektorbasiert und daher immer hochauflösend."
    )
