import matplotlib.pyplot as plt
import numpy as np


def plot_comparison(target_fp, ranked_candidates, top_n=3, filename="comparison.png"):
    """Plot target elevation profile against top N ranked candidates."""
    fig, axes = plt.subplots(top_n + 1, 1, figsize=(10, 3 * (top_n + 1)), sharex=True)

    x = np.linspace(0, 100, len(target_fp["elevation_profile"]))  # % of route distance

    # target on top
    axes[0].plot(x, target_fp["elevation_profile"], color="black", linewidth=2)
    axes[0].set_title(
        f"TARGET — {target_fp['total_distance_km']}km, "
        f"gain {target_fp['total_gain_m']}m, loss {target_fp['total_loss_m']}m"
    )
    axes[0].set_ylabel("Elevation (m)")
    axes[0].grid(alpha=0.3)

    # top N candidates below
    for i in range(top_n):
        candidate, score = ranked_candidates[i]
        fp = candidate["fingerprint"]
        axes[i + 1].plot(x, fp["elevation_profile"], color="tab:blue", linewidth=2)
        axes[i + 1].set_title(
            f"#{i+1} match (score={score:.2f}) — {fp['total_distance_km']}km, "
            f"gain {fp['total_gain_m']}m, loss {fp['total_loss_m']}m"
        )
        axes[i + 1].set_ylabel("Elevation (m)")
        axes[i + 1].grid(alpha=0.3)

    axes[-1].set_xlabel("% of route distance")
    plt.tight_layout()
    plt.savefig(filename, dpi=120)
    print(f"Saved chart to {filename}")