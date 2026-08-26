"""
map_utils.py
------------
All Folium/matplotlib map-building code for the DTCA Bus Route Explorer.

This module turns the analysis.py data structures into:
  * an interactive folium.Map (routes, stops, corridors, admin boundaries,
    selection highlighting, temporary user drawings, O/D recommendation
    markers) - equivalent to the Leaflet map in the original JS/app.js.
  * a static JPEG export of the current selection (selected route + its
    stops + temporary drawings + legend + north arrow + scale bar), which
    mirrors the exportJPEG() function of the original app.

Nothing here reads Streamlit session state directly - app.py passes in
plain values, keeping this module reusable/testable.
"""

from __future__ import annotations

import io
import math
from typing import Optional

import folium
from folium.plugins import Draw, MarkerCluster

import analysis as an

# --------------------------------------------------------------------------
# Base map
# --------------------------------------------------------------------------

TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
TILE_ATTR = "&copy; OpenStreetMap contributors &copy; CARTO"


def build_base_map(center: tuple[float, float] = an.DEFAULT_CENTER,
                    zoom: int = an.DEFAULT_ZOOM) -> folium.Map:
    m = folium.Map(location=list(center), zoom_start=zoom,
                    tiles=None, control_scale=True, min_zoom=9, max_zoom=18)
    folium.TileLayer(tiles=TILE_URL, attr=TILE_ATTR, name="Basemap",
                      subdomains="abcd", max_zoom=20, control=False).add_to(m)
    return m


# --------------------------------------------------------------------------
# Read-only source layers
# --------------------------------------------------------------------------

def add_admin_layer(m: folium.Map, admin_fc: dict, show: bool = True) -> folium.FeatureGroup:
    fg = folium.FeatureGroup(name="Admin boundaries", show=show)
    folium.GeoJson(
        admin_fc,
        style_function=lambda _: {
            "color": an.ADMIN_COLOR, "weight": 1,
            "fillColor": an.ADMIN_FILL, "fillOpacity": 0.10, "opacity": 0.55,
        },
    ).add_to(fg)
    fg.add_to(m)
    return fg


def add_corridor_layer(m: folium.Map, corridors_fc: dict, show: bool = True) -> folium.FeatureGroup:
    fg = folium.FeatureGroup(name="Corridors", show=show)
    folium.GeoJson(
        corridors_fc,
        style_function=lambda _: {
            "color": an.CORRIDOR_COLOR, "weight": 2,
            "dashArray": "6 5", "opacity": 0.7,
        },
    ).add_to(fg)
    fg.add_to(m)
    return fg


def add_routes_layer(m: folium.Map, routes_fc: dict,
                      selected_route_id: Optional[str] = None,
                      show: bool = True) -> folium.FeatureGroup:
    """Adds every official route, highlighting `selected_route_id` if given.
    Each feature carries a rich HTML popup mirroring renderRouteDetail()."""
    fg = folium.FeatureGroup(name="Routes", show=show)

    def style_fn(feature):
        props = feature.get("properties", {})
        rid = props.get("Route_ID")
        if selected_route_id is not None and str(rid) == str(selected_route_id):
            return {"color": an.SELECTED_COLOR, "weight": 5, "opacity": 1}
        return {"color": an.route_color(props), "weight": 2.2, "opacity": 0.62}

    def highlight_fn(_feature):
        return {"weight": 4.5, "opacity": 0.95}

    folium.GeoJson(
        routes_fc,
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=folium.GeoJsonTooltip(fields=["Route_ID", "Operator"],
                                       aliases=["Route", "Operator"]),
        popup=folium.GeoJsonPopup(fields=["Route_ID", "Operator", "Bus Type",
                                           "Length", "Headway", "No of Trip",
                                           "Travel Tim"],
                                   aliases=["Route ID", "Operator", "Bus Type",
                                            "Length (km)", "Headway (min)",
                                            "Trips/day", "Travel time (min)"],
                                   max_width=320),
    ).add_to(fg)
    fg.add_to(m)
    return fg


def add_stops_layer(m: folium.Map, stops: list[dict],
                     selected_stop_name: Optional[str] = None,
                     cluster: bool = True, show: bool = True) -> folium.FeatureGroup:
    fg = folium.FeatureGroup(name="Stops", show=show)
    container = MarkerCluster(disableClusteringAtZoom=15).add_to(fg) if cluster else fg

    for s in stops:
        if s.get("lat") is None or s.get("lng") is None:
            continue
        selected = (selected_stop_name is not None
                    and s.get("name") == selected_stop_name)
        folium.CircleMarker(
            location=[s["lat"], s["lng"]],
            radius=7 if selected else 5,
            color="#fff", weight=1.4 if not selected else 2,
            fill=True,
            fill_color=an.SELECTED_COLOR if selected else an.STOP_COLOR,
            fill_opacity=0.95,
            tooltip=str(s.get("name") or ""),
            popup=folium.Popup(
                f"<b>{s.get('name','')}</b><br>Route {s.get('route_id','\u2014')}"
                f"<br>{s['lat']:.6f}, {s['lng']:.6f}", max_width=250),
        ).add_to(container)

    fg.add_to(m)
    return fg


def add_recommendation_markers(m: folium.Map, origin: Optional[dict],
                                destination: Optional[dict]) -> None:
    if origin:
        folium.CircleMarker(
            location=[origin["lat"], origin["lng"]], radius=10,
            color="#fff", weight=3, fill=True, fill_color=an.ORIGIN_COLOR,
            fill_opacity=1,
            tooltip=f"Origin: {origin.get('name','')}",
        ).add_to(m)
    if destination:
        folium.CircleMarker(
            location=[destination["lat"], destination["lng"]], radius=10,
            color="#fff", weight=3, fill=True, fill_color=an.DESTINATION_COLOR,
            fill_opacity=1,
            tooltip=f"Destination: {destination.get('name','')}",
        ).add_to(m)


# --------------------------------------------------------------------------
# Temporary drawings (mirrors "Draw -> Route / Point" + "Edit Drawings")
# --------------------------------------------------------------------------

def add_draw_control(m: folium.Map) -> Draw:
    """Wire up Leaflet.draw so the user can create/edit/delete temporary
    routes (polylines) and stops (markers). These never touch the read-only
    source GeoJSON layers - they only live in Streamlit session_state and
    are (de)serialised as their own small GeoJSON FeatureCollection, exactly
    as the JS app kept tempRoutes/tempPoints separate from ROUTES_DATA."""
    draw = Draw(
        export=False,
        position="topleft",
        draw_options={
            "polyline": {"shapeOptions": {"color": an.TEMP_COLOR, "weight": 5,
                                           "dashArray": "10 6"}},
            "marker": True,
            "polygon": True,   # used for "Select by Polygon"
            "circle": False,
            "circlemarker": False,
            "rectangle": False,
        },
        edit_options={"edit": True, "remove": True},
    )
    draw.add_to(m)
    return draw


def add_temp_layer(m: folium.Map, temp_fc: dict) -> folium.FeatureGroup:
    """Renders a previously-drawn temporary FeatureCollection (as produced by
    st_folium's `all_drawings` / `last_active_drawing`) back onto the map,
    e.g. after the user reloads the recommendation or route selection."""
    fg = folium.FeatureGroup(name="Temporary drawings", show=True)
    if not temp_fc or not temp_fc.get("features"):
        fg.add_to(m)
        return fg

    for feat in temp_fc["features"]:
        geom = feat.get("geometry", {})
        props = feat.get("properties", {}) or {}
        name = props.get("name", "Temporary feature")
        if geom.get("type") == "Point":
            lng, lat = geom["coordinates"]
            folium.CircleMarker(
                location=[lat, lng], radius=7, color="#fff", weight=2,
                fill=True, fill_color=an.TEMP_COLOR, fill_opacity=0.95,
                tooltip=name,
            ).add_to(fg)
        elif geom.get("type") in ("LineString",):
            latlngs = [[c[1], c[0]] for c in geom["coordinates"]]
            folium.PolyLine(latlngs, color=an.TEMP_COLOR, weight=5,
                             dash_array="10 6", opacity=0.95,
                             tooltip=name).add_to(fg)
        elif geom.get("type") == "Polygon":
            latlngs = [[c[1], c[0]] for c in geom["coordinates"][0]]
            folium.Polygon(latlngs, color=an.NON_AC_COLOR, weight=2,
                            dash_array="6 5", fill_opacity=0.1,
                            tooltip=name or "Selection polygon").add_to(fg)
    fg.add_to(m)
    return fg


# --------------------------------------------------------------------------
# Selection-by-polygon (server-side point/line-in-polygon test)
# --------------------------------------------------------------------------

def point_in_polygon(lat: float, lng: float, poly_latlng: list[tuple[float, float]]) -> bool:
    """Ray-casting test, ported from JS pointInPoly()."""
    inside = False
    n = len(poly_latlng)
    j = n - 1
    for i in range(n):
        yi, xi = poly_latlng[i]
        yj, xj = poly_latlng[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def line_intersects_polygon(coords_lnglat: list[list[float]],
                             poly_latlng: list[tuple[float, float]]) -> bool:
    """lineIntersectsPolygon(): true if any route vertex falls inside the
    polygon, or any polygon vertex sits within 120m of the route."""
    for lng, lat in coords_lnglat:
        if point_in_polygon(lat, lng, poly_latlng):
            return True
    for plat, plng in poly_latlng:
        for lng, lat in coords_lnglat:
            if an.haversine_m((plat, plng), (lat, lng)) < 120:
                return True
    return False


def select_by_polygon(routes_fc: dict, stops: list[dict],
                       poly_latlng: list[tuple[float, float]]
                       ) -> tuple[list[dict], list[dict]]:
    """finishPolygon(): returns (matching route features, matching stops)."""
    if len(poly_latlng) < 3:
        return [], []
    matched_routes = []
    for feat in routes_fc.get("features", []):
        coords = an.route_geometry_coords(feat)
        if coords and line_intersects_polygon(coords, poly_latlng):
            matched_routes.append(feat)
    matched_stops = [s for s in stops
                      if s.get("lat") is not None
                      and point_in_polygon(s["lat"], s["lng"], poly_latlng)]
    return matched_routes, matched_stops


# --------------------------------------------------------------------------
# JPEG export (mirrors exportJPEG() in the original app)
# --------------------------------------------------------------------------

def export_map_jpeg(selected_route: Optional[dict],
                     selected_route_stops: list[dict],
                     temp_fc: Optional[dict],
                     title: str = "DTCA Bus Route Rationalization Project",
                     subtitle: str = "Selected Route Map \u00b7 Official Stops & Temporary User Drawings"
                     ) -> bytes:
    """Builds a static map figure (basemap + selected route + its stops +
    temporary drawings + legend + north arrow + scale bar + title block)
    and returns it as JPEG bytes, mirroring the canvas composition done by
    exportJPEG()/drawExportLegend()/drawExportNorthScale() in JS/app.js.

    Uses matplotlib (+ contextily for the basemap tiles when available).
    Falls back to a plain white background if contextily / network tiles
    are unavailable, so export still works offline.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyArrow
    from matplotlib.lines import Line2D

    fig = plt.figure(figsize=(18, 12), dpi=100)
    fig.patch.set_facecolor("#f3f5f7")

    # header band
    header_ax = fig.add_axes([0, 0.90, 1, 0.10])
    header_ax.set_facecolor("#122240")
    header_ax.set_xticks([]); header_ax.set_yticks([])
    for spine in header_ax.spines.values():
        spine.set_visible(False)
    header_ax.text(0.02, 0.62, title, color="white", fontsize=20,
                    fontweight="bold", va="center", transform=header_ax.transAxes)
    header_ax.text(0.02, 0.20, subtitle, color="#dbe7f5", fontsize=11,
                    va="center", transform=header_ax.transAxes)

    # map axes
    ax = fig.add_axes([0.04, 0.09, 0.92, 0.79])

    all_lats, all_lngs = [], []

    def collect(lat, lng):
        all_lats.append(lat); all_lngs.append(lng)

    # selected route
    if selected_route is not None:
        coords = an.route_geometry_coords(selected_route)
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        ax.plot(xs, ys, color=an.SELECTED_COLOR, linewidth=3.2, zorder=5)
        for x, y in zip(xs, ys):
            collect(y, x)

    for s in selected_route_stops:
        if s.get("lat") is None:
            continue
        ax.scatter([s["lng"]], [s["lat"]], s=45, color=an.STOP_COLOR,
                    edgecolor="white", linewidth=1.2, zorder=6)
        ax.annotate(str(s.get("name", "")), (s["lng"], s["lat"]),
                    fontsize=7, xytext=(3, 3), textcoords="offset points",
                    zorder=7)
        collect(s["lat"], s["lng"])

    # temporary drawings
    if temp_fc and temp_fc.get("features"):
        for feat in temp_fc["features"]:
            geom = feat.get("geometry", {})
            if geom.get("type") == "LineString":
                xs = [c[0] for c in geom["coordinates"]]
                ys = [c[1] for c in geom["coordinates"]]
                ax.plot(xs, ys, color=an.TEMP_COLOR, linewidth=3.2,
                         linestyle=(0, (8, 4)), zorder=5)
                for x, y in zip(xs, ys):
                    collect(y, x)
            elif geom.get("type") == "Point":
                lng, lat = geom["coordinates"]
                ax.scatter([lng], [lat], s=70, color=an.TEMP_COLOR,
                            edgecolor="white", linewidth=1.4, zorder=6)
                name = (feat.get("properties") or {}).get("name", "")
                ax.annotate(name, (lng, lat), fontsize=7,
                            xytext=(3, 3), textcoords="offset points", zorder=7)
                collect(lat, lng)

    if all_lats:
        lat_pad = max((max(all_lats) - min(all_lats)) * 0.18, 0.01)
        lng_pad = max((max(all_lngs) - min(all_lngs)) * 0.18, 0.01)
        ax.set_xlim(min(all_lngs) - lng_pad, max(all_lngs) + lng_pad)
        ax.set_ylim(min(all_lats) - lat_pad, max(all_lats) + lat_pad)
    else:
        ax.set_xlim(90.30, 90.55)
        ax.set_ylim(23.65, 23.90)

    ax.set_facecolor("#eef2f5")
    ax.set_aspect("auto")

    # try to add a basemap via contextily (network permitting)
    try:
        import contextily as cx
        cx.add_basemap(ax, crs="EPSG:4326",
                        source=cx.providers.CartoDB.Positron)
    except Exception:
        ax.grid(True, color="#d7dee6", linewidth=0.6)

    ax.tick_params(labelbottom=False, labelleft=False, bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_edgecolor("#9aa8b8")

    # legend
    legend_elements = [
        Line2D([0], [0], color=an.SELECTED_COLOR, lw=4, label="Selected route"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=an.STOP_COLOR,
               markersize=8, label="Official bus stop"),
        Line2D([0], [0], color=an.TEMP_COLOR, lw=4, linestyle=(0, (8, 4)),
               label="Temporary route"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=an.TEMP_COLOR,
               markersize=8, label="Temporary stop"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", frameon=True,
               facecolor="white", framealpha=0.97, fontsize=9,
               title="Legend", title_fontsize=10)

    # north arrow
    nx, ny = 0.94, 0.80
    ax.annotate("N", xy=(nx, ny + 0.06), xycoords="axes fraction",
                fontsize=16, fontweight="bold", ha="center", color="#122240")
    ax.annotate("", xy=(nx, ny + 0.05), xytext=(nx, ny - 0.03),
                xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="#122240", lw=2))

    # scale bar (approximate, based on current axis span)
    if all_lngs:
        span_deg = max(all_lngs) - min(all_lngs) if len(all_lngs) > 1 else 0.05
        span_km = span_deg * 111.0 * math.cos(math.radians(sum(all_lats) / len(all_lats)))
        bar_km = max(0.5, round(span_km / 4, 1))
        bar_frac = (bar_km / max(span_km, 0.001)) * 0.6
        bx0, by0 = 0.05, 0.05
        ax.annotate("", xy=(bx0 + bar_frac, by0), xytext=(bx0, by0),
                    xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="-", color="#17243a", lw=3))
        ax.text(bx0, by0 + 0.02, f"{bar_km:g} km", transform=ax.transAxes,
                fontsize=9, fontweight="bold", color="#17243a")

    # footer
    footer_ax = fig.add_axes([0, 0.0, 1, 0.045])
    footer_ax.set_xticks([]); footer_ax.set_yticks([])
    for spine in footer_ax.spines.values():
        spine.set_visible(False)
    footer_ax.text(0.02, 0.5, "Basemap: \u00a9 OpenStreetMap contributors \u00a9 CARTO",
                    fontsize=9, va="center", color="#334155",
                    transform=footer_ax.transAxes)
    footer_ax.text(0.02, -0.6, "Source: DTCA BRR Project", fontsize=9,
                    va="center", color="#334155", transform=footer_ax.transAxes)
    import datetime
    footer_ax.text(0.98, 0.5, datetime.date.today().isoformat(), fontsize=9,
                    va="center", ha="right", color="#334155",
                    transform=footer_ax.transAxes)

    buf = io.BytesIO()
    fig.savefig(buf, format="jpg", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
