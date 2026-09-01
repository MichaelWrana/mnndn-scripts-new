# save_cka.py

import os
import argparse
import random
import json
import numpy as np
import torch
import torch.nn as nn

from WFlib import models
from WFlib.tools import data_processor


def parse_args():
    p = argparse.ArgumentParser(description="Save layerwise CKA matrix for WFlib models")

    p.add_argument("--dataset_a", required=True)
    p.add_argument("--dataset_b", required=True)
    p.add_argument("--models", nargs="+", default=["DF", "TikTok"])

    p.add_argument("--checkpoints", default="../checkpoints/")
    p.add_argument("--load_name", default="base")
    p.add_argument("--same_checkpoint", action="store_true")

    p.add_argument("--split", default="test")
    p.add_argument("--feature", default="DIR")
    p.add_argument("--seq_len", type=int, default=5000)
    p.add_argument("--num_tabs", type=int, default=1)

    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--num_workers", type=int, default=4)
    p.add_argument("--max_samples", type=int, default=512)

    p.add_argument("--device", default="cuda:0")
    p.add_argument("--pool", choices=["avg", "flatten"], default="avg")
    p.add_argument("--out_dir", default="./cka_results")

    return p.parse_args()


def fix_seed(seed=2024):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_npz_dataset(dataset, split, feature, seq_len, num_tabs):
    path = os.path.join("../datasets", dataset, f"{split}.npz")
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    X, y = data_processor.load_data(path, feature, seq_len, num_tabs)

    if num_tabs == 1:
        num_classes = len(np.unique(y))
        assert num_classes == y.max() + 1, "Labels are not continuous"
    else:
        num_classes = y.shape[1]

    return X, y, num_classes


def make_loader(X, y, batch_size, num_workers):
    return data_processor.load_iter(X, y, batch_size, False, num_workers)


def load_model(model_name, dataset_for_checkpoint, num_classes, args):
    if model_name in ["BAPM", "TMWF"]:
        model = getattr(models, model_name)(num_classes, args.num_tabs)
    else:
        model = getattr(models, model_name)(num_classes)

    ckpt_path = os.path.join(
        args.checkpoints,
        dataset_for_checkpoint,
        model_name,
        f"{args.load_name}.pth",
    )

    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(ckpt_path)

    state = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(state)
    model.to(args.device)
    model.eval()

    return model


def is_hookable_layer(module):
    return isinstance(
        module,
        (
            nn.Conv1d,
            nn.Conv2d,
            nn.Linear,
            nn.BatchNorm1d,
            nn.BatchNorm2d,
        ),
    )


def activation_to_matrix(x, pool="avg"):
    x = x.detach()

    if x.ndim == 2:
        return x

    if pool == "avg":
        dims = tuple(range(2, x.ndim))
        return x.mean(dim=dims)

    return x.flatten(start_dim=1)


def collect_activations(model, loader, device, max_samples, pool):
    activations = {}
    handles = []

    def make_hook(name):
        def hook(module, inp, out):
            if isinstance(out, tuple):
                out = out[0]

            mat = activation_to_matrix(out, pool=pool)
            mat = mat.detach().float().cpu()

            if name not in activations:
                activations[name] = []
            activations[name].append(mat)

        return hook

    for name, module in model.named_modules():
        if is_hookable_layer(module):
            handles.append(module.register_forward_hook(make_hook(name)))

    seen = 0

    with torch.no_grad():
        for batch in loader:
            x = batch[0] if isinstance(batch, (list, tuple)) else batch

            remaining = max_samples - seen
            if remaining <= 0:
                break

            x = x[:remaining].to(device)
            model(x)

            seen += x.shape[0]

    for h in handles:
        h.remove()

    out = {}
    for name, parts in activations.items():
        out[name] = torch.cat(parts, dim=0)[:max_samples]

    return out


def center_gram(K):
    n = K.shape[0]
    unit = torch.ones((n, n), dtype=K.dtype, device=K.device) / n
    return K - unit @ K - K @ unit + unit @ K @ unit


def linear_cka(X, Y, eps=1e-12):
    X = X.float()
    Y = Y.float()

    K = X @ X.T
    L = Y @ Y.T

    Kc = center_gram(K)
    Lc = center_gram(L)

    hsic = (Kc * Lc).sum()
    norm_x = torch.sqrt((Kc * Kc).sum())
    norm_y = torch.sqrt((Lc * Lc).sum())

    return (hsic / (norm_x * norm_y + eps)).item()


def compute_cka_matrix(acts_a, acts_b):
    names_a = list(acts_a.keys())
    names_b = list(acts_b.keys())

    C = np.zeros((len(names_a), len(names_b)), dtype=np.float32)

    for i, name_a in enumerate(names_a):
        for j, name_b in enumerate(names_b):
            C[i, j] = linear_cka(acts_a[name_a], acts_b[name_b])

    return C, names_a, names_b


def save_cka_file(C, names_a, names_b, metadata, out_path):
    np.savez_compressed(
        out_path,
        cka=C,
        layer_names_a=np.array(names_a, dtype=object),
        layer_names_b=np.array(names_b, dtype=object),
        metadata=json.dumps(metadata),
    )


def main():
    args = parse_args()
    fix_seed()

    if args.device.startswith("cuda"):
        assert torch.cuda.is_available(), f"{args.device} requested but CUDA is unavailable"

    os.makedirs(args.out_dir, exist_ok=True)

    X_a, y_a, classes_a = load_npz_dataset(
        args.dataset_a, args.split, args.feature, args.seq_len, args.num_tabs
    )
    X_b, y_b, classes_b = load_npz_dataset(
        args.dataset_b, args.split, args.feature, args.seq_len, args.num_tabs
    )

    loader_a = make_loader(X_a, y_a, args.batch_size, args.num_workers)
    loader_b = make_loader(X_b, y_b, args.batch_size, args.num_workers)

    for model_name in args.models:
        ckpt_dataset_a = args.dataset_a
        ckpt_dataset_b = args.dataset_a if args.same_checkpoint else args.dataset_b

        print(f"[INFO] Model: {model_name}")
        print(f"[INFO] Checkpoint A: {ckpt_dataset_a}")
        print(f"[INFO] Checkpoint B: {ckpt_dataset_b}")

        model_a = load_model(model_name, ckpt_dataset_a, classes_a, args)
        model_b = load_model(model_name, ckpt_dataset_b, classes_b, args)

        print(f"[INFO] Collecting activations for {args.dataset_a}")
        acts_a = collect_activations(model_a, loader_a, args.device, args.max_samples, args.pool)

        print(f"[INFO] Collecting activations for {args.dataset_b}")
        acts_b = collect_activations(model_b, loader_b, args.device, args.max_samples, args.pool)

        print("[INFO] Computing CKA matrix")
        C, names_a, names_b = compute_cka_matrix(acts_a, acts_b)

        mode = "same_ckpt" if args.same_checkpoint else "separate_ckpts"
        out_name = f"{model_name}_{args.dataset_a}_vs_{args.dataset_b}_{mode}_{args.pool}.npz"
        out_path = os.path.join(args.out_dir, out_name)

        metadata = {
            "model": model_name,
            "dataset_a": args.dataset_a,
            "dataset_b": args.dataset_b,
            "checkpoint_dataset_a": ckpt_dataset_a,
            "checkpoint_dataset_b": ckpt_dataset_b,
            "same_checkpoint": args.same_checkpoint,
            "split": args.split,
            "feature": args.feature,
            "seq_len": args.seq_len,
            "num_tabs": args.num_tabs,
            "max_samples": args.max_samples,
            "pool": args.pool,
            "classes_a": int(classes_a),
            "classes_b": int(classes_b),
        }

        save_cka_file(C, names_a, names_b, metadata, out_path)
        print(f"[DONE] Saved CKA file: {out_path}")


if __name__ == "__main__":
    main()
