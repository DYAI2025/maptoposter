"""
Poster generator module - core rendering engine for CityMaps.

Handles map data fetching, layer rendering, and poster generation.
Extracted and refactored from create_map_poster.py.
"""

import json
import time
from pathlib import Path
from typing import cast
from datetime import datetime

import numpy as np

# Setup matplotlib backend before importing pyplot
import sys
import os
# Add the project root to the path to import the fix
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
import fix_matplotlib_backend

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
import osmnx as ox
from networkx import MultiDiGraph
from geopandas import GeoDataFrame
from tqdm import tqdm
import random

from .config import (
    THEMES_DIR,
    FONTS_DIR,
    POSTERS_DIR,
    PAPER_SIZES,
    DEFAULT_THEME,
    DEFAULT_FONT,
    DEFAULT_FACECOLOR,
    OUTPUT_DPI,
    PREVIEW_DPI,
    DEFAULT_THEME_COLORS,
    ROAD_HIERARCHY,
    DETAIL_LAYER_TAGS,
    LAYER_ZORDER,
    DETAIL_LAYER_LINEWIDTHS,
    LAYER_ZOOM_THRESHOLDS,
)
from .geocoding import cache_get, cache_set, CacheError
from .text_positioning import apply_text_overlay, load_fonts


# ============================================================================
# NIGHT LIGHTS HELPER FUNCTIONS
# ============================================================================

def create_glow_effect(ax, lines, color, base_width, num_layers=8, max_alpha=0.9, zorder=5):
    """Create realistic glow effect for night lights mode."""
    if not lines:
        return

    # Outer soft glow layers
    for i in range(num_layers, 0, -1):
        layer_width = base_width * (1 + (i - 1) ** 1.2 * 0.5)
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


def get_night_road_lines(G_proj, center_x, center_y):
    """Separate roads by hierarchy and distance from center for color temperature."""
    highways = {
        'major_inner': [], 'major_outer': [],
        'secondary_inner': [], 'secondary_outer': [],
        'minor_inner': [], 'minor_outer': []
    }

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

        if segments:
            mid_x = (segments[0][0][0] + segments[0][1][0]) / 2
            mid_y = (segments[0][0][1] + segments[0][1][1]) / 2
            dist = np.sqrt((mid_x - center_x)**2 + (mid_y - center_y)**2)
            is_inner = dist < max_dist
        else:
            is_inner = True

        if highway in ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link']:
            key = 'major_inner' if is_inner else 'major_outer'
        elif highway in ['secondary', 'secondary_link', 'tertiary', 'tertiary_link']:
            key = 'secondary_inner' if is_inner else 'secondary_outer'
        else:
            key = 'minor_inner' if is_inner else 'minor_outer'

        highways[key].extend(segments)

    return highways


def add_window_lights(ax, buildings_gdf, center_x, center_y, max_dist, theme, zorder=8):
    """Add scattered window lights with color temperature variation."""
    if buildings_gdf is None or buildings_gdf.empty:
        return

    buildings_polys = buildings_gdf[buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]

    inner_colors = theme.get('window_lights_inner', ['#E8E8FF', '#D0E0FF', '#F0F0FF', '#FFFFFF'])
    outer_colors = theme.get('window_lights_outer', ['#FFE4B5', '#FFEFD5', '#FFD700', '#FFA500'])

    lights_x, lights_y, lights_c, lights_s = [], [], [], []

    for idx, row in buildings_polys.iterrows():
        try:
            bounds = row.geometry.bounds
            minx, miny, maxx, maxy = bounds

            if (maxx - minx) < 10 or (maxy - miny) < 10:
                continue

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
        ax.scatter(lights_x, lights_y, c=lights_c, s=[s * 20 for s in lights_s], alpha=0.15, zorder=zorder, marker='o')
        ax.scatter(lights_x, lights_y, c=lights_c, s=[s * 5 for s in lights_s], alpha=0.4, zorder=zorder + 1, marker='o')
        ax.scatter(lights_x, lights_y, c=lights_c, s=lights_s, alpha=0.9, zorder=zorder + 2, marker='o')


def create_horizon_glow(ax, color='#0a1530', intensity=0.25):
    """Create atmospheric horizon glow at the top."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]

    gradient = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((gradient, gradient))

    rgb = mcolors.to_rgb(color)
    colors = np.zeros((256, 4))
    for i in range(256):
        t = i / 255
        colors[i, 0] = rgb[0]
        colors[i, 1] = rgb[1]
        colors[i, 2] = rgb[2]
        colors[i, 3] = intensity * t ** 2

    cmap = mcolors.ListedColormap(colors)

    y_start = ylim[0] + y_range * 0.7
    ax.imshow(gradient, extent=[xlim[0], xlim[1], y_start, ylim[1]], aspect='auto', cmap=cmap, zorder=12, origin='lower')


# ============================================================================
# HOLONIGHT HELPER FUNCTIONS
# ============================================================================

def create_holonight_glow(ax, lines, color, inner_color, base_width, num_layers=10, max_alpha=1.0, glow_falloff=1.5, zorder=5):
    """Create intense neon glow effect for holonight mode with white-hot center."""
    if not lines:
        return

    # Outer glow layers - wide and soft
    for i in range(num_layers, 0, -1):
        layer_width = base_width * (1 + (i - 1) ** glow_falloff * 0.6)
        t = (num_layers - i) / num_layers
        layer_alpha = max_alpha * np.exp(-4 * (1 - t) ** 2) * 0.35
        lc = LineCollection(lines, linewidths=layer_width, colors=color, alpha=layer_alpha, zorder=zorder)
        ax.add_collection(lc)

    # Mid-bright layer
    lc_mid = LineCollection(lines, linewidths=base_width * 0.9, colors=color, alpha=max_alpha * 0.75, zorder=zorder + 1)
    ax.add_collection(lc_mid)

    # Bright core
    lc_bright = LineCollection(lines, linewidths=base_width * 0.5, colors=inner_color, alpha=max_alpha * 0.85, zorder=zorder + 2)
    ax.add_collection(lc_bright)

    # White hot center
    lc_core = LineCollection(lines, linewidths=base_width * 0.15, colors='#FFFFFF', alpha=max_alpha, zorder=zorder + 3)
    ax.add_collection(lc_core)


def get_holonight_road_lines(G_proj):
    """Separate roads by hierarchy for holonight mode."""
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


def add_intersection_glows(ax, G_proj, theme, zorder=9):
    """Add glowing points at major intersections."""
    if not theme.get('render_intersections', False):
        return

    glow_color = theme.get('intersection_glow', '#00FFFF')
    inner_color = theme.get('intersection_glow_inner', '#FFFFFF')
    base_size = theme.get('intersection_size', 2.5)

    # Find nodes with high degree (intersections)
    nodes_x, nodes_y, sizes = [], [], []

    for node, degree in G_proj.degree():
        if degree >= 3:  # 3+ connections = intersection
            node_data = G_proj.nodes[node]
            nodes_x.append(node_data['x'])
            nodes_y.append(node_data['y'])
            # Size based on degree
            size_factor = min(degree / 4, 2.5)
            sizes.append(base_size * size_factor)

    if not nodes_x:
        return

    # Outer glow
    ax.scatter(nodes_x, nodes_y, c=glow_color, s=[s * 40 for s in sizes], alpha=0.15, zorder=zorder, marker='o')
    ax.scatter(nodes_x, nodes_y, c=glow_color, s=[s * 15 for s in sizes], alpha=0.35, zorder=zorder + 1, marker='o')
    # Inner glow
    ax.scatter(nodes_x, nodes_y, c=inner_color, s=[s * 5 for s in sizes], alpha=0.6, zorder=zorder + 2, marker='o')
    # Core
    ax.scatter(nodes_x, nodes_y, c='#FFFFFF', s=sizes, alpha=0.9, zorder=zorder + 3, marker='o')


def create_radial_vignette(ax, center_x, center_y, radius, intensity=0.3):
    """Create subtle radial vignette - darker at edges."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    x = np.linspace(xlim[0], xlim[1], 150)
    y = np.linspace(ylim[0], ylim[1], 150)
    X, Y = np.meshgrid(x, y)

    dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
    dist_norm = dist / radius

    vignette = 1 - np.clip(dist_norm ** 2 * intensity, 0, 0.6)
    dark_overlay = np.zeros((*vignette.shape, 4))
    dark_overlay[:, :, 3] = (1 - vignette) * 0.5

    ax.imshow(dark_overlay, extent=[xlim[0], xlim[1], ylim[0], ylim[1]], aspect='auto', zorder=15, origin='lower')


# ============================================================================
# KANDINCITY HELPER FUNCTIONS
# ============================================================================

def get_block_color(theme, seed_value):
    """Get a weighted random color for a building block based on theme palette."""
    block_colors = theme.get('block_colors', ['#E8642C', '#3C4654', '#8B8860'])
    weights = theme.get('block_color_weights', None)

    if weights and len(weights) == len(block_colors):
        # Use seeded random for consistent coloring
        rng = random.Random(seed_value)
        return rng.choices(block_colors, weights=weights, k=1)[0]
    else:
        rng = random.Random(seed_value)
        return rng.choice(block_colors)


def render_kandinsky_buildings(ax, buildings_gdf, theme, zorder=3):
    """Render buildings as Kandinsky-style colored blocks."""
    if buildings_gdf is None or buildings_gdf.empty:
        return

    buildings_polys = buildings_gdf[buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    if buildings_polys.empty:
        return

    edge_color = theme.get('buildings_edge', '#1A1A1A')
    edge_width = theme.get('building_edge_width', 0.3)

    for idx, row in buildings_polys.iterrows():
        try:
            # Use geometry hash as seed for consistent color
            geom_hash = hash(row.geometry.wkt) % 1000000
            fill_color = get_block_color(theme, geom_hash)

            from geopandas import GeoSeries
            gs = GeoSeries([row.geometry], crs=buildings_polys.crs)
            gs.plot(
                ax=ax,
                facecolor=fill_color,
                edgecolor=edge_color,
                linewidth=edge_width,
                alpha=1.0,
                zorder=zorder
            )
        except Exception:
            continue


class PosterGenerator:
    """
    Main class for generating map posters.

    Handles theme loading, data fetching, rendering, and file output.
    """

    def __init__(self, theme_name: str = DEFAULT_THEME, font_id: str = DEFAULT_FONT):
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

    @staticmethod
    def load_theme(theme_name: str) -> dict:
        """
        Load theme from JSON file or return default.

        Args:
            theme_name: Name of theme (without .json)

        Returns:
            Dict with theme color definitions
        """
        theme_file = THEMES_DIR / f"{theme_name}.json"

        if not theme_file.exists():
            print(f"⚠ Theme '{theme_name}' not found. Using default theme.")
            return DEFAULT_THEME_COLORS

        try:
            with open(theme_file, "r") as f:
                theme = json.load(f)
                name = theme.get("name", theme_name)
                desc = theme.get("description", "")
                print(f"✓ Loaded theme: {name}")
                if desc:
                    print(f"  {desc}")
                return theme
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠ Error loading theme: {e}. Using default.")
            return DEFAULT_THEME_COLORS

    @staticmethod
    def get_available_themes() -> list[str]:
        """
        Get list of available theme names.

        Returns:
            List of theme names (sorted)
        """
        THEMES_DIR.mkdir(exist_ok=True)

        themes = []
        for file in sorted(THEMES_DIR.iterdir()):
            if file.suffix == ".json":
                themes.append(file.stem)

        return themes

    def get_edge_colors_by_type(self, G: MultiDiGraph) -> list[str]:
        """
        Assign colors to edges based on road type hierarchy.

        Args:
            G: NetworkX MultiDiGraph

        Returns:
            List of color hex strings
        """
        edge_colors = []

        for u, v, data in G.edges(data=True):
            highway = data.get("highway", "unclassified")

            # Handle list of highway types
            if isinstance(highway, list):
                highway = highway[0] if highway else "unclassified"

            # Look up color in hierarchy
            if highway in ROAD_HIERARCHY:
                color_key, _ = ROAD_HIERARCHY[highway]
                color = self.theme.get(color_key, self.theme["road_default"])
            else:
                color = self.theme.get("road_default", "#CCCCCC")

            edge_colors.append(color)

        return edge_colors

    def get_edge_widths_by_type(self, G: MultiDiGraph) -> list[float]:
        """
        Assign line widths to edges based on road type.

        Args:
            G: NetworkX MultiDiGraph

        Returns:
            List of width values
        """
        edge_widths = []

        for u, v, data in G.edges(data=True):
            highway = data.get("highway", "unclassified")

            # Handle list of highway types
            if isinstance(highway, list):
                highway = highway[0] if highway else "unclassified"

            # Look up width in hierarchy
            if highway in ROAD_HIERARCHY:
                _, width = ROAD_HIERARCHY[highway]
            else:
                width = 0.4

            edge_widths.append(width)

        return edge_widths

    @staticmethod
    def get_crop_limits(
        G: MultiDiGraph, fig: Figure
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """
        Determine cropping limits to maintain figure aspect ratio.

        Args:
            G: NetworkX MultiDiGraph with nodes
            fig: Matplotlib Figure object

        Returns:
            Tuple of ((x_min, x_max), (y_min, y_max)) crop limits
        """
        # Get node extents
        xs = [data["x"] for _, data in G.nodes(data=True)]
        ys = [data["y"] for _, data in G.nodes(data=True)]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        x_range = maxx - minx
        y_range = maxy - miny

        # Get figure aspect ratio
        fig_width, fig_height = fig.get_size_inches()
        desired_aspect = fig_width / fig_height
        current_aspect = x_range / y_range

        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2

        # Crop to match aspect ratio
        if current_aspect > desired_aspect:
            # Too wide, crop horizontally
            desired_x_range = y_range * desired_aspect
            new_minx = center_x - desired_x_range / 2
            new_maxx = center_x + desired_x_range / 2
            crop_xlim = (new_minx, new_maxx)
            crop_ylim = (miny, maxy)
        elif current_aspect < desired_aspect:
            # Too tall, crop vertically
            desired_y_range = x_range / desired_aspect
            new_miny = center_y - desired_y_range / 2
            new_maxy = center_y + desired_y_range / 2
            crop_xlim = (minx, maxx)
            crop_ylim = (new_miny, new_maxy)
        else:
            # Perfect aspect ratio
            crop_xlim = (minx, maxx)
            crop_ylim = (miny, maxy)

        return crop_xlim, crop_ylim

    @staticmethod
    def create_gradient_fade(ax, color: str, location: str = "bottom", zorder: int = 10) -> None:
        """
        Create fade gradient effect at top or bottom of map.

        Args:
            ax: Matplotlib axes object
            color: Hex color string for gradient
            location: 'top' or 'bottom'
            zorder: Z-order for rendering
        """
        vals = np.linspace(0, 1, 256).reshape(-1, 1)
        gradient = np.hstack((vals, vals))

        rgb = mcolors.to_rgb(color)
        my_colors = np.zeros((256, 4))
        my_colors[:, 0] = rgb[0]
        my_colors[:, 1] = rgb[1]
        my_colors[:, 2] = rgb[2]

        if location == "bottom":
            my_colors[:, 3] = np.linspace(1, 0, 256)
            extent_y_start = 0
            extent_y_end = 0.25
        else:
            my_colors[:, 3] = np.linspace(0, 1, 256)
            extent_y_start = 0.75
            extent_y_end = 1.0

        custom_cmap = mcolors.ListedColormap(my_colors)

        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        y_range = ylim[1] - ylim[0]

        y_bottom = ylim[0] + y_range * extent_y_start
        y_top = ylim[0] + y_range * extent_y_end

        ax.imshow(
            gradient,
            extent=[xlim[0], xlim[1], y_bottom, y_top],
            aspect="auto",
            cmap=custom_cmap,
            zorder=zorder,
            origin="lower",
        )

    @staticmethod
    def fetch_graph(point: tuple[float, float], dist: int) -> MultiDiGraph | None:
        """
        Fetch street network graph from OSM via OSMnx.

        Uses cache to avoid repeated API calls.

        Args:
            point: (lat, lon) tuple
            dist: Distance in meters

        Returns:
            MultiDiGraph or None if fetch fails
        """
        lat, lon = point
        cache_key = f"graph_{lat}_{lon}_{dist}"
        cached = cache_get(cache_key)

        if cached is not None:
            print("✓ Using cached street network")
            return cast(MultiDiGraph, cached)

        try:
            print(f"Fetching street network (radius: {dist}m)...")
            G = ox.graph_from_point(point, dist=dist, dist_type="bbox", network_type="all")
            time.sleep(0.5)

            try:
                cache_set(cache_key, G)
            except CacheError as e:
                print(f"⚠ {e}")

            return G

        except Exception as e:
            print(f"⚠ OSMnx error: {e}")
            return None

    @staticmethod
    def fetch_features(
        point: tuple[float, float], dist: int, tags: dict, name: str
    ) -> GeoDataFrame | None:
        """
        Fetch features (water, parks) from OSM via OSMnx.

        Uses cache to avoid repeated API calls.

        Args:
            point: (lat, lon) tuple
            dist: Distance in meters
            tags: OSM tags dict (e.g., {'natural': 'water'})
            name: Feature name for caching

        Returns:
            GeoDataFrame or None if fetch fails
        """
        lat, lon = point
        tag_str = "_".join(tags.keys())
        cache_key = f"{name}_{lat}_{lon}_{dist}_{tag_str}"
        cached = cache_get(cache_key)

        if cached is not None:
            print(f"✓ Using cached {name}")
            return cast(GeoDataFrame, cached)

        try:
            print(f"Fetching {name} features (radius: {dist}m)...")
            data = ox.features_from_point(point, tags=tags, dist=dist)
            time.sleep(0.3)

            try:
                cache_set(cache_key, data)
            except CacheError as e:
                print(f"⚠ {e}")

            return data

        except Exception as e:
            print(f"⚠ OSMnx error fetching {name}: {e}")
            return None

    def fetch_buildings(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch building footprints from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["buildings"], "buildings"
        )

    def fetch_paths(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch paths/tracks from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["paths"], "paths"
        )

    def fetch_landscape(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch landscape features (farmland, forests, meadows) from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["landscape"], "landscape"
        )

    def fetch_waterways(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch waterways (streams, rivers, canals) from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["waterways"], "waterways"
        )

    def fetch_railways(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch railways (train tracks, tram lines) from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["railways"], "railways"
        )

    def fetch_hedges(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch hedges/barriers (hedges, fences, walls) from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["hedges"], "hedges"
        )

    def fetch_leisure(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch leisure areas (sports, playgrounds, gardens) from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["leisure"], "leisure"
        )

    def fetch_amenities(
        self, point: tuple[float, float], dist: int
    ) -> GeoDataFrame | None:
        """Fetch amenities (churches, schools, cemeteries) from OSM."""
        return self.fetch_features(
            point, dist, DETAIL_LAYER_TAGS["amenities"], "amenities"
        )

    @staticmethod
    def get_layer_defaults(distance_m: int) -> dict:
        """
        Get default layer visibility based on zoom level.

        Args:
            distance_m: Map radius in meters

        Returns:
            Dict with layer visibility booleans
        """
        # All available detail layers
        all_layers = {
            "buildings": False,
            "paths": False,
            "landscape": False,
            "waterways": False,
            "railways": False,
            "hedges": False,
            "leisure": False,
            "amenities": False,
            "forests": False,
            "farmland": False,
            "meadows": False,
            "beaches": False,
            "sand": False,
            "grass": False,
            "retail": False,
            "industrial": False,
            "residential": False,
            "commercial": False,
            "parking": False,
            "sports_pitches": False,
            "golf_courses": False,
            "airports": False,
            "heliports": False,
            "runways": False,
            "taxiways": False,
            "aeroways": False,
            "bridges": False,
            "tunnels": False,
            "fords": False,
            "piers": False,
            "docks": False,
            "marinas": False,
            "breakwaters": False,
            "groynes": False,
            "weirs": False,
            "dams": False,
            "locks": False,
            "canals": False,
            "rivers": False,
            "streams": False,
            "lakes": False,
            "reservoirs": False,
            "ponds": False,
            "swimming_pools": False,
            "fountains": False,
            "water_towers": False,
            "water_works": False,
            "power_plants": False,
            "substations": False,
            "wind_turbines": False,
            "solar_panels": False,
            "quarries": False,
            "mines": False,
            "landfills": False,
            "wastewater_plants": False,
            "sewage_treatment_plants": False,
            "cemeteries": False,
            "churches": False,
            "mosques": False,
            "synagogues": False,
            "temples": False,
            "shrines": False,
            "monuments": False,
            "memorials": False,
            "statues": False,
            "artwork": False,
            "benches": False,
            "street_lamps": False,
            "waste_baskets": False,
            "post_boxes": False,
            "fire_hydrants": False,
            "telecom_masts": False,
            "communication_towers": False,
        }

        if distance_m <= LAYER_ZOOM_THRESHOLDS["all_on"]:
            # Village zoom (<=2km): all layers on
            return {k: True for k in all_layers}
        elif distance_m <= LAYER_ZOOM_THRESHOLDS["buildings_only"]:
            # Town zoom (<=8km): buildings, waterways, railways
            all_layers["buildings"] = True
            all_layers["waterways"] = True
            all_layers["railways"] = True
            all_layers["leisure"] = True
            all_layers["amenities"] = True
            all_layers["forests"] = True
            all_layers["meadows"] = True
            all_layers["grass"] = True
            all_layers["retail"] = True
            all_layers["residential"] = True
            all_layers["commercial"] = True
            all_layers["parking"] = True
            all_layers["sports_pitches"] = True
            all_layers["golf_courses"] = True
            all_layers["cemeteries"] = True
            all_layers["churches"] = True
            all_layers["mosques"] = True
            all_layers["synagogues"] = True
            all_layers["temples"] = True
            all_layers["shrines"] = True
            all_layers["monuments"] = True
            all_layers["memorials"] = True
            all_layers["statues"] = True
            all_layers["artwork"] = True
            all_layers["benches"] = True
            all_layers["street_lamps"] = True
            all_layers["waste_baskets"] = True
            all_layers["post_boxes"] = True
            all_layers["fire_hydrants"] = True
            all_layers["telecom_masts"] = True
            all_layers["communication_towers"] = True
            return all_layers
        elif distance_m <= LAYER_ZOOM_THRESHOLDS["water_rail_only"]:
            # City zoom (<=16km): waterways, railways, airports, industrial, power plants
            all_layers["waterways"] = True
            all_layers["railways"] = True
            all_layers["airports"] = True
            all_layers["industrial"] = True
            all_layers["power_plants"] = True
            all_layers["substations"] = True
            all_layers["wind_turbines"] = True
            all_layers["solar_panels"] = True
            all_layers["quarries"] = True
            all_layers["mines"] = True
            all_layers["landfills"] = True
            all_layers["wastewater_plants"] = True
            all_layers["sewage_treatment_plants"] = True
            return all_layers
        else:
            # Regional zoom (>16km): only major water and transport features
            all_layers["waterways"] = True
            all_layers["railways"] = True
            all_layers["airports"] = True
            all_layers["rivers"] = True
            all_layers["lakes"] = True
            all_layers["reservoirs"] = True
            all_layers["canals"] = True
            return all_layers

    def get_layer_color(self, layer_key: str, fallback_key: str = None) -> str:
        """

        Args:
            layer_key: Primary key to look up
            fallback_key: Fallback key if primary not found

        Returns:
            Hex color string
        """
        if layer_key in self.theme:
            return self.theme[layer_key]
        if fallback_key and fallback_key in self.theme:
            # Use fallback with slight modification
            return self.theme[fallback_key]
        # Ultimate fallback: derive from background
        bg = self.theme.get("bg", "#FFFFFF")
        return bg  # Will be handled by rendering code

    def generate_poster(
        self,
        lat: float,
        lon: float,
        city_name: str,
        country_name: str,
        paper_size: str = "A4",
        distance: int = 8000,
        dpi: int = None,
        text_position: dict = None,
        layers: dict = None,
    ) -> Figure:
        """
        Generate map poster as matplotlib Figure.

        Args:
            lat: Latitude
            lon: Longitude
            city_name: City name
            country_name: Country name
            paper_size: Paper format ('A2', 'A3', 'A4', 'A5')
            distance: Map radius in meters
            dpi: DPI for rendering (used for preview vs final)
            text_position: Text positioning config dict
            layers: Optional dict with layer visibility:
                    {"buildings": bool, "paths": bool, "landscape": bool}
                    If None, uses zoom-dependent defaults.

        Returns:
            Matplotlib Figure object (not saved)
        """
        # Set layer defaults based on zoom if not provided
        if layers is None:
            layers = self.get_layer_defaults(distance)
        point = (lat, lon)

        print(f"\nGenerating map for {city_name}, {country_name}...")

        # Validate paper size
        if paper_size not in PAPER_SIZES:
            print(f"⚠ Unknown paper size '{paper_size}'. Using A4.")
            paper_size = "A4"

        fig_width, fig_height = PAPER_SIZES[paper_size]

        # Calculate fetch steps based on enabled layers
        fetch_steps = 3  # Base: streets, water, parks
        for layer_name in ["buildings", "paths", "landscape", "waterways", "railways", "hedges", "leisure", "amenities"]:
            if layers.get(layer_name):
                fetch_steps += 1

        # Fetch map data - initialize all layer variables
        buildings = None
        paths = None
        landscape = None
        waterways = None
        railways = None
        hedges = None
        leisure = None
        amenities = None

        with tqdm(
            total=fetch_steps,
            desc="Fetching map data",
            unit="step",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
        ) as pbar:
            pbar.set_description("Downloading street network")
            G = self.fetch_graph(point, distance)
            if G is None:
                raise RuntimeError("Failed to retrieve street network data.")
            pbar.update(1)

            pbar.set_description("Downloading water features")
            water = self.fetch_features(
                point,
                distance,
                {"natural": "water", "waterway": "riverbank"},
                "water",
            )
            pbar.update(1)

            pbar.set_description("Downloading parks/green spaces")
            parks = self.fetch_features(
                point,
                distance,
                {"leisure": "park", "landuse": "grass"},
                "parks",
            )
            pbar.update(1)

            # Fetch detail layers if enabled
            if layers.get("landscape"):
                pbar.set_description("Downloading landscape features")
                landscape = self.fetch_landscape(point, distance)
                pbar.update(1)

            if layers.get("buildings"):
                pbar.set_description("Downloading building footprints")
                buildings = self.fetch_buildings(point, distance)
                pbar.update(1)

            if layers.get("paths"):
                pbar.set_description("Downloading paths/tracks")
                paths = self.fetch_paths(point, distance)
                pbar.update(1)

            if layers.get("waterways"):
                pbar.set_description("Downloading waterways")
                waterways = self.fetch_waterways(point, distance)
                pbar.update(1)

            if layers.get("railways"):
                pbar.set_description("Downloading railways")
                railways = self.fetch_railways(point, distance)
                pbar.update(1)

            if layers.get("hedges"):
                pbar.set_description("Downloading hedges/barriers")
                hedges = self.fetch_hedges(point, distance)
                pbar.update(1)

            if layers.get("leisure"):
                pbar.set_description("Downloading leisure areas")
                leisure = self.fetch_leisure(point, distance)
                pbar.update(1)

            if layers.get("amenities"):
                pbar.set_description("Downloading amenities")
                amenities = self.fetch_amenities(point, distance)
                pbar.update(1)

        print("✓ All data retrieved successfully!")

        # Project graph to metric CRS
        G_proj = ox.project_graph(G)

        # Check for special rendering modes
        render_mode = self.theme.get("mode", "standard")

        if render_mode == "night_lights":
            # ================================================================
            # NIGHT LIGHTS RENDERING MODE
            # ================================================================
            return self._render_night_lights(
                G_proj, water, parks, buildings, lat, lon,
                city_name, country_name, paper_size, distance, dpi, text_position
            )

        if render_mode == "holonight":
            # ================================================================
            # HOLONIGHT RENDERING MODE
            # ================================================================
            return self._render_holonight(
                G_proj, water, parks, buildings, lat, lon,
                city_name, country_name, paper_size, distance, dpi, text_position
            )

        if render_mode == "kandincity":
            # ================================================================
            # KANDINCITY RENDERING MODE
            # ================================================================
            return self._render_kandincity(
                G_proj, water, parks, buildings, lat, lon,
                city_name, country_name, paper_size, distance, dpi, text_position
            )

        # ================================================================
        # STANDARD RENDERING MODE
        # ================================================================
        # Create figure
        print("Rendering map...")
        fig, ax = plt.subplots(
            figsize=(fig_width, fig_height),
            facecolor=self.theme["bg"],
            dpi=dpi or PREVIEW_DPI,
        )
        ax.set_facecolor(self.theme["bg"])
        ax.set_position((0.0, 0.0, 1.0, 1.0))
        ax.axis("off")

        # Render landscape features (z=0, beneath everything)
        if landscape is not None and not landscape.empty:
            landscape_polys = landscape[
                landscape.geometry.type.isin(["Polygon", "MultiPolygon"])
            ]
            if not landscape_polys.empty:
                try:
                    landscape_polys = ox.projection.project_gdf(landscape_polys)
                except Exception:
                    landscape_polys = landscape_polys.to_crs(G_proj.graph["crs"])

                # Render different landscape types with different colors
                for idx, row in landscape_polys.iterrows():
                    landuse = row.get("landuse", None)
                    natural = row.get("natural", None)

                    # Determine color based on feature type
                    if landuse == "farmland":
                        color = self.get_layer_color("farmland", "parks")
                    elif landuse == "meadow" or natural == "grassland":
                        color = self.get_layer_color("meadow", "parks")
                    elif landuse == "forest" or natural in ["wood", "scrub"]:
                        color = self.get_layer_color("forest", "parks")
                    else:
                        color = self.get_layer_color("meadow", "parks")

                    # Plot individual feature
                    from geopandas import GeoSeries
                    gs = GeoSeries([row.geometry], crs=landscape_polys.crs)
                    gs.plot(
                        ax=ax,
                        facecolor=color,
                        edgecolor="none",
                        alpha=0.5,
                        zorder=LAYER_ZORDER["landscape"],
                    )

        # Render water features (z=1)
        if water is not None and not water.empty:
            water_polys = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])]
            if not water_polys.empty:
                try:
                    water_polys = ox.projection.project_gdf(water_polys)
                except Exception:
                    water_polys = water_polys.to_crs(G_proj.graph["crs"])
                water_polys.plot(
                    ax=ax,
                    facecolor=self.theme["water"],
                    edgecolor="none",
                    zorder=LAYER_ZORDER["water"],
                )

        # Render waterways (streams, rivers, canals) (z=1.5)
        if waterways is not None and not waterways.empty:
            waterways_lines = waterways[
                waterways.geometry.type.isin(["LineString", "MultiLineString"])
            ]
            if not waterways_lines.empty:
                try:
                    waterways_lines = ox.projection.project_gdf(waterways_lines)
                except Exception:
                    waterways_lines = waterways_lines.to_crs(G_proj.graph["crs"])

                waterway_color = self.get_layer_color("waterways", "water")

                waterways_lines.plot(
                    ax=ax,
                    color=waterway_color,
                    linewidth=DETAIL_LAYER_LINEWIDTHS["waterways"],
                    alpha=0.8,
                    zorder=LAYER_ZORDER["waterways"],
                )

        # Render parks features (z=2)
        if parks is not None and not parks.empty:
            parks_polys = parks[parks.geometry.type.isin(["Polygon", "MultiPolygon"])]
            if not parks_polys.empty:
                try:
                    parks_polys = ox.projection.project_gdf(parks_polys)
                except Exception:
                    parks_polys = parks_polys.to_crs(G_proj.graph["crs"])
                parks_polys.plot(
                    ax=ax,
                    facecolor=self.theme["parks"],
                    edgecolor="none",
                    zorder=LAYER_ZORDER["parks"],
                )

        # Render leisure areas (sports, playgrounds, gardens) (z=2.5)
        if leisure is not None and not leisure.empty:
            leisure_polys = leisure[
                leisure.geometry.type.isin(["Polygon", "MultiPolygon"])
            ]
            if not leisure_polys.empty:
                try:
                    leisure_polys = ox.projection.project_gdf(leisure_polys)
                except Exception:
                    leisure_polys = leisure_polys.to_crs(G_proj.graph["crs"])

                leisure_color = self.get_layer_color("leisure", "parks")

                leisure_polys.plot(
                    ax=ax,
                    facecolor=leisure_color,
                    edgecolor="none",
                    alpha=0.6,
                    zorder=LAYER_ZORDER["leisure"],
                )

        # Render amenities (churches, schools, cemeteries) (z=2.8)
        if amenities is not None and not amenities.empty:
            amenities_polys = amenities[
                amenities.geometry.type.isin(["Polygon", "MultiPolygon"])
            ]
            if not amenities_polys.empty:
                try:
                    amenities_polys = ox.projection.project_gdf(amenities_polys)
                except Exception:
                    amenities_polys = amenities_polys.to_crs(G_proj.graph["crs"])

                amenity_fill = self.get_layer_color("amenities", "buildings_fill")
                amenity_edge = self.get_layer_color("amenities_edge", "buildings")

                amenities_polys.plot(
                    ax=ax,
                    facecolor=amenity_fill,
                    edgecolor=amenity_edge,
                    linewidth=0.3,
                    alpha=0.7,
                    zorder=LAYER_ZORDER["amenities"],
                )

        # Render buildings (z=3)
        if buildings is not None and not buildings.empty:
            buildings_polys = buildings[
                buildings.geometry.type.isin(["Polygon", "MultiPolygon"])
            ]
            if not buildings_polys.empty:
                try:
                    buildings_polys = ox.projection.project_gdf(buildings_polys)
                except Exception:
                    buildings_polys = buildings_polys.to_crs(G_proj.graph["crs"])

                # Get building colors from theme
                building_edge = self.get_layer_color("buildings", "text")
                building_fill = self.get_layer_color("buildings_fill", "bg")

                buildings_polys.plot(
                    ax=ax,
                    facecolor=building_fill,
                    edgecolor=building_edge,
                    linewidth=DETAIL_LAYER_LINEWIDTHS["buildings_edge"],
                    alpha=0.8,
                    zorder=LAYER_ZORDER["buildings"],
                )

        # Render hedges/barriers (z=3.5)
        if hedges is not None and not hedges.empty:
            hedges_lines = hedges[
                hedges.geometry.type.isin(["LineString", "MultiLineString"])
            ]
            if not hedges_lines.empty:
                try:
                    hedges_lines = ox.projection.project_gdf(hedges_lines)
                except Exception:
                    hedges_lines = hedges_lines.to_crs(G_proj.graph["crs"])

                hedge_color = self.get_layer_color("hedges", "parks")

                hedges_lines.plot(
                    ax=ax,
                    color=hedge_color,
                    linewidth=DETAIL_LAYER_LINEWIDTHS["hedges"],
                    alpha=0.7,
                    zorder=LAYER_ZORDER["hedges"],
                )

        # Render paths/tracks (z=4)
        if paths is not None and not paths.empty:
            # Paths are usually LineStrings
            paths_lines = paths[
                paths.geometry.type.isin(["LineString", "MultiLineString"])
            ]
            if not paths_lines.empty:
                try:
                    paths_lines = ox.projection.project_gdf(paths_lines)
                except Exception:
                    paths_lines = paths_lines.to_crs(G_proj.graph["crs"])

                path_color = self.get_layer_color("paths", "road_residential")

                paths_lines.plot(
                    ax=ax,
                    color=path_color,
                    linewidth=DETAIL_LAYER_LINEWIDTHS["paths"],
                    alpha=0.6,
                    zorder=LAYER_ZORDER["paths"],
                )

        # Render railways (z=4.5)
        if railways is not None and not railways.empty:
            railways_lines = railways[
                railways.geometry.type.isin(["LineString", "MultiLineString"])
            ]
            if not railways_lines.empty:
                try:
                    railways_lines = ox.projection.project_gdf(railways_lines)
                except Exception:
                    railways_lines = railways_lines.to_crs(G_proj.graph["crs"])

                railway_color = self.get_layer_color("railways", "text")

                # Draw railway lines with characteristic dashed style
                railways_lines.plot(
                    ax=ax,
                    color=railway_color,
                    linewidth=DETAIL_LAYER_LINEWIDTHS["railways"],
                    linestyle=(0, (5, 3)),  # Dashed pattern for railway look
                    alpha=0.9,
                    zorder=LAYER_ZORDER["railways"],
                )

        # Render roads with hierarchy
        print("Applying road hierarchy colors...")
        edge_colors = self.get_edge_colors_by_type(G_proj)
        edge_widths = self.get_edge_widths_by_type(G_proj)

        # Get crop limits to maintain aspect ratio
        crop_xlim, crop_ylim = self.get_crop_limits(G_proj, fig)

        # Plot street network
        ox.plot_graph(
            G_proj,
            ax=ax,
            bgcolor=self.theme["bg"],
            node_size=0,
            edge_color=edge_colors,
            edge_linewidth=edge_widths,
            show=False,
            close=False,
        )
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(crop_xlim)
        ax.set_ylim(crop_ylim)

        # Apply gradient overlays
        self.create_gradient_fade(
            ax, self.theme["gradient_color"], location="bottom", zorder=10
        )
        self.create_gradient_fade(
            ax, self.theme["gradient_color"], location="top", zorder=10
        )

        # Apply text overlay with font scaling
        apply_text_overlay(
            ax,
            city_name,
            country_name,
            lat,
            lon,
            self.theme,
            fonts=self.fonts,
            text_config=text_position,
            paper_size=paper_size,
            distance_m=distance,
        )

        print("✓ Map generated successfully!")
        return fig

    def _render_night_lights(
        self,
        G_proj,
        water,
        parks,
        buildings,
        lat: float,
        lon: float,
        city_name: str,
        country_name: str,
        paper_size: str,
        distance: int,
        dpi: int,
        text_position: dict,
    ) -> Figure:
        """
        Render map in Night Lights mode - glowing streets on dark background.

        Creates an aerial night photography effect with:
        - Glowing road lines with bloom effect
        - Dark building silhouettes
        - Scattered window lights
        - Color temperature variation (cool center, warm edges)
        """
        print("Rendering in Night Lights mode...")

        fig_width, fig_height = PAPER_SIZES[paper_size]
        bg_color = self.theme.get("bg", "#040408")

        fig, ax = plt.subplots(
            figsize=(fig_width, fig_height),
            facecolor=bg_color,
            dpi=dpi or PREVIEW_DPI,
        )
        ax.set_facecolor(bg_color)
        ax.set_position((0.0, 0.0, 1.0, 1.0))
        ax.axis("off")

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

        # Render water as very dark
        if water is not None and not water.empty:
            water_polys = water[water.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not water_polys.empty:
                try:
                    water_polys = ox.projection.project_gdf(water_polys)
                except Exception:
                    water_polys = water_polys.to_crs(G_proj.graph["crs"])
                water_color = self.theme.get("water", "#020208")
                water_polys.plot(ax=ax, facecolor=water_color, edgecolor='none', alpha=1.0, zorder=1)
                # Subtle reflection
                water_polys.plot(ax=ax, facecolor='#FFB34720', edgecolor='none', alpha=0.15, zorder=1.5)

        # Render parks as very dark
        if parks is not None and not parks.empty:
            parks_polys = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not parks_polys.empty:
                try:
                    parks_polys = ox.projection.project_gdf(parks_polys)
                except Exception:
                    parks_polys = parks_polys.to_crs(G_proj.graph["crs"])
                parks_color = self.theme.get("parks", "#030306")
                parks_polys.plot(ax=ax, facecolor=parks_color, edgecolor='none', alpha=0.95, zorder=1)

        # Render buildings as dark silhouettes
        if buildings is not None and not buildings.empty:
            buildings_polys = buildings[buildings.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not buildings_polys.empty:
                try:
                    buildings_polys = ox.projection.project_gdf(buildings_polys)
                except Exception:
                    buildings_polys = buildings_polys.to_crs(G_proj.graph["crs"])
                fill_color = self.theme.get("buildings_fill", "#08080f")
                edge_color = self.theme.get("buildings_edge", "#101018")
                buildings_polys.plot(ax=ax, facecolor=fill_color, edgecolor=edge_color, linewidth=0.08, alpha=0.97, zorder=2)

        # Get roads with color temperature
        highways = get_night_road_lines(G_proj, center_x, center_y)

        # Color palette - outer (warm/orange) and inner (cool/white)
        colors_outer = {
            'major': self.theme.get("road_motorway", "#FFB030"),
            'secondary': self.theme.get("road_secondary", "#FF9020"),
            'minor': self.theme.get("road_residential", "#E07010")
        }
        colors_inner = {
            'major': self.theme.get("road_motorway_inner", "#FFEEDD"),
            'secondary': self.theme.get("road_secondary_inner", "#FFE0C0"),
            'minor': self.theme.get("road_residential_inner", "#FFD8A8")
        }

        glow_layers = self.theme.get("glow_layers", 8)
        glow_intensity = self.theme.get("glow_intensity", 0.9)

        # Render roads with glow effect
        print("  Rendering road glow effects...")
        create_glow_effect(ax, highways['minor_outer'], colors_outer['minor'], base_width=0.25, num_layers=5, max_alpha=0.45, zorder=3)
        create_glow_effect(ax, highways['minor_inner'], colors_inner['minor'], base_width=0.25, num_layers=5, max_alpha=0.45, zorder=3)
        create_glow_effect(ax, highways['secondary_outer'], colors_outer['secondary'], base_width=0.45, num_layers=6, max_alpha=0.65, zorder=4)
        create_glow_effect(ax, highways['secondary_inner'], colors_inner['secondary'], base_width=0.45, num_layers=6, max_alpha=0.65, zorder=4)
        create_glow_effect(ax, highways['major_outer'], colors_outer['major'], base_width=0.8, num_layers=glow_layers, max_alpha=glow_intensity, zorder=5)
        create_glow_effect(ax, highways['major_inner'], colors_inner['major'], base_width=0.8, num_layers=glow_layers, max_alpha=glow_intensity, zorder=5)

        # Add window lights
        if buildings is not None:
            print("  Adding window lights...")
            try:
                add_window_lights(ax, buildings_polys, center_x, center_y, max_dist, self.theme, zorder=8)
            except Exception:
                pass

        # Add horizon glow
        print("  Adding atmospheric effects...")
        horizon_color = self.theme.get("horizon_glow", "#0a1530")
        create_horizon_glow(ax, horizon_color, intensity=0.25)

        # Apply text overlay
        apply_text_overlay(
            ax,
            city_name,
            country_name,
            lat,
            lon,
            self.theme,
            fonts=self.fonts,
            text_config=text_position,
            paper_size=paper_size,
            distance_m=distance,
        )

        print("✓ Night Lights map generated successfully!")
        return fig

    def _render_holonight(
        self,
        G_proj,
        water,
        parks,
        buildings,
        lat: float,
        lon: float,
        city_name: str,
        country_name: str,
        paper_size: str,
        distance: int,
        dpi: int,
        text_position: dict,
    ) -> Figure:
        """
        Render map in Holonight mode - cyan neon glow on pure black.

        Creates a cyberpunk/holographic effect with:
        - Intense cyan neon glow on roads
        - Pure black background for maximum contrast
        - Glowing intersection points
        - White-hot line centers
        """
        print("Rendering in Holonight mode...")

        fig_width, fig_height = PAPER_SIZES[paper_size]
        bg_color = self.theme.get("bg", "#000008")

        fig, ax = plt.subplots(
            figsize=(fig_width, fig_height),
            facecolor=bg_color,
            dpi=dpi or PREVIEW_DPI,
        )
        ax.set_facecolor(bg_color)
        ax.set_position((0.0, 0.0, 1.0, 1.0))
        ax.axis("off")

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

        # Render water as very dark with subtle cyan edge
        if water is not None and not water.empty:
            water_polys = water[water.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not water_polys.empty:
                try:
                    water_polys = ox.projection.project_gdf(water_polys)
                except Exception:
                    water_polys = water_polys.to_crs(G_proj.graph["crs"])
                water_color = self.theme.get("water", "#021020")
                water_edge = self.theme.get("water_edge", "#004060")
                water_polys.plot(ax=ax, facecolor=water_color, edgecolor=water_edge, linewidth=0.3, alpha=1.0, zorder=1)

        # Render parks as very dark
        if parks is not None and not parks.empty:
            parks_polys = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not parks_polys.empty:
                try:
                    parks_polys = ox.projection.project_gdf(parks_polys)
                except Exception:
                    parks_polys = parks_polys.to_crs(G_proj.graph["crs"])
                parks_color = self.theme.get("parks", "#010408")
                parks_polys.plot(ax=ax, facecolor=parks_color, edgecolor='none', alpha=0.95, zorder=1)

        # Render buildings as dark silhouettes with subtle edge
        if buildings is not None and not buildings.empty:
            buildings_polys = buildings[buildings.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not buildings_polys.empty:
                try:
                    buildings_polys = ox.projection.project_gdf(buildings_polys)
                except Exception:
                    buildings_polys = buildings_polys.to_crs(G_proj.graph["crs"])
                fill_color = self.theme.get("buildings_fill", "#040812")
                edge_color = self.theme.get("buildings_edge", "#0A1530")
                buildings_polys.plot(ax=ax, facecolor=fill_color, edgecolor=edge_color, linewidth=0.05, alpha=0.98, zorder=2)

        # Get road lines
        highways = get_holonight_road_lines(G_proj)

        # Cyan color palette
        colors = {
            'major': self.theme.get("road_motorway", "#00FFFF"),
            'secondary': self.theme.get("road_secondary", "#00D4FF"),
            'minor': self.theme.get("road_residential", "#00A8E8")
        }
        inner_colors = {
            'major': self.theme.get("road_motorway_inner", "#FFFFFF"),
            'secondary': self.theme.get("road_secondary_inner", "#E0FFFF"),
            'minor': self.theme.get("road_residential_inner", "#C0FFFF")
        }

        glow_layers = self.theme.get("glow_layers", 10)
        glow_intensity = self.theme.get("glow_intensity", 1.0)
        glow_falloff = self.theme.get("glow_falloff", 1.5)

        # Render roads with intense neon glow
        print("  Rendering neon glow effects...")
        create_holonight_glow(ax, highways['minor'], colors['minor'], inner_colors['minor'],
                              base_width=0.3, num_layers=6, max_alpha=0.6, glow_falloff=glow_falloff, zorder=3)
        create_holonight_glow(ax, highways['secondary'], colors['secondary'], inner_colors['secondary'],
                              base_width=0.5, num_layers=8, max_alpha=0.8, glow_falloff=glow_falloff, zorder=4)
        create_holonight_glow(ax, highways['major'], colors['major'], inner_colors['major'],
                              base_width=0.9, num_layers=glow_layers, max_alpha=glow_intensity, glow_falloff=glow_falloff, zorder=5)

        # Add intersection glows
        print("  Adding intersection glows...")
        add_intersection_glows(ax, G_proj, self.theme, zorder=9)

        # Add subtle radial vignette
        vignette_intensity = self.theme.get("vignette_intensity", 0.3)
        if vignette_intensity > 0:
            print("  Adding vignette effect...")
            create_radial_vignette(ax, center_x, center_y, max_dist, intensity=vignette_intensity)

        # Apply text overlay
        apply_text_overlay(
            ax,
            city_name,
            country_name,
            lat,
            lon,
            self.theme,
            fonts=self.fonts,
            text_config=text_position,
            paper_size=paper_size,
            distance_m=distance,
        )

        print("✓ Holonight map generated successfully!")
        return fig

    def _render_kandincity(
        self,
        G_proj,
        water,
        parks,
        buildings,
        lat: float,
        lon: float,
        city_name: str,
        country_name: str,
        paper_size: str,
        distance: int,
        dpi: int,
        text_position: dict,
    ) -> Figure:
        """
        Render map in Kandincity mode - Kandinsky-inspired abstract geometric style.

        Creates an abstract art effect with:
        - Colorful building blocks (orange, grey, olive tones)
        - Thin dark road lines
        - Cream/beige background
        - Bauhaus aesthetic
        """
        print("Rendering in Kandincity mode...")

        fig_width, fig_height = PAPER_SIZES[paper_size]
        bg_color = self.theme.get("bg", "#E8DCC8")

        fig, ax = plt.subplots(
            figsize=(fig_width, fig_height),
            facecolor=bg_color,
            dpi=dpi or PREVIEW_DPI,
        )
        ax.set_facecolor(bg_color)
        ax.set_position((0.0, 0.0, 1.0, 1.0))
        ax.axis("off")

        # Get crop limits to maintain aspect ratio
        crop_xlim, crop_ylim = self.get_crop_limits(G_proj, fig)
        ax.set_xlim(crop_xlim)
        ax.set_ylim(crop_ylim)
        ax.set_aspect('equal')

        # Render water as background color (blends in)
        if water is not None and not water.empty:
            water_polys = water[water.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not water_polys.empty:
                try:
                    water_polys = ox.projection.project_gdf(water_polys)
                except Exception:
                    water_polys = water_polys.to_crs(G_proj.graph["crs"])
                water_color = self.theme.get("water", bg_color)
                water_polys.plot(ax=ax, facecolor=water_color, edgecolor='none', alpha=1.0, zorder=1)

        # Render parks with muted green
        if parks is not None and not parks.empty:
            parks_polys = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            if not parks_polys.empty:
                try:
                    parks_polys = ox.projection.project_gdf(parks_polys)
                except Exception:
                    parks_polys = parks_polys.to_crs(G_proj.graph["crs"])
                parks_color = self.theme.get("parks", "#8B9860")
                parks_polys.plot(ax=ax, facecolor=parks_color, edgecolor='none', alpha=0.9, zorder=2)

        # Render buildings as colorful Kandinsky-style blocks
        if buildings is not None and not buildings.empty:
            print("  Rendering Kandinsky-style building blocks...")
            try:
                buildings_proj = ox.projection.project_gdf(buildings)
            except Exception:
                buildings_proj = buildings.to_crs(G_proj.graph["crs"])
            render_kandinsky_buildings(ax, buildings_proj, self.theme, zorder=3)

        # Render roads as thin dark lines
        print("  Rendering road network...")
        edge_colors = []
        edge_widths = []

        for u, v, data in G_proj.edges(data=True):
            highway = data.get("highway", "unclassified")
            if isinstance(highway, list):
                highway = highway[0] if highway else "unclassified"

            # Get color based on road type
            if highway in ['motorway', 'motorway_link', 'trunk', 'trunk_link']:
                color = self.theme.get("road_motorway", "#1A1A1A")
                width = self.theme.get("road_width_motorway", 1.2)
            elif highway in ['primary', 'primary_link']:
                color = self.theme.get("road_primary", "#2A2A2A")
                width = self.theme.get("road_width_primary", 1.0)
            elif highway in ['secondary', 'secondary_link']:
                color = self.theme.get("road_secondary", "#3A3A3A")
                width = self.theme.get("road_width_secondary", 0.8)
            elif highway in ['tertiary', 'tertiary_link']:
                color = self.theme.get("road_tertiary", "#4A4A4A")
                width = self.theme.get("road_width_tertiary", 0.6)
            elif highway in ['residential', 'living_street']:
                color = self.theme.get("road_residential", "#5A5A5A")
                width = self.theme.get("road_width_residential", 0.4)
            else:
                color = self.theme.get("road_default", "#6A6A6A")
                width = 0.3

            edge_colors.append(color)
            edge_widths.append(width)

        # Plot street network
        ox.plot_graph(
            G_proj,
            ax=ax,
            bgcolor=bg_color,
            node_size=0,
            edge_color=edge_colors,
            edge_linewidth=edge_widths,
            show=False,
            close=False,
        )

        # Apply text overlay
        apply_text_overlay(
            ax,
            city_name,
            country_name,
            lat,
            lon,
            self.theme,
            fonts=self.fonts,
            text_config=text_position,
            paper_size=paper_size,
            distance_m=distance,
        )

        print("✓ Kandincity map generated successfully!")
        return fig

    def save_poster(
        self,
        fig: Figure,
        output_path: str | Path,
        output_format: str = "png",
        dpi: int = OUTPUT_DPI,
    ) -> None:
        """
        Save figure to file.

        Args:
            fig: Matplotlib Figure object
            output_path: Path where to save
            output_format: Format ('png', 'svg', 'pdf')
            dpi: DPI for output (mainly for PNG)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fmt = output_format.lower()
        save_kwargs = dict(
            facecolor=self.theme["bg"],
            bbox_inches="tight",
            pad_inches=0.05,
        )

        if fmt == "png":
            save_kwargs["dpi"] = dpi

        print(f"Saving to {output_path}...")
        # Save the figure to file
        plt.savefig(output_path, format=fmt, **save_kwargs)

        # Close the figure to free memory and avoid display issues
        plt.close(fig)

        print(f"✓ Done! Saved as {output_path}")

    @staticmethod
    def generate_output_filename(
        city: str, theme_name: str, output_format: str = "png"
    ) -> str:
        """
        Generate unique output filename.

        Args:
            city: City name
            theme_name: Theme name
            output_format: File format

        Returns:
            Filename string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        city_slug = city.lower().replace(" ", "_")
        ext = output_format.lower()

        return f"{city_slug}_{theme_name}_{timestamp}.{ext}"
