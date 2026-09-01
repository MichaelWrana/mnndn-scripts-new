import os
import pandas as pd
import numpy as np

def adjust_files_for_negative_two_bursts(folder_path):
    for filename in os.listdir(folder_path):
        if not filename.endswith('.txt'):
            continue

        file_path = os.path.join(folder_path, filename)
        df = pd.read_csv(file_path, sep='\t', header=None, names=['time', 'direction'])

        # Step 1: Identify all -2 entries
        matched_neg2_indices = []
        times = df['time'].values
        dirs = df['direction'].values

        for i in range(1, len(df)):
            if dirs[i] == -2 and dirs[i - 1] == 2 and np.isclose(times[i] - times[i - 1], 0.00001, atol=1e-8):
                matched_neg2_indices.append(i)

        # Step 2: Get sorted unique -1 burst timestamps
        minus_one_bursts = df[df['direction'] == -1]['time'].unique()
        minus_one_bursts.sort()

        # Step 3: Move matched -2s to the closest larger -1 burst
        for idx in matched_neg2_indices:
            current_time = df.at[idx, 'time']
            later_bursts = minus_one_bursts[minus_one_bursts > current_time]
            if len(later_bursts) > 0:
                df.at[idx, 'time'] = later_bursts[0]

        # Step 4: Sort by timestamp
        df.sort_values(by='time', inplace=True)

        # Step 5: Flip the first ±2 to +2 if it's -2
        abs_2_index = df[df['direction'].abs() == 2].index
        if not abs_2_index.empty:
            first_idx = abs_2_index[0]
            if df.at[first_idx, 'direction'] == -2:
                df.at[first_idx, 'direction'] = 2

        # Step 6: Save the modified file
        df.to_csv(file_path, sep='\t', header=False, index=False, float_format='%.5f')

def flip_first_negative_two_and_append(folder_path):
    for filename in os.listdir(folder_path):
        if not filename.endswith('.txt'):
            continue

        file_path = os.path.join(folder_path, filename)
        df = pd.read_csv(file_path, sep='\t', header=None, names=['time', 'direction'])

        # Find the first occurrence where abs(direction) == 2
        abs_2_index = df[df['direction'].abs() == 2].index
        flipped = False

        if not abs_2_index.empty:
            first_idx = abs_2_index[0]
            if df.at[first_idx, 'direction'] == -2:
                original_time = df.at[first_idx, 'time']
                df.at[first_idx, 'direction'] = 2
                new_row = pd.DataFrame([[original_time + 0.00001, -2]], columns=['time', 'direction'])
                df = pd.concat([df, new_row], ignore_index=True)
                flipped = True

        # Sort by timestamp to keep order
        df.sort_values(by='time', inplace=True)

        # Save the modified file
        df.to_csv(file_path, sep='\t', header=False, index=False, float_format='%.5f')

        # Print progress
        status = "FLIPPED -2 to 2 + APPENDED -2" if flipped else "no change"
        print(f"{filename}: {status}")

import random

def sample_discrete_triangular(a, b, m):
    if not (a <= m <= b):
        raise ValueError("Mode m must be between a and b (inclusive).")
    
    support = list(range(a, b + 1))
    probabilities = []

    for x in support:
        if x <= m:
            prob = 2 * (x - a + 1) / ((b - a + 1) * (m - a + 1))
        else:
            prob = 2 * (b - x + 1) / ((b - a + 1) * (b - m + 1))
        probabilities.append(prob)

    return random.choices(support, weights=probabilities, k=1)[0]

# Example usage:
for _ in range(20):
    print(sample_discrete_triangular(1, 3, 1), end=' ')

#flip_first_negative_two_and_append("../andana_final/")
#OPTIONAL
#adjust_files_for_negative_two_bursts("../andana_final")