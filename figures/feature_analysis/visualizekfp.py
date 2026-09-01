#!/usr/bin/env python3

import re
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42

# =========================
# Feature renaming
# =========================

def canonical_feature_name(name):
    """
    Rename old tail.feature_i names into the newer internal feature names.

    Mapping:
      tail.feature_i, i < 20   -> alt_concentration20.i
      tail.feature_i, i >= 20  -> alt_per_sec.i
    """
    m = re.fullmatch(r"tail\.feature_(\d+)", name)
    if not m:
        return name

    i = int(m.group(1))
    if i < 20:
        return f"alt_concentration20.{i}"
    return f"alt_per_sec.{i-19}"


# =========================
# Top-10 importances
# =========================

our_top10 = {
    "direction_ratio.out_fraction": 0.022967,
    "tail.feature_013": 0.022725,
    "tail.feature_024": 0.022484,
    "concentration20.avg_out_per_chunk": 0.022336,
    "direction_ratio.in_fraction": 0.021967,
    "concentration20.std_out_per_chunk": 0.021502,
    "tail.feature_025": 0.021435,
    "tail.feature_018": 0.021302,
    "tail.feature_020": 0.020510,
    "tail.feature_016": 0.020305,
}

their_top10 = {
    "ordering.avg_out_position": 0.031159,
    "count.in": 0.024847,
    "ordering.std_out_position": 0.024711,
    "ordering.std_in_position": 0.020700,
    "ordering.avg_in_position": 0.019085,
    "sum.packet_counts": 0.018931,
    "count.total": 0.018526,
    "sum.alt_per_sec_20bins": 0.018206,
    "direction_ratio.in_fraction": 0.017881,
    "direction_ratio.out_fraction": 0.016834,
}

# Apply internal renaming
our_top10 = {canonical_feature_name(k): v for k, v in our_top10.items()}
their_top10 = {canonical_feature_name(k): v for k, v in their_top10.items()}


# =========================
# Human-readable labels
# =========================

SPECIAL_NAMES = {
    "direction_ratio.out_fraction": "Out pkt frac.",
    "direction_ratio.in_fraction": "In pkt frac.",

    "concentration20.avg_out_per_chunk": "Out. conc. avg.",
    "concentration20.std_out_per_chunk": "Out. conc. std.",

    "ordering.avg_out_position": "Avg. out pos.",
    "ordering.std_out_position": "Std. out pos.",
    "ordering.std_in_position": "Std. in pos.",
    "ordering.avg_in_position": "Avg. in pos.",

    "count.in": "In pkt count",
    "count.total": "Total pkt count",

    "sum.packet_counts": "Pkt-count summary",
    "sum.alt_per_sec_20bins": "Per-sec summary",
}


def humanize_feature(name):
    if name in SPECIAL_NAMES:
        return SPECIAL_NAMES[name]

    m = re.fullmatch(r"alt_concentration20\.(\d+)", name)
    if m:
        return f"Alt. conc. {int(m.group(1))}"

    m = re.fullmatch(r"alt_per_sec\.(\d+)", name)
    if m:
        return f"Alt. pkt/sec. {int(m.group(1))}"

    s = name
    s = s.replace("interarrival", "IAT")
    s = s.replace("concentration20", "Conc.")
    s = s.replace("per_sec", "Per-sec")
    s = s.replace("ordering", "Order")
    s = s.replace("direction_ratio", "Dir. ratio")
    s = s.replace("count", "Count")
    s = s.replace("sum", "Summary")
    s = s.replace("_", " ")
    s = s.replace(".", " · ")
    return s


# =========================
# Category / color mapping
# =========================

CATEGORY_COLORS = {
    "timing": "#4C78A8",     # blue
    "direction": "#E45756",  # red
}

CATEGORY_LABELS = {
    "timing": "Timing-based",
    "direction": "Direction-based",
}


def feature_category(name):
    # Timing-based features
    if (
        name.startswith("interarrival.")
        or name.startswith("time.")
        or name.startswith("per_sec.")
        or name.startswith("concentration20.")
        or name.startswith("alt_per_sec.")
        or name.startswith("alt_concentration20.")
        or name == "sum.alt_per_sec_20bins"
        or name == "sum.interarrival_stats"
        or name == "sum.time_percentiles"
        or name == "sum.alt_concentration20_70bins"
    ):
        return "timing"

    # Direction-based features, including packet counts
    if (
        name.startswith("count.")
        or name.startswith("direction_ratio.")
        or name.startswith("ordering.")
        or name == "sum.packet_counts"
    ):
        return "direction"

    return "direction"


def plot_top10(ax, data, title, xmax):
    ranked = sorted(data.items(), key=lambda x: x[1], reverse=True)

    labels = [humanize_feature(k) for k, _ in ranked]
    values = [v for _, v in ranked]
    cats = [feature_category(k) for k, _ in ranked]
    colors = [CATEGORY_COLORS[c] for c in cats]

    labels = labels[::-1]
    values = values[::-1]
    colors = colors[::-1]

    ax.barh(range(len(labels)), values, color=colors, height=0.56)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=16)
    ax.set_xlim(0, xmax)
    ax.set_title(title, fontsize=20, pad=6, weight="bold")

    # Remove x-axis increments completely
    ax.set_xticks([])
    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="y", length=0)

    # Value labels at bar ends
    for i, v in enumerate(values):
        ax.text(v + xmax * 0.010, i, f"{v:.3f}", va="center", fontsize=14, weight="bold")

    # Clean up spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)


def main():
    plt.rcParams.update({
        "font.size": 16,
        "axes.titlesize": 20,
        "axes.labelsize": 16,
        "xtick.labelsize": 14,
        "ytick.labelsize": 16,
    })

    xmax = max(max(our_top10.values()), max(their_top10.values())) * 1.24

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6))
    plot_top10(axes[0], our_top10, "NDN", xmax)
    plot_top10(axes[1], their_top10, "TCP/IP", xmax)

    fig.text(
        0.5,
        0.17,
        "Feature Importance (mean decrease in impurity)",
        ha="center",
        va="center",
        fontsize=16,
        weight="bold",
    )

    handles = [
        Patch(facecolor=CATEGORY_COLORS[c], label=CATEGORY_LABELS[c])
        for c in ["timing", "direction"]
    ]

    # Manual spacing so the bottom legend has room and won't get cut off
    plt.subplots_adjust(top=0.80, bottom=0.20, left=0.12, right=0.98, wspace=0.55)

    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.03),
        ncol=2,
        frameon=False,
        fontsize=15,
        handlelength=1.5,
        columnspacing=1.6,
    )

    plt.savefig("kfp_feature_importance.pdf", bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()