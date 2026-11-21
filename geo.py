"""Geospatial helpers: GeoJSON export, radius search, and an explorer-journey route."""
import math


def haversine_km(a_lat, a_lon, b_lat, b_lon):
    r = 6371.0088
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def to_geojson(sites):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
         "properties": {k: s[k] for k in ("id", "title", "place", "state", "category", "photo_count", "native_name")}}
        for s in sites]}


def nearby(sites, lat, lon, radius_km):
    out = []
    for s in sites:
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if d <= radius_km:
            out.append({**s, "distance_km": round(d, 1)})
    return sorted(out, key=lambda x: x["distance_km"])


def journey(sites, start_id=None):
    """Nearest-neighbour tour through the sites (a cheap TSP heuristic) with leg and total distances."""
    if not sites:
        return {"stops": [], "total_km": 0}
    left = list(sites)
    cur = next((s for s in left if s["id"] == start_id), None) or min(left, key=lambda s: -s["lat"])
    left.remove(cur)
    stops, total = [{"id": cur["id"], "title": cur["title"], "lat": cur["lat"], "lon": cur["lon"], "leg_km": 0}], 0.0
    while left:
        nxt = min(left, key=lambda s: haversine_km(cur["lat"], cur["lon"], s["lat"], s["lon"]))
        leg = haversine_km(cur["lat"], cur["lon"], nxt["lat"], nxt["lon"])
        total += leg
        stops.append({"id": nxt["id"], "title": nxt["title"], "lat": nxt["lat"], "lon": nxt["lon"], "leg_km": round(leg, 1)})
        left.remove(nxt); cur = nxt
    return {"stops": stops, "total_km": round(total, 1)}
