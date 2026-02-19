# MapToPoster — MVP Scope Definition & Map API Research

## Summary

Conducted comprehensive research on map API providers and defined the initial MVP feature set for MapToPoster — a web app that generates beautiful, minimalist map posters from any location worldwide.

## What Was Done

### 1. Map API Research (`docs/MAP-API-RESEARCH.md`)

Evaluated 7+ map data and rendering providers for commercial poster generation:

| Provider | Commercial Print OK? | Cost | Verdict |
|----------|---------------------|------|---------|
| **OSMnx + Overpass (OSM)** | Yes (ODbL attribution) | Free | **Recommended** |
| **Google Maps** | **No** (ToS explicitly prohibits posters) | $2/1K | Rejected |
| **Mapbox** | Limited (2K copies/yr) | $1/1K | Preview only |
| **Stadia Maps** | Up to 5K copies/image | $20+/mo | Alternative |
| **TileServer GL (self-hosted)** | Yes (ODbL) | Hosting only | Future option |
| **Mapnik** | Yes (ODbL) | Free | Future option |

**Key finding:** Google Maps cannot be used for commercial poster sales — posters are explicitly listed as prohibited merchandise in their Terms of Service. OpenStreetMap with ODbL license is the only viable free option for unlimited commercial use.

**Recommended MVP stack:**
- Map Data: OSMnx + Overpass API (already integrated, free, unlimited)
- Geocoding: Nominatim (public for dev, self-hosted at scale)
- Rendering: Matplotlib (already working, poster-quality, no resolution limits)
- Interactive Preview: MapLibre GL JS (free, for future web frontend)

### 2. MVP Scope Definition (`docs/MVP-SCOPE.md`)

Defined the "first sellable product" scope with priority matrix:

**Already working (P0 complete):**
- Core map generation via OSMnx
- 30+ theme system
- 5 font families
- Text & color personalization
- Paper sizes (A2-A5), export formats (PNG/SVG/PDF)

**MVP must-build (P0-P1):**
- Backend API with async generation (FastAPI, Celery/RQ)
- Web frontend with location search and live preview
- Quick preview mode (<3 seconds)
- Stripe Checkout payment integration
- File storage & delivery (S3-compatible)

**Curated 8 themes for MVP:** noir, midnight_blue, warm_beige, japanese_ink, neon_cyberpunk, blueprint, feature_based, forest

**Pricing model:** Digital download — A4: €9.99, A3: €14.99, A2: €19.99

**Out of scope for MVP:** Print-on-demand, user accounts, GPS track overlay, 3D buildings, mobile app, API for third parties.

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `docs/MAP-API-RESEARCH.md` | Created | Detailed API research: 7 providers, pricing, terms, legal analysis, architecture recommendations |
| `docs/MVP-SCOPE.md` | Created | MVP feature set, priority matrix, tech architecture, success metrics, risk assessment |
| `RESULT.md` | Replaced | This summary document |

## Commit

- **Branch:** main
- **Repository:** https://github.com/DYAI2025/maptoposter
