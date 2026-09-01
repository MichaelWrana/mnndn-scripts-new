import numpy as np
import argparse
from pathlib import Path

from util.load import load_and_merge_txt, load_and_merge_ow
from util.process import reformat_wflib, reformat_cm, reformat_rf, reformat_wflib_multi

def parse_args():
    p = argparse.ArgumentParser(
        description="Run one or more reformat steps based on flags.",
    )
    p.add_argument("--tracescw", type=Path, help="Path to closed-world traces folder (required).")
    p.add_argument("--tracesow", type=Path, default=None, help="Path to open-world traces folder (default=None).")
    p.add_argument("--outdir", type=Path, default=Path("formatted_traces") , help="Path to traces output (default='formatted_traces')")

    p.add_argument("--sites", type=int, default=100, help="Number of sites in dataset (default=100).")
    p.add_argument("--exp", type=int, default=100, help="Number of experiments per website in dataset (default=100).")
    p.add_argument("--numopen", type=int, default=10000, help="Number of traces in open-world data (default=10,000).  Only required when --tracesow is set. ")

    p.add_argument("--numtabs", type=int, default=1, help="Number of tabs in each trace. Specify number of tabs as positive integer (default=1)")
    p.add_argument("--nummulti", type=int, default=50000, help="Number of multi-tab traces to generate if --numtabs > 1 (default=50,000)")

    args = p.parse_args()

    return args

args = parse_args()

out_dir = args.outdir
cw_dir = args.tracescw
num_monitored_sites = args.sites
num_unmonitored_sites = args.numopen
num_experiments = args.exp

print("[INFO] Loading 1-Tab closed-world traces from txt...")
cw_traces = load_and_merge_txt(cw_dir, num_monitored_sites, num_experiments)

if args.tracesow:
    ow_dir = args.tracesow
    print("[INFO] Loading 1-tab open-world traces from txt...")
    ow_traces = load_and_merge_ow(ow_dir, num_unmonitored_sites, cw_traces)

    if args.numtabs > 1:
        print(f"[INFO] Generating {args.nummulti} {args.numtabs}-tab traces...")
        X, y = reformat_wflib_multi(
            ow_traces,
            num_tabs=args.numtabs,
            num_traces=args.nummulti,
        )

        print("[INFO] Saving for WFLib...")
        out_file_path = out_dir / f"{ow_dir.name}_{args.numtabs}tab_wflib"
        np.savez_compressed(out_file_path, X=X, y=y)

        print("[INFO] Saving for CountMamba...")
        sign = np.where(X >= 0, 1.0, -1.0)
        X_cm = np.stack((np.abs(X), sign), axis=-1)
        out_file_path = out_dir / f"{ow_dir.name}_{args.numtabs}tab_cm"
        np.savez_compressed(out_file_path, X=X_cm, y=y)

    else:
        print("[INFO] Processing and saving for WFLib...")
        X, y = reformat_wflib(ow_traces)
        out_file_path = out_dir / f"{ow_dir.name}_wflib"
        np.savez(out_file_path, X=X, y=y)

        print("[INFO] Processing and saving for CountMamba...")
        X, y = reformat_cm(ow_traces)
        out_file_path = out_dir / f"{ow_dir.name}_cm"
        np.savez_compressed(out_file_path, X=X, y=y)

        print("[INFO] Processing traces and saving for RF...")
        out_dir_path = out_dir / f"{ow_dir.name}_rf"
        reformat_rf(ow_traces, out_dir_path)

else:

    if args.numtabs > 1:
        print(f"[INFO] Generating {args.nummulti} {args.numtabs}-tab traces...")
        X, y = reformat_wflib_multi(
            cw_traces,
            num_tabs=args.numtabs,
            num_traces=args.nummulti,
        )

        print("[INFO] Saving for WFLib...")
        out_file_path = out_dir / f"{cw_dir.name}_{args.numtabs}tab_wflib"
        np.savez_compressed(out_file_path, X=X, y=y)

        print("[INFO] Saving for CountMamba...")
        sign = np.where(X >= 0, 1.0, -1.0)
        X_cm = np.stack((np.abs(X), sign), axis=-1)
        out_file_path = out_dir / f"{cw_dir.name}_{args.numtabs}tab_cm"
        np.savez_compressed(out_file_path, X=X_cm, y=y)

    else:
        print("[INFO] Processing and saving for WFLib...")
        X, y = reformat_wflib(cw_traces)
        out_file_path = out_dir / f"{cw_dir.name}_wflib"
        np.savez(out_file_path, X=X, y=y)

        #print("[INFO] Processing and saving for CountMamba...")
        #X, y = reformat_cm(cw_traces)
        #out_file_path = out_dir / f"{cw_dir.name}_cm"
        #np.savez_compressed(out_file_path, X=X, y=y)

        #print("[INFO] Processing traces and saving for RF...")
        #out_dir_path = out_dir / f"{cw_dir.name}_rf"
        #reformat_rf(cw_traces, out_dir_path)