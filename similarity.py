import numpy as np
from dtaidistance import dtw


def similarity_score(target_fp, candidate_fp):
    """Lower score = more similar. Combines elevation shape (DTW) with
    total distance and total gain differences."""
    t = np.array(target_fp["elevation_profile"])
    c = np.array(candidate_fp["elevation_profile"])

    # normalize to zero mean so we compare *shape*, not absolute altitude
    t_norm = t - np.mean(t)
    c_norm = c - np.mean(c)
    shape_dist = dtw.distance(t_norm, c_norm)

    dist_diff = abs(target_fp["total_distance_km"] - candidate_fp["total_distance_km"])
    gain_diff = abs(target_fp["total_gain_m"] - candidate_fp["total_gain_m"])

    score = (
        0.6 * shape_dist
        + 0.25 * dist_diff
        + 0.15 * (gain_diff / 10)
    )
    return score


def rank_candidates(target_fp, candidates):
    scored = [(c, similarity_score(target_fp, c["fingerprint"])) for c in candidates]
    scored.sort(key=lambda pair: pair[1])
    return scored

def score_to_percent(score, k=10):
    return round(100 / (1 + score / k), 1)