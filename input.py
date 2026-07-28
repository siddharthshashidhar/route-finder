import gpxpy as gpx
import numpy as np
from geopy.distance import geodesic
from scipy.ndimage import uniform_filter1d

def read_gpx_file(file_path):
    with open (file_path) as f:
        gpx=gpx.parse(f)

    points=[]
    for track in gpx.tracks:
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


def hill_finding(grid,elev,min_gradient=0.03, min_length=100):
    gradients=np.gradient(elev, grid)

    segments=[]
    in_climb=False
    start_id=None

    for i,g in enumerate(gradients):
        if g>=min_gradient:
            if not in_climb:
                in_climb=True
                start_id=i
        elif g<min_gradient and in_climb:
            in_climb=False
            length=grid[i]-grid[start_id]
            if length>=min_length:
                gain=elev[i]-elev[start_id]
                segments.append({
                    "start":round(grid[start_id]/1000,2),
                    "end":round(grid[i]/1000,2),
                    "gain":round(gain,1),
                    "gradient %":round((gain/length)*100,1)
                })

    if in_climb:
        length=grid[-1]-grid[start_id]
        if length>=min_length:
            gain=elev[-1]-elev[start_id]
            segments.append({
                "start":round(grid[start_id]/1000,2),
                "end":round(grid[-1]/1000,2),
                "gain":round(gain,1),
                "gradient %":round((gain/length)*100,1)
            })


    return segments



