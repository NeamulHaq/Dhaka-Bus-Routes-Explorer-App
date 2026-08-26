DTCA BUS ROUTE EXPLORER — STREAMLIT EDITION
=============================================

This is a complete, runnable Streamlit port of the original Leaflet/HTML
"DTCA Bus Route Explorer" web app. All analysis logic, map layers, drawing
tools, upload and export features from the original app have been
preserved and re-implemented in Python.

FILES
-----
app.py            Main Streamlit application (UI, sidebar, map, tables).
analysis.py        Pure-Python business logic ported from the original
                    JS/app.js: styling rules (AC/Non-AC colors), route<->stop
                    matching, nearest-point-on-line projection, the
                    Origin->Destination route recommendation algorithm and
                    its fare formula, search/filter helpers, summary stats.
map_utils.py        Folium map construction (base layers, route/stop
                    styling and popups, the Leaflet.draw-equivalent drawing
                    tool, polygon-selection logic) and the static JPEG map
                    export (matplotlib + contextily), mirroring the
                    original app's exportJPEG()/drawExportLegend()/
                    drawExportNorthScale().
requirements.txt    Python dependencies.
data/               The four original, read-only source GeoJSON layers:
                    routes.geojson, stops.geojson, corridors.geojson,
                    admin.geojson (unchanged from the original app).

SETUP
-----
1. Create and activate a virtual environment (recommended):
       python -m venv venv
       source venv/bin/activate        (Windows: venv\Scripts\activate)

2. Install dependencies:
       pip install -r requirements.txt

3. Run the app:
       streamlit run app.py

4. Streamlit will open the app in your browser (usually
   http://localhost:8501). The app needs internet access to fetch basemap
   tiles (CARTO Positron / OpenStreetMap), same as the original hosted app.

DATA MODEL (unchanged from the original)
-----------------------------------------
The files in data/ are the official source layers and are READ-ONLY in the
application, exactly as documented in the original app's README:
  - routes.geojson
  - stops.geojson
  - corridors.geojson
  - admin.geojson
The application never writes edits back to these GeoJSON files. Nothing in
app.py, analysis.py or map_utils.py opens them in write mode.

FEATURE MAPPING (original web app -> Streamlit app)
-----------------------------------------------------
Search/select an official route
    -> Sidebar "Search routes" box (Route ID / Operator / alignment text)
       plus the Routes tab of the Attribute table.

View route/stop detail (view-only)
    -> "Detail panel" on the right of the map, shown whenever a route is
       selected (via search, table, map click popup, or recommendation).

Draw -> Route / Draw -> Point (temporary features)
    -> The Leaflet-draw toolbar embedded directly in the map (top-left
       tools icon). Drawn polylines/markers are kept in
       st.session_state.temp_features as a small GeoJSON
       FeatureCollection, completely separate from the official layers -
       identical in spirit to tempRoutes/tempPoints in the original JS.

Edit Drawings (move/reshape/add/delete vertices, delete features)
    -> Handled natively by the embedded Leaflet.draw "edit" toolbar
       (edit_options={"edit": True, "remove": True} in map_utils.py).
       Edited/deleted geometry is re-synced into session state on every
       interaction.

Select by Polygon
    -> Use the polygon draw tool on the map; the last drawn polygon is
       run through the same point-in-polygon / line-in-polygon logic as
       the original finishPolygon()/pointInPoly()/lineIntersectsPolygon()
       (see map_utils.select_by_polygon). Matching route/stop counts are
       shown under the map, exactly as the "Selected N route(s) and M
       stop(s)" status message did.

Origin/Destination route recommendation
    -> Sidebar "Route recommendation" section: pick an Origin and
       Destination stop and click "Recommend route". Uses the same
       nearest-point-on-line projection and fare formula
       (max(10, ceil((distance_km * 2.53)/5) * 5) BDT) as the original
       recommend() function, implemented in analysis.recommend_route().

Attribute table (Routes / Stops tabs, search box)
    -> "Attribute table" section at the bottom of the page, with the same
       two tabs, a filter box, and CSV export (the original only allowed
       browsing; CSV download has been added as a natural Streamlit
       equivalent of "view then take the data with you").

Map JPEG export
    -> "Export selected route" panel: downloads a JPEG containing the
       basemap, the selected route, its labelled stops, any temporary
       drawings, a legend, north arrow and scale bar - the same
       composition as the original exportJPEG(), rebuilt with matplotlib
       + contextily instead of html2canvas/Canvas2D.

KML/CSV import & export of official data (disabled in the original)
    -> Still not supported for the official layers, by design.
       "Upload temporary drawing" in the sidebar lets you bring in your
       own GeoJSON of routes/points as ADDITIONAL temporary features
       (same semantics as hand-drawn temporary features) - this is the
       natural Streamlit replacement for the original's disabled
       importKmlBtn, and never touches routes.geojson/stops.geojson.

Layer toggles (Routes / Stops / Corridors / Admin)
    -> Sidebar checkboxes, applied when the map is rebuilt each run.

Reset view
    -> Sidebar "Reset view / selection" button.

NOTES
-----
- All coordinate math (haversine distance, nearest-point-on-polyline
  projection, ray-casting point-in-polygon) is implemented in pure Python
  in analysis.py / map_utils.py with no native dependencies, so it runs
  anywhere Python + the listed pip packages run.
- The stop-clustering behaviour is provided by folium.plugins.MarkerCluster
  (toggle "Cluster stops" in the sidebar), matching Leaflet.markercluster
  in the original app.
- Basemap tiles are CARTO "light_all" (OpenStreetMap contributors / CARTO),
  same as the original app; attribution is shown on the map and on the
  exported JPEG footer.
