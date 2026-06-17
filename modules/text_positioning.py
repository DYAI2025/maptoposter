"""
Text positioning module for map poster typography.

Handles dynamic text sizing, placement, and rendering of city names,
coordinates, and attribution on map axes.

Includes automatic font scaling based on paper format and zoom level.
"""

from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt

from .config import PAPER_SCALE_FACTORS, ZOOM_SCALE_FACTORS, FONT_SIZES, PAPER_SIZES


def get_paper_scale_factor(paper_size: str) -> float:
    """
    Get font scale factor for paper size.

    Args:
        paper_size: Paper format (A2, A3, A4, A5)

    Returns:
        Scale factor (1.0 = A4 reference)
    """
    return PAPER_SCALE_FACTORS.get(paper_size, 1.0)


def get_zoom_scale_factor(distance_m: int) -> float:
    """
    Get font scale factor for zoom/distance level.

    Uses interpolation between defined thresholds.

    Args:
        distance_m: Map radius in meters

    Returns:
        Scale factor (1.0 = 15km+ reference)
    """
    # Sort thresholds by distance
    thresholds = sorted(ZOOM_SCALE_FACTORS, key=lambda x: x[0])

    # If below minimum, use minimum factor
    if distance_m <= thresholds[0][0]:
        return thresholds[0][1]

    # If above maximum, use maximum factor
    if distance_m >= thresholds[-1][0]:
        return thresholds[-1][1]

    # Interpolate between thresholds
    for i, (dist, factor) in enumerate(thresholds[:-1]):
        next_dist, next_factor = thresholds[i + 1]
        if dist <= distance_m < next_dist:
            # Linear interpolation
            ratio = (distance_m - dist) / (next_dist - dist)
            return factor + ratio * (next_factor - factor)

    return 1.0


def calculate_font_scale(paper_size: str, distance_m: int) -> float:
    """
    Calculate combined font scale factor.

    Args:
        paper_size: Paper format (A2, A3, A4, A5)
        distance_m: Map radius in meters

    Returns:
        Combined scale factor
    """
    paper_factor = get_paper_scale_factor(paper_size)
    zoom_factor = get_zoom_scale_factor(distance_m)
    return paper_factor * zoom_factor


def get_scaled_font_size(
    base_size: int,
    paper_size: str,
    distance_m: int,
    min_size: int = 8
) -> int:
    """
    Calculate scaled font size based on paper and zoom.

    Args:
        base_size: Base font size (for A4 at 15km)
        paper_size: Paper format
        distance_m: Map radius in meters
        min_size: Minimum allowed font size

    Returns:
        Scaled font size (int)
    """
    scale = calculate_font_scale(paper_size, distance_m)
    scaled = base_size * scale
    return max(int(scaled), min_size)


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


def get_dynamic_font_size(
    city_name: str,
    base_size: int = 60,
    min_size: int = 24,
    threshold: int = 10,
) -> int:
    """
    Calculate dynamic font size based on city name length.

    Prevents long city names from being truncated by scaling down font size.

    Args:
        city_name: Name of city
        base_size: Base font size for short names
        min_size: Minimum allowed font size
        threshold: Character count before scaling begins

    Returns:
        Adjusted font size (int)
    """
    char_count = len(city_name)

    if char_count > threshold:
        scale_factor = threshold / char_count
        adjusted_size = max(base_size * scale_factor, min_size)
        return int(adjusted_size)
    else:
        return base_size


def format_coordinates(lat: float, lon: float, format_type: str = "default") -> str:
    """
    Format latitude and longitude as readable string with hemisphere indicators.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        format_type: Format type - "default", "decimal", "compact", " DMS"

    Returns:
        Formatted coordinate string
    """
    lat_hemisphere = "N" if lat >= 0 else "S"
    lon_hemisphere = "E" if lon >= 0 else "W"

    lat_abs = abs(lat)
    lon_abs = abs(lon)

    if format_type == "decimal":
        # Pure decimal format: 48.8566, 2.3522
        return f"{lat_abs:.4f}, {lon_abs:.4f}"
    elif format_type == "compact":
        # Compact: 48.9°N / 2.4°E
        return f"{lat_abs:.1f}°{lat_hemisphere} / {lon_abs:.1f}°{lon_hemisphere}"
    elif format_type == "dms":
        # Degrees, minutes, seconds format
        lat_deg = int(lat_abs)
        lat_min = (lat_abs - lat_deg) * 60
        lon_deg = int(lon_abs)
        lon_min = (lon_abs - lon_deg) * 60

        return f"{lat_deg}°{int(lat_min)}'{lat_hemisphere} / {lon_deg}°{int(lon_min)}'{lon_hemisphere}"
    else:
        # Default with hemisphere symbols
        return f"{lat_abs:.4f}° {lat_hemisphere} / {lon_abs:.4f}° {lon_hemisphere}"


def _compute_text_spacing(size_city: int, size_country: int, size_coords: int,
                          paper_size: str) -> dict:
    """Compute dynamic vertical spacing between text elements.

    Spacing is derived from actual font sizes so elements never overlap,
    regardless of paper format, zoom level, or name length.  Values are
    expressed in normalised axes coordinates (0-1).

    The reference frame is a portrait A4 at 11.69" height; other formats
    scale proportionally via their pixel height.
    """
    _, paper_h = PAPER_SIZES.get(paper_size, PAPER_SIZES["A4"])
    # PAPER_SIZES values are in inches (config.py).  72 pt = 1 inch.
    pt_to_axes = 1.0 / (paper_h * 72)

    # Gap = 40 % of the larger neighbour's size (visually airy, never touching)
    city_gap = size_city * pt_to_axes * 1.6      # city name → next element
    subtitle_gap = size_country * pt_to_axes * 1.2
    line_gap = 4 * pt_to_axes                     # decorative line thickness
    country_gap = size_country * pt_to_axes * 1.4
    coords_gap = size_coords * pt_to_axes * 1.4

    return {
        "city_gap": city_gap,
        "subtitle_gap": subtitle_gap,
        "line_gap": line_gap,
        "country_gap": country_gap,
        "coords_gap": coords_gap,
    }


def apply_text_overlay(
    ax,
    city: str,
    country: str,
    lat: float,
    lon: float,
    theme: dict,
    fonts: dict | None = None,
    text_config: dict | None = None,
    paper_size: str = "A4",
    distance_m: int = 8000,
    custom_city_text: str | None = None,
    custom_country_text: str | None = None,
    custom_subtitle: str | None = None,
    coords_format: str = "default",
    custom_coords_text: str | None = None,
    text_color: str | None = None,
) -> None:
    """Apply text overlay to map axes.

    Font sizes are read from ``FONT_SIZES`` in *config.py* and then scaled
    by paper format and zoom level.  Vertical spacing between elements is
    **computed dynamically** from the resulting sizes so that text never
    overlaps — even on A5 at 500 m zoom with a 25-character city name.
    """
    if text_config is None:
        text_config = {
            "x": 0.5,
            "y": 0.14,
            "alignment": "center",
            "show_coords": True,
            "show_country": True,
        }

    display_city = custom_city_text if custom_city_text else city
    display_country = custom_country_text if custom_country_text else country
    text_color_final = text_color if text_color else theme["text"]

    # --- Scaled font sizes (from config, not hardcoded) ---
    size_city = get_scaled_font_size(
        FONT_SIZES["city_name"], paper_size, distance_m, min_size=16
    )
    size_country = get_scaled_font_size(
        FONT_SIZES["country"], paper_size, distance_m, min_size=10
    )
    size_coords = get_scaled_font_size(
        FONT_SIZES["coordinates"], paper_size, distance_m, min_size=8
    )
    size_attr = get_scaled_font_size(
        FONT_SIZES["attribution"], paper_size, distance_m, min_size=6
    )

    # --- Long-name scaling (on top of paper/zoom) ---
    name_scale = 1.0
    if len(display_city) > 10:
        name_scale = max(10 / len(display_city), 0.5)
    adjusted_city_size = max(int(size_city * name_scale), 16)

    # --- Build FontProperties ---
    if fonts:
        font_main = FontProperties(fname=fonts["bold"], size=adjusted_city_size)
        font_sub = FontProperties(fname=fonts["light"], size=size_country)
        font_subtitle = FontProperties(fname=fonts["light"], size=int(size_country * 0.8))
        font_coords = FontProperties(fname=fonts["regular"], size=size_coords)
        font_attr = FontProperties(fname=fonts["light"], size=size_attr)
    else:
        font_main = FontProperties(family="monospace", weight="bold", size=adjusted_city_size)
        font_sub = FontProperties(family="monospace", weight="normal", size=size_country)
        font_subtitle = FontProperties(family="monospace", weight="normal", size=int(size_country * 0.8))
        font_coords = FontProperties(family="monospace", size=size_coords)
        font_attr = FontProperties(family="monospace", size=size_attr)

    # --- Dynamic spacing (prevents text overlap at any scale) ---
    spacing = _compute_text_spacing(adjusted_city_size, size_country, size_coords, paper_size)

    ha = text_config.get("alignment", "center")
    x_pos = text_config.get("x", 0.5)
    cursor_y = text_config.get("y", 0.14)

    # --- CITY NAME ---
    spaced_city = "  ".join(list(display_city.upper()))
    ax.text(
        x_pos, cursor_y, spaced_city,
        transform=ax.transAxes, color=text_color_final,
        ha=ha, fontproperties=font_main, zorder=11,
    )
    cursor_y -= spacing["city_gap"]

    # --- CUSTOM SUBTITLE ---
    if custom_subtitle:
        ax.text(
            x_pos, cursor_y, custom_subtitle.upper(),
            transform=ax.transAxes, color=text_color_final, alpha=0.8,
            ha=ha, fontproperties=font_subtitle, zorder=11,
        )
        cursor_y -= spacing["subtitle_gap"]

    # --- DECORATIVE LINE (scaled) ---
    scale_factor = calculate_font_scale(paper_size, distance_m)
    line_length = 0.2 * scale_factor
    line_half = line_length / 2
    if ha == "center":
        line_left = 0.5 - line_half
        line_right = 0.5 + line_half
    else:
        line_left = 0.1
        line_right = 0.1 + line_length
    line_width = max(0.5, 1.0 * scale_factor)
    ax.plot(
        [line_left, line_right], [cursor_y, cursor_y],
        transform=ax.transAxes, color=text_color_final,
        linewidth=line_width, zorder=11,
    )
    cursor_y -= spacing["line_gap"]

    # --- COUNTRY NAME ---
    if text_config.get("show_country", True):
        ax.text(
            x_pos, cursor_y, display_country.upper(),
            transform=ax.transAxes, color=text_color_final,
            ha=ha, fontproperties=font_sub, zorder=11,
        )
        cursor_y -= spacing["country_gap"]

    # --- COORDINATES ---
    if text_config.get("show_coords", True):
        if custom_coords_text:
            coords_text = custom_coords_text
        else:
            coords_text = format_coordinates(lat, lon, coords_format)

        ax.text(
            x_pos, cursor_y, coords_text,
            transform=ax.transAxes, color=text_color_final, alpha=0.7,
            ha=ha, fontproperties=font_coords, zorder=11,
        )

    # --- ATTRIBUTION (bottom right, always) ---
    ax.text(
        0.98, 0.02, "© OpenStreetMap contributors",
        transform=ax.transAxes, color=text_color_final, alpha=0.5,
        ha="right", va="bottom", fontproperties=font_attr, zorder=11,
    )


def get_text_preview_box(
    x: float, y: float, width: float = 0.2, height: float = 0.15
) -> dict:
    """
    Get rectangle coordinates for text box preview overlay.

    Useful for showing in Streamlit where text will be positioned.

    Args:
        x: Horizontal center position (0-1)
        y: Vertical center position (0-1)
        width: Box width (0-1)
        height: Box height (0-1)

    Returns:
        Dict with 'left', 'right', 'top', 'bottom' coordinates
    """
    left = max(0, x - width / 2)
    right = min(1, x + width / 2)
    top = min(1, y + height / 2)
    bottom = max(0, y - height / 2)

    return {
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "width": right - left,
        "height": top - bottom,
    }


def slider_to_axes_coords(slider_x: int, slider_y: int) -> tuple[float, float]:
    """
    Convert slider values (0-100) to matplotlib axes coordinates (0-1).

    Useful for Streamlit sliders that typically use 0-100 range.

    Args:
        slider_x: X position from slider (0-100)
        slider_y: Y position from slider (0-100)

    Returns:
        Tuple of (axes_x, axes_y) in 0-1 range
    """
    return (slider_x / 100.0, slider_y / 100.0)


def axes_coords_to_slider(axes_x: float, axes_y: float) -> tuple[int, int]:
    """
    Convert matplotlib axes coordinates (0-1) to slider values (0-100).

    Inverse of slider_to_axes_coords.

    Args:
        axes_x: X position in axes coordinates (0-1)
        axes_y: Y position in axes coordinates (0-1)

    Returns:
        Tuple of (slider_x, slider_y) in 0-100 range
    """
    return (int(axes_x * 100), int(axes_y * 100))
