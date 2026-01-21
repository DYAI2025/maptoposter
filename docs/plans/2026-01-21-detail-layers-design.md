# CityMaps: Detail-Layer & Schrift-Skalierung

**Datum:** 2026-01-21
**Status:** Approved

## Ziel

Dörfer und kleine Orte visuell interessanter darstellen durch zusätzliche OSM-Layer. Schriftgröße automatisch an Papierformat und Zoom-Stufe anpassen.

## Entscheidungen

| Aspekt | Entscheidung |
|--------|--------------|
| Neue Layer | Gebäude + Feldwege + Landschaft |
| Steuerung | Einzelne Checkboxen pro Layer |
| Farben | Eigene Werte pro Theme (17 Themes) |
| Defaults | Zoom-abhängig (< 2km AN, > 8km AUS) |
| Schrift | Skaliert mit Papierformat + Zoom |

---

## Teil 1: Neue OSM Layer

### 1.1 Gebäude (`buildings`)
```python
tags = {'building': True}
```
Alle Gebäude-Polygone: Wohnhäuser, Scheunen, Kirchen.

### 1.2 Feldwege & Pfade (`paths`)
```python
tags = {'highway': ['track', 'path', 'footway', 'cycleway', 'bridleway']}
```
Landwirtschaftliche Wege, Wanderpfade, Radwege.

### 1.3 Landschaft (`landscape`)
```python
tags = {
    'landuse': ['farmland', 'meadow', 'orchard', 'vineyard', 'forest'],
    'natural': ['wood', 'scrub', 'heath', 'grassland']
}
```
Felder, Wiesen, Wälder als Hintergrundflächen.

### 1.4 Rendering-Reihenfolge (z-order)
1. Landschaft (z=0)
2. Wasser (z=1)
3. Parks (z=2)
4. Gebäude (z=3)
5. Feldwege (z=4)
6. Straßen (z=5)

---

## Teil 2: Theme-Farben

### 2.1 Neue Keys pro Theme
```json
{
  "buildings": "#1a1a1a",
  "buildings_fill": "#0d0d0d",
  "paths": "#333333",
  "farmland": "#0a0a0a",
  "forest": "#0d1a0d",
  "meadow": "#0a0f0a"
}
```

### 2.2 Fallback-Strategie
Falls Keys fehlen:
- `buildings` = BG ± 15% Helligkeit
- `paths` = `road_residential` mit 50% Alpha
- `farmland`/`forest` = `parks` mit 30% Alpha

---

## Teil 3: Schrift-Skalierung

### 3.1 Formel
```
final_font_size = base_size × paper_factor × zoom_factor
```

### 3.2 Paper-Factor
| Format | Faktor |
|--------|--------|
| A2 | 1.4 |
| A3 | 1.2 |
| A4 | 1.0 |
| A5 | 0.7 |

### 3.3 Zoom-Factor
| Radius | Faktor |
|--------|--------|
| ≤ 500m | 0.4 |
| 1 km | 0.5 |
| 2 km | 0.6 |
| 4 km | 0.75 |
| 8 km | 0.9 |
| ≥ 15 km | 1.0 |

### 3.4 Skalierte Elemente
- Stadtname: `base × factors`
- Land/Region: `base × factors × 0.37`
- Koordinaten: `base × factors × 0.23`
- Trennlinie: Länge proportional

---

## Teil 4: GUI-Änderungen

### 4.1 Neue Sektion
```
### 🏘️ Detail-Layer
☑️ Gebäude
☑️ Feldwege
☑️ Landschaft
```

### 4.2 Zoom-abhängige Defaults
```python
def get_layer_defaults(distance_m: int) -> dict:
    if distance_m <= 2000:
        return {"buildings": True, "paths": True, "landscape": True}
    elif distance_m <= 8000:
        return {"buildings": True, "paths": False, "landscape": False}
    else:
        return {"buildings": False, "paths": False, "landscape": False}
```

---

## Teil 5: Dateien

| Datei | Änderung |
|-------|----------|
| `modules/config.py` | Skalierungsfaktoren |
| `modules/text_positioning.py` | Font-Skalierung |
| `modules/poster_generator.py` | Neue Layer-Methoden |
| `themes/*.json` | 6 neue Farbkeys |
| `gui_app.py` | Checkbox-Sektion |
