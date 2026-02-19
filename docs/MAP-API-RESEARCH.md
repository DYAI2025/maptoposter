# Map API Research — MapToPoster

> Research date: February 2026
> Purpose: Evaluate map data sources and rendering options for commercial poster generation

---

## Executive Summary

**Recommended stack for MapToPoster MVP:**

| Layer | Solution | Why |
|-------|----------|-----|
| **Map Data** | OSMnx + Overpass API | Free, open data, already integrated, perfect for vector rendering |
| **Geocoding** | Nominatim (public for dev, self-hosted for prod) | Free, adequate for user-triggered lookups |
| **Rendering** | Matplotlib/Mapnik (server-side) | Already working, full control, poster-quality output |
| **Interactive Preview** | MapLibre GL JS + self-hosted tiles | Free, customizable, no commercial restrictions |

**Key finding:** Google Maps **cannot** be used for commercial poster sales (explicit ToS violation). OSM with ODbL license is the only viable free option. Mapbox allows limited print (2K copies/year).

---

## 1. OpenStreetMap Ecosystem

### 1.1 OSMnx (Current Solution)

**Status:** Already integrated in MapToPoster via `modules/poster_generator.py`

| Aspect | Details |
|--------|---------|
| Version | 2.1.0 (Feb 2026) |
| License | MIT |
| Data Source | Overpass API + Nominatim |
| Output | NetworkX graphs + GeoPandas dataframes |
| Dependencies | GeoPandas, NetworkX, NumPy, Shapely, Matplotlib |

**Capabilities:**
- Street networks (drive, walk, bike, all)
- Building footprints, parks, water bodies
- Any OSM feature via tags (railways, amenities, POIs)
- Built-in rate limiting and caching
- Direct rendering via Matplotlib

**Rate Limits (inherited):**
- Overpass API: ~10,000 requests/day, HTTP 429 on overload
- Nominatim: 1 request/second, ~2,500/day

**Verdict:** Excellent. Keep as primary data source.

### 1.2 Overpass API

| Aspect | Details |
|--------|---------|
| Cost | Free |
| Rate Limit | Slot-based, ~10K requests/day recommended |
| Timeout | 180s default (configurable) |
| Memory | 512 MiB per request default |
| Commercial Use | Allowed |

**Key considerations:**
- HTTP 429 when rate limited (implement exponential backoff)
- HTTP 504 on resource exhaustion
- Cache aggressively — city map data rarely changes
- For high volume (>10K/day): self-host Overpass instance

### 1.3 Nominatim Geocoding

| Aspect | Public Instance | Self-Hosted |
|--------|----------------|-------------|
| Cost | Free | ~$20-50/month VPS |
| Rate Limit | 1 req/sec, ~2,500/day | Unlimited |
| Autocomplete | Forbidden | Allowed |
| Bulk Geocoding | Discouraged | Allowed |
| Commercial | Limited | Full |

**Recommendation for MVP:** Public Nominatim is sufficient for user-triggered geocoding (one lookup per poster). Self-host when scaling past ~2,000 posters/day.

### 1.4 OSM Tile Servers

**tile.openstreetmap.org — NOT recommended:**
- No SLA, access can be revoked without notice
- Bulk downloading and offline use prohibited
- Not suitable for poster generation pipeline

**Alternative tile providers (for interactive preview only):**

| Provider | Free Tier | Paid Starting | Key Styles |
|----------|-----------|---------------|------------|
| Stadia Maps | 200K credits/mo (non-commercial) | $20/month | Stamen Toner, Terrain, Watercolor |
| Thunderforest | 150K requests/mo | $125/month | Transport, Outdoors, Atlas |
| Geoapify | 3K credits/day | $59/month | Positron, Dark Matter, OSM |

### 1.5 ODbL License — Commercial Rights

**Can we sell posters made from OSM data? YES.**

- Posters are "Produced Works" — not derivative databases
- No share-alike requirement for produced works
- No license fees or royalties
- **Only requirement:** Attribution "© OpenStreetMap contributors" on every poster
- Many existing businesses (Mapiful, Grafomap, etc.) operate this model

---

## 2. Google Maps Platform

### 2.1 Pricing Overview

| API | Cost per 1,000 requests | Free Tier |
|-----|------------------------|-----------|
| Static Maps | $2.00 | 10K/month |
| JavaScript Maps | $7.00 per 1K loads | 10K/month |
| Geocoding | $5.00 | 10K/month |

### 2.2 Static Maps API

- **Max resolution:** 640x640 (1280x1280 with scale=2)
- **Custom styling:** Yes, extensive (nearly 100 features, colors, visibility)
- **Styling tools:** Styling Wizard, Cloud-based styling, JSON styles

### 2.3 Commercial Use — DEALBREAKER

**Google Maps CANNOT be used for commercial poster sales.**

From Google Maps Platform Terms of Service:
> "Consumer & retail goods or packaging (t-shirts, beach towels, shower curtains, mugs, **posters**, stationery, etc.)" are explicitly restricted.

Additional restrictions:
- Cannot create derivative products from Google Maps content
- Cannot incorporate content as "core part of printed matter redistributed for a fee"
- Print limited to 5,000 copies for supplemental business collateral only
- 30-day cache maximum (no offline rendering)
- Enterprise license required for any print merchandise — custom pricing, not publicly available

### 2.4 Geocoding Comparison

| Feature | Google | Nominatim |
|---------|--------|-----------|
| Accuracy | ~99.9% | ~70-80% |
| Cost | $5/1K after 10K free | Free |
| Rate Limit | 50 req/sec | 1 req/sec |
| Data Caching | 30-day max | Unlimited |
| Self-Hosting | No | Yes |

**Verdict:** Google geocoding could be used as a fallback for accuracy, but Nominatim is sufficient for city-level lookups. The existing `geocoding.py` module already implements Nominatim with Google Places fallback — keep this architecture.

---

## 3. Mapbox

### 3.1 Static Images API

| Aspect | Details |
|--------|---------|
| Free Tier | 50K requests/month |
| Paid | $1.00 per 1,000 requests |
| Max Resolution | 1280x1280 (2560x2560 @2x retina) |
| Custom Styles | Excellent (Mapbox Studio, LUTs, monochrome) |

### 3.2 Commercial Print Rights

- **Standard plan:** Up to 2,000 print copies/year with attribution
- **Higher volumes:** Contact sales for custom pricing
- Attribution required on all prints

### 3.3 Mapbox Studio Styling

- Component-based editing
- Dark/light monochrome themes (ideal for poster aesthetics)
- Custom color LUTs (Look-Up Tables)
- Full custom icon and font support

**Verdict:** Viable for low-volume poster sales (<2K/year). Resolution limit (2560x2560) insufficient for large posters (A2 at 300 DPI needs ~5000x7000px). Best used for interactive preview, not final render.

---

## 4. Self-Hosted Rendering Options

### 4.1 TileServer GL + MapLibre

| Aspect | Details |
|--------|---------|
| Cost | $0 software + hosting (~$20-50/month) |
| License | BSD (open source) |
| Max Resolution | Configurable (hardware-limited) |
| Styling | MapLibre GL styles (full customization) |
| Output | PNG, JPG, WEBP |
| Default Limits | 2048x2048 (adjustable via maxSize) |

**Pros:** Full control, no API limits, custom styles, unlimited commercial use
**Cons:** DevOps overhead, storage for tile data, moderate setup complexity

### 4.2 pymgl (Python MapLibre)

| Aspect | Details |
|--------|---------|
| Cost | Free |
| Output | PNG image data |
| Resolution | Hardware-limited |
| Use Case | Server-side rendering for print |

**Verdict:** Good option for future high-quality renders. Current Matplotlib pipeline is adequate for MVP.

### 4.3 Mapnik

| Aspect | Details |
|--------|---------|
| Cost | Free (open source) |
| Resolution | Unlimited (vector-based) |
| Styling | CartoCSS or XML |
| Performance | Fast, C++ core |
| Python Binding | python-mapnik |

**Verdict:** Industry standard for OSM rendering. Consider for v2 if Matplotlib performance becomes a bottleneck.

---

## 5. Provider Comparison Matrix

| Provider | Free Tier | Cost/1K Renders | Max Resolution | Custom Styles | Commercial Print | Self-Host |
|----------|-----------|----------------|----------------|---------------|-----------------|-----------|
| **OSMnx + Matplotlib** | Unlimited | $0 | Unlimited (vector) | Full control | Yes (ODbL attribution) | Yes |
| **Google Maps** | 10K/mo | $2.00 | 1280x1280 | Good | **NO (ToS prohibits posters)** | No |
| **Mapbox** | 50K/mo | $1.00 | 2560x2560 | Excellent | Limited (2K copies/yr) | No |
| **Stadia Maps** | 200K credits | ~$0.03/credit | Not specified | Good | Up to 5K copies/image | No |
| **MapTiler** | No static free | Varies | Not specified | Good | OSM attribution | Yes (paid) |
| **TileServer GL** | Unlimited | $0 + hosting | Configurable | Full (MapLibre) | Yes (ODbL) | Yes |
| **Mapnik** | Unlimited | $0 + hosting | Unlimited | Full (CartoCSS) | Yes (ODbL) | Yes |

---

## 6. Recommended Architecture for MapToPoster

### MVP (Current + Improvements)

```
User Input
    │
    ├── Geocoding: Nominatim (with Google Places fallback)
    │
    ├── Map Data: OSMnx → Overpass API
    │   └── Cache: Local pickle files (existing)
    │
    ├── Rendering: Matplotlib (existing pipeline)
    │   ├── Roads, water, parks, buildings (OSMnx)
    │   ├── Theme system (30+ JSON themes)
    │   └── Text overlay + gradient fades
    │
    └── Output: PNG/SVG/PDF at 300-600 DPI
```

### Future Scale (v2)

```
User Input
    │
    ├── Geocoding: Self-hosted Nominatim
    │
    ├── Interactive Preview: MapLibre GL JS + self-hosted vector tiles
    │
    ├── Map Data: Overpass API with Redis cache
    │
    ├── Rendering: Mapnik or MapLibre Native (server-side)
    │   └── Worker queue for async generation
    │
    └── Output: High-res PNG/PDF, print-ready
```

### Cost Projections

| Volume | Monthly Cost | Stack |
|--------|-------------|-------|
| 0-100 posters/mo | $0 (development) | OSMnx + Matplotlib (current) |
| 100-1,000/mo | $20-50 | + VPS for API, local cache |
| 1,000-10,000/mo | $50-150 | + Redis cache, self-hosted Nominatim |
| 10,000+/mo | $150-500 | + Self-hosted Overpass, worker queue, CDN |

---

## 7. Attribution Requirements Summary

Every poster must include:

```
© OpenStreetMap contributors
```

Best practices:
- Small text in bottom corner (existing attribution area at y=0.02)
- Link to openstreetmap.org/copyright on website/product pages
- One attribution per poster is sufficient

---

## Sources

### OpenStreetMap
- [OSMF Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)
- [Overpass API Documentation](https://dev.overpass-api.de/overpass-doc/en/)
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
- [ODbL License FAQ](https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ)
- [OSMnx Documentation](https://osmnx.readthedocs.io/)
- [Commercial use of OSM in poster-prints](https://help.openstreetmap.org/questions/20608/)

### Google Maps
- [Maps Platform Pricing](https://mapsplatform.google.com/pricing/)
- [Maps Platform Terms of Service](https://cloud.google.com/maps-platform/terms)
- [Service Specific Terms (print restrictions)](https://cloud.google.com/maps-platform/terms/maps-service-terms)

### Mapbox
- [Mapbox Pricing](https://www.mapbox.com/pricing)
- [Static Images API](https://docs.mapbox.com/api/maps/static-images/)
- [Product Terms (print media)](https://www.mapbox.com/legal/product-terms)

### Other Providers
- [Stadia Maps Pricing](https://stadiamaps.com/pricing/)
- [Thunderforest Pricing](https://www.thunderforest.com/pricing/)
- [Geoapify Pricing](https://www.geoapify.com/pricing/)
- [TileServer GL](https://github.com/maptiler/tileserver-gl)
- [pymgl](https://github.com/brendan-ward/pymgl)
