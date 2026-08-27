# DTCA Bus Route Explorer — Final Read-Only + Temporary Drawing Edition

## Data model
The files in `data/` are the official source layers and are **read-only in the web application**:
- `routes.geojson`
- `stops.geojson`
- `corridors.geojson`
- `admin.geojson`

The application never writes edits back to these GeoJSON layers.

## User workflow
1. Search/select an official route. Official geometry and attributes are view-only.
2. Use **Draw → Route** to create a temporary route.
3. Use **Draw → Point** to create temporary stops/points.
4. Use **Edit Drawings** to move temporary features, reshape temporary routes, add/delete temporary route vertices, move temporary stops, or delete temporary features.
5. Temporary features can be included in **Map JPEG** export.
6. KML and CSV download functions are disabled/removed.

## Route recommendation
Enter an Origin and Destination in the sidebar. The application ranks the existing route layer using route alignment names and mapped stop names, highlights the best matching route, and reports:
- Route ID
- Bus operator
- Origin / Destination entered by user
- Approx. distance
- Approx. time
- Approx. fare

Fare rule: `max(10, ceil((distance_km × 2.53) / 5) × 5)` BDT.

## Hosting
Upload the complete folder to normal web hosting while preserving the folder structure. The hosted application reads the GeoJSON files from `data/` using `fetch()`.

The light basemap uses CARTO/OSM tiles and therefore requires internet access for the basemap only.
