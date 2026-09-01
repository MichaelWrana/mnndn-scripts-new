#!/usr/bin/env python3

import os
import argparse
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate two TikTok analysis figures with highlighted learned clusters and reference domain pairs."
    )
    p.add_argument("--in_dir", type=str, required=True, help="Directory containing analysis CSV files")
    p.add_argument("--out_dir", type=str, required=True, help="Directory to save PDF figures")
    p.add_argument("--top_soft_edges", type=int, default=20, help="Base number of top soft-confusion edges")
    return p.parse_args()


def zscore(s):
    std = s.std()
    if std == 0 or np.isnan(std):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.mean()) / std


# ---------------------------------------------------------------------
# Model-derived learned ambiguity groups (filled markers)
# ---------------------------------------------------------------------
CLUSTERS = [
    {"name": "22–23 pair", "classes": {22, 23}, "color": "#E45756"},
    {"name": "84–94 pair", "classes": {84, 94}, "color": "#4C78A8"},
    {"name": "18–27–28–41 cluster", "classes": {18, 27, 28, 41}, "color": "#8C564B"},
]
# ---------------------------------------------------------------------
# Real-world similar domain pairs (outlined markers)
# ---------------------------------------------------------------------
REFERENCE_PAIRS = [
    {
        "name": "WordPress pair",
        "classes": [20, 48],
        "domains": ["wordpress.org", "wordpress.com"],
        "color": "#9467bd",
        "marker": "s",
    },
    {
        "name": "GitHub pair",
        "classes": [14, 61],
        "domains": ["github.com", "github.io"],
        "color": "#ff7f0e",
        "marker": "D",
    },
    {
        "name": "Adobe pair",
        "classes": [32, 86],
        "domains": ["adobe.com", "adobe.io"],
        "color": "#2ca02c",
        "marker": "^",
    },
]


CLUSTER_CLASS_TO_NAME = {}
CLUSTER_NAME_TO_COLOR = {}
for c in CLUSTERS:
    CLUSTER_NAME_TO_COLOR[c["name"]] = c["color"]
    for cls in c["classes"]:
        CLUSTER_CLASS_TO_NAME[cls] = c["name"]


def get_cluster_name(c):
    return CLUSTER_CLASS_TO_NAME.get(int(c), None)


def set_large_style():
    plt.rcParams.update({
        "font.size": 32,
        "axes.titlesize": 40,
        "axes.labelsize": 40,
        "xtick.labelsize": 20,
        "ytick.labelsize": 20,
        "legend.fontsize": 23,
    })


def load_and_merge(in_dir):
    per_class = pd.read_csv(os.path.join(in_dir, "per_class_confidence_margin.csv"))
    embedding = pd.read_csv(os.path.join(in_dir, "embedding_class_summary.csv"))
    soft_neighbors = pd.read_csv(os.path.join(in_dir, "soft_confusion_top_neighbors.csv"))

    df = per_class.merge(
        embedding,
        on=["class", "support"],
        how="inner"
    )

    df["neg_log_margin"] = -np.log10(df["mean_margin"].clip(lower=1e-12))
    df["neg_log_separability"] = -np.log10(df["separability_euclidean"].clip(lower=1e-12))

    df["mean_entropy_z"] = zscore(df["mean_entropy"])
    df["neg_log_margin_z"] = zscore(df["neg_log_margin"])
    df["embedding_spread_mean_z"] = zscore(df["embedding_spread_mean"])
    df["neg_log_separability_z"] = zscore(df["neg_log_separability"])

    df["ambiguity_score"] = (
        df["mean_entropy_z"]
        + df["neg_log_margin_z"]
        + df["embedding_spread_mean_z"]
        + df["neg_log_separability_z"]
    )

    df["cluster_name"] = df["class"].map(get_cluster_name)

    soft_neighbors["true_cluster"] = soft_neighbors["true_class"].map(get_cluster_name)
    soft_neighbors["neighbor_cluster"] = soft_neighbors["soft_neighbor_class"].map(get_cluster_name)

    def edge_cluster(row):
        if pd.notna(row["true_cluster"]) and row["true_cluster"] == row["neighbor_cluster"]:
            return row["true_cluster"]
        return None

    soft_neighbors["edge_cluster"] = soft_neighbors.apply(edge_cluster, axis=1)

    return df, soft_neighbors


def plot_embedding_geometry(df, out_file):
    set_large_style()

    fig, ax = plt.subplots(figsize=(10.0, 10.0))

    cluster_classes = set()
    for c in CLUSTERS:
        cluster_classes |= set(c["classes"])

    reference_classes = set()
    for p in REFERENCE_PAIRS:
        reference_classes |= set(p["classes"])

    highlight_classes = cluster_classes | reference_classes

    background = df[~df["class"].isin(highlight_classes)]
    ax.scatter(
        background["embedding_spread_mean"],
        background["nearest_euclidean_distance"],
        s=120,
        color="#d0d0d0",
        alpha=0.75,
        edgecolors="none",
        zorder=1
    )

    legend_handles = [
        Line2D([0], [0], marker='o', color='w', label='Other classes',
               markerfacecolor="#d0d0d0", markersize=12)
    ]

    # Learned clusters as filled circles
    for cluster in CLUSTERS:
        sub = df[df["class"].isin(cluster["classes"])]
        if len(sub) == 0:
            continue

        ax.scatter(
            sub["embedding_spread_mean"],
            sub["nearest_euclidean_distance"],
            s=280,
            color=cluster["color"],
            alpha=0.95,
            edgecolors="black",
            linewidths=1.4,
            zorder=3
        )

        legend_handles.append(
            Line2D([0], [0], marker='o', color='w', label=cluster["name"],
                   markerfacecolor=cluster["color"], markeredgecolor="black", markersize=14)
        )

    # Real-world similar domain pairs as outlined markers + dashed connectors
    for pair in REFERENCE_PAIRS:
        sub = df[df["class"].isin(pair["classes"])].copy()
        if len(sub) != 2:
            continue

        sub = sub.set_index("class").loc[pair["classes"]].reset_index()

        x = sub["embedding_spread_mean"].values
        y = sub["nearest_euclidean_distance"].values

        ax.plot(
            x, y,
            linestyle="--",
            linewidth=2.5,
            color=pair["color"],
            alpha=0.95,
            zorder=2
        )

        ax.scatter(
            x, y,
            s=300,
            facecolors="white",
            edgecolors=pair["color"],
            marker=pair["marker"],
            linewidths=2.6,
            zorder=4
        )

        legend_handles.append(
            Line2D([0], [0], marker=pair["marker"], color=pair["color"], label=pair["name"],
                   markerfacecolor="white", markeredgecolor=pair["color"], markersize=13,
                   linestyle="--", linewidth=2.5)
        )

    ax.set_xlabel("Within-class Spread")
    ax.set_ylabel("Nearest-neighbor Distance")
    ax.set_title("TikTok Embedding Geometry")

    ax.grid(True, linewidth=0.6, alpha=0.35)
    ax.legend(handles=legend_handles, loc="best", frameon=True)

    fig.tight_layout()
    fig.savefig(out_file, bbox_inches="tight")
    plt.close(fig)


def plot_top_soft_confusion_edges(soft_neighbors, out_file, top_k):
    set_large_style()

    top_soft = soft_neighbors.sort_values("mean_probability", ascending=False).head(top_k).copy()
    cluster_edges = soft_neighbors[soft_neighbors["edge_cluster"].notna()].copy()

    top_soft = pd.concat([top_soft, cluster_edges], ignore_index=True)
    top_soft = top_soft.drop_duplicates(subset=["true_class", "soft_neighbor_class"])
    top_soft = top_soft.sort_values("mean_probability", ascending=False)

    def edge_color(row):
        if pd.notna(row["edge_cluster"]):
            return CLUSTER_NAME_TO_COLOR[row["edge_cluster"]]
        return "#d0d0d0"

    top_soft["color"] = top_soft.apply(edge_color, axis=1)
    top_soft["edge"] = top_soft.apply(
        lambda r: f"{int(r['true_class'])}→{int(r['soft_neighbor_class'])}",
        axis=1
    )

    highlighted = top_soft[top_soft["edge_cluster"].notna()]
    non_highlighted = top_soft[top_soft["edge_cluster"].isna()].head(top_k)
    plot_df = pd.concat([highlighted, non_highlighted], ignore_index=True)
    plot_df = plot_df.drop_duplicates(subset=["true_class", "soft_neighbor_class"])
    plot_df = plot_df.sort_values("mean_probability", ascending=True)

    plot_df = plot_df[plot_df["mean_probability"] > 0.001]

    fig, ax = plt.subplots(figsize=(10.0, 10.0))

    print(plot_df["mean_probability"])

    ax.barh(
        plot_df["edge"],
        plot_df["mean_probability"],
        color=plot_df["color"],
        edgecolor="none",
    )

    ax.set_xlabel("Mean Soft-confusion")
    ax.set_ylabel("Class Pair")
    ax.set_title("TikTok Soft Confusion")
    ax.spines[['top', 'right']].set_visible(False)

    ax.grid(True, axis="x", linewidth=0.6, alpha=0.35)

    legend_handles = [
        Line2D([0], [0], color="#d0d0d0", lw=10, label="Other edges")
    ]
    for cluster in CLUSTERS:
        legend_handles.append(
            Line2D([0], [0], color=cluster["color"], lw=10, label=cluster["name"])
        )

    ax.legend(handles=legend_handles, loc="lower right", frameon=True)

    fig.tight_layout()
    fig.savefig(out_file, bbox_inches="tight")
    plt.close(fig)


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    df, soft_neighbors = load_and_merge(args.in_dir)

    plot_embedding_geometry(
        df,
        os.path.join(args.out_dir, "embedding_spread_vs_neighbor_distance.pdf"),
    )

    plot_top_soft_confusion_edges(
        soft_neighbors,
        os.path.join(args.out_dir, "top_soft_confusion_edges.pdf"),
        args.top_soft_edges,
    )

    print(f"[INFO] Wrote figures to {args.out_dir}")
    print("  - embedding_spread_vs_neighbor_distance.pdf")
    print("  - top_soft_confusion_edges.pdf")


if __name__ == "__main__":
    main()