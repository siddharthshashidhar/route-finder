from input import read_gpx_file, build_fingerprint,classify_route_shape
from candidates import (
    generate_loop_waypoints,generate_out_and_back_waypoint, compute_route, decode_route,
    get_elevation_profile_from_polyline, build_candidate_fingerprint,compute_out_and_back_route
)
from similarity import rank_candidates

from cache import load_cached_candidates, save_candidates
from plot import plot_comparison



# 1. Build fingerprint from your uploaded route
uploaded_points = read_gpx_file("Morning_Run3.gpx")
target_fp = build_fingerprint(uploaded_points)
shape=classify_route_shape(uploaded_points)
print(f"Target route: {target_fp['total_distance_km']} km, gain {target_fp['total_gain_m']}m, shape {shape}")

# 2. Generate candidates near a location
center = (12.922622343843708, 77.51939437954685)
n_bearings = 4

if shape=="out_and_back":
    mode = "out_and_back"
    distance_param = target_fp["total_distance_km"] / 2
else:
    mode = "loop"
    distance_param = target_fp["total_distance_km"] / (2 * 3.14159)

candidates = load_cached_candidates(center[0], center[1], distance_param, n_bearings)

if candidates is None:
    print("No cache found — calling Google APIs...(mode={mode})")
    candidates = []

    if mode == "out_and_back":
        endpoints = generate_out_and_back_waypoint(center[0], center[1], distance_param, n_bearings)
        for endpoint in endpoints:
            dist_m, path_points, encoded = compute_out_and_back_route(center, endpoint)
            elevations = get_elevation_profile_from_polyline(encoded, samples=200)
            full_elevations = elevations + elevations[::-1][1:]
            fp = build_candidate_fingerprint(path_points, full_elevations)
            candidates.append({
                "fingerprint": fp,
                "path_points": path_points,
                "elevations": full_elevations,
                "encoded_polyline": encoded,
            })
    else:
        loops = generate_loop_waypoints(center[0], center[1], distance_param, n_bearings)
        for waypoints in loops:
            route_response = compute_route(center, waypoints, center)
            distance_m, path_points = decode_route(route_response)
            encoded = route_response["routes"][0]["polyline"]["encodedPolyline"]
            elevations = get_elevation_profile_from_polyline(encoded, samples=200)
            fp = build_candidate_fingerprint(path_points, elevations)
            candidates.append({
                "fingerprint": fp,
                "path_points": path_points,
                "elevations": elevations,
                "encoded_polyline": encoded,
            })

    save_candidates(center[0], center[1], distance_param, n_bearings, candidates, mode)

else:
    print(f"Loaded {len(candidates)} candidates from cache — no API calls made.")




# 3. Rank by similarity
ranked = rank_candidates(target_fp, candidates)


def route_to_maps_url(path_points):
    """Build a Google Maps directions URL you can open in a browser."""
    origin = path_points[0]
    destination = path_points[-1]
    # sample a few waypoints along the path (Maps URL API caps at ~25 waypoints)
    waypoint_sample = path_points[1:-1:max(1, len(path_points)//10)]
    waypoints_str = "|".join(f"{lat},{lon}" for lat, lon in waypoint_sample)

    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin[0]},{origin[1]}"
        f"&destination={destination[0]},{destination[1]}"
        f"&waypoints={waypoints_str}"
        "&travelmode=walking"
    )
    return url



def export_to_gpx(path_points, elevations, filename):
    with open(filename, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<gpx version="1.1" creator="route-finder">\n<trk><trkseg>\n')
        for (lat, lon), elev in zip(path_points, elevations):
            f.write(f'  <trkpt lat="{lat}" lon="{lon}"><ele>{elev}</ele></trkpt>\n')
        f.write('</trkseg></trk>\n</gpx>\n')




print("\nTop matches:")
for c, score in ranked:
    fp=c["fingerprint"]
    print(f"score={score:.2f} | {fp['total_distance_km']}km | "
          f"gain {fp['total_gain_m']}m | loss {fp['total_loss_m']}m")




best = ranked[0][0]

print("\nBest match route:")
print(route_to_maps_url(best["path_points"]))

export_to_gpx(best["path_points"], best["elevations"], "best_match.gpx")
print("Saved best_match.gpx")

plot_comparison(target_fp, ranked, top_n=min(3, len(ranked)))