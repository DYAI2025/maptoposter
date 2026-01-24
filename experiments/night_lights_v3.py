"""
Night Lights Poster Generator - Experimental V3
Improvements: Water, window lights, radial intensity, parks

Cycle 3: Water bodies, scattered window lights, radial brightness falloff
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
import osmnx as ox
from datetime import datetime
import random

OUTPUT_DIR = project_root / "experiments" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_glow_effect(ax, lines, color, base_width, num_layers=6, max_alpha=0.85, zorder=5):
    """Create enhanced glow effect."""
    if not lines:
        return

    for i in range(num_layers, 0, -1):
        layer_width = base_width * (1 + (i - 1) ** 1.3 * 0.4)
        layer_alpha = max_alpha * ((num_layers - i + 1) / num_layers) ** 2 * 0.35
        lc = LineCollection(lines, linewidths=layer_width, colors=color, alpha=layer_alpha, zorder=zorder)
        ax.add_collection(lc)

    lc_mid = LineCollection(lines, linewidths=base_width * 0.7, colors=color, alpha=max_alpha * 0.8, zorder=zorder + 1)
    ax.add_collection(lc_mid)

    lc_core = LineCollection(lines, linewidths=base_width * 0.25, colors='#FFFAF0', alpha=max_alpha, zorder=zorder + 2)
    ax.add_collection(lc_core)


def get_road_hierarchy_lines(G_proj):
    """Separate roads by hierarchy."""
    highways = {'major': [], 'secondary': [], 'minor': []}

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

        if highway in ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link']:
            highways['major'].extend(segments)
        elif highway in ['secondary', 'secondary_link', 'tertiary', 'tertiary_link']:
            highways['secondary'].extend(segments)
        else:
            highways['minor'].extend(segments)

    return highways


def create_radial_vignette(ax, center_x, center_y, radius, intensity=0.4):
    """Create radial vignette - darker at edges, brighter at center."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Create meshgrid
    x = np.linspace(xlim[0], xlim[1], 200)
    y = np.linspace(ylim[0], ylim[1], 200)
    X, Y = np.meshgrid(x, y)

    # Calculate distance from center
    dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
    dist_norm = dist / radius

    # Vignette mask - smooth falloff
    vignette = 1 - np.clip(dist_norm ** 1.5 * intensity, 0, 0.7)

    # Render as dark overlay where vignette < 1
    dark_overlay = np.zeros((*vignette.shape, 4))
    dark_overlay[:, :, 3] = (1 - vignette) * 0.6  # Alpha based on vignette

    ax.imshow(
        dark_overlay,
        extent=[xlim[0], xlim[1], ylim[0], ylim[1]],
        aspect='auto',
        zorder=15,
        origin='lower'
    )


def add_window_lights(ax, buildings_gdf, num_lights_per_building=3, zorder=8):
    """Add scattered window lights as tiny bright points."""
    if buildings_gdf is None or buildings_gdf.empty:
        return

    buildings_polys = buildings_gdf[buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]

    # Light colors - mix of warm and cool
    light_colors = ['#FFE4B5', '#FFF8DC', '#87CEEB', '#E0FFFF', '#FFEFD5', '#FFFACD']

    lights_x = []
    lights_y = []
    lights_c = []
    lights_s = []

    for idx, row in buildings_polys.iterrows():
        try:
            # Get building bounds
            bounds = row.geometry.bounds
            minx, miny, maxx, maxy = bounds

            # Skip very small buildings
            if (maxx - minx) < 10 or (maxy - miny) < 10:
                continue

            # Random number of lights based on building size
            area = (maxx - minx) * (maxy - miny)
            num_lights = min(int(area / 500), 5)

            for _ in range(num_lights):
                # Random position within building bounds
                px = random.uniform(minx + 2, maxx - 2)
                py = random.uniform(miny + 2, maxy - 2)

                # Check if point is inside building
                from shapely.geometry import Point
                if row.geometry.contains(Point(px, py)):
                    lights_x.append(px)
                    lights_y.append(py)
                    lights_c.append(random.choice(light_colors))
                    lights_s.append(random.uniform(0.5, 2))

        except Exception:
            continue

    # Plot lights as scatter
    if lights_x:
        # Glow layer
        ax.scatter(lights_x, lights_y, c=lights_c, s=[s * 15 for s in lights_s],
                  alpha=0.2, zorder=zorder, marker='o')
        # Core
        ax.scatter(lights_x, lights_y, c=lights_c, s=lights_s,
                  alpha=0.8, zorder=zorder + 1, marker='o')


def render_water_dark(ax, water_gdf, color='#030308', zorder=1):
    """Render water as very dark reflective surface."""
    if water_gdf is None or water_gdf.empty:
        return

    water_polys = water_gdf[water_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if water_polys.empty:
        return

    water_polys.plot(
        ax=ax,
        facecolor=color,
        edgecolor='none',
        alpha=1.0,
        zorder=zorder
    )


def render_parks_dark(ax, parks_gdf, color='#040408', zorder=1):
    """Render parks as very dark areas (no lights)."""
    if parks_gdf is None or parks_gdf.empty:
        return

    parks_polys = parks_gdf[parks_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if parks_polys.empty:
        return

    parks_polys.plot(
        ax=ax,
        facecolor=color,
        edgecolor='none',
        alpha=0.9,
        zorder=zorder
    )


def render_buildings_dark(ax, buildings_gdf, fill_color='#0a0a14', edge_color='#12121a', zorder=2):
    """Render buildings as dark silhouettes."""
    if buildings_gdf is None or buildings_gdf.empty:
        return

    buildings_polys = buildings_gdf[buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if buildings_polys.empty:
        return

    buildings_polys.plot(
        ax=ax,
        facecolor=fill_color,
        edgecolor=edge_color,
        linewidth=0.1,
        alpha=0.95,
        zorder=zorder
    )


def generate_night_lights_v3(city_name="Manhattan, New York", distance=8000):
    """
    Generate Night Lights poster - Version 3
    Added: Water, parks, window lights, radial vignette
    """
    print(f"\n{'='*60}")
    print("NIGHT LIGHTS V3 - Water, Windows & Vignette")
    print(f"{'='*60}")

    # Geocode
    print(f"Geocoding {city_name}...")
    location = ox.geocode(city_name)
    lat, lon = location
    print(f"  Coordinates: {lat:.4f}, {lon:.4f}")

    # Fetch data
    print("Fetching street network...")
    G = ox.graph_from_point((lat, lon), dist=distance, dist_type="bbox", network_type="drive")
    G_proj = ox.project_graph(G)

    print("Fetching buildings...")
    try:
        buildings = ox.features_from_point((lat, lon), tags={'building': True}, dist=distance)
        buildings_proj = ox.projection.project_gdf(buildings)
    except Exception as e:
        print(f"  Warning: {e}")
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
    bg_color = '#050510'
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
    radius = max(xmax - xmin, ymax - ymin) / 2

    # Render layers
    print("Rendering water...")
    render_water_dark(ax, water_proj, zorder=1)

    print("Rendering parks...")
    render_parks_dark(ax, parks_proj, zorder=1)

    print("Rendering buildings...")
    render_buildings_dark(ax, buildings_proj, zorder=2)

    # Get roads
    print("Processing roads...")
    highways = get_road_hierarchy_lines(G_proj)

    colors = {
        'major': '#FFB347',
        'secondary': '#FFA040',
        'minor': '#E08020'
    }

    print("Rendering road glow...")
    create_glow_effect(ax, highways['minor'], colors['minor'], base_width=0.3, num_layers=4, max_alpha=0.5, zorder=3)
    create_glow_effect(ax, highways['secondary'], colors['secondary'], base_width=0.5, num_layers=5, max_alpha=0.7, zorder=4)
    create_glow_effect(ax, highways['major'], colors['major'], base_width=0.9, num_layers=6, max_alpha=0.9, zorder=5)

    print("Adding window lights...")
    add_window_lights(ax, buildings_proj, zorder=8)

    print("Adding radial vignette...")
    create_radial_vignette(ax, center_x, center_y, radius, intensity=0.5)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city_name.split(',')[0].lower().replace(' ', '_')
    output_path = OUTPUT_DIR / f"night_lights_v3_{city_slug}_{timestamp}.png"

    print(f"Saving to {output_path}...")
    fig.savefig(output_path, dpi=300, facecolor=bg_color, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    print(f"✓ Done! Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    generate_night_lights_v3("Manhattan, New York", 8000)
