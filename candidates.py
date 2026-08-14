import requests
import polyline
from config import API_KEY
from input import route_build, find_segments  # now safe to import



def generate_loop_waypoints(lat, lon, radius_km, n_bearings=6):
    """Generate a few candidate loop waypoint-sets around a center point."""
    import math
    loops = []
    for start_bearing in range(0, 360, 360 // n_bearings):
        waypoints = []
        for angle_offset in [0, 120, 240]:
            bearing = math.radians(start_bearing + angle_offset)
            dlat = (radius_km / 111.0) * math.cos(bearing)
            dlon = (radius_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(bearing)
            waypoints.append((lat + dlat, lon + dlon))
        loops.append(waypoints)
    return loops


def compute_route(origin, waypoints, destination):
    """Call Routes API to turn waypoints into an actual walking path."""
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.distanceMeters"
    }
    body = {
        "origin": {"location": {"latLng": {"latitude": origin[0], "longitude": origin[1]}}},
        "destination": {"location": {"latLng": {"latitude": destination[0], "longitude": destination[1]}}},
        "intermediates": [
            {"location": {"latLng": {"latitude": w[0], "longitude": w[1]}}} for w in waypoints
        ],
        "travelMode": "WALK",
    }
    resp = requests.post(url, json=body, headers=headers)
    resp.raise_for_status()
    return resp.json()


def get_elevation_profile_from_polyline(encoded_polyline, samples=200, max_chunk_points=100):
    """Sample elevation along a route, splitting into multiple requests
    if the route has too many points for a single Elevation API call."""
    points = polyline.decode(encoded_polyline)
    total_points = len(points)

    if total_points <= max_chunk_points:
        return _fetch_elevation_chunk(points, samples)

    n_chunks = (total_points // max_chunk_points) + 1
    chunk_size = total_points // n_chunks
    elevations = []

    for i in range(n_chunks):
        start = i * chunk_size
        end = start + chunk_size if i < n_chunks - 1 else total_points
        chunk_points = points[start:end]
        if len(chunk_points) < 2:
            continue
        chunk_samples = max(2, samples // n_chunks)
        elevations.extend(_fetch_elevation_chunk(chunk_points, chunk_samples))

    return elevations


def _fetch_elevation_chunk(points, samples):
    path_str = "|".join(f"{lat},{lon}" for lat, lon in points)
    url = "https://maps.googleapis.com/maps/api/elevation/json"
    params = {"path": path_str, "samples": samples, "key": API_KEY}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "OK":
        raise RuntimeError(
            f"Elevation API error: {data['status']} — "
            f"{data.get('error_message', 'no further details')}"
        )
    return [r["elevation"] for r in data["results"]]

def decode_route(route_response):
    """Extract distance and decoded (lat, lon) points from a Routes API response."""
    route = route_response["routes"][0]
    distance_m = route["distanceMeters"]
    encoded = route["polyline"]["encodedPolyline"]
    points = polyline.decode(encoded)  # returns list of (lat, lon) tuples
    return distance_m, points


def build_candidate_fingerprint(path_points, elevations):
    """Turn decoded route points + elevation samples into the same
    fingerprint shape as an uploaded GPX route."""
    # route_build expects (lat, lon, elevation, time) tuples
    points = [(lat, lon, elev, None) for (lat, lon), elev in zip(path_points, elevations)]

    grid, elev, total_dist = route_build(points)
    climbs = find_segments(grid, elev, direction="up")
    descents = find_segments(grid, elev, direction="down")

    total_gain = sum(s["elevation_change_m"] for s in climbs)
    total_loss = sum(abs(s["elevation_change_m"]) for s in descents)

    import numpy as np
    norm_positions = np.linspace(0, 1, 100)
    actual_positions = grid / total_dist
    normalized_elev = np.interp(norm_positions, actual_positions, elev)

    return {
        "total_distance_km": round(total_dist / 1000, 2),
        "total_gain_m": round(total_gain, 1),
        "total_loss_m": round(total_loss, 1),
        "elevation_profile": normalized_elev.tolist(),
        "climb_segments": climbs,
        "descent_segments": descents,
        "start_lat": path_points[0][0],
        "start_lon": path_points[0][1],
    }


def generate_out_and_back_waypoint(lat, lon, one_way_km, n_bearings=6):
    import math
    endpoints = []
    for bearing_deg in range(0, 360, 360 // n_bearings):
        bearing = math.radians(bearing_deg)
        dlat = (one_way_km / 111.0) * math.cos(bearing)
        dlon = (one_way_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(bearing)
        endpoints.append((lat + dlat, lon + dlon))
    return endpoints


def compute_out_and_back_route(origin, endpoint):
    outbound = compute_route(origin, [], endpoint)
    dist_m, out_points = decode_route(outbound)
    full_points = out_points + out_points[::-1][1:]
    total_distance_m = dist_m * 2
    encoded = outbound["routes"][0]["polyline"]["encodedPolyline"]
    return total_distance_m, full_points, encoded

if __name__ == "__main__":
    # quick smoke test with a small radius so it stays well within free tier
    center = (12.922622343843708, 77.51939437954685)  # replace with your actual lat/lon
    loops = generate_loop_waypoints(center[0], center[1], radius_km=1.0, n_bearings=2)

    print(f"Generated {len(loops)} candidate loop(s)")
    for i, waypoints in enumerate(loops):
        route_response = compute_route(center, waypoints, center)
        distance_m, path_points = decode_route(route_response)

        elevations = get_elevation_profile(path_points, samples=min(200, len(path_points)))

        fp = build_candidate_fingerprint(path_points, elevations)

        print(f"\nLoop {i}: {fp['total_distance_km']} km, "
              f"gain {fp['total_gain_m']}m, loss {fp['total_loss_m']}m")
        print("Climbs:", fp["climb_segments"])
        print("Descents:", fp["descent_segments"])