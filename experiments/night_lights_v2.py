"""
Night Lights Poster Generator - Experimental V2
Improvements: Buildings as dark silhouettes, atmospheric gradient, color variation

Cycle 2: Add buildings, atmosphere, and light color variation
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
import osmnx as ox
from datetime import datetime

OUTPUT_DIR = project_root / "experiments" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_glow_effect(ax, lines, color, base_width, num_layers=6, max_alpha=0.85, zorder=5):
    """Create enhanced glow effect with smoother falloff."""
    if not lines:
        return

    # Outer glow layers (wide, dim)
    for i in range(num_layers, 0, -1):
        # Exponential width increase for softer glow
        layer_width = base_width * (1 + (i - 1) ** 1.3 * 0.4)
        # Quadratic alpha falloff for realistic bloom
        layer_alpha = max_alpha * ((num_layers - i + 1) / num_layers) ** 2 * 0.35

        lc = LineCollection(lines, linewidths=layer_width, colors=color, alpha=layer_alpha, zorder=zorder)
        ax.add_collection(lc)

    # Bright core
    lc_mid = LineCollection(lines, linewidths=base_width * 0.7, colors=color, alpha=max_alpha * 0.8, zorder=zorder + 1)
    ax.add_collection(lc_mid)

    # Hot white center
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


def create_atmospheric_gradient(ax, bg_color='#050510', horizon_color='#1a2a4a'):
    """Create atmospheric gradient - darker at bottom, blue-ish at top horizon."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Create gradient from bottom (dark) to top (slightly blue horizon glow)
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    gradient = np.vstack((gradient, gradient))

    # Color mapping
    bg_rgb = mcolors.to_rgb(bg_color)
    horizon_rgb = mcolors.to_rgb(horizon_color)

    colors = np.zeros((256, 4))
    for i in range(256):
        t = i / 255
        # Non-linear blend - more dark at bottom
        t_adjusted = t ** 0.7
        colors[i, 0] = bg_rgb[0] + (horizon_rgb[0] - bg_rgb[0]) * t_adjusted
        colors[i, 1] = bg_rgb[1] + (horizon_rgb[1] - bg_rgb[1]) * t_adjusted
        colors[i, 2] = bg_rgb[2] + (horizon_rgb[2] - bg_rgb[2]) * t_adjusted
        colors[i, 3] = 0.4 * t_adjusted  # Subtle overlay

    cmap = mcolors.ListedColormap(colors)

    ax.imshow(
        gradient.T,
        extent=[xlim[0], xlim[1], ylim[0], ylim[1]],
        aspect='auto',
        cmap=cmap,
        zorder=0,
        origin='lower'
    )


def render_buildings_dark(ax, buildings_gdf, fill_color='#0a0a12', edge_color='#151520', zorder=2):
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
        alpha=0.9,
        zorder=zorder
    )


def generate_night_lights_v2(city_name="Manhattan, New York", distance=8000):
    """
    Generate Night Lights poster - Version 2
    Added: Buildings, atmospheric gradient, improved glow
    """
    print(f"\n{'='*60}")
    print("NIGHT LIGHTS V2 - Buildings & Atmosphere")
    print(f"{'='*60}")

    # Geocode
    print(f"Geocoding {city_name}...")
    location = ox.geocode(city_name)
    lat, lon = location
    print(f"  Coordinates: {lat:.4f}, {lon:.4f}")

    # Fetch data
    print(f"Fetching street network...")
    G = ox.graph_from_point((lat, lon), dist=distance, dist_type="bbox", network_type="drive")
    G_proj = ox.project_graph(G)

    print("Fetching buildings...")
    try:
        buildings = ox.features_from_point((lat, lon), tags={'building': True}, dist=distance)
        buildings_proj = ox.projection.project_gdf(buildings)
    except Exception as e:
        print(f"  Warning: Could not fetch buildings: {e}")
        buildings_proj = None

    # Create figure
    bg_color = '#050510'
    fig, ax = plt.subplots(figsize=(11.69, 16.54), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    ax.set_position((0, 0, 1, 1))
    ax.axis('off')

    # Set view limits first
    nodes = ox.graph_to_gdfs(G_proj, edges=False)
    ax.set_xlim(nodes['x'].min(), nodes['x'].max())
    ax.set_ylim(nodes['y'].min(), nodes['y'].max())
    ax.set_aspect('equal')

    # Add atmospheric gradient
    print("Adding atmospheric gradient...")
    create_atmospheric_gradient(ax, bg_color, '#1a2a4a')

    # Render buildings
    print("Rendering buildings...")
    render_buildings_dark(ax, buildings_proj, zorder=2)

    # Get road hierarchy
    print("Processing roads...")
    highways = get_road_hierarchy_lines(G_proj)

    # Night light colors - warm sodium with some variation
    colors = {
        'major': '#FFB347',      # Bright warm orange
        'secondary': '#FFA040',  # Orange
        'minor': '#E08020'       # Amber
    }

    # Render roads with glow
    print("Rendering glow effects...")

    # Minor roads
    create_glow_effect(ax, highways['minor'], colors['minor'],
                      base_width=0.3, num_layers=4, max_alpha=0.5, zorder=3)

    # Secondary roads
    create_glow_effect(ax, highways['secondary'], colors['secondary'],
                      base_width=0.5, num_layers=5, max_alpha=0.7, zorder=4)

    # Major roads - most intense
    create_glow_effect(ax, highways['major'], colors['major'],
                      base_width=0.9, num_layers=6, max_alpha=0.9, zorder=5)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city_name.split(',')[0].lower().replace(' ', '_')
    output_path = OUTPUT_DIR / f"night_lights_v2_{city_slug}_{timestamp}.png"

    print(f"Saving to {output_path}...")
    fig.savefig(output_path, dpi=300, facecolor=bg_color, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    print(f"✓ Done! Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    generate_night_lights_v2("Manhattan, New York", 8000)
