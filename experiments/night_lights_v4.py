"""
Night Lights Poster Generator - Experimental V4 (FINAL)
Full featured: Text overlay, color temperature, horizon glow, water reflections

Cycle 4: Final polished version with all features
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties
import osmnx as ox
from datetime import datetime
import random

OUTPUT_DIR = project_root / "experiments" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FONTS_DIR = project_root / "fonts"


def create_enhanced_glow(ax, lines, color, base_width, num_layers=8, max_alpha=0.9, zorder=5):
    """Create premium glow effect with smooth falloff."""
    if not lines:
        return

    # Outer soft glow
    for i in range(num_layers, 0, -1):
        layer_width = base_width * (1 + (i - 1) ** 1.2 * 0.5)
        # Gaussian-like falloff
        t = (num_layers - i) / num_layers
        layer_alpha = max_alpha * np.exp(-3 * (1 - t) ** 2) * 0.4

        lc = LineCollection(lines, linewidths=layer_width, colors=color, alpha=layer_alpha, zorder=zorder)
        ax.add_collection(lc)

    # Mid-bright layer
    lc_mid = LineCollection(lines, linewidths=base_width * 0.8, colors=color, alpha=max_alpha * 0.7, zorder=zorder + 1)
    ax.add_collection(lc_mid)

    # Bright core
    lc_bright = LineCollection(lines, linewidths=base_width * 0.4, colors=color, alpha=max_alpha * 0.9, zorder=zorder + 2)
    ax.add_collection(lc_bright)

    # White hot center
    lc_core = LineCollection(lines, linewidths=base_width * 0.15, colors='#FFFFF0', alpha=max_alpha, zorder=zorder + 3)
    ax.add_collection(lc_core)


def get_road_hierarchy_lines(G_proj, center_x, center_y):
    """Separate roads by hierarchy and distance from center for color temperature."""
    highways = {
        'major_inner': [], 'major_outer': [],
        'secondary_inner': [], 'secondary_outer': [],
        'minor_inner': [], 'minor_outer': []
    }

    # Calculate threshold for inner/outer (roughly 40% from center)
    nodes = ox.graph_to_gdfs(G_proj, edges=False)
    max_dist = max(
        abs(nodes['x'].max() - center_x),
        abs(nodes['y'].max() - center_y)
    ) * 0.4

    for u, v, data in G_proj.edges(data=True):
        highway = data.get('highway', 'residential')
        if isinstance(highway, list):
            highway = highway[0]

        if 'geometry' in data:
            coords = list(data['geometry'].coords)
            segments = [[coords[i], coords[i + 1]] for i in range(len(coords) - 1)]
        else:
            x1, y1 = G_proj.nodes[u]['x'], G_proj.nodes[u]['y']
            x2, y2 = G_proj.nodes[v]['x'], G_proj.nodes[v]['y']
            segments = [[(x1, y1), (x2, y2)]]

        # Calculate midpoint distance from center
        if segments:
            mid_x = (segments[0][0][0] + segments[0][1][0]) / 2
            mid_y = (segments[0][0][1] + segments[0][1][1]) / 2
            dist = np.sqrt((mid_x - center_x)**2 + (mid_y - center_y)**2)
            is_inner = dist < max_dist
        else:
            is_inner = True

        # Categorize
        if highway in ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link']:
            key = 'major_inner' if is_inner else 'major_outer'
        elif highway in ['secondary', 'secondary_link', 'tertiary', 'tertiary_link']:
            key = 'secondary_inner' if is_inner else 'secondary_outer'
        else:
            key = 'minor_inner' if is_inner else 'minor_outer'

        highways[key].extend(segments)

    return highways


def create_horizon_glow(ax, color='#1a2a50', intensity=0.3):
    """Create atmospheric horizon glow at the top."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]

    # Gradient from transparent to colored at top
    gradient = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((gradient, gradient))

    rgb = mcolors.to_rgb(color)
    colors = np.zeros((256, 4))
    for i in range(256):
        t = i / 255
        colors[i, 0] = rgb[0]
        colors[i, 1] = rgb[1]
        colors[i, 2] = rgb[2]
        colors[i, 3] = intensity * t ** 2  # Quadratic falloff

    cmap = mcolors.ListedColormap(colors)

    # Only top 30% of image
    y_start = ylim[0] + y_range * 0.7
    ax.imshow(
        gradient,
        extent=[xlim[0], xlim[1], y_start, ylim[1]],
        aspect='auto',
        cmap=cmap,
        zorder=12,
        origin='lower'
    )


def add_water_reflections(ax, water_gdf, roads_highways, center_x, center_y, zorder=1):
    """Add subtle light reflections on water."""
    if water_gdf is None or water_gdf.empty:
        return

    water_polys = water_gdf[water_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if water_polys.empty:
        return

    # First render water as dark
    water_polys.plot(
        ax=ax,
        facecolor='#020208',
        edgecolor='none',
        alpha=1.0,
        zorder=zorder
    )

    # Add reflection lines (simplified - just near roads)
    # This would need more complex geometry to be accurate
    # For now, add subtle ambient reflection
    reflection_color = '#FFB34720'  # Very transparent orange
    water_polys.plot(
        ax=ax,
        facecolor=reflection_color,
        edgecolor='none',
        alpha=0.15,
        zorder=zorder + 0.5
    )


def add_scattered_lights(ax, buildings_gdf, center_x, center_y, max_dist, zorder=8):
    """Add scattered window/building lights with color temperature variation."""
    if buildings_gdf is None or buildings_gdf.empty:
        return

    buildings_polys = buildings_gdf[buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]

    # Inner (downtown) colors - cooler/whiter
    inner_colors = ['#E8E8FF', '#D0E0FF', '#F0F0FF', '#FFFFFF', '#C8D8FF']
    # Outer (residential) colors - warmer
    outer_colors = ['#FFE4B5', '#FFEFD5', '#FFD700', '#FFA500', '#FFFACD']

    lights_x, lights_y, lights_c, lights_s = [], [], [], []

    for idx, row in buildings_polys.iterrows():
        try:
            bounds = row.geometry.bounds
            minx, miny, maxx, maxy = bounds

            if (maxx - minx) < 10 or (maxy - miny) < 10:
                continue

            # Distance from center
            bx = (minx + maxx) / 2
            by = (miny + maxy) / 2
            dist = np.sqrt((bx - center_x)**2 + (by - center_y)**2)
            is_inner = dist < max_dist * 0.4

            area = (maxx - minx) * (maxy - miny)
            num_lights = min(int(area / 400), 6)

            for _ in range(num_lights):
                px = random.uniform(minx + 2, maxx - 2)
                py = random.uniform(miny + 2, maxy - 2)

                from shapely.geometry import Point
                if row.geometry.contains(Point(px, py)):
                    lights_x.append(px)
                    lights_y.append(py)
                    lights_c.append(random.choice(inner_colors if is_inner else outer_colors))
                    lights_s.append(random.uniform(0.3, 1.5))

        except Exception:
            continue

    if lights_x:
        # Soft glow
        ax.scatter(lights_x, lights_y, c=lights_c, s=[s * 20 for s in lights_s],
                  alpha=0.15, zorder=zorder, marker='o')
        # Medium
        ax.scatter(lights_x, lights_y, c=lights_c, s=[s * 5 for s in lights_s],
                  alpha=0.4, zorder=zorder + 1, marker='o')
        # Core
        ax.scatter(lights_x, lights_y, c=lights_c, s=lights_s,
                  alpha=0.9, zorder=zorder + 2, marker='o')


def render_buildings_dark(ax, buildings_gdf, zorder=2):
    """Render buildings as dark silhouettes with subtle variation."""
    if buildings_gdf is None or buildings_gdf.empty:
        return

    buildings_polys = buildings_gdf[buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if buildings_polys.empty:
        return

    buildings_polys.plot(
        ax=ax,
        facecolor='#08080f',
        edgecolor='#101018',
        linewidth=0.08,
        alpha=0.97,
        zorder=zorder
    )


def render_parks_dark(ax, parks_gdf, zorder=1):
    """Render parks as very dark areas."""
    if parks_gdf is None or parks_gdf.empty:
        return

    parks_polys = parks_gdf[parks_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if parks_polys.empty:
        return

    parks_polys.plot(
        ax=ax,
        facecolor='#030306',
        edgecolor='none',
        alpha=0.95,
        zorder=zorder
    )


def add_text_overlay(ax, city_name, country_name, lat, lon):
    """Add stylized text overlay for night theme."""
    try:
        font_bold = FontProperties(fname=str(FONTS_DIR / "Raleway-Bold.ttf"))
        font_light = FontProperties(fname=str(FONTS_DIR / "Raleway-Light.ttf"))
    except Exception:
        font_bold = FontProperties(weight='bold')
        font_light = FontProperties(weight='light')

    # City name - large, spaced letters
    city_display = '  '.join(city_name.upper())

    ax.text(
        0.5, 0.08,
        city_display,
        transform=ax.transAxes,
        fontsize=32,
        fontproperties=font_bold,
        color='#FFFFFF',
        alpha=0.95,
        ha='center',
        va='bottom',
        zorder=20
    )

    # Decorative line
    ax.plot(
        [0.2, 0.8], [0.065, 0.065],
        color='#FFB347',
        alpha=0.7,
        linewidth=1.5,
        transform=ax.transAxes,
        zorder=20,
        solid_capstyle='round'
    )

    # Country
    if country_name:
        ax.text(
            0.5, 0.045,
            country_name.upper(),
            transform=ax.transAxes,
            fontsize=14,
            fontproperties=font_light,
            color='#CCCCCC',
            alpha=0.8,
            ha='center',
            va='bottom',
            zorder=20
        )

    # Coordinates
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    coords_text = f"{abs(lat):.4f}° {lat_dir}  /  {abs(lon):.4f}° {lon_dir}"

    ax.text(
        0.5, 0.025,
        coords_text,
        transform=ax.transAxes,
        fontsize=10,
        fontproperties=font_light,
        color='#888888',
        alpha=0.7,
        ha='center',
        va='bottom',
        zorder=20
    )


def generate_night_lights_v4(city_name="Manhattan, New York", distance=8000, country_name="USA"):
    """
    Generate Night Lights poster - Version 4 (FINAL)
    Full featured with text, color temperature, all effects
    """
    print(f"\n{'='*60}")
    print("NIGHT LIGHTS V4 - FINAL VERSION")
    print(f"{'='*60}")

    # Geocode
    print(f"Geocoding {city_name}...")
    location = ox.geocode(city_name)
    lat, lon = location
    print(f"  Coordinates: {lat:.4f}, {lon:.4f}")

    # Fetch all data
    print("Fetching street network...")
    G = ox.graph_from_point((lat, lon), dist=distance, dist_type="bbox", network_type="drive")
    G_proj = ox.project_graph(G)

    print("Fetching buildings...")
    try:
        buildings = ox.features_from_point((lat, lon), tags={'building': True}, dist=distance)
        buildings_proj = ox.projection.project_gdf(buildings)
    except Exception:
        buildings_proj = None

    print("Fetching water...")
    try:
        water = ox.features_from_point((lat, lon), tags={'natural': 'water', 'waterway': 'riverbank'}, dist=distance)
        water_proj = ox.projection.project_gdf(water)
    except Exception:
        water_proj = None

    print("Fetching parks...")
    try:
        parks = ox.features_from_point((lat, lon), tags={'leisure': 'park', 'landuse': 'grass'}, dist=distance)
        parks_proj = ox.projection.project_gdf(parks)
    except Exception:
        parks_proj = None

    # Create figure
    bg_color = '#040408'
    fig, ax = plt.subplots(figsize=(11.69, 16.54), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    ax.set_position((0, 0, 1, 1))
    ax.axis('off')

    # Set view limits
    nodes = ox.graph_to_gdfs(G_proj, edges=False)
    xmin, xmax = nodes['x'].min(), nodes['x'].max()
    ymin, ymax = nodes['y'].min(), nodes['y'].max()
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect('equal')

    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2
    max_dist = max(xmax - xmin, ymax - ymin) / 2

    # Render layers
    print("Rendering water with reflections...")
    add_water_reflections(ax, water_proj, None, center_x, center_y, zorder=1)

    print("Rendering parks...")
    render_parks_dark(ax, parks_proj, zorder=1)

    print("Rendering buildings...")
    render_buildings_dark(ax, buildings_proj, zorder=2)

    # Get roads with color temperature
    print("Processing roads with color temperature...")
    highways = get_road_hierarchy_lines(G_proj, center_x, center_y)

    # Color palette - inner (cool/white) and outer (warm/orange)
    colors_inner = {
        'major': '#FFEEDD',      # Warm white
        'secondary': '#FFE0C0',  # Slightly warmer
        'minor': '#FFD8A8'       # Light warm
    }
    colors_outer = {
        'major': '#FFB030',      # Bright orange
        'secondary': '#FF9020',  # Orange
        'minor': '#E07010'       # Deep amber
    }

    print("Rendering road glow with color temperature...")
    # Minor roads
    create_enhanced_glow(ax, highways['minor_outer'], colors_outer['minor'],
                        base_width=0.25, num_layers=5, max_alpha=0.45, zorder=3)
    create_enhanced_glow(ax, highways['minor_inner'], colors_inner['minor'],
                        base_width=0.25, num_layers=5, max_alpha=0.45, zorder=3)

    # Secondary roads
    create_enhanced_glow(ax, highways['secondary_outer'], colors_outer['secondary'],
                        base_width=0.45, num_layers=6, max_alpha=0.65, zorder=4)
    create_enhanced_glow(ax, highways['secondary_inner'], colors_inner['secondary'],
                        base_width=0.45, num_layers=6, max_alpha=0.65, zorder=4)

    # Major roads
    create_enhanced_glow(ax, highways['major_outer'], colors_outer['major'],
                        base_width=0.8, num_layers=8, max_alpha=0.9, zorder=5)
    create_enhanced_glow(ax, highways['major_inner'], colors_inner['major'],
                        base_width=0.8, num_layers=8, max_alpha=0.9, zorder=5)

    print("Adding window lights...")
    add_scattered_lights(ax, buildings_proj, center_x, center_y, max_dist, zorder=8)

    print("Adding horizon glow...")
    create_horizon_glow(ax, '#0a1530', intensity=0.25)

    print("Adding text overlay...")
    city_simple = city_name.split(',')[0].strip()
    add_text_overlay(ax, city_simple, country_name, lat, lon)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city_name.split(',')[0].lower().replace(' ', '_')
    output_path = OUTPUT_DIR / f"night_lights_v4_{city_slug}_{timestamp}.png"

    print(f"Saving to {output_path}...")
    fig.savefig(output_path, dpi=300, facecolor=bg_color, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    print(f"✓ Done! Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    # Generate for Manhattan
    generate_night_lights_v4("Manhattan, New York", 8000, "USA")
