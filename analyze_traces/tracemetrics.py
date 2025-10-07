#!/usr/bin/env python3
import argparse
from pathlib import Path

# ----------------- tiny parsing helper -----------------
def collect_stats(path):
    """
    Parse the file once and return:
      counts:       {value -> count}
      first_idx:    {value -> first line index it appears on}
      last_pos_ts:  timestamp (float) of the last row where value > 0
      last_neg_ts:  timestamp (float) of the last row where value < 0
    """
    counts = {}
    first_idx = {}

    last_pos_ts = None
    last_neg_ts = None

    idx = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    ts = float(parts[0])          # column 1: timestamp (sorted ascending)
                    val = int(parts[1])           # column 2: integer event value
                except ValueError:
                    ts = None
                    val = None
            else:
                ts = None
                val = None

            if val is not None:
                counts[val] = counts.get(val, 0) + 1
                if val not in first_idx:
                    first_idx[val] = idx

                # update last timestamp by sign (ignore zeros)
                if ts is not None:
                    if val > 0:
                        last_pos_ts = ts
                    elif val < 0:
                        last_neg_ts = ts

            idx += 1

    return counts, first_idx, last_pos_ts, last_neg_ts

# ----------------- small metric funcs -----------------
def metric_minus2_before_2(counts, first_idx):
    a = first_idx.get(-2)
    b = first_idx.get(2)
    return (a is not None) and (b is None or a < b)

def metric_more_2_than_minus2(counts, first_idx):
    return counts.get(2, 0) > counts.get(-2, 0)

def metric_last_posneg_gap_gt(last_pos_ts, last_neg_ts, gap):
    # Both must exist; compare absolute time gap
    if last_pos_ts is None or last_neg_ts is None:
        return False
    return abs(last_pos_ts - last_neg_ts) > gap

# ----------------- CLI (mostly unchanged) -----------------
def main():
    ap = argparse.ArgumentParser(
        description="Analyze site_i_trace_j.txt files for event ordering and counts."
    )
    ap.add_argument("folder", type=Path, help="Folder containing site_*_trace_*.txt files")
    args = ap.parse_args()

    files = sorted(args.folder.glob("site_*_trace_*.txt"))
    total = len(files)
    if total == 0:
        print("No matching files found.")
        return

    c_minus2_before_2 = 0
    c_more_2_than_minus2 = 0
    c_last_posneg_gap_gt_30 = 0
    gap = 10

    for p in files:
        counts, first_idx, last_pos_ts, last_neg_ts = collect_stats(p)

        if metric_minus2_before_2(counts, first_idx):
            c_minus2_before_2 += 1
        if metric_more_2_than_minus2(counts, first_idx):
            c_more_2_than_minus2 += 1
        if metric_last_posneg_gap_gt(last_pos_ts, last_neg_ts, gap):
            c_last_posneg_gap_gt_30 += 1

        # Paste more metrics here as needed.

    pct1 = (c_minus2_before_2 / total) * 100.0
    pct2 = (c_more_2_than_minus2 / total) * 100.0
    pct3 = (c_last_posneg_gap_gt_30 / total) * 100.0

    print(f"Total files: {total}")
    print(f'Data without Interest: {c_minus2_before_2} ({pct1:.2f}%)')
    print(f'Unsatisfied Interest: {c_more_2_than_minus2} ({pct2:.2f}%)')
    print(f'Interest Timeout ({gap}s): {c_last_posneg_gap_gt_30} ({pct3:.2f}%)')

if __name__ == "__main__":
    main()
