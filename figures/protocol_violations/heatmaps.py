import pathlib
import argparse

import pandas as pd
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt

import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42

def parse_args():
    p = argparse.ArgumentParser(
        description="Run one or more reformat steps based on flags.",
    )
    p.add_argument("--tracesin", type=pathlib.Path, help="Path to traces after the defenses are applied")
    p.add_argument("--sites", type=int, default=100, help="number of sites in dataset (default=100)")
    p.add_argument("--exp", type=int, default=100, help="number of experiments per website in dataset (default=100)")
    p.add_argument("--unsol",  action="store_true", help="Count the number of Unsolicited Data Violations")
    p.add_argument("--unsat",  action="store_true", help="Count the number of Unsatisfied Interest Violations")
    p.add_argument("--timeout",  default=0, help="Count the number of Interest Timeout Violations (default=False).  When setting, specify timeout in seconds as a positive integer.")
    p.add_argument("--overhead",   action="store_true", help="Calculate Data overhead as a percent")
    p.add_argument("--heatmap",   action="store_true", help="Create heatmap of violations (closed-world only)")

    args = p.parse_args()

    if args.tracesin is None:
        p.error("Must specify path to traces input folder.  Use: --tracesin")

    # Enforce at least one action
    if not (args.unsol or args.unsat or args.timeout or args.overhead):
        p.error("No action specified. Use one or more of: --unsol --unsat --timeout")

    return args

def has_unsolicited_data(trace):
    try:
        interest_idx = trace.index[trace["direction"] == 2][0]
        data_idx = trace.index[trace["direction"] == -2][0]
    except IndexError:
        return False
    
    return data_idx < interest_idx

def has_unsatisfied_interest(trace):
    interest_count = (trace["direction"] == 2).sum()
    data_count = (trace["direction"] == -2).sum()

    return interest_count > data_count

def has_interest_timeout(trace, timeout):
    final_interest_time = min(trace.loc[trace["direction"].eq(1), "time"].iloc[-1], trace.loc[trace["direction"].eq(2), "time"].iloc[-1])
    final_data_time = max(trace.loc[trace["direction"].eq(-2), "time"].iloc[-1], trace.loc[trace["direction"].eq(-1), "time"].iloc[-1])

    return final_data_time - final_interest_time > int(timeout)

def calculate_overhead(trace, data_weight=1, interest_weight=1):
    orig = ((trace["direction"] == 1).sum()  * interest_weight +
            (trace["direction"] == -1).sum() * data_weight)
    dummy = ((trace["direction"] == 2).sum()  * interest_weight +
             (trace["direction"] == -2).sum() * data_weight)
    
    return 100.0 * (dummy / orig)

def create_heatmap(violation_list, violation_type=""):
    hm_data = violation_list.reshape(100, 100).sum(axis=1)
    hm_data = hm_data.reshape(10, 10)

    fig, ax = plt.subplots()

    im = ax.imshow(
        hm_data,
        vmin=0, vmax=100,
        cmap='viridis',
        interpolation='nearest'
    )

    cbar = plt.colorbar(im, ax=ax)
    cbar.ax.tick_params(labelsize=16)

    if "regulator" in str(traces_dir):
        titlestring = f'RegulaTor, {violation_type}'
    elif "front" in str(traces_dir):
        titlestring = f'FRONT, {violation_type}'
    elif "wtfpad" in str(traces_dir):
        titlestring = f'WTF-PAD, {violation_type}'
    elif "tamaraw" in str(traces_dir):
        titlestring = f'Tamaraw, {violation_type}'

    ax.set_title(titlestring, fontsize=24)

    ax.set_xticks([])
    ax.set_yticks([])

    plt.tight_layout()

    filename = titlestring.replace(". ", "_").replace(", ", "_").lower()
    plt.savefig(f"{filename}.pdf")
    plt.show()

args = parse_args()

traces_dir = args.tracesin
num_monitored_sites = args.sites
num_experiments = args.exp

traces_list = []
for i in tqdm(range(num_monitored_sites)):
    if num_experiments > 1:
        for j in range(num_experiments):
            trace_file_path = traces_dir / f"site_{i}_trace_{j}.txt"
            df = pd.read_csv(trace_file_path.absolute(), sep="\t", header=None, names=["time", "direction"])
            traces_list.append(df)
    else:
        trace_file_path = traces_dir / f"site_{i}.txt"
        df = pd.read_csv(trace_file_path.absolute(), sep="\t", header=None, names=["time", "direction"])
        traces_list.append(df)

print(len(traces_list))

if args.unsol:
    unsolicited_data = np.zeros(len(traces_list))
    for i, trace in enumerate(traces_list):
        if has_unsolicited_data(trace):
            unsolicited_data[i] = 1

    unsolicited_data_count = np.sum(unsolicited_data)
    print(f"Number of Traces with unsolicited data: {unsolicited_data_count} ({unsolicited_data_count/len(traces_list)*100:.2f}%)")

    if args.heatmap:
        create_heatmap(unsolicited_data, "Unsol. Data")


if args.unsat:
    unsatisfied_interest = np.zeros(len(traces_list))
    for i, trace in enumerate(traces_list):
        if has_unsatisfied_interest(trace):
            unsatisfied_interest[i] = 1

    unsatisfied_interest_count = np.sum(unsatisfied_interest)
    print(f"Number of Traces with unsatisfied interest(s): {unsatisfied_interest_count} ({unsatisfied_interest_count/len(traces_list)*100:.2f}%)")

    if args.heatmap:
        create_heatmap(unsatisfied_interest, "Unsat. Interest")  

if args.timeout:
    interest_timeout = np.zeros(len(traces_list))
    for i, trace in enumerate(traces_list):
        if has_interest_timeout(trace, args.timeout):
            interest_timeout[i] = 1

    interest_timeout_count = np.sum(interest_timeout)
    print(f"Number of Traces with interest timeout(s) > {args.timeout}sec: {interest_timeout_count} ({interest_timeout_count/len(traces_list)*100:.2f}%)")
    
    if args.heatmap:
        create_heatmap(interest_timeout, f"{args.timeout}s Timeout")  

if args.overhead:
    overheads = []
    for trace in traces_list:
        overheads.append(calculate_overhead(trace))
    print(len(overheads))
    print(f"Average Data Overhead: {np.mean(overheads):.1f}%")
