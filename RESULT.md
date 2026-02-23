# MapToPoster — MVP Scope Definition & Map API Research

## Summary

Conducted comprehensive research on 7+ map API providers (OpenStreetMap, Google Maps, Mapbox, Stadia, MapTiler, TileServer GL, Mapnik) for commercial poster generation. Defined the initial MVP feature set with priority matrix, technical architecture, and cost projections.

**Key finding:** Google Maps ToS explicitly prohibits poster sales. OSM with ODbL license is the recommended stack — free, unlimited resolution, full commercial rights with attribution.

## What Was Done

### 1. Map API Research (`docs/MAP-API-RESEARCH.md`)

Detailed evaluation of map data sources and rendering options:

| Provider | Commercial Print? | Cost | Resolution | Verdict |
|----------|------------------|------|------------|---------|
| **OSMnx + Overpass** | Yes (ODbL) | Free | Unlimited (vector) | **Primary — Recommended** |
| **Google Maps** | **No** (posters explicitly prohibited) | $2/1K | 1280x1280 | **Rejected** |
| **Mapbox** | Limited (2K copies/yr) | $1/1K | 2560x2560 | Preview only |
| **Stadia Maps** | Up to 5K copies/image | $20+/mo | Not specified | Alternative |
| **TileServer GL** | Yes (ODbL) | Hosting only | Configurable | Future option |
| **Mapnik** | Yes (ODbL) | Free | Unlimited | Future option |

Includes: pricing tiers, rate limits, ToS analysis, geocoding comparison (Google vs Nominatim), ODbL license interpretation for produced works, attribution requirements, and cost projections from $0 to $500/month at scale.

### 2. MVP Scope Definition (`docs/MVP-SCOPE.md`)

Defined "first sellable product" — a web app where users create and purchase custom map posters in under 5 minutes.

**Already built (P0 complete):** Core map generation, 30+ themes, 5 fonts, text/color personalization, paper sizes (A2-A5), export formats (PNG/SVG/PDF).

**Must-build for MVP (P0-P1):**
- Backend API with async poster generation (FastAPI + Celery/RQ)
- Web frontend with location search, live preview, theme selector
- Quick preview mode (<3 seconds)
- Stripe Checkout payment (A4: €9.99, A3: €14.99, A2: €19.99)
- File storage & delivery (S3-compatible)

**Curated 8 themes:** noir, midnight_blue, warm_beige, japanese_ink, neon_cyberpunk, blueprint, feature_based, forest

**Out of scope:** Print-on-demand, user accounts, GPS tracks, 3D buildings, mobile app, subscription model.

**Tech stack:** React + Vite frontend, FastAPI backend, OSMnx + Matplotlib rendering, MapLibre GL JS for preview, Celery + Redis job queue, Stripe payments, Vercel + VPS hosting.

## Files Created

| File | Action | Description |
|------|--------|-------------|
| `docs/MAP-API-RESEARCH.md` | Created | 320-line detailed API research across 7 providers |
| `docs/MVP-SCOPE.md` | Created | 260-line MVP scope with priority matrix, architecture, metrics |
| `RESULT.md` | Updated | This summary |

## Commit

- **Commit Hash:** `2252046`
- **Branch:** main
- **Repository:** https://github.com/DYAI2025/maptoposter
