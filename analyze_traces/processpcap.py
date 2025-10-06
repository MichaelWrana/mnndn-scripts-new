#!/usr/bin/env python3
import argparse
import re
import pathlib
import dpkt
import socket

from pathlib import Path

TARGET_IP_DEFAULT = "10.0.3.69"
EXP_RE = re.compile(r"^experiment_(\d+)$")

def ip_to_str(ip_bytes: bytes) -> str:
    return socket.inet_ntoa(ip_bytes)

def classify_packet(ts, buf, target_ip: str) -> tuple[float, int] | None:
    """
    Returns (timestamp, dir_flag) where dir_flag is 1 (outgoing) or -1 (incoming).
    Non-IP and unmatched IP packets are classified as incoming (-1).
    """
    try:
        eth = dpkt.ethernet.Ethernet(buf)
    except Exception:
        # Corrupt frame: treat as incoming to keep "every packet" guarantee.
        return (float(ts), -1)

    if isinstance(eth.data, dpkt.ip.IP):
        ip = eth.data
        try:
            src = ip_to_str(ip.src)
            dst = ip_to_str(ip.dst)
        except Exception:
            return (float(ts), -1)

        if dst == target_ip:
            return (float(ts), 1)
        elif src == target_ip:
            return (float(ts), -1)
        else:
            # IPv4 but neither endpoint is target: classify as incoming.
            return (float(ts), -1)
    else:
        # Non-IP (e.g., ARP): incoming.
        return (float(ts), -1)

def process_pcap(pcap_path: Path, out_path: Path, target_ip: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pcap_path.open("rb") as f, out_path.open("w", encoding="utf-8") as out:
        reader = dpkt.pcap.Reader(f)
        base_ts = None  # <-- added
        for ts, buf in reader:
            if base_ts is None:                 # <-- added
                base_ts = ts                    # <-- added
            _, flag = classify_packet(ts, buf, target_ip)
            out.write(f"{float(ts - base_ts):.4f}\t{flag}\n")  # <-- changed to relative timestamp

def main():
    ap = argparse.ArgumentParser(
        description="Generate website_i_trace_j files from experiment_* subfolders of IPv4 pcaps."
    )
    ap.add_argument("--root", type=Path, default=pathlib.Path("../experiment/generated_traces"),help="Root folder containing experiment_0, experiment_1, ...")
    ap.add_argument("--target-ip", default=TARGET_IP_DEFAULT,
                    help=f"IPv4 address to treat as local host (default: {TARGET_IP_DEFAULT})")
    # add this argument (near the other argparse.add_argument calls)
    ap.add_argument("--out-dir", default="default/", help="Subfolder name inside each experiment_* to write outputs")

    
    args = ap.parse_args()

    root: Path = args.root
    target_ip: str = args.target_ip
    out_dir = Path(args.out_dir)

    if not root.is_dir():
        raise SystemExit(f"Error: {root} is not a directory")

    # Find experiment_* folders and sort by their numeric suffix
    exp_dirs = []
    for p in root.iterdir():
        if p.is_dir():
            m = EXP_RE.match(p.name)
            if m:
                exp_dirs.append((int(m.group(1)), p))
    if not exp_dirs:
        raise SystemExit("Error: no experiment_* subfolders found")

    exp_dirs.sort(key=lambda x: x[0])

    for j, exp_dir in exp_dirs:                      
        pcaps = sorted([p for p in exp_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pcap"])
        if not pcaps:
            continue

        for i, pcap_path in enumerate(pcaps):        
            out_name = f"site_{i}_trace_{j}.txt"     
            out_path = out_dir / out_name
            process_pcap(pcap_path, out_path, target_ip)
            print(out_name)

if __name__ == "__main__":
    main()

'''
DEFENSE COMMANDS (COPY-PASTE)
FRONT:
    sudo python main.py ../../nopet_nodef_static -format .txt -c t1 

'''
