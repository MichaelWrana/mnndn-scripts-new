import numpy as np
from tqdm import tqdm

def load_and_merge_txt(folder, num_monitored_sites, num_experiments):
    merged_traces = {}

    for i in tqdm(range(num_monitored_sites)):
        merged_traces[i] = []
        for j in range(num_experiments):
            trace_file_path = folder / f"site_{i}_trace_{j}.txt"

            with trace_file_path.open("r") as f:
                trace = [
                    float(val1) * np.sign(float(val2))
                    for val1, val2 in (line.strip().split() for line in f)
                ]

            merged_traces[i].append(trace)

    return merged_traces

def load_and_merge_ow(folder, num_unmonitored_sites, cw_traces):
    ow_label = len(cw_traces)
    cw_traces[ow_label] = []
    
    for i in tqdm(range(num_unmonitored_sites)):
        trace_file_path = folder / f"site_{i}.txt"
        with trace_file_path.open("r") as f:
            trace = [
                float(val1) * np.sign(float(val2))
                for val1, val2 in (line.strip().split() for line in f)
            ]
        
        cw_traces[ow_label].append(trace)

    return cw_traces