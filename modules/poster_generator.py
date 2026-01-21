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
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
import osmnx as ox
from networkx import MultiDiGraph
from geopandas import GeoDataFrame
from tqdm import tqdm

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
)
from .geocoding import cache_get, cache_set, CacheError
from .text_positioning import apply_text_overlay, load_fonts


class PosterGenerator:
    """
    Main class for generating map posters.

    Handles theme loading, data fetching, rendering, and file output.
    """

    def __init__(self, theme_name: str = DEFAULT_THEME):
        """
        Initialize poster generator with a specific theme.

        Args:
            theme_name: Name of theme JSON file (without .json extension)
        """
        self.theme_name = theme_name
        self.theme = self.load_theme(theme_name)
        self.fonts = load_fonts(FONTS_DIR)

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

    @staticmethod
    def get_layer_defaults(distance_m: int) -> dict:
        """
        Get default layer visibility based on zoom level.

        Args:
            distance_m: Map radius in meters

        Returns:
            Dict with layer visibility booleans
        """
        if distance_m <= LAYER_ZOOM_THRESHOLDS["all_on"]:
            # Village zoom: all layers on
            return {"buildings": True, "paths": True, "landscape": True}
        elif distance_m <= LAYER_ZOOM_THRESHOLDS["buildings_only"]:
            # Town zoom: only buildings
            return {"buildings": True, "paths": False, "landscape": False}
        else:
            # City zoom: no detail layers
            return {"buildings": False, "paths": False, "landscape": False}

    def get_layer_color(self, layer_key: str, fallback_key: str = None) -> str:
        """
        Get color for a layer from theme, with fallback.

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
        if layers.get("buildings"):
            fetch_steps += 1
        if layers.get("paths"):
            fetch_steps += 1
        if layers.get("landscape"):
            fetch_steps += 1

        # Fetch map data
        buildings = None
        paths = None
        landscape = None

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

        print("✓ All data retrieved successfully!")

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

        # Project graph to metric CRS
        G_proj = ox.project_graph(G)

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
        plt.savefig(output_path, format=fmt, **save_kwargs)
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
