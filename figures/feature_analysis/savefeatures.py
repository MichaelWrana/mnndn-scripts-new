import os
import json
import random
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from WFlib import models
from WFlib.tools import data_processor


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def parse_args():
    p = argparse.ArgumentParser(description="TikTok class-level dataset/model analysis")

    p.add_argument("--dataset", type=str, required=True)
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--test_file", type=str, default="test")
    p.add_argument("--feature", type=str, default="DIR")
    p.add_argument("--seq_len", type=int, default=5000)
    p.add_argument("--num_tabs", type=int, default=1)

    p.add_argument("--batch_size", type=int, default=256)
    p.add_argument("--num_workers", type=int, default=8)

    p.add_argument("--checkpoints", type=str, default="./checkpoints/")
    p.add_argument("--load_name", type=str, default="base")

    p.add_argument("--out_dir", type=str, default="./logs/tiktok_analysis")
    p.add_argument("--save_probs", action="store_true")
    p.add_argument("--save_embeddings", action="store_true")
    p.add_argument("--second_choice_correct_only", action="store_true")

    p.add_argument("--seed", type=int, default=2024)

    return p.parse_args()


def get_tiktok_embedding_and_logits(model, x):
    """
    TikTok-specific forward pass.

    model.feature_extraction:
        Conv blocks

    model.classifier:
        0 Flatten
        1 Linear -> 512
        2 BN
        3 ReLU
        4 Dropout
        5 Linear -> 512
        6 BN
        7 ReLU
        8 Dropout
        9 Linear -> num_classes

    The returned embedding is the 512-d vector immediately before
    the final classification layer.
    """
    z = model.feature_extraction(x)
    emb = model.classifier[:-1](z)
    logits = model.classifier[-1](emb)
    return emb, logits


def collect_outputs(model, data_iter, device, num_classes):
    model.eval()

    all_y = []
    all_logits = []
    all_probs = []
    all_embs = []

    with torch.no_grad():
        for cur_X, cur_y in data_iter:
            cur_X = cur_X.to(device)
            cur_y = cur_y.to(device)

            emb, logits = get_tiktok_embedding_and_logits(model, cur_X)
            probs = F.softmax(logits, dim=1)

            all_y.append(cur_y.cpu().numpy())
            all_logits.append(logits.cpu().numpy())
            all_probs.append(probs.cpu().numpy())
            all_embs.append(emb.cpu().numpy())

    y_true = np.concatenate(all_y).astype(int)
    logits = np.concatenate(all_logits)
    probs = np.concatenate(all_probs)
    embs = np.concatenate(all_embs)

    assert probs.shape[1] == num_classes
    assert embs.ndim == 2

    y_pred = probs.argmax(axis=1)

    return y_true, y_pred, logits, probs, embs


def entropy_np(probs, eps=1e-12):
    return -(probs * np.log(probs + eps)).sum(axis=1)


def make_per_sample_table(y_true, y_pred, probs):
    top2_idx = np.argsort(probs, axis=1)[:, -2:][:, ::-1]
    top1_cls = top2_idx[:, 0]
    top2_cls = top2_idx[:, 1]

    top1_prob = probs[np.arange(len(probs)), top1_cls]
    top2_prob = probs[np.arange(len(probs)), top2_cls]

    df = pd.DataFrame({
        "sample_idx": np.arange(len(y_true)),
        "true_class": y_true,
        "pred_class": y_pred,
        "correct": y_true == y_pred,
        "top1_class": top1_cls,
        "top1_prob": top1_prob,
        "top2_class": top2_cls,
        "top2_prob": top2_prob,
        "margin_top1_top2": top1_prob - top2_prob,
        "true_class_prob": probs[np.arange(len(probs)), y_true],
        "entropy": entropy_np(probs),
    })

    return df


def make_per_class_confidence_table(per_sample_df, num_classes):
    rows = []

    for c in range(num_classes):
        d = per_sample_df[per_sample_df["true_class"] == c]
        if len(d) == 0:
            rows.append({
                "class": c,
                "support": 0,
                "accuracy": np.nan,
                "mean_top1_prob": np.nan,
                "median_top1_prob": np.nan,
                "mean_true_class_prob": np.nan,
                "median_true_class_prob": np.nan,
                "mean_margin": np.nan,
                "median_margin": np.nan,
                "mean_entropy": np.nan,
                "median_entropy": np.nan,
            })
            continue

        rows.append({
            "class": c,
            "support": int(len(d)),
            "accuracy": float(d["correct"].mean()),
            "mean_top1_prob": float(d["top1_prob"].mean()),
            "median_top1_prob": float(d["top1_prob"].median()),
            "mean_true_class_prob": float(d["true_class_prob"].mean()),
            "median_true_class_prob": float(d["true_class_prob"].median()),
            "mean_margin": float(d["margin_top1_top2"].mean()),
            "median_margin": float(d["margin_top1_top2"].median()),
            "mean_entropy": float(d["entropy"].mean()),
            "median_entropy": float(d["entropy"].median()),
        })

    return pd.DataFrame(rows)


def make_soft_confusion(y_true, probs, num_classes):
    """
    soft_confusion[i, j] =
        average probability assigned to class j
        over samples whose true class is i.
    """
    soft_conf = np.zeros((num_classes, num_classes), dtype=np.float64)

    for c in range(num_classes):
        idx = np.where(y_true == c)[0]
        if len(idx) > 0:
            soft_conf[c] = probs[idx].mean(axis=0)

    soft_conf_df = pd.DataFrame(
        soft_conf,
        index=[f"true_{i}" for i in range(num_classes)],
        columns=[f"prob_{j}" for j in range(num_classes)]
    )

    return soft_conf, soft_conf_df


def make_soft_confusion_edges(soft_conf, top_k=5):
    """
    For each true class, list the largest off-diagonal soft-confusion classes.
    """
    rows = []
    num_classes = soft_conf.shape[0]

    for c in range(num_classes):
        row = soft_conf[c].copy()
        row[c] = -np.inf

        for rank, other in enumerate(np.argsort(row)[::-1][:top_k], start=1):
            rows.append({
                "true_class": c,
                "rank": rank,
                "soft_neighbor_class": int(other),
                "mean_probability": float(soft_conf[c, other]),
            })

    return pd.DataFrame(rows)


def make_second_choice_table(per_sample_df, num_classes, correct_only=False):
    rows = []

    if correct_only:
        base = per_sample_df[per_sample_df["correct"]]
    else:
        base = per_sample_df

    for c in range(num_classes):
        d = base[base["true_class"] == c]
        denom = len(d)

        if denom == 0:
            continue

        counts = d["top2_class"].value_counts()

        for rank, (second_cls, count) in enumerate(counts.items(), start=1):
            rows.append({
                "true_class": c,
                "rank": rank,
                "second_choice_class": int(second_cls),
                "count": int(count),
                "fraction": float(count / denom),
                "mean_second_prob": float(d[d["top2_class"] == second_cls]["top2_prob"].mean()),
                "correct_only": bool(correct_only),
            })

    return pd.DataFrame(rows)


def l2_normalize_np(x, eps=1e-12):
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + eps)


def pairwise_euclidean(a, b):
    """
    Squared expansion for pairwise Euclidean distance.
    """
    a2 = (a * a).sum(axis=1, keepdims=True)
    b2 = (b * b).sum(axis=1, keepdims=True).T
    d2 = np.maximum(a2 + b2 - 2 * a @ b.T, 0.0)
    return np.sqrt(d2)


def make_embedding_analysis(y_true, embs, num_classes):
    """
    Computes:
      - class centroids
      - within-class embedding spread
      - nearest centroid under Euclidean distance
      - nearest centroid under cosine distance
      - separability = nearest Euclidean centroid distance / mean within-class spread
    """
    dim = embs.shape[1]
    centroids = np.zeros((num_classes, dim), dtype=np.float64)

    spread_mean = np.full(num_classes, np.nan)
    spread_median = np.full(num_classes, np.nan)
    spread_p90 = np.full(num_classes, np.nan)
    support = np.zeros(num_classes, dtype=int)

    for c in range(num_classes):
        idx = np.where(y_true == c)[0]
        support[c] = len(idx)

        if len(idx) == 0:
            continue

        class_embs = embs[idx]
        centroid = class_embs.mean(axis=0)
        centroids[c] = centroid

        dists = np.linalg.norm(class_embs - centroid[None, :], axis=1)
        spread_mean[c] = dists.mean()
        spread_median[c] = np.median(dists)
        spread_p90[c] = np.percentile(dists, 90)

    euclidean_centroid_dist = pairwise_euclidean(centroids, centroids)

    norm_centroids = l2_normalize_np(centroids)
    cosine_sim = norm_centroids @ norm_centroids.T
    cosine_dist = 1.0 - cosine_sim

    np.fill_diagonal(euclidean_centroid_dist, np.inf)
    np.fill_diagonal(cosine_dist, np.inf)

    nearest_euc = np.argmin(euclidean_centroid_dist, axis=1)
    nearest_cos = np.argmin(cosine_dist, axis=1)

    rows = []
    for c in range(num_classes):
        nearest_euc_dist = float(euclidean_centroid_dist[c, nearest_euc[c]])
        nearest_cos_dist = float(cosine_dist[c, nearest_cos[c]])

        sep = nearest_euc_dist / spread_mean[c] if spread_mean[c] > 0 else np.nan

        rows.append({
            "class": c,
            "support": int(support[c]),
            "embedding_spread_mean": float(spread_mean[c]),
            "embedding_spread_median": float(spread_median[c]),
            "embedding_spread_p90": float(spread_p90[c]),
            "nearest_euclidean_class": int(nearest_euc[c]),
            "nearest_euclidean_distance": nearest_euc_dist,
            "nearest_cosine_class": int(nearest_cos[c]),
            "nearest_cosine_distance": nearest_cos_dist,
            "separability_euclidean": float(sep),
        })

    summary_df = pd.DataFrame(rows)

    return {
        "embeddings": embs,
        "centroids": centroids,
        "euclidean_centroid_dist": euclidean_centroid_dist,
        "cosine_centroid_dist": cosine_dist,
        "summary_df": summary_df,
    }


def make_centroid_pair_table(euclidean_dist, cosine_dist, top_k=100):
    rows = []
    num_classes = euclidean_dist.shape[0]

    for i in range(num_classes):
        for j in range(i + 1, num_classes):
            rows.append({
                "class_a": i,
                "class_b": j,
                "euclidean_centroid_distance": float(euclidean_dist[i, j]),
                "cosine_centroid_distance": float(cosine_dist[i, j]),
            })

    df = pd.DataFrame(rows)
    df = df.sort_values("euclidean_centroid_distance", ascending=True)
    return df.head(top_k)


def main():
    args = parse_args()
    set_seed(args.seed)

    if args.num_tabs != 1:
        raise ValueError("This script is written for the 100-class single-tab multiclass case.")

    if args.device.startswith("cuda"):
        assert torch.cuda.is_available(), f"Device {args.device} requested but CUDA is unavailable."

    device = torch.device(args.device)

    in_path = os.path.join("../datasets", args.dataset)
    ckp_path = os.path.join(args.checkpoints, args.dataset, "TikTok")
    ckpt_file = os.path.join(ckp_path, f"{args.load_name}.pth")

    if not os.path.exists(in_path):
        raise FileNotFoundError(f"Dataset path does not exist: {in_path}")
    if not os.path.exists(ckpt_file):
        raise FileNotFoundError(f"Checkpoint does not exist: {ckpt_file}")

    os.makedirs(args.out_dir, exist_ok=True)

    test_path = os.path.join(in_path, f"{args.test_file}.npz")
    print(f"[INFO] Loading test data: {test_path}")

    test_X, test_y = data_processor.load_data(
        test_path,
        args.feature,
        args.seq_len,
        args.num_tabs
    )

    num_classes = len(np.unique(test_y.numpy()))
    assert num_classes == test_y.max().item() + 1, "Labels are not continuous."
    print(f"[INFO] Test X={tuple(test_X.shape)}, y={tuple(test_y.shape)}")
    print(f"[INFO] num_classes={num_classes}")

    test_iter = data_processor.load_iter(
        test_X,
        test_y,
        args.batch_size,
        False,
        args.num_workers
    )

    model = models.TikTok(num_classes)
    model.load_state_dict(torch.load(ckpt_file, map_location="cpu"))
    model.to(device)
    model.eval()

    print("[INFO] Running TikTok and collecting logits, probabilities, and embeddings...")
    y_true, y_pred, logits, probs, embs = collect_outputs(
        model,
        test_iter,
        device,
        num_classes
    )

    acc = float((y_true == y_pred).mean())
    print(f"[INFO] Top-1 accuracy = {acc:.4f}")
    print(f"[INFO] embedding shape = {embs.shape}")

    # 1. Per-class confidence and margin
    per_sample_df = make_per_sample_table(y_true, y_pred, probs)
    per_class_df = make_per_class_confidence_table(per_sample_df, num_classes)

    per_sample_df.to_csv(os.path.join(args.out_dir, "per_sample_predictions.csv"), index=False)
    per_class_df.to_csv(os.path.join(args.out_dir, "per_class_confidence_margin.csv"), index=False)

    # 2. Soft confusion and second-choice class analysis
    soft_conf, soft_conf_df = make_soft_confusion(y_true, probs, num_classes)
    soft_edges_df = make_soft_confusion_edges(soft_conf, top_k=5)

    second_choice_df = make_second_choice_table(
        per_sample_df,
        num_classes,
        correct_only=args.second_choice_correct_only
    )

    soft_conf_df.to_csv(os.path.join(args.out_dir, "soft_confusion_matrix.csv"))
    soft_edges_df.to_csv(os.path.join(args.out_dir, "soft_confusion_top_neighbors.csv"), index=False)
    second_choice_df.to_csv(os.path.join(args.out_dir, "second_choice_summary.csv"), index=False)

    # 3. Penultimate-layer embedding analysis
    emb_info = make_embedding_analysis(y_true, embs, num_classes)
    emb_summary_df = emb_info["summary_df"]
    centroid_pairs_df = make_centroid_pair_table(
        emb_info["euclidean_centroid_dist"],
        emb_info["cosine_centroid_dist"],
        top_k=100
    )

    emb_summary_df.to_csv(os.path.join(args.out_dir, "embedding_class_summary.csv"), index=False)
    centroid_pairs_df.to_csv(os.path.join(args.out_dir, "nearest_centroid_pairs.csv"), index=False)

    # Compact JSON summary
    summary = {
        "dataset": args.dataset,
        "model": "TikTok",
        "test_file": args.test_file,
        "feature": args.feature,
        "seq_len": args.seq_len,
        "num_classes": int(num_classes),
        "num_samples": int(len(y_true)),
        "accuracy": acc,
        "mean_margin": float(per_sample_df["margin_top1_top2"].mean()),
        "median_margin": float(per_sample_df["margin_top1_top2"].median()),
        "mean_entropy": float(per_sample_df["entropy"].mean()),
        "median_entropy": float(per_sample_df["entropy"].median()),
        "embedding_dim": int(embs.shape[1]),
    }

    with open(os.path.join(args.out_dir, "summary.json"), "w") as fp:
        json.dump(summary, fp, indent=4)

    # Optional large arrays
    arrays = {
        "y_true": y_true,
        "y_pred": y_pred,
        "logits": logits,
        "soft_confusion": soft_conf,
        "centroids": emb_info["centroids"],
        "euclidean_centroid_dist": emb_info["euclidean_centroid_dist"],
        "cosine_centroid_dist": emb_info["cosine_centroid_dist"],
    }

    if args.save_probs:
        arrays["probs"] = probs

    if args.save_embeddings:
        arrays["embeddings"] = embs

    np.savez_compressed(os.path.join(args.out_dir, "analysis_arrays.npz"), **arrays)

    print(f"[INFO] Wrote analysis outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()