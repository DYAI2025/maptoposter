# MapToPoster - Modulare Web-Integration Architektur

## 🎯 Ziel

Transformation des MapToPoster-Tools in ein **modulares, plugin-basiertes System** mit:

- ✅ Einfache Website-Integration (Embed-Widget)
- ✅ Vollständig modulare Services (aktivierbar/deaktivierbar)
- ✅ RESTful API Backend
- ✅ Moderne Web-Komponenten (React/Vue/Vanilla JS)
- ✅ Plugin-System für Erweiterungen

---

## 🏗️ System-Architektur

```text
┌─────────────────────────────────────────────────────────────┐
│                    Client Websites                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Embed JS   │  │  React SDK   │  │   Vue SDK    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   API Gateway    │
                    │   (FastAPI)      │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
    │  Service  │     │  Service  │     │  Service  │
    │  Registry │     │   API     │     │   Core    │
    └─────┬─────┘     └─────┬─────┘     └─────┬─────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼─────────┐
                    │     Modules      │
                    │  (Plugins)       │
                    └──────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
  ┌─────▼──────┐      ┌─────▼──────┐      ┌─────▼──────┐
  │  Geocoding │      │   Poster   │      │   Themes   │
  │   Service  │      │  Generator │      │   Service  │
  └────────────┘      └────────────┘      └────────────┘
        │                    │                    │
  ┌─────▼──────┐      ┌─────▼──────┐      ┌─────▼──────┐
  │   Cache    │      │   Export   │      │   Custom   │
  │   Service  │      │  Service   │      │   Themes   │
  └────────────┘      └────────────┘      └────────────┘
```

---

## 📦 Modul-System (Plugin-Architektur)

### Service-Registry-Pattern

Jeder Service ist:

- **Eigenständig**: Kann ohne andere Services funktionieren
- **Austauschbar**: Interface-basiert, verschiedene Implementierungen möglich
- **Konfigurierbar**: Aktivierung/Deaktivierung via Config
- **Erweiterbar**: Plugins können Services hinzufügen

### Core Services (Minimal-Setup)

1. **GeocodingService** - Adresse → Koordinaten
2. **PosterGeneratorService** - OSM-Daten → Poster-Rendering
3. **ThemeService** - Theme-Verwaltung & Custom Themes
4. **ExportService** - PNG/SVG/PDF-Export

### Optional Services (Plugins)

1. **CacheService** - Redis/Memory-Cache für Geocoding
2. **StorageService** - S3/Cloud-Storage für generierte Poster
3. **PaymentService** - Stripe/PayPal-Integration
4. **PrintService** - Printful/Gelato-Integration
5. **AnalyticsService** - User-Tracking & Metrics
6. **EmailService** - Order-Confirmations, Newsletter
7. **CustomizationService** - Text-Overlays, Multi-Panel
8. **WatermarkService** - Branding/Logo-Integration

---

## 🌐 Web-Integration (Embed-Widget)

### Option 1: JavaScript Embed (Vanilla JS)

**Einfachste Integration:**

```html
<!-- Minimal Setup -->
<div id="maptoposter-widget"></div>
<script src="https://cdn.maptoposter.com/widget.js"></script>
<script>
  MapToPosterWidget.init({
    container: '#maptoposter-widget',
    apiKey: 'your-api-key',
    theme: 'noir',
    enabledServices: ['geocoding', 'generator', 'themes', 'export']
  });
</script>
```

**Features:**

- ✅ Keine Framework-Abhängigkeit
- ✅ ~50KB gzipped
- ✅ Responsive & Mobile-optimiert
- ✅ Customizable CSS (CSS Variables)

### Option 2: React SDK

```jsx
import { MapToPosterWidget } from '@maptoposter/react';

function MyApp() {
  return (
    <MapToPosterWidget
      apiKey="your-api-key"
      theme="noir"
      services={{
        geocoding: true,
        generator: true,
        themes: true,
        export: true,
        payment: true,  // Optional
        print: false     // Deaktiviert
      }}
      onGenerate={(posterData) => {
        console.log('Poster generated!', posterData);
      }}
    />
  );
}
```

### Option 3: Vue SDK

```vue
<template>
  <MapToPosterWidget
    :api-key="apiKey"
    theme="noir"
    :services="enabledServices"
    @generate="handleGenerate"
  />
</template>

<script setup>
import { MapToPosterWidget } from '@maptoposter/vue';

const apiKey = 'your-api-key';
const enabledServices = {
  geocoding: true,
  generator: true,
  themes: true,
  export: true
};

const handleGenerate = (posterData) => {
  console.log('Poster generated!', posterData);
};
</script>
```

---

## 🔌 API-Struktur (FastAPI Backend)

### Core Endpoints

```http
POST   /api/v1/geocode              # Geocoding-Service
POST   /api/v1/posters/generate     # Poster-Generierung
GET    /api/v1/themes                # Theme-Liste
GET    /api/v1/themes/{id}          # Theme Details
POST   /api/v1/themes/custom        # Custom Theme erstellen
POST   /api/v1/export               # Export (PNG/SVG/PDF)
```

### Service-Management (Admin)

```http
GET    /api/v1/services              # Verfügbare Services
GET    /api/v1/services/status       # Service-Status
POST   /api/v1/services/{id}/enable  # Service aktivieren
POST   /api/v1/services/{id}/disable # Service deaktivieren
GET    /api/v1/config                # Aktuelle Konfiguration
```

### Optional Endpoints (Plugin-basiert)

```http
# Payment Service
POST   /api/v1/payments/checkout     # Stripe Checkout Session
POST   /api/v1/payments/webhook      # Stripe Webhook

# Print Service
POST   /api/v1/print/order           # Printful Order
GET    /api/v1/print/status/{id}     # Order Status

# Storage Service
POST   /api/v1/storage/upload        # Poster-Upload (S3)
GET    /api/v1/storage/{id}          # Poster-Download-Link
```

---

## 🛠️ Implementierungs-Phasen

### Phase 1: Core Backend (Woche 1-2)

- [ ] Service-Registry-System
- [ ] Plugin-Loader-Mechanismus
- [ ] Core Services (Geocoding, Generator, Themes, Export)
- [ ] FastAPI-Setup mit Auto-Dokumentation
- [ ] Configuration-Management (YAML/JSON)
- [ ] Docker-Setup

### Phase 2: Web-Widget (Woche 3-4)

- [ ] Vanilla JS Widget (Embed-Script)
- [ ] UI-Komponenten (Theme-Selector, Map-Preview, Export-Options)
- [ ] Responsive Design (Mobile-First)
- [ ] CSS Variables für Customization
- [ ] Event-System (onGenerate, onExport, onError)

### Phase 3: Optional Services (Woche 5-6)

- [ ] Cache-Service (Redis)
- [ ] Storage-Service (S3)
- [ ] Analytics-Service (Basic Tracking)
- [ ] Payment-Service (Stripe Stub)

### Phase 4: SDKs (Woche 7-8)

- [ ] React SDK (@maptoposter/react)
- [ ] Vue SDK (@maptoposter/vue)
- [ ] TypeScript-Definitionen
- [ ] NPM-Publishing

---

## 📁 Dateistruktur

```plaintext
maptoposter/
├── backend/                   # FastAPI Backend
│   ├── api/                   # API-Endpoints
│   │   ├── v1/
│   │   │   ├── geocoding.py
│   │   │   ├── posters.py
│   │   │   ├── themes.py
│   │   │   ├── export.py
│   │   │   └── services.py
│   │   └── dependencies.py
│   ├── core/                  # Core System
│   │   ├── service_registry.py
│   │   ├── plugin_loader.py
│   │   ├── config.py
│   │   └── events.py
│   ├── services/              # Service Implementations
│   │   ├── base.py           # Base Service Interface
│   │   ├── geocoding/
│   │   │   ├── __init__.py
│   │   │   ├── nominatim.py  # Nominatim Implementation
│   │   │   └── google.py     # Google Places (fallback)
│   │   ├── generator/
│   │   │   ├── __init__.py
│   │   │   └── osm_generator.py
│   │   ├── themes/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py
│   │   │   └── custom.py
│   │   └── export/
│   │       ├── __init__.py
│   │       ├── png.py
│   │       ├── svg.py
│   │       └── pdf.py
│   ├── plugins/               # Optional Services (Plugins)
│   │   ├── cache/
│   │   ├── storage/
│   │   ├── payment/
│   │   ├── print/
│   │   └── analytics/
│   ├── main.py               # FastAPI App
│   ├── config.yaml           # Service Configuration
│   └── requirements.txt
│
├── frontend/                  # Web-Widget & SDKs
│   ├── widget/               # Vanilla JS Widget
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── api/
│   │   │   ├── utils/
│   │   │   ├── styles/
│   │   │   └── index.js
│   │   ├── dist/
│   │   │   └── widget.min.js
│   │   └── package.json
│   ├── react-sdk/            # React SDK
│   │   ├── src/
│   │   └── package.json
│   └── vue-sdk/              # Vue SDK
│       ├── src/
│       └── package.json
│
├── modules/                   # Existing Python Modules (legacy)
├── themes/                    # Theme JSON files
├── fonts/                     # Font files
├── docker-compose.yml
└── README.md
```

---

## 🔧 Service Configuration (config.yaml)

```yaml
# Core Settings
app:
  name: "MapToPoster API"
  version: "2.0.0"
  debug: false
  api_prefix: "/api/v1"

# Service Registry
services:
  # Core Services (always enabled)
  geocoding:
    enabled: true
    provider: "nominatim"
    fallback: "google"
    cache_ttl: 86400
  
  generator:
    enabled: true
    default_theme: "feature_based"
    max_distance: 50000
    default_dpi: 300
  
  themes:
    enabled: true
    allow_custom: true
    max_custom_themes_per_user: 10
  
  export:
    enabled: true
    formats: ["png", "svg", "pdf"]
    max_file_size_mb: 50

  # Optional Services (plugins)
  cache:
    enabled: false
    provider: "redis"
    redis_url: "redis://localhost:6379"
  
  storage:
    enabled: false
    provider: "s3"
    bucket: "maptoposter-posters"
    region: "eu-central-1"
  
  payment:
    enabled: false
    provider: "stripe"
    stripe_key: "${STRIPE_SECRET_KEY}"
    webhook_secret: "${STRIPE_WEBHOOK_SECRET}"
  
  print:
    enabled: false
    provider: "printful"
    api_key: "${PRINTFUL_API_KEY}"
  
  analytics:
    enabled: false
    provider: "custom"
    tracking_id: "UA-XXXXX-Y"

# Rate Limiting
rate_limit:
  enabled: true
  requests_per_minute: 60
  burst: 10

# CORS
cors:
  enabled: true
  origins: ["*"]
  methods: ["GET", "POST"]
```

---

## 🎨 UI-Komponenten (Modulare Widgets)

### Komponenten-Bibliothek

1. **ThemeSelector** - Theme-Auswahl mit Previews
2. **LocationInput** - Adresse/Koordinaten-Eingabe
3. **CustomThemeEditor** - Farbwähler für Custom Themes
4. **MapPreview** - Live-Vorschau des Posters
5. **ExportOptions** - Format/Größen-Auswahl
6. **ProgressIndicator** - Generierungs-Status
7. **DownloadButton** - Download-Link für Poster

### Customization (CSS Variables)

```css
:root {
  --mtp-primary-color: #1a3a52;
  --mtp-accent-color: #d4a574;
  --mtp-bg-color: #f5f3f0;
  --mtp-text-color: #2c2c2c;
  --mtp-border-radius: 8px;
  --mtp-font-family: 'Inter', sans-serif;
}
```

---

## 🚀 Deployment-Optionen

### Option 1: Docker Compose (Self-Hosted)

```bash
docker-compose up -d
# API läuft auf http://localhost:8000
# Widget einbinden via <script src="http://localhost:8000/widget.js"></script>
```

### Option 2: Cloud (Serverless)

- **Backend:** AWS Lambda / Google Cloud Functions
- **Widget CDN:** Cloudflare/AWS CloudFront
- **Cache:** Redis Cloud / AWS ElastiCache
- **Storage:** S3 / Google Cloud Storage

### Option 3: Managed SaaS

```plaintext
https://api.maptoposter.com        # API
https://cdn.maptoposter.com        # Widget CDN
https://storage.maptoposter.com    # Poster-Storage
```

---

## 📊 Nächste Schritte

1. **Phase 1 starten** - Service-Registry implementieren
2. **Docker-Setup** - Entwicklungsumgebung aufsetzen
3. **API-Endpoints** - Core Services als REST-API
4. **Widget-Prototyp** - Minimales Embed-Widget (Vanilla JS)
5. **Dokumentation** - API-Docs (OpenAPI/Swagger)
6. **Testing** - Unit-Tests & Integration-Tests

---

## 💡 Erweiterungsmöglichkeiten

- **Multi-Tenancy:** Verschiedene Kunden mit eigenen Configs
- **White-Labeling:** Custom Branding pro Kunde
- **Webhooks:** Event-Benachrichtigungen (poster.generated, order.completed)
- **GraphQL API:** Alternative zu REST
- **WebSocket:** Real-time Preview-Updates
- **CLI-Tool:** `maptoposter generate --city Berlin --theme noir`
