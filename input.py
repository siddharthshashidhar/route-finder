import gpxpy as gpx
import numpy as np
from geopy.distance import geodesic
from scipy.ndimage import uniform_filter1d

def read_gpx_file(file_path):
    with open (file_path) as f:
        gpx_d=gpx.parse(f)

    points=[]
    for track in gpx_d.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude, point.elevation, point.time))

    return points



def route_build(points):
    dist=[0.0]
    for i in range(1,len(points)):
        d=geodesic((points[i-1][0], points[i-1][1]), (points[i][0], points[i][1])).meters
        dist.append(dist[-1]+d)

    total_distance=dist[-1]

    elevations=np.array([point[2]for point in points])
    smoothen_elevation=uniform_filter1d(elevations, size=5)

    grid=np.arange(0, total_distance, 100)
    elevation_resampled=np.interp(grid,dist,smoothen_elevation)

    return grid, elevation_resampled, total_distance

def find_segments(grid, elev, min_gradient=0.03, min_length=100, direction="up"):
    gradients = np.gradient(elev, grid)

    sign = 1 if direction == "up" else -1
    threshold = sign * min_gradient

    start_id = None
    in_segment = False
    segments = []

    def close_segment(end_id):
        length = grid[end_id] - grid[start_id]
        if length >= min_length:
            gain = elev[end_id] - elev[start_id]
            segments.append({
                "type": direction,
                "start": float(round(grid[start_id] / 1000, 2)),
                "end": float(round(grid[end_id] / 1000, 2)),
                "elevation_change_m": float(round(gain, 1)),
                "gradient_pct": float(round((gain / length) * 100, 1)),
            })

    for i, g in enumerate(gradients):
        crossed = (g >= threshold) if direction == "up" else (g <= threshold)
        if crossed and not in_segment:
            in_segment = True
            start_id = i
        elif not crossed and in_segment:
            in_segment = False
            close_segment(i)

    if in_segment:
        close_segment(len(grid) - 1)

    return segments

def hill_finding(grid,elev,min_gradient=0.03, min_length=100):
    climbs = find_segments(grid, elev, min_gradient, min_length, direction="up")
    descents = find_segments(grid, elev, min_gradient, min_length, direction="down")
    return sorted(climbs + descents, key=lambda s: s["start"])


def build_fingerprint(points):
    grid, elev, total_dist = route_build(points)
    climbs = find_segments(grid, elev, direction="up")
    descents = find_segments(grid, elev, direction="down")

    total_gain = sum(s["elevation_change_m"] for s in climbs)
    total_loss = sum(abs(s["elevation_change_m"]) for s in descents)

    # normalize elevation profile to a fixed length (100 points, 0-100% of distance)
    # so routes of different lengths can still be compared by shape
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
        "start_lat": points[0][0],
        "start_lon": points[0][1],
    }



def classify_route_shape(points, tolerance_km=0.3):
    """Guess whether a route is a loop, out-and-back, or point-to-point."""
    start = points[0][:2]
    end = points[-1][:2]
    start_end_dist_km = geodesic(start, end).km

    if start_end_dist_km > tolerance_km:
        return "point_to_point"

    # start ≈ end — now check if it's a loop or an out-and-back.
    # Out-and-back: the outbound half and return half retrace the same roads.
    mid = len(points) // 2
    outbound = points[:mid]
    inbound = points[mid:][::-1]  # reverse so it lines up direction-wise

    # sample a few matching points and check how close they are geographically
    sample_idxs = range(0, min(len(outbound), len(inbound)), max(1, mid // 10))
    diffs = [
        geodesic(outbound[i][:2], inbound[i][:2]).km
        for i in sample_idxs
    ]
    avg_diff = sum(diffs) / len(diffs)

    return "out_and_back" if avg_diff < tolerance_km else "loop"




if __name__ == "__main__":
    points = read_gpx_file("Morning_Run.gpx")
    fp = build_fingerprint(points)
    print(f"Distance: {fp['total_distance_km']} km")
    print(f"Total gain: {fp['total_gain_m']}m, Total loss: {fp['total_loss_m']}m")
    print("\nClimbs:")
    for c in fp["climb_segments"]:
        print(c)
    print("\nDescents:")
    for d in fp["descent_segments"]:
        print(d)
    print(classify_route_shape(points))