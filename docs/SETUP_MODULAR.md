# MapToPoster - Modular Web Integration

## 🚀 Quick Start

### 1. Start the Backend API

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run the API
cd backend
python main.py
```

API will be available at: `http://localhost:8000`  
API Documentation (Swagger): `http://localhost:8000/api/v1/docs`

### 2. Test the Web Widget

```bash
# Serve widget demo page
cd frontend/widget
python -m http.server 3000
```

Open: `http://localhost:3000/demo.html`

### 3. Using Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# API: http://localhost:8000
# Widget Demo: http://localhost:8080
```

---

## 📦 Architecture Overview

### Modular Service System

```
┌─────────────────────────────────────────┐
│         Application Layer                │
│   (FastAPI API + Web Widget)             │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Service Registry                   │
│  (Dynamic Service Loading/Management)    │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐  ┌──▼───┐  ┌──▼───┐
│ Core  │  │Plugin│  │Plugin│
│Service│  │  1   │  │  2   │
└───────┘  └──────┘  └──────┘
```

### Core Services (Always Active)

1. **GeocodingService** - Address → Coordinates
2. **PosterGeneratorService** - Map Rendering
3. **ThemeService** - Theme Management
4. **ExportService** - Export (PNG/SVG/PDF)

### Plugin Services (Optional)

1. **CacheService** - Redis caching
2. **StorageService** - S3/Cloud storage
3. **PaymentService** - Stripe integration
4. **PrintService** - Printful fulfillment
5. **AnalyticsService** - User tracking

---

## 🔌 Service Management

### Enable/Disable Services via Config

Edit `config.yaml`:

```yaml
services:
  geocoding:
    enabled: true  # Change to false to disable
  
  cache:
    enabled: false  # Enable for Redis caching
    redis_url: "redis://localhost:6379"
```

### Enable/Disable Services via API

```bash
# Enable cache service
curl -X POST http://localhost:8000/api/v1/services/cache/enable

# Disable cache service
curl -X POST http://localhost:8000/api/v1/services/cache/disable

# List all services
curl http://localhost:8000/api/v1/services
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

---

## 🌐 Web Widget Integration

### Vanilla JavaScript

```html
<div id="maptoposter-widget"></div>
<script src="https://cdn.maptoposter.com/widget.js"></script>
<script>
  MapToPosterWidget.init({
    container: '#maptoposter-widget',
    apiUrl: 'http://localhost:8000/api/v1'
  });
</script>
```

### React (Coming Soon)

```jsx
import { MapToPosterWidget } from '@maptoposter/react';

function App() {
  return (
    <MapToPosterWidget
      apiKey="your-api-key"
      theme="noir"
      services={{ geocoding: true, generator: true }}
    />
  );
}
```

---

## 🛠️ API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/geocode` | Geocode an address |
| POST | `/api/v1/posters/generate` | Generate poster |
| GET | `/api/v1/themes` | List available themes |
| GET | `/api/v1/services` | List all services |
| GET | `/api/v1/health` | Health check |

### Example: Geocode Address

```bash
curl -X POST http://localhost:8000/api/v1/geocode \
  -H "Content-Type: application/json" \
  -d '{"address": "Berlin, Germany"}'
```

### Example: Generate Poster

```bash
curl -X POST http://localhost:8000/api/v1/posters/generate \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 52.5200,
    "longitude": 13.4050,
    "city_name": "Berlin",
    "country_name": "Germany",
    "theme": "noir",
    "distance": 8000,
    "paper_size": "A4",
    "dpi": 300
  }'
```

---

## 📝 Creating Custom Services (Plugins)

### 1. Create Service Class

```python
# backend/plugins/custom_service.py

from backend.core.service_registry import BaseService, ServiceMetadata

class CustomService(BaseService):
    @classmethod
    def get_metadata(cls) -> ServiceMetadata:
        return ServiceMetadata(
            name="custom",
            version="1.0.0",
            description="My custom service",
            dependencies=[],  # List dependencies
            optional=True
        )
    
    async def initialize(self) -> bool:
        # Setup logic
        self._initialized = True
        return True
    
    async def shutdown(self) -> bool:
        # Cleanup logic
        self._initialized = False
        return True
    
    async def health_check(self) -> dict:
        return {
            "healthy": True,
            "message": "Service OK"
        }
    
    # Your custom methods
    async def do_something(self):
        pass
```

### 2. Register Service

```python
# backend/main.py

from backend.plugins.custom_service import CustomService

@app.on_event("startup")
async def startup_event():
    # Register custom service
    service_registry.register(CustomService)
    
    # Enable if configured
    if config_manager.is_service_enabled("custom"):
        await service_registry.enable("custom")
```

### 3. Configure Service

```yaml
# config.yaml

services:
  custom:
    enabled: true
    custom_setting: "value"
```

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest backend/tests/
```

---

## 📚 Documentation

- **API Docs (Swagger):** `http://localhost:8000/api/v1/docs`
- **Architecture:** `docs/ARCHITECTURE_MODULAR.md`
- **Service Registry:** `backend/core/service_registry.py`
- **Configuration:** `backend/core/config.py`

---

## 🔒 Security

### API Key Authentication (Coming Soon)

```python
# backend/middleware/auth.py

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(credentials = Security(security)):
    api_key = credentials.credentials
    # Verify API key
    if not is_valid_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

### Rate Limiting

Configured in `config.yaml`:

```yaml
rate_limit:
  enabled: true
  requests_per_minute: 60
  burst: 10
```

---

## 🚀 Production Deployment

### Environment Variables

```bash
export APP_DEBUG=false
export APP_PORT=8000

# Optional services
export SERVICE_CACHE_ENABLED=true
export REDIS_URL=redis://redis:6379

export SERVICE_STORAGE_ENABLED=true
export S3_BUCKET=maptoposter-posters
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx

export SERVICE_PAYMENT_ENABLED=true
export STRIPE_SECRET_KEY=sk_xxx
```

### Docker Production

```bash
# Build image
docker build -t maptoposter-api:latest .

# Run container
docker run -p 8000:8000 \
  -e APP_DEBUG=false \
  -e SERVICE_CACHE_ENABLED=true \
  maptoposter-api:latest
```

---

## 🆘 Troubleshooting

### Service Won't Start

```bash
# Check service status
curl http://localhost:8000/api/v1/services

# Check health
curl http://localhost:8000/api/v1/health
```

### Enable Debug Logging

```yaml
# config.yaml
app:
  debug: true
```

---

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Pull requests are welcome! See `docs/CONTRIBUTING.md`
