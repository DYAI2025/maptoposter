# MapToPoster JS Integration

## Übersicht

Diese Integration kombiniert das **MapToPoster JS Frontend** (Vite/Vanilla JS) mit dem **Python FastAPI Backend** für hochwertige Poster-Generierung.

### Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    MapToPoster JS Frontend                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Leaflet     │  │ MapLibre GL  │  │ html2canvas      │   │
│  │ (Tile Map)  │  │ (Artistic)   │  │ (Export)         │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                           │                                  │
│                    API Client (api.js)                       │
└───────────────────────────┼──────────────────────────────────┘
                            │ HTTP/JSON
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Python FastAPI Backend                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Geocoding   │  │ Poster       │  │ Theme            │   │
│  │ Service     │  │ Generator    │  │ Manager          │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                           │                                  │
│                    OSMnx + Matplotlib                        │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Frontend (JS)
- **Leaflet Maps** - Standard Kachelkarten-Ansicht
- **MapLibre GL** - Künstlerische Themes mit Vektor-Tiles
- **Marker & Routen** - OSRM-basiertes Routing mit A/B-Punkten
- **Live-Vorschau** - Sofortige Visualisierung im Browser
- **html2canvas Export** - Client-seitiger PNG-Export

### Backend (Python)
- **High-Resolution Export** - Bis zu 300 DPI für Druck
- **17 Themes** - JSON-basierte Farbschemata
- **OSMnx Integration** - Rohe OpenStreetMap-Daten
- **Matplotlib Rendering** - Vektorgrafiken (SVG/PDF)
- **Geocoding** - Nominatim + Google Places Fallback

## Quick Start

### Entwicklung (Docker)

```bash
# Alle Services starten (Backend + JS Frontend)
docker-compose up -d

# Zugriff:
# - JS Frontend: http://localhost:5173
# - FastAPI Docs: http://localhost:8000/api/v1/docs
# - Streamlit GUI: docker-compose --profile streamlit up -d
```

### Lokal

**Backend:**
```bash
cd /home/dyai/Dokumente/Pers.Tests-Page/social-role/DYAI_home/DEV/TOOLS/map2poster/maptoposter
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend/webapp
npm install
npm run dev
```

## API-Endpoints

### Poster generieren
```bash
POST /api/v1/posters/generate
Content-Type: application/json

{
  "latitude": 52.52,
  "longitude": 13.405,
  "city_name": "Berlin",
  "country_name": "Germany",
  "theme": "noir",
  "distance": 8000,
  "paper_size": "A4",
  "dpi": 300
}

Response:
{
  "status": "success",
  "poster_id": "uuid...",
  "download_url": "/api/v1/posters/uuid/download"
}
```

### Themes auflisten
```bash
GET /api/v1/themes

Response:
[
  {
    "name": "Noir",
    "description": "Pure black background...",
    "colors": {
      "bg": "#000000",
      "text": "#FFFFFF",
      ...
    }
  }
]
```

### Location suchen
```bash
GET /api/v1/geocode/search?q=Berlin,Germany

Response:
[
  {
    "name": "Berlin",
    "latitude": 52.52,
    "longitude": 13.405,
    "display_name": "Berlin, Deutschland",
    "type": "locality"
  }
]
```

### Custom Theme speichern
```bash
POST /api/v1/themes
Content-Type: application/json

{
  "name": "my_theme",
  "colors": {
    "bg": "#FFFFFF",
    "text": "#000000",
    "water": "#0066CC",
    ...
  }
}
```

## Routing & Marker

Das JS-Frontend unterstützt:

### A/B Routenpunkte
```javascript
// Route von A nach B
updateState({
  routeStartLat: 52.52,
  routeStartLon: 13.405,
  routeEndLat: 52.51,
  routeEndLon: 13.39,
  showRoute: true
});
```

### Via-Punkte
```javascript
// Zwischenpunkt hinzufügen
insertViaPoint(52.515, 13.400);

// Via-Punkte werden automatisch in die Route eingefügt
// Doppelklick zum Entfernen
```

### Drag & Drop
- **A/B Marker** - Frei positionierbar
- **Route** - Per Drag neue Via-Punkte erstellen
- **Via-Punkte** - Verschiebbar, löschbar

## Theme Mapping

| JS Theme | Python Theme |
|----------|--------------|
| `minimal` | `feature_based` |
| `dark` | `noir` |
| `light` | `warm_beige` |
| `blueprint` | `blueprint` |
| `cyber_noir` | `neon_cyberpunk` |
| `ocean` | `ocean` |
| `forest` | `forest` |

## Build für Production

```bash
# Frontend bauen
cd frontend/webapp
npm run build

# Output: frontend/webapp/dist/

# Mit Nginx servieren
docker-compose --profile production up -d

# Zugriff: http://localhost:80
```

## Projektstruktur

```
maptoposter/
├── backend/                    # FastAPI Backend
│   ├── main.py                 # API mit neuen Endpoints
│   ├── services/               # Business Logic
│   └── core/                   # Config, Registry
│
├── frontend/
│   ├── webapp/                 # MapToPoster JS
│   │   ├── src/
│   │   │   ├── core/
│   │   │   │   ├── api.js      # Backend Integration
│   │   │   │   ├── state.js    # App State
│   │   │   │   └── routing.js  # OSRM Integration
│   │   │   ├── map/            # Leaflet + MapLibre
│   │   │   └── ui/             # Form Controls
│   │   ├── index.html
│   │   ├── main.js
│   │   └── vite.config.js
│   │
│   └── widget/                 # Legacy Embed Widget
│
├── modules/                    # Python Core Modules
│   ├── poster_generator.py     # Rendering Engine
│   ├── geocoding.py            # Location Services
│   └── config.py               # Constants
│
├── themes/                     # JSON Themes
├── docker-compose.yml          # Multi-Service Setup
└── README.md
```

## Umgebungsvariablen

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api/v1
```

### Backend (.env)
```env
GOOGLE_PLACES_API_KEY=your_key_here
CACHE_DIR=cache
POSTERS_DIR=posters
```

## Docker Profiles

```bash
# Standard: Backend + JS Frontend
docker-compose up -d

# Mit Streamlit GUI
docker-compose --profile streamlit up -d

# Mit Redis Cache
docker-compose --profile with-cache up -d

# Production Build
docker-compose --profile production up -d
```

## Nächste Schritte

### TODO
- [ ] Poster-Vorschau im Backend für JS-Frontend
- [ ] WebSocket für Live-Status-Updates
- [ ] Batch-Export für mehrere Poster
- [ ] User-Authentifizierung
- [ ] Cloud-Storage (S3) für generierte Poster

### Geplant
- [ ] Mapbox-Integration als Alternative zu OSM
- [ ] 3D-Gebäude im künstlerischen Modus
- [ ] QR-Codes auf Postern für digitale Version
- [ ] Print-on-Demand Integration

## Troubleshooting

### CORS Fehler
```bash
# Backend CORS prüfen
# In backend/main.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für Entwicklung
    ...
)
```

### API nicht erreichbar
```bash
# Backend Health Check
curl http://localhost:8000/api/v1/health

# Sollte zurückgeben:
{"overall_healthy": true, "services": {...}}
```

### Frontend lädt keine Tiles
```bash
# Vite Proxy prüfen
# In vite.config.js:
server: {
  proxy: {
    '/api': 'http://localhost:8000',
  },
}
```

## Lizenz

MIT - Siehe LICENSE Datei
