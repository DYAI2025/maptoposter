"""
Text positioning module for map poster typography.

Handles dynamic text sizing, placement, and rendering of city names,
coordinates, and attribution on map axes.

Includes automatic font scaling based on paper format and zoom level.
"""

from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt

from .config import PAPER_SCALE_FACTORS, ZOOM_SCALE_FACTORS


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
    # User personalization parameters
    custom_city_text: str | None = None,
    custom_country_text: str | None = None,
    custom_subtitle: str | None = None,
    coords_format: str = "default",
    custom_coords_text: str | None = None,
    text_color: str | None = None,
) -> None:
    """
    Apply text overlay to map axes.

    Renders city name, country, coordinates, and attribution on the map.
    Font sizes are automatically scaled based on paper format and zoom level.

    Args:
        ax: Matplotlib axes object
        city: City name (default text)
        country: Country name
        lat: Latitude coordinate
        lon: Longitude coordinate
        theme: Theme dictionary with color definitions
        fonts: Font paths dict ('bold', 'regular', 'light'), or None for system fonts
        text_config: Optional text configuration dict with keys:
            - x: Horizontal position (0-1), default 0.5
            - y: Vertical position (0-1), default 0.14
            - alignment: 'left', 'center', 'right', default 'center'
            - show_coords: bool, default True
            - show_country: bool, default True
        paper_size: Paper format for font scaling (A2, A3, A4, A5)
        distance_m: Map radius in meters for font scaling
        # User personalization parameters:
        custom_city_text: Override city name with custom text
        custom_country_text: Override country name with custom text
        custom_subtitle: Add custom subtitle below city name
        coords_format: Format for coordinates ("default", "decimal", "compact", "dms")
        custom_coords_text: Completely override coordinates with custom text
        text_color: Override text color from theme
    """
    if text_config is None:
        text_config = {
            "x": 0.5,
            "y": 0.14,
            "alignment": "center",
            "show_coords": True,
            "show_country": True,
        }

    # Use personalization or fall back to defaults
    display_city = custom_city_text if custom_city_text else city
    display_country = custom_country_text if custom_country_text else country

    # Determine text color (custom or from theme)
    text_color_final = text_color if text_color else theme["text"]

    # Calculate scaled font sizes
    size_city = get_scaled_font_size(60, paper_size, distance_m, min_size=16)
    size_country = get_scaled_font_size(22, paper_size, distance_m, min_size=10)
    size_coords = get_scaled_font_size(14, paper_size, distance_m, min_size=8)
    size_attr = get_scaled_font_size(8, paper_size, distance_m, min_size=6)

    # Load fonts with scaled sizes
    if fonts:
        font_main = FontProperties(fname=fonts["bold"], size=size_city)
        font_sub = FontProperties(fname=fonts["light"], size=size_country)
        font_coords = FontProperties(fname=fonts["regular"], size=size_coords)
        font_attr = FontProperties(fname=fonts["light"], size=size_attr)
    else:
        # Fallback to system fonts
        font_main = FontProperties(family="monospace", weight="bold", size=size_city)
        font_sub = FontProperties(family="monospace", weight="normal", size=size_country)
        font_coords = FontProperties(family="monospace", size=size_coords)
        font_attr = FontProperties(family="monospace", size=size_attr)

    # Format city name with spacing (use display_city for personalization)
    spaced_city = "  ".join(list(display_city.upper()))

    # Additional dynamic sizing for long names (on top of paper/zoom scaling)
    name_scale = 1.0
    if len(display_city) > 10:
        name_scale = 10 / len(display_city)
        name_scale = max(name_scale, 0.5)  # Don't go below 50%

    adjusted_font_size = int(size_city * name_scale)
    if fonts:
        font_main_adjusted = FontProperties(
            fname=fonts["bold"], size=adjusted_font_size
        )
        font_subtitle = FontProperties(
            fname=fonts["light"], size=int(size_country * 0.8)
        )
    else:
        font_main_adjusted = FontProperties(
            family="monospace", weight="bold", size=adjusted_font_size
        )
        font_subtitle = FontProperties(
            family="monospace", weight="normal", size=int(size_country * 0.8)
        )

    # Get alignment
    ha = text_config.get("alignment", "center")
    x_pos = text_config.get("x", 0.5)
    y_pos = text_config.get("y", 0.14)

    # --- CITY NAME ---
    ax.text(
        x_pos,
        y_pos,
        spaced_city,
        transform=ax.transAxes,
        color=text_color_final,
        ha=ha,
        fontproperties=font_main_adjusted,
        zorder=11,
    )

    # --- CUSTOM SUBTITLE (if provided) ---
    if custom_subtitle:
        ax.text(
            x_pos,
            y_pos - 0.025,
            custom_subtitle.upper(),
            transform=ax.transAxes,
            color=text_color_final,
            alpha=0.8,
            ha=ha,
            fontproperties=font_subtitle,
            zorder=11,
        )

    # --- DECORATIVE LINE (scaled) ---
    scale_factor = calculate_font_scale(paper_size, distance_m)
    line_length = 0.2 * scale_factor  # Scale line length
    line_half = line_length / 2
    if ha == "center":
        line_left = 0.5 - line_half
        line_right = 0.5 + line_half
    else:
        line_left = 0.1
        line_right = 0.1 + line_length
    line_width = max(0.5, 1.0 * scale_factor)  # Scale line width
    ax.plot(
        [line_left, line_right],
        [y_pos - 0.04, y_pos - 0.04],
        transform=ax.transAxes,
        color=text_color_final,
        linewidth=line_width,
        zorder=11,
    )

    # --- COUNTRY NAME ---
    if text_config.get("show_country", True):
        ax.text(
            x_pos,
            y_pos - 0.04 - (0.025 if custom_subtitle else 0.04),
            display_country.upper(),
            transform=ax.transAxes,
            color=text_color_final,
            ha=ha,
            fontproperties=font_sub,
            zorder=11,
        )

    # --- COORDINATES ---
    if text_config.get("show_coords", True):
        coords_y = y_pos - (0.07 if text_config.get("show_country", True) else 0.04)
        coords_y -= 0.025 if custom_subtitle else 0.0

        # Use custom coords text or format based on preference
        if custom_coords_text:
            coords_text = custom_coords_text
        else:
            coords_text = format_coordinates(lat, lon, coords_format)

        ax.text(
            x_pos,
            coords_y,
            coords_text,
            transform=ax.transAxes,
            color=text_color_final,
            alpha=0.7,
            ha=ha,
            fontproperties=font_coords,
            zorder=11,
        )

    # --- ATTRIBUTION (bottom right) ---
    ax.text(
        0.98,
        0.02,
        "© OpenStreetMap contributors",
        transform=ax.transAxes,
        color=text_color_final,
        alpha=0.5,
        ha="right",
        va="bottom",
        fontproperties=font_attr,
        zorder=11,
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
