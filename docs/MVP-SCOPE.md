# MapToPoster — MVP Scope Definition

> Version: 1.0
> Date: February 2026
> Status: Draft

---

## Product Vision

**MapToPoster** turns any location in the world into a beautiful, minimalist map poster — ready to print and hang on a wall. Users enter a city or address, choose a style, customize text and colors, and receive a high-resolution poster file.

**Target market:** Personal wall art, gifts, home decor.
**Revenue model:** Direct poster file sales (digital download) with optional print-on-demand.

---

## What Already Exists

The codebase has significant functionality built:

| Component | Status | Details |
|-----------|--------|---------|
| CLI poster generation | Working | `create_map_poster.py` |
| Streamlit GUI | Working | `gui_app.py` |
| Modular architecture | Working | `modules/` (config, geocoding, poster_generator, text_positioning) |
| 30+ themes | Working | `themes/*.json` |
| 5 font families | Working | `fonts/` |
| Detail layers | Working | Buildings, paths, railways, waterways, etc. |
| FastAPI backend | Scaffolded | `backend/` (service registry, geocoding, generator) |
| Web widget | Scaffolded | `frontend/widget/` |
| Docker setup | Configured | `Dockerfile`, `docker-compose.yml` |
| Text personalization | Working | Custom city/country text, subtitle, coords format |
| Color personalization | Working | Background, water, parks, road colors |
| Paper sizes | Working | A2, A3, A4, A5 |
| Export formats | Working | PNG, SVG, PDF |

---

## MVP Scope — "First Sellable Product"

The MVP goal is: **A web app where a user can create and purchase a custom map poster in under 5 minutes.**

### IN Scope (MVP v1.0)

#### 1. Core Map Generation
- [x] Location input via city/country name or address
- [x] Geocoding via Nominatim (with Google Places fallback)
- [x] Map data from OpenStreetMap via OSMnx
- [x] Road hierarchy rendering (motorway → residential)
- [x] Water bodies, parks, buildings
- [x] Configurable map radius (zoom level)
- [ ] **Quick preview mode** (low-res, <3 seconds)
- [ ] **Final render** (300 DPI, high-quality, async)

#### 2. Design & Styling
- [x] Theme selection (30+ pre-built themes)
- [x] 5 font families
- [x] Detail layers (buildings, paths, railways at close zoom)
- [ ] **Theme preview gallery** (show all themes for selected location)
- [ ] **Top 6-8 curated themes** for MVP (reduce choice paralysis)

#### 3. Text Personalization
- [x] Custom city name text
- [x] Custom country text
- [x] Custom subtitle
- [x] 4 coordinate format options
- [x] Custom coordinates text override
- [x] Text color override

#### 4. Color Personalization
- [x] Background color override
- [x] Water color override
- [x] Parks color override
- [x] Individual road color overrides
- [ ] **Color presets** (5-8 quick-select palettes)

#### 5. Paper & Output
- [x] Paper sizes: A2, A3, A4, A5
- [x] Formats: PNG, SVG, PDF
- [x] 300/600 DPI output
- [ ] **Poster orientation** (portrait/landscape)
- [ ] **Print-ready PDF** with bleed marks

#### 6. Web Frontend
- [ ] **Location search** with autocomplete
- [ ] **Live map preview** (interactive, low-res)
- [ ] **Theme selector** with visual thumbnails
- [ ] **Text customization panel**
- [ ] **Color customization panel**
- [ ] **Paper size selector**
- [ ] **Download button** (after payment)

#### 7. Backend API
- [x] FastAPI scaffolding with service registry
- [ ] **POST /generate-preview** — quick low-res preview
- [ ] **POST /generate-poster** — full-res async generation
- [ ] **GET /poster/{id}** — download completed poster
- [ ] **GET /themes** — list available themes with thumbnails
- [ ] **Background job queue** for poster generation (Celery or similar)

#### 8. Payment (Minimal)
- [ ] **Stripe Checkout** integration (single payment per poster)
- [ ] **Pricing:** 3 tiers by paper size (e.g., A4: €9.99, A3: €14.99, A2: €19.99)
- [ ] **Digital delivery:** Download link after payment

#### 9. Legal & Attribution
- [ ] OSM attribution on every poster ("© OpenStreetMap contributors")
- [ ] Terms of service page
- [ ] Privacy policy (GDPR-compliant for EU market)

---

### OUT of Scope (Post-MVP)

These are planned but not in the initial release:

| Feature | Planned Phase |
|---------|---------------|
| Print-on-demand (Printful/Gelato) | v1.1 |
| User accounts & order history | v1.1 |
| Custom map area selection (drag bounding box) | v1.1 |
| Framing options & mockup preview | v1.2 |
| Gift cards / gift wrapping | v1.2 |
| Multi-poster sets (city pairs, trip maps) | v1.2 |
| GPS track overlay (running routes, trips) | v2.0 |
| 3D building rendering | v2.0 |
| Satellite/aerial photo posters | v2.0 |
| Mobile app | v2.0 |
| API for third-party integrations | v2.0 |
| Subscription model (poster credits) | v2.0 |
| Social sharing / community gallery | v2.0 |
| White-label / B2B offering | v3.0 |

---

## Technical Architecture — MVP

### Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Frontend   │────▶│  Backend API │────▶│  Poster Worker   │
│  (React/Vue) │◀────│  (FastAPI)   │◀────│  (Celery/RQ)     │
└──────────────┘     └──────────────┘     └──────────────────┘
                            │                      │
                     ┌──────┴──────┐        ┌──────┴──────┐
                     │   Stripe    │        │   OSMnx +   │
                     │  Payments   │        │  Matplotlib  │
                     └─────────────┘        └─────────────┘
                                                   │
                                            ┌──────┴──────┐
                                            │ Overpass API│
                                            │ + Nominatim │
                                            └─────────────┘
```

### Technology Choices

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | React + Vite (or Next.js) | Modern, fast, good ecosystem |
| **Interactive Map Preview** | MapLibre GL JS | Free, customizable, OSM-based |
| **Backend API** | FastAPI (Python) | Already scaffolded, async support |
| **Map Data** | OSMnx + Overpass API | Already integrated, free, commercial-OK |
| **Rendering** | Matplotlib (existing pipeline) | Working, poster-quality output |
| **Job Queue** | Celery + Redis (or RQ) | Async poster generation |
| **Payment** | Stripe Checkout | Simple integration, global |
| **File Storage** | S3-compatible (Cloudflare R2 or AWS S3) | Poster file delivery |
| **Hosting** | Vercel (frontend) + VPS/Railway (backend) | Cost-effective |
| **Database** | PostgreSQL (or SQLite for MVP) | Order tracking |

### Map Data Strategy (from API Research)

**Primary stack (free, unlimited):**
- OSMnx for street networks and features (roads, water, parks, buildings)
- Overpass API as the underlying data source
- Nominatim for geocoding (public API for MVP, self-hosted when scaling)
- Matplotlib for server-side poster rendering

**Why not Google Maps:** ToS explicitly prohibits poster sales.
**Why not Mapbox:** Resolution limit (2560px) insufficient for large posters; 2K copies/year limit.
**Why OSM wins:** Free, open license (ODbL), unlimited commercial use, unlimited resolution (vector-based), full rendering control.

See [MAP-API-RESEARCH.md](./MAP-API-RESEARCH.md) for detailed analysis.

---

## MVP Feature Priority Matrix

| Priority | Feature | Effort | Impact | Status |
|----------|---------|--------|--------|--------|
| P0 | Map generation (core) | Done | Critical | Working |
| P0 | Theme system | Done | High | Working |
| P0 | Text/color personalization | Done | High | Working |
| P0 | Backend API (generate endpoint) | Medium | Critical | Scaffolded |
| P0 | Payment (Stripe Checkout) | Medium | Critical | Not started |
| P1 | Web frontend (location input + preview) | Large | Critical | Widget scaffolded |
| P1 | Quick preview mode | Medium | High | Not started |
| P1 | Async job queue | Medium | High | Not started |
| P1 | File storage + delivery | Small | Critical | Not started |
| P2 | Theme preview gallery | Small | Medium | Not started |
| P2 | Color presets | Small | Medium | Not started |
| P2 | Print-ready PDF | Small | Medium | Not started |
| P3 | User accounts | Medium | Low (for MVP) | Not started |

---

## Curated Theme Selection for MVP

From the 30+ existing themes, these 8 are recommended for MVP to minimize choice paralysis while covering popular aesthetics:

| Theme | Style | Best For |
|-------|-------|----------|
| `noir` | Pure black + white roads | Universal classic |
| `midnight_blue` | Navy + gold | Elegant, gift-worthy |
| `warm_beige` | Vintage sepia | Cozy, timeless |
| `japanese_ink` | Ink wash minimalist | Artistic, unique |
| `neon_cyberpunk` | Dark + electric colors | Modern, bold |
| `blueprint` | Architectural blue | Technical, distinctive |
| `feature_based` | Classic colored roads | Detailed, informative |
| `forest` | Deep greens | Nature lovers |

---

## Success Metrics — MVP Launch

| Metric | Target | Measurement |
|--------|--------|-------------|
| Poster generation time | < 30 seconds (full res) | Server logs |
| Preview generation time | < 3 seconds | Frontend timing |
| Conversion rate | > 2% visitors → purchase | Stripe + analytics |
| First month revenue | > €500 | Stripe dashboard |
| Customer satisfaction | < 5% refund rate | Support tickets |
| Uptime | > 99% | Monitoring |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| OSM data quality varies by region | Medium | Medium | Show preview before purchase; curate popular cities |
| Overpass API rate limiting under load | Low | High | Implement caching (Redis), exponential backoff |
| Poster generation too slow for users | Medium | High | Quick preview + async generation with email delivery |
| Low conversion without print-on-demand | Medium | Medium | Launch with digital-only; add print in v1.1 |
| Stripe compliance (digital goods) | Low | Medium | Proper ToS, refund policy |

---

## Related Tasks

This MVP scope connects to these Kanban tasks:

1. **Backend Core API Development** — Implements P0 API endpoints, job queue, file storage
2. **Advanced Design Template System** — Extends theme system, adds theme previews
3. **Frontend UI for Location Input & Preview** — Builds the web frontend
4. **User Personalization Features** — Already implemented (text/color customization)
5. **Map Data Integration & Basic Rendering PoC** — Already working (OSMnx pipeline)
