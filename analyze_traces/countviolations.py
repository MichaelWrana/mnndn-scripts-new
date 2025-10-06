#!/usr/bin/env python3
import argparse
from pathlib import Path

def analyze_file(path: Path):
    """
    Returns:
      (minus2_before_2: bool, more_2_than_minus2: bool)
    """
    first_idx_minus2 = None
    first_idx_2 = None
    count_minus2 = 0
    count_2 = 0

    idx = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2:
                idx += 1
                continue
            try:
                val = int(parts[1])
            except ValueError:
                idx += 1
                continue

            if val == -2:
                count_minus2 += 1
                if first_idx_minus2 is None:
                    first_idx_minus2 = idx
            elif val == 2:
                count_2 += 1
                if first_idx_2 is None:
                    first_idx_2 = idx

            idx += 1

    minus2_before_2 = (
        first_idx_minus2 is not None and
        (first_idx_2 is None or first_idx_minus2 < first_idx_2)
    )
    more_2_than_minus2 = (count_2 > count_minus2)
    return minus2_before_2, more_2_than_minus2


def main():
    ap = argparse.ArgumentParser(
        description="Analyze site_i_trace_j.txt files for event ordering and counts."
    )
    ap.add_argument("folder", type=Path, help="Folder containing site_i_trace_j.txt files")
    args = ap.parse_args()

    files = sorted(args.folder.glob("site_*_trace_*.txt"))
    total = len(files)
    if total == 0:
        print("No matching files found.")
        return

    c_minus2_before_2 = 0
    c_more_2_than_minus2 = 0

    for p in files:
        minus2_before_2, more_2_than_minus2 = analyze_file(p)
        if minus2_before_2:
            c_minus2_before_2 += 1
        if more_2_than_minus2:
            c_more_2_than_minus2 += 1

    pct1 = (c_minus2_before_2 / total) * 100.0
    pct2 = (c_more_2_than_minus2 / total) * 100.0

    print(f"Total files: {total}")
    print(f'1) "-2" appears before "2": {c_minus2_before_2} ({pct1:.1f}%)')
    print(f'2) More "2"s than "-2"s: {c_more_2_than_minus2} ({pct2:.1f}%)')


if __name__ == "__main__":
    main()
