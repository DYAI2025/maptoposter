#!/usr/bin/env python3
"""
Generate theme preview thumbnails for all available themes.

This script generates small preview images (thumbnails) for each theme
using Berlin as the example city. These thumbnails are displayed in the
theme selection gallery in the GUI.

Usage:
    python generate_theme_previews.py
    python generate_theme_previews.py --city "Paris" --country "France"
    python generate_theme_previews.py --theme noir  # Generate only one theme
"""

import os
import sys
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# Setup matplotlib backend before importing pyplot
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from modules.poster_generator import PosterGenerator
from modules.geocoding import geocode_address
from modules.config import THEMES_DIR


# Preview configuration
PREVIEW_CITY = "Berlin"
PREVIEW_COUNTRY = "Germany"
PREVIEW_LAT = 52.5200
PREVIEW_LON = 13.4050
PREVIEW_DISTANCE = 8000  # 8km radius for good overview
PREVIEW_DPI = 80  # Low DPI for small thumbnails
PREVIEW_DIR = Path(__file__).parent / "theme_previews"


def get_all_themes() -> list[str]:
    """Get list of all available theme names."""
    themes_path = Path(THEMES_DIR)
    if not themes_path.exists():
        return []

    themes = []
    for f in themes_path.glob("*.json"):
        themes.append(f.stem)

    return sorted(themes)


def generate_single_preview(
    theme_name: str,
    lat: float,
    lon: float,
    city: str,
    country: str,
    distance: int,
    output_dir: Path,
    force: bool = False
) -> tuple[str, bool, str]:
    """
    Generate a single theme preview image.

    Returns:
        Tuple of (theme_name, success, message)
    """
    output_path = output_dir / f"{theme_name}.png"

    # Skip if exists and not forcing
    if output_path.exists() and not force:
        return (theme_name, True, "Already exists (skipped)")

    try:
        # Create generator with theme
        generator = PosterGenerator(theme_name=theme_name)

        # Simple text config (centered at bottom)
        text_config = {
            "x": 0.5,
            "y": 0.12,
            "alignment": "center",
            "show_coords": False,
            "show_country": True,
        }

        # Minimal layers for fast generation
        layer_config = {
            "buildings": False,
            "paths": False,
            "landscape": False,
            "waterways": True,
            "railways": False,
            "hedges": False,
            "leisure": False,
            "amenities": False,
        }

        # Generate poster
        fig = generator.generate_poster(
            lat=lat,
            lon=lon,
            city_name=city,
            country_name=country,
            paper_size="A4",
            distance=distance,
            text_position=text_config,
            layers=layer_config,
        )

        # Save as thumbnail
        fig.savefig(
            output_path,
            format="png",
            dpi=PREVIEW_DPI,
            bbox_inches="tight",
            pad_inches=0.02,
            facecolor=fig.get_facecolor(),
        )
        plt.close(fig)

        return (theme_name, True, f"Generated: {output_path.name}")

    except Exception as e:
        return (theme_name, False, f"Error: {str(e)}")


def generate_all_previews(
    city: str = PREVIEW_CITY,
    country: str = PREVIEW_COUNTRY,
    lat: float = None,
    lon: float = None,
    theme_filter: str = None,
    force: bool = False,
    parallel: bool = False
) -> None:
    """Generate preview images for all themes."""

    # Create output directory
    PREVIEW_DIR.mkdir(exist_ok=True)

    # Get coordinates if not provided
    if lat is None or lon is None:
        print(f"Geocoding {city}, {country}...")
        try:
            lat, lon, _ = geocode_address(f"{city}, {country}")
            print(f"  Coordinates: {lat:.4f}, {lon:.4f}")
        except Exception as e:
            print(f"  Using default Berlin coordinates (geocoding failed: {e})")
            lat, lon = PREVIEW_LAT, PREVIEW_LON

    # Get themes to process
    all_themes = get_all_themes()

    if theme_filter:
        if theme_filter in all_themes:
            themes = [theme_filter]
        else:
            print(f"Theme '{theme_filter}' not found. Available: {', '.join(all_themes)}")
            return
    else:
        themes = all_themes

    print(f"\nGenerating {len(themes)} theme preview(s)...")
    print(f"Output directory: {PREVIEW_DIR}\n")

    # Process themes
    results = []

    if parallel and len(themes) > 1:
        # Parallel processing (faster but uses more memory)
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    generate_single_preview,
                    theme, lat, lon, city, country, PREVIEW_DISTANCE, PREVIEW_DIR, force
                ): theme
                for theme in themes
            }

            for future in as_completed(futures):
                theme_name, success, message = future.result()
                status = "OK" if success else "FAIL"
                print(f"  [{status}] {theme_name}: {message}")
                results.append((theme_name, success))
    else:
        # Sequential processing (more stable)
        for i, theme in enumerate(themes, 1):
            print(f"  [{i}/{len(themes)}] Processing {theme}...", end=" ", flush=True)
            theme_name, success, message = generate_single_preview(
                theme, lat, lon, city, country, PREVIEW_DISTANCE, PREVIEW_DIR, force
            )
            status = "OK" if success else "FAIL"
            print(f"[{status}] {message}")
            results.append((theme_name, success))

    # Summary
    successful = sum(1 for _, s in results if s)
    failed = len(results) - successful

    print(f"\n{'='*50}")
    print(f"Summary: {successful} successful, {failed} failed")
    print(f"Previews saved to: {PREVIEW_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate theme preview thumbnails"
    )
    parser.add_argument(
        "--city", "-c",
        default=PREVIEW_CITY,
        help=f"City name for preview (default: {PREVIEW_CITY})"
    )
    parser.add_argument(
        "--country", "-C",
        default=PREVIEW_COUNTRY,
        help=f"Country name (default: {PREVIEW_COUNTRY})"
    )
    parser.add_argument(
        "--lat",
        type=float,
        help="Latitude (skips geocoding)"
    )
    parser.add_argument(
        "--lon",
        type=float,
        help="Longitude (skips geocoding)"
    )
    parser.add_argument(
        "--theme", "-t",
        help="Generate only this theme"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Regenerate even if preview exists"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Use parallel processing (faster but more memory)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available themes and exit"
    )

    args = parser.parse_args()

    if args.list:
        themes = get_all_themes()
        print(f"Available themes ({len(themes)}):")
        for theme in themes:
            print(f"  - {theme}")
        return

    generate_all_previews(
        city=args.city,
        country=args.country,
        lat=args.lat,
        lon=args.lon,
        theme_filter=args.theme,
        force=args.force,
        parallel=args.parallel,
    )


if __name__ == "__main__":
    main()
