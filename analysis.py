"""
analysis.py
-----------
Core, UI-independent business logic for the DTCA Bus Route Explorer.

This module is a faithful Python port of the analysis logic that lived in the
original web app's JS/app.js (route/stop styling rules, route <-> stop
matching, nearest-point-on-line projection, the Origin/Destination route
recommendation algorithm and its fare formula, and search/filter helpers).

Nothing in this module touches Streamlit or Folium - it only works with
plain Python data structures (dicts / lists / pandas DataFrames) so it can be
unit-tested or reused outside the app.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# --------------------------------------------------------------------------
# Constants (ported 1:1 from JS/app.js and README.md)
# --------------------------------------------------------------------------

DEFAULT_CENTER = (23.79, 90.41)  # (lat, lon) - matches map.setView([23.79,90.41],11)
DEFAULT_ZOOM = 11

AC_COLOR = "#0E7C86"
NON_AC_COLOR = "#2B6CB0"
SELECTED_COLOR = "#E4572E"
CORRIDOR_COLOR = "#B9860A"
ADMIN_COLOR = "#9fb0c2"
ADMIN_FILL = "#c9d3de"
STOP_COLOR = "#122240"
TEMP_COLOR = "#7c3aed"
ORIGIN_COLOR = "#16a34a"
DESTINATION_COLOR = "#dc2626"

EARTH_RADIUS_M = 6371000.0

DATA_DIR = Path(__file__).parent / "data"


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def load_geojson(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class ExplorerData:
    routes: dict            # GeoJSON FeatureCollection (read-only source layer)
    stops: list[dict]       # flattened stop dicts: name, route_id, lat, lng
    stops_df: pd.DataFrame
    corridors: dict
    admin: dict


def load_all_data(data_dir: Path = DATA_DIR) -> ExplorerData:
    """Load the four read-only source layers, mirroring script/bootstrap.js."""
    routes = load_geojson(data_dir / "routes.geojson")
    stops_raw = load_geojson(data_dir / "stops.geojson")
    corridors = load_geojson(data_dir / "corridors.geojson")
    admin = load_geojson(data_dir / "admin.geojson")

    stops: list[dict] = []
    for feat in stops_raw.get("features", []):
        props = dict(feat.get("properties") or {})
        coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
        props["lng"] = coords[0]
        props["lat"] = coords[1]
        stops.append(props)

    stops_df = pd.DataFrame(stops)
    return ExplorerData(routes=routes, stops=stops, stops_df=stops_df,
                         corridors=corridors, admin=admin)


# --------------------------------------------------------------------------
# Styling / classification helpers (ported from JS)
# --------------------------------------------------------------------------

def is_ac(props: dict) -> bool:
    """isAC(p): bus type contains 'AC' but not 'NON'."""
    t = str(props.get("Bus Type") or "").upper()
    return "AC" in t and "NON" not in t


def route_color(props: dict) -> str:
    return AC_COLOR if is_ac(props) else NON_AC_COLOR


def align_parts(props: dict) -> list[str]:
    """alignParts(p): split the 'Alingment' string on '?' (mojibake dash)."""
    raw = str(props.get("Alingment") or "")
    return [p.strip() for p in raw.split("?") if p.strip()]


def normalize(s: Any) -> str:
    """normalize(s): lowercase, unify dashes, strip non-alphanumerics."""
    s = str(s or "")
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"[^a-z0-9]+", "", s.lower())
    return s.strip()


def fare_for_km(km: float) -> float:
    """fareForKm(km): BDT 2.53/km, min BDT 10, rounded up to nearest BDT 5."""
    raw = max(10.0, float(km or 0) * 2.53)
    return max(10.0, math.ceil(raw / 5.0) * 5.0)


def fmt_num(v: Any, digits: int = 1) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "\u2014"
    if not math.isfinite(x):
        return "\u2014"
    return f"{x:,.{digits}f}"


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------

def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in meters between (lat,lng) points a and b."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def polyline_length_m(coords_latlng: list[tuple[float, float]]) -> float:
    return sum(haversine_m(coords_latlng[i - 1], coords_latlng[i])
               for i in range(1, len(coords_latlng)))


def route_geometry_coords(feature: dict) -> list[list[float]]:
    """routeGeometryCoords(f): returns [lng,lat] pairs for the route's
    LineString, or the longest part of a MultiLineString."""
    geom = feature.get("geometry") or {}
    gtype = geom.get("type")
    if gtype == "LineString":
        return geom.get("coordinates") or []
    if gtype == "MultiLineString":
        parts = geom.get("coordinates") or []
        best: list = []
        for part in parts:
            if len(part) > len(best):
                best = part
        return best
    return []


def project_point_on_route(coords_lnglat: list[list[float]],
                            point_latlng: tuple[float, float]) -> Optional[dict]:
    """projectPointOnRoute(coords, ll): nearest point on the polyline to
    point_latlng, returning distance, along-track distance and total length,
    mirroring the JS implementation (equirectangular-ish planar projection
    per segment, then haversine for actual distances)."""
    if len(coords_lnglat) < 2:
        return None

    best = {"d": math.inf, "seg": 0, "t": 0.0, "pt": None, "along": 0.0}
    cumulative = 0.0
    plat, plng = point_latlng

    for i in range(len(coords_lnglat) - 1):
        a_lng, a_lat = coords_lnglat[i]
        b_lng, b_lat = coords_lnglat[i + 1]
        dx, dy = b_lng - a_lng, b_lat - a_lat
        den = dx * dx + dy * dy
        t = 0.0
        if den > 0:
            t = ((plng - a_lng) * dx + (plat - a_lat) * dy) / den
        t = max(0.0, min(1.0, t))
        pt_lat = a_lat + (b_lat - a_lat) * t
        pt_lng = a_lng + (b_lng - a_lng) * t
        d = haversine_m((plat, plng), (pt_lat, pt_lng))
        seg_len = haversine_m((a_lat, a_lng), (b_lat, b_lng))
        if d < best["d"]:
            best = {"d": d, "seg": i, "t": t, "pt": (pt_lat, pt_lng),
                    "along": cumulative + seg_len * t}
        cumulative += seg_len

    best["total"] = cumulative
    return best


# --------------------------------------------------------------------------
# Route <-> stop matching
# --------------------------------------------------------------------------

def route_stops(feature: dict, stops: list[dict]) -> list[dict]:
    """routeStops(f): stops mapped to this route, ordered by nearest vertex
    index along the route geometry (matches JS behaviour)."""
    rid = feature.get("properties", {}).get("Route_ID")
    st = [dict(s) for s in stops if str(s.get("route_id")) == str(rid)]
    coords = feature.get("geometry", {}).get("coordinates") or []
    if len(coords) < 2:
        return st

    def idx_of(s):
        best_d, best_i = math.inf, 0
        for i, (x_lng, x_lat) in enumerate(coords):
            dx = (x_lng - s["lng"]) * math.cos(math.radians(s["lat"]))
            dy = x_lat - s["lat"]
            d = dx * dx + dy * dy
            if d < best_d:
                best_d, best_i = d, i
        return best_i

    for s in st:
        s["_i"] = idx_of(s)
    st.sort(key=lambda s: s["_i"])
    return st


def stop_candidates(stops: list[dict], name: str) -> list[dict]:
    return [s for s in stops if str(s.get("name")) == str(name)]


def common_route_ids(a: list[dict], b: list[dict]) -> list[str]:
    a_ids = {str(s.get("route_id")) for s in a}
    seen = []
    for s in b:
        rid = str(s.get("route_id"))
        if rid in a_ids and rid not in seen:
            seen.append(rid)
    return seen


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------

def search_routes(routes_fc: dict, query: str, limit: int = 20) -> list[dict]:
    """runSearch(q): match on Route_ID, Operator, or any alignment segment."""
    q = normalize(query)
    if not q:
        return []
    results = []
    for feat in routes_fc.get("features", []):
        p = feat.get("properties", {})
        if (q in normalize(p.get("Route_ID"))
                or q in normalize(p.get("Operator"))
                or any(q in normalize(part) for part in align_parts(p))):
            results.append(feat)
        if len(results) >= limit:
            break
    return results


def search_stops(stops: list[dict], query: str, limit: int = 100) -> list[dict]:
    q = str(query or "").strip().lower()
    arr = [s for s in stops if s.get("name")
           and (not q or q in str(s["name"]).lower())]
    arr.sort(key=lambda s: (str(s.get("name")), str(s.get("route_id"))))
    return arr[:limit]


# --------------------------------------------------------------------------
# Route recommendation (Origin -> Destination)
# --------------------------------------------------------------------------

@dataclass
class Recommendation:
    route_feature: dict
    origin_stop: dict
    destination_stop: dict
    distance_km: float
    time_min: float
    fare_bdt: float


def recommend_route(routes_fc: dict, stops: list[dict],
                     origin_name: str, destination_name: str
                     ) -> Optional[Recommendation]:
    """recommend(): ranks candidate routes that serve both the origin and
    destination stop names and returns the shortest-distance match, exactly
    as the JS implementation does."""
    if not origin_name or not destination_name or origin_name == destination_name:
        return None

    origins = stop_candidates(stops, origin_name)
    destinations = stop_candidates(stops, destination_name)
    route_ids = common_route_ids(origins, destinations)

    routes_by_id = {f["properties"].get("Route_ID"): f
                    for f in routes_fc.get("features", [])}

    candidates = []
    for rid in route_ids:
        feat = routes_by_id.get(rid)
        if not feat:
            continue
        coords = route_geometry_coords(feat)
        if len(coords) < 2:
            continue
        for o in [s for s in origins if str(s.get("route_id")) == rid]:
            for d in [s for s in destinations if str(s.get("route_id")) == rid]:
                op = project_point_on_route(coords, (o["lat"], o["lng"]))
                dp = project_point_on_route(coords, (d["lat"], d["lng"]))
                if not op or not dp:
                    continue
                distance_km = abs(dp["along"] - op["along"]) / 1000.0
                if distance_km > 0:
                    candidates.append({
                        "f": feat, "o": o, "d": d,
                        "distance_km": distance_km,
                        "total_m": op["total"],
                    })

    if not candidates:
        return None

    candidates.sort(key=lambda c: c["distance_km"])
    best = candidates[0]
    feat = best["f"]
    p = feat.get("properties", {})
    km = best["distance_km"]

    full_km = _to_float(p.get("Length")) or (best["total_m"] / 1000.0)
    full_time = _to_float(p.get("Travel Tim"))
    if not full_time or full_time <= 0:
        full_time = full_km / 20.0 * 60.0

    time_min = full_time * (km / full_km) if full_km > 0 else (km / 20.0 * 60.0)
    fare = fare_for_km(km)

    return Recommendation(
        route_feature=feat, origin_stop=best["o"], destination_stop=best["d"],
        distance_km=km, time_min=time_min, fare_bdt=fare,
    )


def _to_float(v: Any) -> Optional[float]:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Attribute-table helpers (used by the "Table" view in app.py)
# --------------------------------------------------------------------------

def routes_table(routes_fc: dict, query: str = "", limit: int = 500) -> pd.DataFrame:
    q = normalize(query)
    rows = []
    for feat in routes_fc.get("features", []):
        p = feat.get("properties", {})
        if q and q not in normalize(json.dumps(p)):
            continue
        rows.append({
            "Route ID": p.get("Route_ID"),
            "Operator": p.get("Operator"),
            "Bus Type": p.get("Bus Type"),
            "Length km": _to_float(p.get("Length")),
            "Trips / Day": round(_to_float(p.get("No of Trip")) or 0),
            "Travel min": _to_float(p.get("Travel Tim")),
        })
        if len(rows) >= limit:
            break
    return pd.DataFrame(rows)


def stops_table(stops: list[dict], query: str = "", limit: int = 500) -> pd.DataFrame:
    q = normalize(query)
    rows = []
    for s in stops:
        if q and q not in normalize(json.dumps(s)):
            continue
        rows.append({
            "Stop": s.get("name"),
            "Route ID": s.get("route_id"),
            "Latitude": s.get("lat"),
            "Longitude": s.get("lng"),
        })
        if len(rows) >= limit:
            break
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Summary stats (used in the header / sidebar, matches statRoutes etc.)
# --------------------------------------------------------------------------

def summary_stats(routes_fc: dict, stops: list[dict]) -> dict:
    total_len = 0.0
    ac_count = 0
    for feat in routes_fc.get("features", []):
        p = feat.get("properties", {})
        total_len += _to_float(p.get("Length")) or 0.0
        if is_ac(p):
            ac_count += 1
    return {
        "routes": len(routes_fc.get("features", [])),
        "stops": len(stops),
        "length_km": round(total_len),
        "ac_routes": ac_count,
    }
