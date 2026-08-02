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



points = read_gpx_file("Morning_Run.gpx")
grid, elev, total_dist = route_build(points)
hills = hill_finding(grid, elev)

print(f"Total distance: {total_dist/1000:.2f} km")
print(f"Found {len(hills)} climb/descent segments:")
for h in hills:
    print(h)