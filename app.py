"""
DTCA Bus Route Explorer - Streamlit Edition
============================================
A Streamlit port of the original Leaflet-based "DTCA Bus Route Explorer"
web app. Read-only official GeoJSON layers (routes / stops / corridors /
admin boundaries) are shown on an interactive map; users can search and
select routes/stops, get an Origin -> Destination route recommendation,
draw temporary routes/points (which never modify the official data),
browse an attribute table, upload their own temporary-drawing GeoJSON,
and export the current selection as a JPEG map, GeoJSON or CSV.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import analysis as an
import map_utils as mu

st.set_page_config(page_title="DTCA Bus Route Explorer", layout="wide",
                    initial_sidebar_state="expanded")

# --------------------------------------------------------------------------
# Data (cached - the official layers are read-only, exactly as in the
# original app: "The application never writes edits back to these GeoJSON
# layers.")
# --------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading DTCA bus network data...")
def get_data() -> an.ExplorerData:
    return an.load_all_data()


data = get_data()

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

DEFAULTS = {
    "selected_route_id": None,
    "selected_stop_name": None,
    "origin_stop": None,
    "destination_stop": None,
    "recommendation": None,
    "temp_features": [],          # list of GeoJSON Feature dicts (routes/points)
    "map_center": list(an.DEFAULT_CENTER),
    "map_zoom": an.DEFAULT_ZOOM,
    "last_polygon_selection": None,  # (route_ids, stop_names)
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def temp_feature_collection() -> dict:
    return {"type": "FeatureCollection", "features": st.session_state.temp_features}


def selected_route_feature() -> dict | None:
    rid = st.session_state.selected_route_id
    if rid is None:
        return None
    for feat in data.routes["features"]:
        if str(feat["properties"].get("Route_ID")) == str(rid):
            return feat
    return None


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

stats = an.summary_stats(data.routes, data.stops)

with st.sidebar:
    st.title("\U0001F68C DTCA Bus Route Explorer")
    st.caption("Final Read-Only + Temporary Drawing Edition (Streamlit)")

    c1, c2 = st.columns(2)
    c1.metric("Routes", stats["routes"])
    c2.metric("Stops", f"{stats['stops']:,}")
    c1.metric("Network length", f"{stats['length_km']:,} km")
    c2.metric("AC routes", stats["ac_routes"])

    st.divider()

    # ---- Layer toggles -----------------------------------------------
    st.subheader("Layers")
    show_routes = st.checkbox("Routes", value=True)
    show_stops = st.checkbox("Stops", value=True)
    show_corridors = st.checkbox("Corridors", value=True)
    show_admin = st.checkbox("Admin boundaries", value=False)
    show_temp = st.checkbox("Temporary drawings", value=True)
    cluster_stops = st.checkbox("Cluster stops", value=True)

    st.divider()

    # ---- Search ---------------------------------------------------------
    st.subheader("Search routes")
    query = st.text_input("Route ID, operator or alignment place",
                           placeholder="e.g. A-182 or Mirpur", key="search_query")
    if query:
        results = an.search_routes(data.routes, query)
        if results:
            options = {f"{f['properties'].get('Route_ID')} \u2014 "
                       f"{f['properties'].get('Operator', '')}": f['properties'].get('Route_ID')
                       for f in results}
            picked = st.selectbox("Matches", list(options.keys()))
            if st.button("Select route", use_container_width=True):
                st.session_state.selected_route_id = options[picked]
                st.session_state.selected_stop_name = None
        else:
            st.caption("No matching routes.")

    st.divider()

    # ---- Route recommendation -------------------------------------------
    st.subheader("Route recommendation")
    stop_names = sorted({s["name"] for s in data.stops if s.get("name")})
    origin_name = st.selectbox("Origin", [""] + stop_names, key="origin_select")
    dest_name = st.selectbox("Destination", [""] + stop_names, key="dest_select")

    if st.button("Recommend route", type="primary", use_container_width=True):
        rec = an.recommend_route(data.routes, data.stops, origin_name, dest_name)
        if rec is None:
            st.session_state.recommendation = None
            st.warning("No existing route serves both selected stops, or "
                       "choose an Origin and Destination first.")
        else:
            st.session_state.recommendation = rec
            st.session_state.selected_route_id = rec.route_feature["properties"].get("Route_ID")
            st.session_state.origin_stop = rec.origin_stop
            st.session_state.destination_stop = rec.destination_stop

    rec = st.session_state.recommendation
    if rec:
        p = rec.route_feature["properties"]
        st.success(f"**Recommended Route {p.get('Route_ID')}**")
        st.write(f"**Bus name:** {p.get('Operator', '\u2014')}")
        st.write(f"**Origin:** {rec.origin_stop.get('name')}")
        st.write(f"**Destination:** {rec.destination_stop.get('name')}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Distance", f"{rec.distance_km:.1f} km")
        m2.metric("Time", f"{round(rec.time_min)} min")
        m3.metric("Fare", f"BDT {rec.fare_bdt:,.0f}")
        st.caption("Distance measured along the selected route between the "
                   "two official stops. Fare: BDT 2.53/km, minimum BDT 10, "
                   "rounded up to the nearest BDT 5.")

    st.divider()

    # ---- Upload (temporary drawings only - official data stays read-only)
    st.subheader("Upload temporary drawing")
    uploaded = st.file_uploader(
        "GeoJSON of temporary routes/points to overlay",
        type=["geojson", "json"],
        help="Uploaded features are treated exactly like hand-drawn "
             "temporary features: they can be edited/deleted and are "
             "never merged into the official read-only layers.")
    if uploaded is not None:
        try:
            gj = json.load(uploaded)
            feats = gj.get("features", []) if gj.get("type") == "FeatureCollection" else [gj]
            if st.button("Add uploaded features to map", use_container_width=True):
                st.session_state.temp_features.extend(feats)
                st.success(f"Added {len(feats)} temporary feature(s).")
        except Exception as e:
            st.error(f"Could not parse file: {e}")

    if st.button("Clear all temporary drawings", use_container_width=True):
        st.session_state.temp_features = []
        st.success("Temporary drawings cleared. Official GeoJSON was not changed.")

    st.divider()
    if st.button("Reset view / selection", use_container_width=True):
        st.session_state.selected_route_id = None
        st.session_state.selected_stop_name = None
        st.session_state.recommendation = None
        st.session_state.origin_stop = None
        st.session_state.destination_stop = None
        st.session_state.map_center = list(an.DEFAULT_CENTER)
        st.session_state.map_zoom = an.DEFAULT_ZOOM

# --------------------------------------------------------------------------
# Main layout: map + detail panel
# --------------------------------------------------------------------------

st.title("DTCA Bus Route Explorer")
st.caption("Official routes, stops, corridors and administrative boundaries "
           "are read-only. Use the Draw tools on the map to add temporary "
           "routes/points - these can be edited or deleted and never change "
           "the source GeoJSON.")

map_col, detail_col = st.columns([2.4, 1])

with map_col:
    center = st.session_state.map_center
    zoom = st.session_state.map_zoom

    # If a route is selected, center on it
    sel_feat = selected_route_feature()
    if sel_feat is not None:
        coords = an.route_geometry_coords(sel_feat)
        if coords:
            lats = [c[1] for c in coords]
            lngs = [c[0] for c in coords]
            center = [(min(lats) + max(lats)) / 2, (min(lngs) + max(lngs)) / 2]

    fmap = mu.build_base_map(center=center, zoom=zoom)

    if show_admin:
        mu.add_admin_layer(fmap, data.admin, show=True)
    if show_corridors:
        mu.add_corridor_layer(fmap, data.corridors, show=True)
    if show_routes:
        mu.add_routes_layer(fmap, data.routes,
                             selected_route_id=st.session_state.selected_route_id,
                             show=True)
    if show_stops:
        mu.add_stops_layer(fmap, data.stops,
                            selected_stop_name=st.session_state.selected_stop_name,
                            cluster=cluster_stops, show=True)
    if show_temp:
        mu.add_temp_layer(fmap, temp_feature_collection())

    mu.add_recommendation_markers(fmap, st.session_state.origin_stop,
                                   st.session_state.destination_stop)
    mu.add_draw_control(fmap)
    folium.LayerControl(collapsed=True).add_to(fmap)

    map_state = st_folium(
        fmap, height=640, width=None,
        returned_objects=["last_active_drawing", "all_drawings",
                           "last_object_clicked_popup", "last_clicked"],
        key="main_map",
    )

    # --- Sync drawing tool output into session_state temporary features ---
    if map_state and map_state.get("all_drawings"):
        drawn = map_state["all_drawings"]
        # Tag each freshly drawn feature with a name if it doesn't have one
        existing_ids = {json.dumps(f.get("geometry")) for f in st.session_state.temp_features}
        for i, feat in enumerate(drawn):
            gid = json.dumps(feat.get("geometry"))
            if gid not in existing_ids:
                props = feat.setdefault("properties", {}) or {}
                if not props.get("name"):
                    kind = "Route" if feat["geometry"]["type"] == "LineString" else \
                           "Point" if feat["geometry"]["type"] == "Point" else "Selection"
                    props["name"] = f"Temporary {kind} {len(st.session_state.temp_features) + 1}"
                    feat["properties"] = props
                st.session_state.temp_features.append(feat)

    # --- Handle "select by polygon" (last drawn Polygon = selection tool) --
    if map_state and map_state.get("last_active_drawing"):
        last = map_state["last_active_drawing"]
        if last.get("geometry", {}).get("type") == "Polygon":
            ring = last["geometry"]["coordinates"][0]
            poly_latlng = [(lat, lng) for lng, lat in ring]
            routes_hit, stops_hit = mu.select_by_polygon(data.routes, data.stops, poly_latlng)
            st.session_state.last_polygon_selection = (
                [r["properties"].get("Route_ID") for r in routes_hit],
                [s.get("name") for s in stops_hit],
            )

    if st.session_state.last_polygon_selection:
        rids, snames = st.session_state.last_polygon_selection
        st.info(f"Polygon selection: **{len(rids)}** route(s), "
                f"**{len(snames)}** stop(s). GeoJSON remains read-only.")
        if rids and st.button("Select first matched route"):
            st.session_state.selected_route_id = rids[0]

with detail_col:
    st.subheader("Detail panel")

    sel_feat = selected_route_feature()
    if sel_feat is not None:
        p = sel_feat["properties"]
        st.markdown(f"### {p.get('Route_ID')}")
        badge = "AC" if an.is_ac(p) else "Non-AC"
        st.caption(f"{p.get('Operator', 'Operator not recorded')} \u00b7 {badge}")

        g1, g2 = st.columns(2)
        g1.metric("Route length", f"{an.fmt_num(p.get('Length'), 1)} km")
        g2.metric("Headway", f"{an.fmt_num(p.get('Headway'), 0)} min")
        g1.metric("Buses operating", an.fmt_num(p.get("Actual Bus"), 0))
        g2.metric("Permitted fleet", an.fmt_num(p.get("Permitted "), 0))
        g1.metric("Trips / day", f"{round(an._to_float(p.get('No of Trip')) or 0)}")
        g2.metric("Travel time", f"{an.fmt_num(p.get('Travel Tim'), 0)} min")

        parts = an.align_parts(p)
        if parts:
            st.markdown("**Alignment**")
            st.write(" \u2192 ".join(parts))

        stops_on_route = an.route_stops(sel_feat, data.stops)
        st.markdown(f"**Mapped stops on this route ({len(stops_on_route)})**")
        if stops_on_route:
            st.dataframe(
                pd.DataFrame([{"#": i + 1, "Stop": s.get("name"),
                                "Lat": round(s["lat"], 4), "Lng": round(s["lng"], 4)}
                               for i, s in enumerate(stops_on_route)]),
                hide_index=True, use_container_width=True, height=220,
            )
        else:
            st.caption("No individually mapped stops recorded.")

        st.caption("Official GeoJSON route and attributes are view-only. "
                   "Use Draw on the map to create temporary user features.")

        st.divider()
        st.markdown("### Export selected route")
        jpeg_bytes = mu.export_map_jpeg(
            selected_route=sel_feat,
            selected_route_stops=stops_on_route,
            temp_fc=temp_feature_collection(),
        )
        st.download_button(
            "\U0001F4F7 Download map as JPEG",
            data=jpeg_bytes,
            file_name="DTCA_selected_route_map.jpg",
            mime="image/jpeg",
            use_container_width=True,
        )
    else:
        st.info("Search or click a route/stop on the map, or run a route "
                "recommendation, to see its details here.")

    if st.session_state.temp_features:
        st.divider()
        st.markdown(f"**Temporary drawings ({len(st.session_state.temp_features)})**")
        temp_names = [f.get("properties", {}).get("name", "Temporary feature")
                      for f in st.session_state.temp_features]
        st.write(", ".join(temp_names))
        d1, d2 = st.columns(2)
        d1.download_button(
            "Download drawings (GeoJSON)",
            data=json.dumps(temp_feature_collection(), indent=2),
            file_name="temporary_drawings.geojson",
            mime="application/geo+json",
            use_container_width=True,
        )
        if d2.button("Clear drawings", use_container_width=True):
            st.session_state.temp_features = []
            st.rerun()

# --------------------------------------------------------------------------
# Attribute table (view-only, mirrors the "Table" panel of the JS app)
# --------------------------------------------------------------------------

st.divider()
st.subheader("Attribute table")

tab_routes, tab_stops = st.tabs(["Routes", "Stops"])

with tab_routes:
    tquery = st.text_input("Filter routes", key="table_route_query")
    df_routes = an.routes_table(data.routes, tquery)
    st.caption(f"{len(df_routes)} record(s)")
    st.dataframe(df_routes, hide_index=True, use_container_width=True, height=340)
    st.download_button(
        "Download routes table (CSV)",
        data=df_routes.to_csv(index=False).encode("utf-8"),
        file_name="dtca_routes.csv",
        mime="text/csv",
    )
    picked_rid = st.selectbox(
        "Select a Route ID from the table to view its detail",
        [""] + df_routes["Route ID"].astype(str).tolist() if not df_routes.empty else [""],
    )
    if picked_rid:
        st.session_state.selected_route_id = picked_rid

with tab_stops:
    squery = st.text_input("Filter stops", key="table_stop_query")
    df_stops = an.stops_table(data.stops, squery)
    st.caption(f"{len(df_stops)} record(s)")
    st.dataframe(df_stops, hide_index=True, use_container_width=True, height=340)
    st.download_button(
        "Download stops table (CSV)",
        data=df_stops.to_csv(index=False).encode("utf-8"),
        file_name="dtca_stops.csv",
        mime="text/csv",
    )
    picked_stop = st.selectbox(
        "Select a stop from the table to highlight it",
        [""] + df_stops["Stop"].astype(str).tolist() if not df_stops.empty else [""],
    )
    if picked_stop:
        st.session_state.selected_stop_name = picked_stop
        match = next((s for s in data.stops if s.get("name") == picked_stop), None)
        if match:
            st.session_state.map_center = [match["lat"], match["lng"]]
            st.session_state.map_zoom = 16

st.caption("KML/CSV editing of official data is disabled by design - this "
           "explorer mirrors the original app's read-only + temporary-"
           "drawing workflow (see README.txt).")
