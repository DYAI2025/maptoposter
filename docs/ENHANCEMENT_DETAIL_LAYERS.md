# MapToPoster - Enhanced Detail Layers für Nahe Karten

## 🎯 Problem

Bei nahen/gezoomten Karten (< 2km) wirken die Poster oft leer, besonders in weniger urbanen Gebieten.

## ✅ Lösung: Mehr Detail-Layer mit unterschiedlichen Farben

### Neue Detail-Layer hinzugefügt

1. **🌳 Einzelne Bäume** (`natural=tree`)
   - Kleine Kreise in Grüntönen
   - Versch. Größen basierend auf `height` Tag

2. **🏡 Grundstücksgrenzen** (`boundary=parcel`)
   - Dünne Linien als Struktur-Element

3. **🚗 Parkplätze** (`amenity=parking`)
   - Unterschiedliche Farbe je nach Typ

4. **🏘️ Land

use** (verschiedene Arten)

- `residential` - hellgrau
- `commercial` - orange-grau
- `industrial` - dunkelgrau
- `retail` - warmgrau

1. **🎯 Points of Interest** (erweitert)
   - Restaurants, Cafés, Shops
   - Kleine Marker-Icons in Themenfarben

2. **🌾 Landwirtschaft** (detailliert)
   - `farmyard` - braun
   - `greenhouse` - hellgrün
   - `orchard` - dunkelgrün mit Pattern

3. **💧 Wasser-Details**
   - `fountain` - hellblau Kreis
   - `swimming_pool` - cyan Rechteck
   - `water_well` - dunkelblauer Punkt

4. **🏗️ Bauwerke** (detailliert)
   - Gebäude nach Typ:
     - `house` - standard
     - `garage` - grau
     - `shed` - hellgrau
     - `greenhouse` - grün-transparent

### Farbschema für Detail-Reichtum

```yaml
detail_colors:
  # Vegetation
  tree: "#4A7C59"
  tree_deciduous: "#6B8E23"
  tree_coniferous: "#228B22"
  shrub: "#90BE6D"
  hedge_detailed: "#556B2F"
  
  # Landnutzung
  residential_area: "#E8E8E8"
  commercial_area: "#FFD8AA"
  industrial_area: "#C0C0C0"
  retail_area: "#FFE4B5"
  
  # Landwirtschaft
  farmyard: "#DEB887"
  greenhouse: "#98FB98"
  orchard: "#556B2F"
  vineyard: "#8B4789"
  
  # Wasser-Details
  fountain: "#87CEEB"
  swimming_pool: "#00CED1"
  pond: "#4682B4"
  
  # Bauwerke
  house: "#D0D0D0"
  garage: "#A0A0A0"
  shed: "#B8B8B8"
  greenhouse_building: "#90EE90"
  
  # POIs
  restaurant: "#FF6B6B"
  cafe: "#FFD93D"
  shop: "#6BCB77"
  school: "#4D96FF"
  
  # Infrastruktur
  parking: "#F0F0F0"
  parking_underground: "#D0D0D0"
  street_furniture: "#808080"
  bench: "#8B4513"
```

## 🔧 Implementierung

Die Updates werden in folgenden Dateien vorgenommen:

1. **`modules/config.py`**
   - Neue `DETAIL_LAYER_TAGS` für Bäume, Parkplätze, etc.
   - Erweiterte Farbpalette in `DEFAULT_THEME_COLORS`

2. **`modules/poster_generator.py`**
   - Neue `fetch_trees()`, `fetch_parking()` Methoden
   - Rendering-Logik für Point-Features (Bäume als Kreise)
   - Gebäude-Typ-basierte Färbung

3. **`themes/*.json`**
   - Alle Themes erweitern mit neuen Detail-Farben

## 📊 Zoom-Level Strategie

```
Distance  | Layer-Set                          | Farb-Varianz
----------|------------------------------------|--------------
< 500m    | ALLE Details (max. Farben)         | Sehr hoch
500-1km   | Bäume, Gebäude-Typen, POIs         | Hoch  
1-2km     | Gebäude, Landuse, Hauptstraßen     | Mittel
2-8km     | Gebäude, Waterways, Railways       | Basi

s
> 8km     | Nur Straßen, Wasser, Parks         | Minimal
```

## 🎨 Farb-Hierarchie für Lesbarkeit

1. **Hintergrund** (hellste)
2. **Landwirtschaft** (pastellfarben)
3. **Grundstücke** (sehr hell)
4. **Länduse-Zonen** (hell)
5. **Vegetation** (mittel)
6. **Wasser** (mittel-dunkel)
7. **Gebäude** (dunkel-kontrast)
8. **Straßen** (kräftig)
9. **POIs** (accent-farben)
10. **Text** (dunkelste/kontrastreichste)

## ⚡ Performance-Optimierung

- Limit POIs zu max. 200 Features bei < 500m
- Tree-Rendering nur wenn > 50 Bäume vorhanden
- Adaptive Point-Größe basierend auf Feature-Dichte

---

**Status:** Bereit zur Implementierung
**Priorität:** Hoch - verbessert UX bei nahen Zoom-Levels signifikant
**Aufwand:** ~2-3h
