🚌 Dhaka Bus Route Explorer

An interactive GIS-based web application for exploring, visualizing, and analyzing the Dhaka bus and minibus network using Python and Streamlit.

This project is a complete Streamlit implementation of the original DTCA Bus Route Explorer web application, with route visualization, bus-stop exploration, spatial analysis, route recommendation, interactive drawing, filtering, and map export capabilities.

🚀 Key Features
🚌 Bus Route Explorer — Search and explore bus routes by route ID, operator, and alignment.
🗺️ Interactive GIS Map — Visualize routes, stops, corridors, and administrative boundaries.
📍 Bus Stop Analysis — Explore stops and their relationships with bus routes.
🔄 Route Overlap Analysis — Identify routes sharing common network segments.
🔎 Route & Stop Search — Filter and inspect route and stop attributes.
✏️ Interactive Drawing — Draw, edit, and delete temporary routes and points directly on the map.
🔷 Polygon Selection — Select routes and stops using a user-defined polygon.
🚌 Origin–Destination Route Recommendation — Recommend routes between selected bus stops.
💰 Fare Estimation — Calculate estimated fares using the application's implemented fare formula.
📊 Attribute Tables — Browse and filter route and stop datasets.
📥 GeoJSON Upload — Add temporary user-defined routes and points without modifying official data.
📤 CSV Export — Export route and stop attribute tables.
🖼️ JPEG Map Export — Export selected routes with basemap, stops, legend, north arrow, and scale bar.
🔄 Reset & Layer Controls — Easily manage map layers and reset the current selection.
🗂️ Project Structure
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
Main Files
File	Description
app.py	Main Streamlit application and user interface
analysis.py	Route analysis, stop matching, distance calculation, route recommendation, fare calculation, search and statistics
map_utils.py	Folium map creation, layer styling, drawing tools, polygon selection and static map export
requirements.txt	Python package dependencies
data/routes.geojson	Bus route geometries and attributes
data/stops.geojson	Bus stop locations and attributes
data/corridors.geojson	Bus corridor layer
data/admin.geojson	Administrative boundary layer
🛠️ Technology Stack
Python
Streamlit
GeoPandas
Pandas
NumPy
Shapely
Folium
Matplotlib
Contextily
⚙️ Installation
1. Clone the repository
git clone https://github.com/YOUR_USERNAME/DTCA_Bus_Route_Explorer.git
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
streamlit run app.py

Open the application in your browser:

http://localhost:8501
🗺️ Interactive Map

The application provides an interactive GIS environment for exploring:

Bus Routes
     │
     ├── Bus Stops
     │
     ├── Corridors
     │
     └── Administrative Areas

Users can enable or disable individual layers from the sidebar.

Stop clustering can also be enabled for improved visualization when displaying a large number of bus stops.

🔎 Route Explorer

Users can search and inspect routes using:

Route ID
Operator
Route alignment

Selecting a route displays its available information and spatial alignment on the map.

🔄 Route–Stop Analysis

The application provides spatial relationships between routes and stops, allowing users to examine:

Stops served by a route
Routes serving a stop
Route coverage
Route-stop relationships
✏️ Interactive Drawing

Temporary spatial features can be created directly on the map.

Supported operations include:

Draw route/polyline
Add point
Edit geometry
Move vertices
Add/remove vertices
Delete features

Temporary features are stored separately from the official source layers.

🔷 Polygon Selection

Users can draw a polygon to identify features within the selected area.

The application reports:

Selected Routes
Selected Stops

The spatial selection uses point-in-polygon and line-polygon intersection logic.

🚌 Origin → Destination Route Recommendation

Select an Origin Stop and Destination Stop to obtain a route recommendation.

The workflow uses:

Origin Stop
     ↓
Candidate Routes
     ↓
Destination Stop
     ↓
Nearest Point-on-Line Analysis
     ↓
Route Distance
     ↓
Recommended Route
     ↓
Estimated Fare

The implemented fare formula is:

Fare = max(10, ceil((distance_km × 2.53) / 5) × 5) BDT
📊 Attribute Tables

The application provides searchable attribute tables for:

Routes

View and filter available route attributes.

Stops

View and filter available bus-stop attributes.

Both tables support CSV download for further analysis.

📥 Temporary GeoJSON Upload

Users can upload their own GeoJSON files containing temporary:

Route geometries
Point features

Uploaded data is treated as temporary information and does not modify the official GeoJSON layers.

📤 Map Export

The application provides static JPEG map export for selected routes.

The exported map can include:

Basemap
Selected route
Route stops
Temporary drawings
Legend
North arrow
Scale bar

Static map generation is implemented using:

Matplotlib + Contextily

📁 Data

The application uses four read-only GeoJSON layers:

data/
├── routes.geojson
├── stops.geojson
├── corridors.geojson
└── admin.geojson

The application does not write edits back to these source files.

Temporary drawings and uploaded features remain separate from the official datasets.

🌐 Basemap

The interactive map uses online basemap tiles such as CARTO Positron and OpenStreetMap.

An internet connection is therefore required when using online basemaps.

Appropriate map attribution is displayed within the application and exported maps.

🧩 Application Architecture
                    ┌───────────────────┐
                    │    Streamlit UI   │
                    │      app.py       │
                    └─────────┬─────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
       ┌─────────────────┐         ┌─────────────────┐
       │   analysis.py   │         │  map_utils.py   │
       │                 │         │                 │
       │ Route Analysis  │         │ Folium Mapping  │
       │ Stop Matching   │         │ Drawing Tools   │
       │ Recommendation  │         │ Polygon Select  │
       │ Fare Calculation│         │ Map Export      │
       └────────┬────────┘         └────────┬────────┘
                │                           │
                └─────────────┬─────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │    GeoJSON Data   │
                    ├───────────────────┤
                    │ routes.geojson    │
                    │ stops.geojson     │
                    │ corridors.geojson │
                    │ admin.geojson     │
                    └───────────────────┘
🎯 Project Objectives

The DTCA Bus Route Explorer provides a practical GIS environment for understanding the existing Dhaka bus network.

The application supports analysis of:

Existing bus routes
Route alignments
Bus-stop distribution
Route–stop relationships
Bus corridor coverage
Route overlaps
Spatial service patterns
Origin–destination connectivity
Preliminary bus route rationalization

The broader DTCA survey framework includes baseline road inventory, classified traffic counts, vehicle occupancy, travel speed and delay, roadside OD interviews, and active bus-route surveys.

🔒 Data & Usage Notice

Only data that you are authorized to distribute should be included in a public GitHub repository.

If project datasets are subject to contractual, organizational, copyright, confidentiality, or other restrictions, keep those datasets private and publish only:

Application source code
Analytical methods
Data schemas
Non-confidential sample data
Documentation
Screenshots
Reproducible workflows
🚧 Project Status

Active Development

The DTCA Bus Route Explorer — Streamlit Edition is being developed as an interactive GIS and transport-network analysis platform for exploring and understanding the Dhaka bus and minibus network.

👨‍💻 Data Source:

Dhaka Transport Coordination Authority, 2026

GIS • Python • Streamlit • Spatial Analysis • Public Transport Planning
