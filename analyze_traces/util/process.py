import os
import shutil
import random
import math

import numpy as np

from tqdm import tqdm

def reformat_wflib(traces, target_len=5000):
    X = []
    y = []

    for label, sequence_list in traces.items():
        for seq in sequence_list:
            X.append(seq)
            y.append(label)

    y = np.asarray(y)

    X_fixed = []

    for seq in X:
        seq = np.asarray(seq)
        if len(seq) > target_len:
            X_fixed.append(seq[:target_len])
        else:
            padded = np.pad(seq, (0, target_len - len(seq)), mode='constant')
            X_fixed.append(padded)

    X_fixed = np.stack(X_fixed)  # shape: (num_samples, 5000)

    print(X_fixed.shape)
    print(y.shape)

    return X_fixed, y

def reformat_cm(traces, target_len=10000):
    X = []
    y = []

    for label, sequence_list in traces.items():
        for seq in sequence_list:
            seq = np.asarray(seq)
            timestamps = np.abs(seq)
            directions = np.sign(seq)

            # Trim/pad timestamps
            if len(timestamps) > target_len:
                timestamps = timestamps[:target_len]
                directions = directions[:target_len]
            else:
                pad_len = target_len - len(timestamps)
                timestamps = np.pad(timestamps, (0, pad_len), mode='constant', constant_values=0.0)
                directions = np.pad(directions, (0, pad_len), mode='constant', constant_values=0.0)

            # Handle 0s in timestamps
            timestamps = np.trim_zeros(timestamps, 'b')
            timestamps[timestamps == 0.0] = 1e-6
            timestamps = np.pad(timestamps, (0, target_len - len(timestamps)), mode='constant', constant_values=0.0)

            # Reshape and concatenate as (1, 10000, 2)
            timestamps = timestamps.reshape((1, -1, 1))
            directions = directions.reshape((1, -1, 1))
            combined = np.concatenate([timestamps, directions], axis=-1).astype(np.float32)
            X.append(combined)
            y.append(label)

    X = np.concatenate(X, axis=0)  # shape: (num_samples, 10000, 2)
    y = np.asarray(y)
    max_category = np.max(y[y != -1])
    y[y == -1] = max_category + 1
    y = y.astype(np.uint8)

    return X, y

def reformat_rf(traces, out_dir_path):
    os.makedirs(out_dir_path, exist_ok=True)

    for label, sequence_list in traces.items():
        for idx, sequence in enumerate(sequence_list):
            trace_path = out_dir_path / f"{label}-{idx}.txt"

            with trace_path.open('w') as f:
                for value in sequence:
                    abs_val = abs(value)
                    sign_val = int(np.sign(value))
                    sign_val = sign_val if sign_val != 0 else 1
                    f.write(f"{abs_val:.4f}\t{sign_val}\n")
                
                
    # Get all trace filenames ending in .txt
    trace_files = [f for f in os.listdir(out_dir_path) if f.endswith('.txt')]
    random.shuffle(trace_files)

    total = len(trace_files)
    n_train = int(total * 0.8)
    n_test = int(total * 0.1)

    train_files = trace_files[:n_train]
    test_files = trace_files[n_train:n_train + n_test]
    # remaining_files = trace_files[n_train + n_test:]  # Ignored

    train_idx_path = out_dir_path / 'index_train.txt'
    with train_idx_path.open('w') as f:
        for name in train_files:
            f.write(f"{name}\n")

    
    test_idx_path = out_dir_path / 'index_test.txt'
    with test_idx_path.open('w') as f:
        for name in test_files:
            f.write(f"{name}\n")

    # Compress the folder into a .zip file
    shutil.make_archive(out_dir_path, 'zip', out_dir_path)

    # Remove the original folder and its contents
    shutil.rmtree(out_dir_path)


def merge_left(left, right, overlap):
    overlap_count = math.floor(min(len(left), len(right)) * overlap)
    start_time = abs(left[-overlap_count])
    right_shifted = [abs(time) + start_time if time >= 0 else - (abs(time) + start_time) for time in right]
    merged = sorted(left + right_shifted, key=abs)
    return merged

def create_multi_tab(traces_to_merge, overlaps):
    if len(traces_to_merge) == 1:
        return traces_to_merge[0]
    else:
        merged = merge_left(traces_to_merge[0], traces_to_merge[1], overlaps[0])
        return create_multi_tab([merged] + traces_to_merge[2:], overlaps[1:])
    
def reformat_wflib_multi(traces, num_tabs, num_traces):
    
    X = []
    y = []

    site_id_list = list(traces.keys())
    site_id_weights = np.array([len(traces[site_id]) for site_id in site_id_list], dtype=float)
    proba = site_id_weights / site_id_weights.sum()

    for _ in tqdm(range(num_traces)):
        
        
        site_ids = np.random.choice(site_id_list, size=num_tabs, replace=False, p=proba).tolist()

        traces_to_merge = [random.choice(traces[site_id]) for site_id in site_ids]
        trimmed_traces, removed = trim_lists_to_limit(traces_to_merge, 10000)
        overlaps = random.sample([i / 100 for i in range(0, 41, 5)], num_tabs-1)

        multi_trace = create_multi_tab(trimmed_traces, overlaps)

        if len(multi_trace) < 10000:
            multi_trace.extend([0] * (10000 - len(multi_trace)))
        
        X.append(multi_trace)
        
        labels = np.zeros(len(traces), dtype=int)
        labels[site_ids] = 1
        
        y.append(labels)
    
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int8)

def trim_lists_to_limit(lists, limit):
    """
    Trim a list of lists so the total length <= limit.
    - Always trim from the END of each list.
    - Always trim the LONGEST lists first (i.e., level down the peaks).
    Returns (trimmed_lists, removed_counts_per_list).
    """
    n = len(lists)
    lengths = [len(lst) for lst in lists]
    total = sum(lengths)
    if total <= limit:
        return lists, [0]*n

    over = total - limit
    # sort by length desc, keep original indices
    order = sorted(range(n), key=lambda i: lengths[i], reverse=True)
    L = [lengths[i] for i in order]  # descending lengths
    target = L[:]  # we'll reduce these

    # Level down the tallest stacks until we've removed 'over' items total
    for i in range(n):
        curr = L[i]
        nxt = L[i+1] if i+1 < n else 0
        # we can lower the top (i+1) lists from 'curr' down to 'nxt'
        delta_per_list = curr - nxt
        if delta_per_list <= 0:
            continue
        delta_total = delta_per_list * (i+1)

        if over >= delta_total:
            # lower top (i+1) lists entirely down to 'nxt'
            for j in range(i+1):
                target[j] -= delta_per_list
            over -= delta_total
        else:
            # only partial lowering needed
            full_steps = over // (i+1)
            rem = over % (i+1)
            if full_steps:
                for j in range(i+1):
                    target[j] -= full_steps
            # distribute the remainder: take 1 extra from the longest ones first
            for j in range(rem):
                target[j] -= 1
            over = 0
            break

    # Safety: if anything remains (shouldn't), shave from the very top
    if over > 0:
        for j in range(n):
            if over == 0: break
            take = min(over, target[j])
            target[j] -= take
            over -= take

    # Map targets back to original order
    target_by_orig = [0]*n
    for rank, idx in enumerate(order):
        target_by_orig[idx] = max(0, target[rank])

    # Apply trims from the END and record how many we removed
    trimmed = []
    removed = []
    for lst, tlen in zip(lists, target_by_orig):
        cut = len(lst) - tlen
        trimmed.append(lst[:tlen])  # trim from end
        removed.append(max(0, cut))

    return trimmed, removed
