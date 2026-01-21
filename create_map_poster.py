"""
CityMaps Poster Generator - CLI Interface

Command-line interface for generating beautiful map posters.
For GUI version, use: streamlit run gui_app.py
"""

import sys
import argparse
from pathlib import Path

# Import modular components
from modules.geocoding import geocode_address
from modules.poster_generator import PosterGenerator
from modules.config import DEFAULT_THEME, POSTERS_DIR


def print_examples():
    """Print usage examples."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║              CityMaps Poster Generator - CLI                   ║
╚════════════════════════════════════════════════════════════════╝

Generate beautiful map posters for any city using OpenStreetMap data.

USAGE:
  python create_map_poster.py --city <NAME> --country <NAME> [OPTIONS]

REQUIRED:
  --city, -c          City name (e.g., "Berlin")
  --country, -C       Country name (e.g., "Germany")

OPTIONS:
  --theme, -t         Theme name (default: feature_based)
  --distance, -d      Map radius in meters (default: 8000)
  --format, -f        Output format: png|svg|pdf (default: png)
  --list-themes       Show all available themes
  --help              Show this help message

EXAMPLES:
  python create_map_poster.py -c Berlin -C Germany
  python create_map_poster.py -c Tokyo -C Japan -t midnight_blue
  python create_map_poster.py -c Paris -C France -t noir -d 15000
  python create_map_poster.py --list-themes

GUI VERSION:
  For an interactive interface, use:
  streamlit run gui_app.py

For more information, visit: https://github.com/yourusername/citymaps
""")


def list_themes():
    """Display available themes."""
    print("\n" + "=" * 60)
    print("Available Themes")
    print("=" * 60 + "\n")

    generator = PosterGenerator()
    available_themes = generator.get_available_themes()

    if not available_themes:
        print("No themes found in themes/ directory.")
        return

    # Load each theme and display info
    for theme_name in sorted(available_themes):
        generator_themed = PosterGenerator(theme_name)
        theme = generator_themed.theme
        name = theme.get("name", theme_name)
        desc = theme.get("description", "")

        print(f"  • {theme_name:20s} {name}")
        if desc:
            print(f"    {desc}")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    parser.add_argument("--city", "-c", type=str, help="City name")
    parser.add_argument("--country", "-C", type=str, help="Country name")
    parser.add_argument(
        "--theme",
        "-t",
        type=str,
        default=DEFAULT_THEME,
        help=f"Theme name (default: {DEFAULT_THEME})",
    )
    parser.add_argument(
        "--distance",
        "-d",
        type=int,
        default=8000,
        help="Map radius in meters (default: 8000)",
    )
    parser.add_argument(
        "--format",
        "-f",
        default="png",
        choices=["png", "svg", "pdf"],
        help="Output format (default: png)",
    )
    parser.add_argument(
        "--list-themes", action="store_true", help="List all available themes"
    )
    parser.add_argument("--help", action="store_true", help="Show this help message")

    args = parser.parse_args()

    # Handle help
    if args.help or len(sys.argv) == 1:
        print_examples()
        return 0

    # List themes if requested
    if args.list_themes:
        list_themes()
        return 0

    # Validate required arguments
    if not args.city or not args.country:
        print("❌ Error: --city and --country are required.\n")
        print_examples()
        return 1

    # Validate theme exists
    generator = PosterGenerator()
    available_themes = generator.get_available_themes()
    if args.theme not in available_themes:
        print(f"❌ Error: Theme '{args.theme}' not found.")
        print(f"Available themes: {', '.join(available_themes)}")
        return 1

    # Print header
    print("=" * 60)
    print("CityMaps Poster Generator")
    print("=" * 60)

    # Geocode address
    try:
        print(f"\n📍 Geocoding {args.city}, {args.country}...")
        lat, lon, formatted_address = geocode_address(
            f"{args.city}, {args.country}"
        )
    except Exception as e:
        print(f"❌ Geocoding failed: {e}")
        return 1

    # Generate poster
    try:
        generator = PosterGenerator(theme_name=args.theme)

        fig = generator.generate_poster(
            lat=lat,
            lon=lon,
            city_name=args.city,
            country_name=args.country,
            paper_size="A4",
            distance=args.distance,
            dpi=300,
        )

        # Generate filename
        output_filename = generator.generate_output_filename(
            args.city, args.theme, args.format
        )
        output_path = POSTERS_DIR / output_filename

        # Save poster
        generator.save_poster(
            fig, output_path, output_format=args.format, dpi=300
        )

        print("\n" + "=" * 60)
        print("✅ Poster generation complete!")
        print(f"Saved to: {output_path}")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
