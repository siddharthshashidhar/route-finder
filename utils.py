def route_to_maps_url(path_points):
    origin = path_points[0]
    destination = path_points[-1]
    waypoint_sample = path_points[1:-1:max(1, len(path_points)//10)]
    waypoints_str = "|".join(f"{lat},{lon}" for lat, lon in waypoint_sample)
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin[0]},{origin[1]}"
        f"&destination={destination[0]},{destination[1]}"
        f"&waypoints={waypoints_str}"
        "&travelmode=walking"
    )


def build_gpx_string(path_points, elevations):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<gpx version="1.1" creator="route-finder">', '<trk><trkseg>']
    for (lat, lon), elev in zip(path_points, elevations):
        lines.append(f'  <trkpt lat="{lat}" lon="{lon}"><ele>{elev}</ele></trkpt>')
    lines.append('</trkseg></trk>\n</gpx>')
    return "\n".join(lines)