"""
Geocoding module with Google Places API and Nominatim fallback.

Abstracts address-to-coordinates conversion with caching and rate limiting.
"""

import asyncio
import time
from hashlib import md5
from pathlib import Path
import pickle

from geopy.geocoders import Nominatim
import googlemaps

from .config import (
    CACHE_DIR,
    GOOGLE_PLACES_API_KEY,
    NOMINATIM_USER_AGENT,
    GEOCODING_RATE_LIMIT,
)


class CacheError(Exception):
    """Exception for cache-related errors."""
    pass


def cache_file(key: str) -> Path:
    """Generate cache filename from key using MD5 hash."""
    encoded = md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{encoded}.pkl"


def cache_get(name: str):
    """Retrieve object from cache. Returns None if not found or error."""
    path = cache_file(name)
    if path.exists():
        try:
            with path.open("rb") as f:
                return pickle.load(f)
        except (pickle.PickleError, OSError, IOError) as e:
            print(f"⚠ Cache read error for '{name}': {e}")
            return None
    return None


def cache_set(name: str, obj) -> None:
    """Store object in cache."""
    path = cache_file(name)
    try:
        with path.open("wb") as f:
            pickle.dump(obj, f)
    except pickle.PickleError as e:
        raise CacheError(
            f"Serialization error while saving cache for '{name}': {e}"
        ) from e
    except (OSError, IOError) as e:
        raise CacheError(
            f"File error while saving cache for '{name}': {e}"
        ) from e


def geocode_address(
    address: str,
    use_google: bool = None,
) -> tuple[float, float, str]:
    """
    Geocode address to coordinates.

    Args:
        address: Full address (e.g., "Berlin, Germany")
        use_google: If True, try Google Places API first. If None, auto-detect
                   based on API key availability.

    Returns:
        Tuple of (latitude, longitude, formatted_address)

    Raises:
        ValueError: If geocoding fails for the address
    """
    cache_key = f"coords_{address.lower()}"
    cached = cache_get(cache_key)
    if cached:
        print(f"✓ Using cached coordinates for '{address}'")
        return cached

    # Determine which geocoder to use
    if use_google is None:
        use_google = GOOGLE_PLACES_API_KEY is not None

    if use_google and GOOGLE_PLACES_API_KEY:
        try:
            result = geocode_google_places(address)
            cache_set(cache_key, result)
            return result
        except Exception as e:
            print(f"⚠ Google Places geocoding failed: {e}")
            print("  Falling back to Nominatim...")

    # Fallback to Nominatim
    try:
        result = geocode_nominatim(address)
        cache_set(cache_key, result)
        return result
    except Exception as e:
        raise ValueError(f"Geocoding failed for '{address}': {e}") from e


def geocode_google_places(address: str) -> tuple[float, float, str]:
    """
    Geocode address using Google Places API.

    Args:
        address: Address string to geocode

    Returns:
        Tuple of (latitude, longitude, formatted_address)

    Raises:
        ValueError: If geocoding fails
    """
    if not GOOGLE_PLACES_API_KEY:
        raise ValueError("Google Places API key not configured")

    try:
        gmaps = googlemaps.Client(key=GOOGLE_PLACES_API_KEY)
        result = gmaps.geocode(address)

        if not result:
            raise ValueError(f"No results found for '{address}'")

        location = result[0]
        lat = location["geometry"]["location"]["lat"]
        lon = location["geometry"]["location"]["lng"]
        formatted = location.get("formatted_address", address)

        print(f"✓ Found: {formatted}")
        print(f"✓ Coordinates: {lat}, {lon}")

        return (lat, lon, formatted)

    except googlemaps.exceptions.GoogleMapsAPIException as e:
        raise ValueError(f"Google Places API error: {e}") from e
    except Exception as e:
        raise ValueError(f"Google Places geocoding error: {e}") from e


def geocode_nominatim(address: str) -> tuple[float, float, str]:
    """
    Geocode address using Nominatim (OpenStreetMap).

    Args:
        address: Address string to geocode

    Returns:
        Tuple of (latitude, longitude, formatted_address)

    Raises:
        ValueError: If geocoding fails
    """
    print(f"Looking up coordinates via Nominatim...")

    geolocator = Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=10)

    # Rate limiting: be respectful to Nominatim
    time.sleep(GEOCODING_RATE_LIMIT)

    try:
        location = geolocator.geocode(address)

        # Handle asyncio coroutines (can happen in some environments)
        if asyncio.iscoroutine(location):
            try:
                location = asyncio.run(location)
            except RuntimeError:
                # Event loop already running
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    raise RuntimeError(
                        "Geocoder returned a coroutine while an event loop is "
                        "already running. Run this script in a synchronous "
                        "environment."
                    )
                location = loop.run_until_complete(location)

        if not location:
            raise ValueError(f"Could not find coordinates for '{address}'")

        formatted = getattr(location, "address", address)
        lat = location.latitude
        lon = location.longitude

        print(f"✓ Found: {formatted}")
        print(f"✓ Coordinates: {lat}, {lon}")

        return (lat, lon, formatted)

    except Exception as e:
        raise ValueError(f"Nominatim geocoding failed: {e}") from e
