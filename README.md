🚌 Dhaka Bus Route Explorer — Streamlit Edition

An interactive GIS-based Streamlit application for exploring, visualizing, and analyzing the Dhaka bus route network.

This project is a complete Python/Streamlit port of the original Leaflet/HTML DTCA Bus Route Explorer web application. The major analysis logic, interactive mapping functions, route/stop analysis, drawing tools, route recommendation, filtering, and export capabilities have been reimplemented in Python.

✨ Features
🗺️ Interactive Bus Route Map
Display official bus routes on an interactive Folium map
Visualize bus stops, corridors, and administrative boundaries
Toggle map layers:
Routes
Stops
Corridors
Administrative boundaries
Optional stop clustering
Interactive route and stop popups
Route selection and detailed route information
🔎 Route Search & Filtering

Search official bus routes using:

Route ID
Operator
Route alignment
Other available route attributes

The application provides an interactive Routes attribute table for browsing and filtering route information.

📍 Bus Stop Explorer

Explore bus stops through:

Interactive map markers
Stop attributes
Route-to-stop relationships
Search and filtering
Spatial selection
🔄 Route–Stop Matching

The application implements route-to-stop matching logic to identify the relationship between official bus routes and bus stops.

This supports analysis of:

Stops served by individual routes
Routes serving particular stops
Route coverage
Route-level stop information
✏️ Interactive Drawing Tools

The map includes a Leaflet.draw-equivalent interface for creating temporary spatial features.

Users can:

Draw routes/polylines
Add points
Edit geometries
Move vertices
Add/remove vertices
Delete temporary features

Temporary drawings are maintained separately from the official GeoJSON datasets.

🔷 Polygon Selection

Users can draw a polygon on the map to perform spatial selection.

The application identifies:

Routes intersecting the polygon
Stops located inside the polygon
Number of selected routes
Number of selected stops

The selection logic implements point-in-polygon and line-polygon intersection operations.

🚌 Origin → Destination Route Recommendation

The application provides an interactive route recommendation tool.

Users can select:

Origin Stop → Destination Stop

and receive a recommended route based on the application's route-matching and spatial-distance logic.

The recommendation uses:

Nearest-point-on-line projection
Route/stop spatial relationships
Distance calculation
Fare estimation
💰 Fare Calculation

The implemented fare formula is:

Fare = max(10, ceil((distance_km × 2.53) / 5) × 5) BDT

The calculated fare is presented as an estimated fare based on the application's implemented formula.

📊 Attribute Tables

The application provides searchable attribute tables for:

Routes
Stops

CSV export is available directly from the Streamlit interface.

📥 Temporary GeoJSON Upload

Users can upload their own GeoJSON containing:

Temporary route geometries
Temporary point features

Uploaded features are treated as additional temporary features and do not modify the official project datasets.

📤 Map JPEG Export

The application can export the selected route as a JPEG map containing:

Basemap
Selected route
Labelled stops
Temporary drawings
Legend
North arrow
Scale bar

The export functionality is implemented using Matplotlib + Contextily.

📁 Project Structure
DTCA_Bus_Route_Explorer/
│
├── app.py
├── analysis.py
├── map_utils.py
├── requirements.txt
├── README.md
│
└── data/
    ├── routes.geojson
    ├── stops.geojson
    ├── corridors.geojson
    └── admin.geojson
📄 File Description
File	Description
app.py	Main Streamlit application containing the UI, sidebar, map, tables, controls, upload and export functionality
analysis.py	Pure-Python analytical/business logic including route styling, route-stop matching, distance calculations, nearest-point projection, route recommendation, fare calculation, search/filter functions and summary statistics
map_utils.py	Folium map construction, layer styling, popups, drawing tools, polygon-selection logic and JPEG map export
requirements.txt	Required Python packages
data/routes.geojson	Official bus-route layer
data/stops.geojson	Official bus-stop layer
data/corridors.geojson	Corridor layer
data/admin.geojson	Administrative boundary layer
🚀 Installation
1. Clone the repository
git clone https://github.com/YOUR_USERNAME/DTCA_Bus_Route_Explorer.git

Move into the project directory:

cd DTCA_Bus_Route_Explorer
2. Create a virtual environment
Windows
python -m venv venv
venv\Scripts\activate
Linux / macOS
python -m venv venv
source venv/bin/activate
3. Install dependencies
pip install -r requirements.txt
▶️ Run the Application

Start Streamlit:

streamlit run app.py

The application will normally be available at:

http://localhost:8501
🧩 Application Architecture
                   ┌───────────────────────┐
                   │       Streamlit       │
                   │        app.py         │
                   └───────────┬───────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
       ┌─────────────────┐          ┌─────────────────┐
       │   analysis.py   │          │  map_utils.py   │
       │                 │          │                 │
       │ Route Analysis  │          │ Folium Mapping  │
       │ Stop Matching   │          │ Drawing Tools   │
       │ Recommendation  │          │ Polygon Select  │
       │ Distance/Fare   │          │ Map Export      │
       └────────┬────────┘          └────────┬────────┘
                │                            │
                └─────────────┬──────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   GeoJSON Data    │
                    ├───────────────────┤
                    │ routes.geojson    │
                    │ stops.geojson     │
                    │ corridors.geojson │
                    │ admin.geojson     │
                    └───────────────────┘
🗂️ Data Model

The application uses four official, read-only GeoJSON layers:

routes.geojson

Contains the official bus-route geometries and associated route attributes.

stops.geojson

Contains official bus-stop locations and associated stop attributes.

corridors.geojson

Contains the corridor/network information used for map visualization and spatial analysis.

admin.geojson

Contains administrative boundary information used as a reference layer.

🔒 Read-Only Official Data

The official GeoJSON files are treated as read-only source layers.

The application does not write changes back to:

routes.geojson
stops.geojson
corridors.geojson
admin.geojson

Temporary drawings and uploaded GeoJSON features remain separate from the official datasets.

🔁 Feature Mapping

The following table describes how the original Leaflet/HTML application has been implemented in Streamlit.

Original Web Application	Streamlit Edition
Search official route	Sidebar route search
Route/stop detail	Interactive detail panel
Leaflet route map	Folium interactive map
Leaflet.draw	Embedded drawing toolbar
Temporary routes	st.session_state.temp_features
Temporary points	st.session_state.temp_features
Edit drawings	Leaflet.draw editing tools
Delete drawings	Leaflet.draw remove tool
Polygon selection	Spatial polygon selection
Point-in-polygon	Python spatial logic
Line-polygon intersection	Python spatial logic
Route recommendation	analysis.recommend_route()
Route/stop tables	Streamlit data tables
CSV export	Streamlit download
JPEG map export	Matplotlib + Contextily
Marker clustering	folium.plugins.MarkerCluster
Layer controls	Streamlit sidebar
Reset view	Streamlit reset control
🧮 Spatial Analysis

The application implements several spatial-analysis functions in Python.

These include:

Haversine distance calculation
Nearest-point-on-line projection
Route-to-stop matching
Point-in-polygon analysis
Line-polygon intersection
Spatial route filtering
Route distance calculation
Route recommendation

The coordinate and geometric calculations are implemented in Python without requiring a separate GIS desktop application.

🚌 Route Recommendation

The route recommendation workflow can be summarized as:

Select Origin Stop
        │
        ▼
Select Destination Stop
        │
        ▼
Identify Candidate Routes
        │
        ▼
Match Origin/Destination
        │
        ▼
Nearest Point-on-Route Analysis
        │
        ▼
Calculate Route Distance
        │
        ▼
Recommend Route
        │
        ▼
Estimate Fare
🗺️ Map Layers

The application supports four primary map layers:

Routes
Stops
Corridors
Administrative Boundaries

Users can turn individual layers on or off from the Streamlit sidebar.

📤 Export
CSV

Route and stop attribute tables can be downloaded as CSV files.

JPEG

The selected route can be exported as a static JPEG map containing:

Selected route
Route stops
Basemap
Temporary features
Legend
North arrow
Scale bar
🌐 Basemap

The interactive map uses online basemap tiles, including:

CARTO Positron
OpenStreetMap

Therefore, internet access is required when running the application with online basemaps.

Basemap attribution is displayed within the application and on exported maps where applicable.

🛠️ Technology Stack
Technology	Purpose
Python	Application and analytical logic
Streamlit	Web application framework
GeoPandas	Geospatial data processing
Folium	Interactive web mapping
Shapely	Geometric and spatial operations
Pandas	Tabular data processing
NumPy	Numerical computation
Matplotlib	Static map generation
Contextily	Basemap integration for static maps
Plotly	Interactive data visualization, where applicable
🎯 Project Purpose

The DTCA Bus Route Explorer is designed to make the Dhaka bus network easier to explore and analyze through an interactive GIS environment.

The application can support transport-planning activities such as:

Existing route inventory
Bus network visualization
Route and stop exploration
Route coverage assessment
Route overlap investigation
Bus corridor analysis
Spatial identification of route relationships
Origin–destination route exploration
Preliminary route rationalization analysis

The broader survey methodology supporting the Dhaka bus-route rationalization work includes baseline road inventory, classified traffic counts, vehicle occupancy, travel speed and delay, roadside OD interviews, and bus-route surveys.

📌 Project Status

Status: 🚧 Active Development

The Streamlit edition provides a Python-based implementation of the original DTCA Bus Route Explorer and is intended to serve as an interactive GIS and transport-network analysis platform.

⚠️ Data & Usage Notice

The repository should contain only data and materials that you are authorized to distribute publicly.

If the underlying route, stop, corridor, administrative, or survey datasets are subject to project, organizational, contractual, or copyright restrictions, they should not be uploaded to a public GitHub repository without appropriate permission.

For a public repository, consider publishing:

Application source code
Analytical algorithms
Non-confidential sample data
Data schemas
Methodology
Screenshots
Documentation
Installation instructions

while keeping restricted project datasets private.

👨‍💻 Author
A.T. M Neamul
Data Source: Dhaka Transport Coordination Authority, 2026

Developed as a GIS and transport-network analysis application for exploring the Dhaka bus and minibus network
