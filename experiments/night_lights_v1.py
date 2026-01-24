"""
Night Lights Poster Generator - Experimental V1
Simulates aerial night photography with glowing street lights.

Cycle 1: Basic glow effect with warm sodium light colors
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
import osmnx as ox
from datetime import datetime

# Configuration
TEST_CITY = "Manhattan, New York"
TEST_DISTANCE = 8000  # 8km radius
OUTPUT_DIR = project_root / "experiments" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_glow_effect(ax, lines, color, base_width, num_layers=5, max_alpha=0.8):
    """
    Create a glow effect by rendering multiple layers with decreasing alpha.

    Args:
        ax: Matplotlib axes
        lines: List of line coordinates [(x1,y1), (x2,y2), ...]
        color: Base color for the glow
        base_width: Width of the core line
        num_layers: Number of glow layers
        max_alpha: Maximum alpha for the core
    """
    # Render from outer (dim, wide) to inner (bright, narrow)
    for i in range(num_layers, 0, -1):
        layer_width = base_width * (1 + (i - 1) * 0.8)
        layer_alpha = max_alpha * (1 - (i - 1) / num_layers) * 0.5

        lc = LineCollection(lines, linewidths=layer_width, colors=color, alpha=layer_alpha)
        ax.add_collection(lc)

    # Core line (brightest)
    lc_core = LineCollection(lines, linewidths=base_width * 0.5, colors='white', alpha=max_alpha)
    ax.add_collection(lc_core)


def get_edge_lines(G_proj):
    """Extract edge geometries as line segments."""
    lines = []
    for u, v, data in G_proj.edges(data=True):
        if 'geometry' in data:
            coords = list(data['geometry'].coords)
            for i in range(len(coords) - 1):
                lines.append([coords[i], coords[i + 1]])
        else:
            x1 = G_proj.nodes[u]['x']
            y1 = G_proj.nodes[u]['y']
            x2 = G_proj.nodes[v]['x']
            y2 = G_proj.nodes[v]['y']
            lines.append([(x1, y1), (x2, y2)])
    return lines


def get_road_hierarchy_lines(G_proj):
    """Separate roads by hierarchy for different glow intensities."""
    highways_major = []  # motorway, trunk, primary
    highways_secondary = []  # secondary, tertiary
    highways_minor = []  # residential, others

    for u, v, data in G_proj.edges(data=True):
        highway = data.get('highway', 'residential')
        if isinstance(highway, list):
            highway = highway[0]

        # Get line geometry
        if 'geometry' in data:
            coords = list(data['geometry'].coords)
            segments = [[coords[i], coords[i + 1]] for i in range(len(coords) - 1)]
        else:
            x1, y1 = G_proj.nodes[u]['x'], G_proj.nodes[u]['y']
            x2, y2 = G_proj.nodes[v]['x'], G_proj.nodes[v]['y']
            segments = [[(x1, y1), (x2, y2)]]

        # Categorize by road type
        if highway in ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link']:
            highways_major.extend(segments)
        elif highway in ['secondary', 'secondary_link', 'tertiary', 'tertiary_link']:
            highways_secondary.extend(segments)
        else:
            highways_minor.extend(segments)

    return highways_major, highways_secondary, highways_minor


def generate_night_lights_v1(city_name="Manhattan, New York", distance=8000):
    """
    Generate Night Lights poster - Version 1
    Basic glow effect with warm colors.
    """
    print(f"\n{'='*60}")
    print("NIGHT LIGHTS V1 - Basic Glow Effect")
    print(f"{'='*60}")

    # Geocode
    print(f"Geocoding {city_name}...")
    location = ox.geocode(city_name)
    lat, lon = location
    print(f"  Coordinates: {lat:.4f}, {lon:.4f}")

    # Fetch street network
    print(f"Fetching street network (radius: {distance}m)...")
    G = ox.graph_from_point((lat, lon), dist=distance, dist_type="bbox", network_type="drive")
    G_proj = ox.project_graph(G)

    # Create figure with black background
    fig, ax = plt.subplots(figsize=(11.69, 16.54), facecolor='#0a0a0f')
    ax.set_facecolor('#0a0a0f')
    ax.set_position((0, 0, 1, 1))
    ax.axis('off')

    # Get road hierarchy
    print("Processing road hierarchy...")
    major, secondary, minor = get_road_hierarchy_lines(G_proj)

    # Color palette - warm sodium lights
    color_major = '#FFB347'      # Bright orange
    color_secondary = '#FFA500'  # Orange
    color_minor = '#CC8800'      # Darker orange/amber

    # Render roads with glow effect (order: minor -> secondary -> major)
    print("Rendering glow effects...")

    # Minor roads - subtle glow
    if minor:
        create_glow_effect(ax, minor, color_minor, base_width=0.3, num_layers=3, max_alpha=0.4)

    # Secondary roads - medium glow
    if secondary:
        create_glow_effect(ax, secondary, color_secondary, base_width=0.5, num_layers=4, max_alpha=0.6)

    # Major roads - intense glow
    if major:
        create_glow_effect(ax, major, color_major, base_width=0.8, num_layers=5, max_alpha=0.9)

    # Set view limits
    nodes = ox.graph_to_gdfs(G_proj, edges=False)
    ax.set_xlim(nodes['x'].min(), nodes['x'].max())
    ax.set_ylim(nodes['y'].min(), nodes['y'].max())
    ax.set_aspect('equal')

    # Add subtle vignette effect (darker at edges)
    # Create radial gradient overlay
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city_name.split(',')[0].lower().replace(' ', '_')
    output_path = OUTPUT_DIR / f"night_lights_v1_{city_slug}_{timestamp}.png"

    print(f"Saving to {output_path}...")
    fig.savefig(output_path, dpi=300, facecolor='#0a0a0f', bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    print(f"✓ Done! Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    # Test with Manhattan
    generate_night_lights_v1("Manhattan, New York", 8000)
