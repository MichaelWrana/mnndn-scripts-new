# plot_cka.py

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42

# =========================
# Large font settings
# =========================
BASE_FONT_SIZE = 18
TITLE_FONT_SIZE = 60
AXIS_LABEL_FONT_SIZE = 48
TICK_FONT_SIZE = 24
COLORBAR_LABEL_FONT_SIZE = 36
COLORBAR_TICK_FONT_SIZE = 24
STATS_FONT_SIZE = 32


def parse_args():
    p = argparse.ArgumentParser(description="Plot saved CKA matrix")

    p.add_argument("--cka_file", required=True, help="Path to .npz file from save_cka.py")
    p.add_argument("--out_file", default=None, help="Output figure path")
    p.add_argument("--figsize", nargs=2, type=float, default=None)
    p.add_argument("--dpi", type=int, default=300)

    p.add_argument("--show_layer_names", action="store_true")
    p.add_argument("--title", default=None)

    return p.parse_args()


def load_cka(path):
    data = np.load(path, allow_pickle=True)

    C = data["cka"]
    names_a = data["layer_names_a"].tolist()
    names_b = data["layer_names_b"].tolist()

    metadata = {}
    if "metadata" in data:
        metadata = json.loads(str(data["metadata"]))

    return C, names_a, names_b, metadata


def default_title(metadata):
    model = metadata.get("model", "model")
    dataset_a = metadata.get("dataset_a", "dataset A")
    dataset_b = metadata.get("dataset_b", "dataset B")
    mode = "same checkpoint" if metadata.get("same_checkpoint") else "separate checkpoints"
    pool = metadata.get("pool", "unknown pool")
    samples = metadata.get("max_samples", "unknown")

    return f"{model} CKA: {dataset_a} vs {dataset_b}\n{mode}, pool={pool}, samples={samples}"


def summarize_cka(C):
    diag_len = min(C.shape[0], C.shape[1])
    diag = np.array([C[i, i] for i in range(diag_len)])

    return {
        "mean": float(np.mean(diag)),
        "median": float(np.median(diag)),
        "max": float(np.max(diag)),
    }


def plot_cka(C, names_a, names_b, metadata, args):
    stats = summarize_cka(C)

    plt.rcParams.update({"font.size": BASE_FONT_SIZE})

    if args.figsize is None:
        fig_w = max(10, 0.45 * len(names_b))
        fig_h = max(8, 0.45 * len(names_a))
        figsize = (fig_w, fig_h)
    else:
        figsize = tuple(args.figsize)

    fig, ax = plt.subplots(figsize=figsize)

    im = ax.imshow(C, vmin=0, vmax=0.7, aspect="auto")

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    #cbar.set_label("Linear CKA", fontsize=COLORBAR_LABEL_FONT_SIZE)
    cbar.ax.tick_params(labelsize=COLORBAR_TICK_FONT_SIZE)
    cbar.ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
 
    if args.show_layer_names:
        ax.set_xticks(range(len(names_b)))
        ax.set_yticks(range(len(names_a)))
        ax.set_xticklabels(names_b, rotation=90, fontsize=TICK_FONT_SIZE)
        ax.set_yticklabels(names_a, fontsize=TICK_FONT_SIZE)
    else:
        ax.set_xticks([])
        ax.set_yticks([])

    ax.set_xlabel("TCP/IP (Sample 1)", fontsize=AXIS_LABEL_FONT_SIZE)
    ax.set_ylabel("TCP/IP (Sample 2)", fontsize=AXIS_LABEL_FONT_SIZE)

    title = args.title if args.title is not None else default_title(metadata)
    ax.set_title(title, fontsize=TITLE_FONT_SIZE, pad=16)

    stats_text = (
        f"Mean: {stats['mean']:.3f}    "
        f"Median: {stats['median']:.3f}    "
        f"Max: {stats['max']:.3f}"
    )

    fig.text(
        0.5, 0.02, stats_text,
        ha="center", va="bottom", fontsize=STATS_FONT_SIZE)

    plt.tight_layout(rect=[0, 0.07, 1, 1])
    plt.savefig(args.out_file, format="pdf", bbox_inches="tight")
    plt.close()


def main():
    args = parse_args()

    if args.out_file is None:
        args.out_file = args.cka_file.replace(".npz", ".pdf")

    C, names_a, names_b, metadata = load_cka(args.cka_file)

    print("[INFO] Loaded CKA file")
    print(f"[INFO] Matrix shape: {C.shape}")

    stats = summarize_cka(C)
    print("[INFO] Diagonal summary:")
    print(f"  Mean:   {stats['mean']:.6f}")
    print(f"  Median: {stats['median']:.6f}")
    print(f"  Max:    {stats['max']:.6f}")

    if metadata:
        print("[INFO] Metadata:")
        for k, v in metadata.items():
            print(f"  {k}: {v}")

    plot_cka(C, names_a, names_b, metadata, args)

    print(f"[DONE] Saved figure: {args.out_file}")


if __name__ == "__main__":
    main()