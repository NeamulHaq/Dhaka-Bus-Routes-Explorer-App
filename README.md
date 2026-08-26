# DTCA Bus Route Explorer — GIS Editor

## Project structure

- `index.html` — main application
- `data/` — editable GeoJSON source layers
  - `routes.geojson`
  - `stops.geojson`
  - `corridors.geojson`
  - `admin.geojson`
- `CSS/app.css` — application styling
- `JS/app.js` — map, selection, editing, export and table logic
- `Leaflet/` — Leaflet and MarkerCluster libraries
- `script/bootstrap.js` — hosted GeoJSON loading and direct-open fallback

## GIS editing

The Edit tool uses Leaflet-Geoman Free 2.20.0. Geoman is loaded from its pinned public CDN URL in `index.html`.

For a selected route:
- **Move Vertex:** drag a vertex
- **Add Vertex:** click the route segment while in edit mode
- **Delete Vertex:** right-click a vertex
- **Snap:** enabled for precision editing
- **Prevent self-intersection:** enabled
- **Edit Attributes:** use the attribute editor in the right-side route panel

For stops:
- enable Edit
- select a stop
- drag the stop to move it
- edit stop name, route ID and coordinates in the attribute editor

## Attribute table

The Table tool opens a GIS-style attribute table for Routes and Stops. Search records and click a row to select the feature on the map.

## Undo / Redo

- Toolbar Undo / Redo
- `Ctrl+Z` / `Ctrl+Y`
- Up to 30 browser-session edit states

## Save

`Save` stores the current project edits in browser localStorage.

`Save GeoJSON` downloads:
- `routes_edited.geojson`
- `stops_edited.geojson`

Replace the corresponding files in `data/` on your website when you want the edited network to become the new source dataset.

## Hosting

Upload the entire folder to your website while preserving the folder structure. The application loads the four GeoJSON files from `data/` when hosted over HTTP/HTTPS.

The light basemap and pinned Leaflet-Geoman CDN dependency require normal website Internet access.

## GIS Editing v2

The Edit tool now uses an explicit GIS editing sub-toolbar:
- Move: drag the selected route or stop.
- Vertices: displays draggable orange route vertices.
- Add Vertex: click directly on a route segment to insert a vertex.
- Delete Vertex: click an orange vertex to remove it; routes retain at least two vertices.
- Attributes: edit route attributes in the attribute panel.
- Stop: edit stop attributes and coordinates.

Vertex editing is implemented with native Leaflet handles for reliable browser/hosting behavior. Leaflet-Geoman remains loaded for feature drag/edit compatibility and future advanced geometry tools.
