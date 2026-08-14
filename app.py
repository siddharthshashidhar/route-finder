import streamlit as st
import gpxpy

from input import build_fingerprint, classify_route_shape
from candidates import (
    generate_loop_waypoints, generate_out_and_back_waypoint,
    compute_route, compute_out_and_back_route, decode_route,
    get_elevation_profile_from_polyline, build_candidate_fingerprint
)
from similarity import rank_candidates,score_to_percent
from cache import load_cached_candidates, save_candidates, get_usage_count, increment_usage
from plot import plot_comparison
from utils import route_to_maps_url, build_gpx_string

DAILY_LIMIT = 100

st.set_page_config(page_title="Route Finder", layout="wide")
st.write(f"User calls made - {get_usage_count()}")
st.title("Route Finder")
st.write("Upload a GPX file from a race or run, and find similar road-running routes near a location.")

uploaded_file = st.file_uploader("Upload GPX file", type=["gpx"])

st.write("Enter co-ordinates of your location/preferred start point")
col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude", value=12.922517772758622, format="%.6f")
with col2:
    lon = st.number_input("Longitude", value= 77.51957676975401, format="%.6f")

n_bearings = st.slider("Number of candidate directions to try", 2, 8, 4)

if uploaded_file and st.button("Find similar routes", type="primary"):
    with st.spinner("Reading your route..."):
        gpx_data = gpxpy.parse(uploaded_file)
        points = []
        for track in gpx_data.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.latitude, point.longitude, point.elevation, point.time))
        target_fp = build_fingerprint(points)
        shape = classify_route_shape(points)

    st.success(
        f"Your route: {target_fp['total_distance_km']} km, "
        f"gain {target_fp['total_gain_m']}m, Shape: {shape}"
    )

    center = (lat, lon)
    if shape == "out_and_back":
        mode = "out_and_back"
        distance_param = target_fp["total_distance_km"] / 2
    else:
        mode = "loop"
        distance_param = target_fp["total_distance_km"] / (2 * 3.14159)

    candidates = load_cached_candidates(center[0], center[1], distance_param, n_bearings, mode)

    if candidates is None:
        if get_usage_count() >= DAILY_LIMIT:
            st.error("Daily usage limit reached — please try again tomorrow.")
            st.stop()

        with st.spinner("Generating candidate routes via Google Maps..."):
            candidates = []
            if mode == "out_and_back":
                endpoints = generate_out_and_back_waypoint(center[0], center[1], distance_param, n_bearings)
                for endpoint in endpoints:
                    dist_m, path_points, encoded = compute_out_and_back_route(center, endpoint)
                    elevations = get_elevation_profile_from_polyline(encoded, samples=200)
                    full_elevations = elevations + elevations[::-1][1:]
                    fp = build_candidate_fingerprint(path_points, full_elevations)
                    candidates.append({
                        "fingerprint": fp, "path_points": path_points,
                        "elevations": full_elevations, "encoded_polyline": encoded,
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
                        "fingerprint": fp, "path_points": path_points,
                        "elevations": elevations, "encoded_polyline": encoded,
                    })
            save_candidates(center[0], center[1], distance_param, n_bearings, candidates, mode)
            increment_usage(n_bearings * 2)
    else:
        st.info(f"Loaded {len(candidates)} cached candidates — no API calls made.")

    ranked = rank_candidates(target_fp, candidates)

    st.subheader("Top matches")
    for i, (c, score) in enumerate(ranked[:3]):
        fp = c["fingerprint"]
        similarity_pct=score_to_percent(score)
        st.markdown(f"### #{i+1} — Similarity - %")
        st.write(f" - km · gain {fp['total_gain_m']}m · loss {fp['total_loss_m']}m")
        st.markdown(f"[Open route in Google Maps]({route_to_maps_url(c['path_points'])})")
        gpx_str = build_gpx_string(c["path_points"], c["elevations"])
        st.download_button(f"Download GPX #{i+1}", gpx_str, file_name=f"match_{i+1}.gpx", key=f"dl_{i}")
        st.divider()

    st.subheader("Elevation profile comparison")
    plot_comparison(target_fp, ranked, top_n=min(3, len(ranked)), filename="comparison.png")
    st.image("comparison.png")
