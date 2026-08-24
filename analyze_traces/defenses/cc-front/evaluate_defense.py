import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statistics
from scipy.interpolate import interp1d

def load_trace(txt_path):
    data = []
    with open(txt_path, 'r') as f:
        for line in f:
            t, d = line.strip().split('\t')
            data.append([float(t), int(d)])
    return np.array(data)

def plot_trace(trace, title, site_id, trace_id, color, start_index, end_index):

    trace = trace[start_index:end_index]
    # print(len(trace))
    plt.figure(figsize=(25, 5))
    plt.scatter(trace[:, 0], trace[:, 1], color=color, alpha=0.6)
    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel("Direction")
    plt.grid(True)
    plt.tight_layout()
    # plt.savefig(f"site_{site_id}_trace_{trace_id}.pdf", format="pdf", bbox_inches="tight")
    plt.show()

def analyse_trace(trace):
    stats = {
        "original_outgoing":  np.sum(trace[:, 1] == 1),
        "original_incoming":  np.sum(trace[:, 1] == -1),
        "dummy_outgoing":  np.sum(trace[:, 1] == 2),
        "dummy_incoming":  np.sum(trace[:, 1] == -2)
    }

    if (stats["dummy_incoming"]) - (stats["dummy_outgoing"]) < 0:
        more_interests_than_data = 1
        print((stats["dummy_outgoing"]) - (stats["dummy_incoming"]))
    else: more_interests_than_data = 0
    
    stats["total_outgoing"] = stats["original_outgoing"] + stats["dummy_outgoing"]
    stats["total_incoming"] = stats["original_incoming"] + stats["dummy_incoming"]
    stats["total_original"] = stats["original_outgoing"] + stats["original_incoming"]
    stats["total_padded"] = stats["total_incoming"]+ stats["total_outgoing"]

    # + latency 
    # + kfp
    return stats, more_interests_than_data

def check_packets(site_ids, padded_dir, num_of_traces = 10000):
    general = []
    traces_with_more_data = []
    traces_with_more_interests_than_data = []
    num_traces_with_more_interests_than_data = 0
    trace_ids =100

    for site_id in range(site_ids):
        for trace_id in range(trace_ids):
    
            padded_file = padded_dir + f"site_{site_id}_trace_{trace_id}.txt"

            padded_trace = load_trace(padded_file)
            stats_padded, more_interests_than_data = analyse_trace(padded_trace)
            if more_interests_than_data == 1:
                num_traces_with_more_interests_than_data += 1
                traces_with_more_interests_than_data.append(padded_file)
                # print("outgoing", stats_padded["dummy_outgoing"], "incoming", stats_padded["dummy_incoming"])
            else: traces_with_more_data.append(padded_file)
            # general.append(stats_padded)
    
    percentage = num_traces_with_more_interests_than_data / num_of_traces * 100 
    # df = pd.DataFrame(general)
    # output_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/packet_count_perfect_with_dummies-more-increased-time.csv"
    # output_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/wtfpad/packet_count_all-histos-rcv.csv"
    # df.to_csv(output_file, index=False)

    output_file = padded_dir + "more_interests_then_data_front_t1_new_without_pad.txt"

    with open(output_file, 'w') as f:
        f.write(f"Percentage of traces with more interest packets than data: {percentage}% \n"\
                f"Number of traces with more interest packets than data: {num_traces_with_more_interests_than_data} \n"\
                f"Percentage of traces with more data packets than interest: {100 - percentage}% \n" \
                f"Number of traces with more data packets than interest: {len(traces_with_more_data)} \n")
        for file in traces_with_more_interests_than_data:
            f.write(file + "\n")


def check_for_zero(site_ids=100, trace_ids=100):
    count_with_double_zero = 0
    total_checked = 0
    matching = 0
    non_matching = 0
    total_checked = 0

    for site_id in range(site_ids):
        if site_id == 30: trace_ids = 97
        elif site_id == 60: trace_ids = 96
        else: trace_ids = 100
        for trace_id in range(trace_ids):
            # file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/results-final/site_{site_id}_trace:{trace_id}_original.txt"
            # file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/try-7900/site_{site_id}_trace:{trace_id}_original.txt"
            file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/wtfpad/results/all-histos-rcv/site_{site_id}_trace:{trace_id}_padded_wtfpad.txt"

            trace = load_trace(file)
            t1, d1 = trace[0]
            t2, d2 = trace[1]

            total_checked += 1

            if t1 == t2 and {d1, d2} == {-1, 1}:
                matching += 1
            else:
                non_matching += 1

    print(f"\n Matching files with double-zero start (-1 and 1 at same timestamp): {matching}/{total_checked}")
    print(f'matching 0 0 {matching}')
    print(f'non_matching {non_matching}')
    print(f'total_checked {total_checked}')

def check_how_trace_starts(padded_dir, site_ids=100, num_of_traces = 10000):
    general = []
    not_general = []
    not_padded_files = []
    starts_with_dummy_interest = 0
    starts_with_dummy_data = 0
    num_files = 0
    traces_with_zero_dummies = 0
    num_not_padded_with_interest_files = 0 
    trace_ids = 100

    for site_id in range(site_ids):
        for trace_id in range(trace_ids):
            file = padded_dir + f"site_{site_id}_trace_{trace_id}.txt"

            trace = load_trace(file)
            num_files +=1

            directions = trace[:, 1]
            num_dummy_packets = np.sum((directions == 2) | (directions == -2))

            if num_dummy_packets == 0:
                traces_with_zero_dummies += 1
                continue

            num_interest_dummy_packets = np.sum(directions == 2)
                
            filtered_directions = directions[(directions == 2) | (directions == -2)]

            # for i in range (len(directions)):
            if filtered_directions[0] == 2: 
                starts_with_dummy_interest += 1
                general.append(file)
            elif (filtered_directions[0] == -2) and (num_interest_dummy_packets != 0):
                starts_with_dummy_data +=1
                not_general.append(file)
            elif (num_interest_dummy_packets == 0):
                num_not_padded_with_interest_files += 1
            else: 
                # num_not_padded_files += 1
                # not_padded_files.append(file)
                print("No dummies ", file)

    percentage_starts_with_data = starts_with_dummy_data / num_of_traces *100
    percentage_starts_with_interest = starts_with_dummy_interest / num_of_traces *100
    percentage_zero_dummies = traces_with_zero_dummies / num_of_traces *100

    output_file = padded_dir + "data_before_interest_t1_new_without_pad.txt"

    # print(traces_with_zero_dummies, num_files)
    
    with open(output_file, 'w') as f:
        f.write(f"Number of traces where dummy data packet is before dummy interest: {starts_with_dummy_data}\n" \
                f"Percentage of traces where dummy data packet is before dummy interest: {percentage_starts_with_data}%\n" \
                f"Number of traces where dummy interest packet is before dummy data: {starts_with_dummy_interest}\n" \
                f"Percentage of traces where dummy interest packet is before dummy data: {percentage_starts_with_interest}%\n" \
                f"Number of traces without dummy packet: {traces_with_zero_dummies}\n" \
                f"Percentage of traces without dummy packet: {percentage_zero_dummies}%\n" \
                f"Number of traces without dummy interests: {num_not_padded_with_interest_files}")

        # f.write("Starts with dummy interest:\n")
        # for file in general:
        #     f.write(file + "\n")

        f.write("\nStarts with dummy data (not_general):\n")
        for file in not_general:
            f.write(file + "\n")

def count_direction_types(trace):
    counts = {
        "1 (interest)": np.sum(trace[:, 1] == 1),
        "-1 (data)": np.sum(trace[:, 1] == -1),
        "2 (interest)": np.sum(trace[:, 1] == 2),
        "-2 (data)": np.sum(trace[:, 1] == -2),
    }
    print(f"Direction counts:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    if counts["2 (interest)"] != 0 or counts["-2 (data)"] !=0:
        print(f"Sum of interest (1 and 2): {counts['1 (interest)']+counts['2 (interest)']}")
        print(f"Sum of data (-1 and -2): {counts['-1 (data)']+counts['-2 (data)']}")
    return counts

# def calculate_time_diffs_all_sites(padded_file, original_file):
def calculate_time_diffs_all_sites(num_of_traces = 9993):
    all_data = []
    site_ids = 100
    # site_ids = 1
    mismatch =0 
    no_outgoing_incoming =0 

    output_csv = "timestamps-regula-with-29-59.csv"

    max_timeout = 30
    # max_timeout = 20

    num_of_timedout_traces = 0
    num_of_ok_traces = 0

    timedout_trace_list = []
    ok_trace_list = []

    for site_id in range(site_ids):
        if site_id == 30:
            trace_ids = 97
        elif site_id == 60:
            trace_ids = 96
        else:
            trace_ids = 100
        for trace_id in range(trace_ids):
            # padded_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/perfect-regulator-dummies/site_{site_id}_trace:{trace_id}_original.txt"
            # padded_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/full-padded-traces-for-analysis/site_{site_id}_trace:{trace_id}_original.txt"
            
            padded_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/tamaraw/results/all-with-dummy/site_{site_id}_trace_{trace_id}_original.txt"
            original_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/originals-perfect/site_{site_id}_trace_{trace_id}_original.txt"

            padded = load_trace(padded_file)
            original = load_trace(original_file)

            trace_data = []

            for direction in [1, -1]:  
                padded_times = [t for t, d in padded if d == direction]
                original_times = [t for t, d in original if d == direction]

                if len(padded_times) != len(original_times):
                    # print(f"Mismatch in direction {direction} counts for site {site_id}, trace {trace_id} ({len(original_times)} vs {len(padded_times)})")
                    mismatch += 1
                    continue 
                
                num_of_packet = 0
                for i in range(len(original_times)):
                    t_orig = original_times[i]
                    t_pad = padded_times[i]
                    diff = t_pad - t_orig
                    num_of_packet += 1

                    if direction == 1:
                        outgoing_diff = diff
                        incoming_diff = np.nan
                    elif direction == -1:
                        outgoing_diff = np.nan
                        incoming_diff = diff

                    orig_gap = t_orig - original_times[i - 1] if i > 0 else 0.0
                    pad_gap = t_pad - padded_times[i - 1] if i > 0 else 0.0

                    # all_data.append([site_id, trace_id, direction, t_orig, t_pad, diff, outgoing_diff, incoming_diff])
                    # all_data.sort(key=lambda x: x[3])

                    trace_data.append([site_id, trace_id, direction, t_orig, t_pad, outgoing_diff, incoming_diff, num_of_packet])
                
            trace_data.sort(key=lambda x: x[3])

            outgoing_rows = [row for row in trace_data if row[2] == 1]
            incoming_rows = [row for row in trace_data if row[2] == -1]

            if not outgoing_rows or not incoming_rows:
                # print(f"Site {site_id},trace {trace_id} no outgoing or incoming packets.\n")
                # print(len(outgoing_rows))
                # print(len(incoming_rows))
                no_outgoing_incoming  += 1
                continue

            for i in range(1, len(incoming_rows)):
                incoming_row = incoming_rows[-i]
                incoming_padded_timestamp = incoming_row[4]
                incoming_diff = incoming_row[6]

                outgoing_row = outgoing_rows[-i]
                outgoing_padded_timestamp = outgoing_row[4]
                outgoing_diff = outgoing_row[5]

                gap = incoming_padded_timestamp - outgoing_padded_timestamp
                    
                if gap < 0:
                    continue
                elif gap > max_timeout:
                    num_of_timedout_traces += 1
                    timedout_trace_list.append((site_id, trace_id))
                    break
                else: 
                    num_of_ok_traces += 1
                    ok_trace_list.append((site_id, trace_id))
                    break


            all_data.extend(trace_data)
            
    total_checked_traces = num_of_timedout_traces + num_of_ok_traces
    percentage_of_timedout_traces = num_of_timedout_traces / total_checked_traces *100
    percentage_of_ok_traces = num_of_ok_traces / total_checked_traces *100
    print(total_checked_traces)
    print('mismatch', mismatch)
    print('no_outgoing_incoming', no_outgoing_incoming)
    # output_file = "/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/timedout_traces_regulator_30_sec.txt"
    # output_file = "/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/timedout_traces_regulator_30_sec_not_full.txt"
    output_file = "/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/timedout_traces_tamaraw_30_sec.txt"
    with open(output_file, 'w') as f:
        f.write(f"Percentage of traces that exceeded timeout: {percentage_of_timedout_traces}\n" \
                f"Number of traces that exceeded timeout:{num_of_timedout_traces}\n" \
                f"Percentage of traces that didn't exceed timeout: {percentage_of_ok_traces}\n" \
                f"Number of traces that didn't exceed timeout: {num_of_ok_traces}\n")
        
        # f.write("\nTraces that exceeded timeout (site_id, trace_id):\n")
        # for site_id, trace_id in timedout_trace_list:
        #     f.write(f"Site {site_id}, Trace {trace_id}\n")
    
        # f.write("\nTraces that didn't exceed timeout (site_id, trace_id):\n")
        # for site_id, trace_id in ok_trace_list:
        #     f.write(f"Site {site_id}, Trace {trace_id}\n")

    # all_data.sort(key=lambda x: x[3])

    # df = pd.DataFrame(all_data, columns=["site_id", "trace_id", "direction", "original_time", "padded_time", "difference", "time_diff_outgoing", "time_diff_incoming"])
    # df.to_csv(output_csv, index=False)

def plot_for_regulator(file):
    df = pd.read_csv(file)

    plt.figure(figsize=(14, 6))

    plt.plot(df[df['direction']==1]['original_time'], 
            df[df['direction']==1]['time_diff_outgoing'], 
            label='Outgoing Pakcet Delay', color='red')

    plt.plot(df[df['direction']==-1]['original_time'], 
            df[df['direction']==-1]['time_diff_incoming'], 
            label='Incoming Packet Delay', color='blue')

    plt.title("Delays Added by RegulaTor", fontsize=16)
    plt.xlabel("Original Time (seconds)", fontsize=14)
    plt.ylabel("Delay Added to Packet (seconds)", fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"Delayes_added_by_RegulaTor-5.pdf", format="pdf", bbox_inches="tight")

    plt.show()

def create_csv_for_regulator_gap(padded_file, original_file):
    all_data = []
    mismatch =0 

    output_csv = "timestamps-regula-with-3-1.csv"

    padded = load_trace(padded_file)
    original = load_trace(original_file)

    trace_data = []

    for direction in [1, -1]:  
            padded_times = [t for t, d in padded if d == direction]
            original_times = [t for t, d in original if d == direction]

            if len(padded_times) != len(original_times):
                # print(f"Mismatch in direction {direction} counts for site {site_id}, trace {trace_id} ({len(original_times)} vs {len(padded_times)})")
                mismatch += 1
                continue 
                
            num_of_packet = 0
            for i in range(len(original_times)):
                t_orig = original_times[i]
                t_pad = padded_times[i]
                diff = t_pad - t_orig
                num_of_packet += 1

                if direction == 1:
                    outgoing_diff = diff
                    incoming_diff = np.nan
                elif direction == -1:
                    outgoing_diff = np.nan
                    incoming_diff = diff

                orig_gap = t_orig - original_times[i - 1] if i > 0 else 0.0
                pad_gap = t_pad - padded_times[i - 1] if i > 0 else 0.0

                all_data.append([site_id, trace_id, direction, t_orig, t_pad, diff, outgoing_diff, incoming_diff])

    all_data.sort(key=lambda x: x[3])


    # print(all_data)
    print(f"Mismatches: {mismatch}")

    df = pd.DataFrame(all_data, columns=["site_id", "trace_id", "direction", "original_time", "padded_time", "difference", "time_diff_outgoing", "time_diff_incoming"])
    # df.to_csv(output_csv, index=False)

    # df = pd.read_csv(output_csv)

    # plt.figure(figsize=(14, 6))

    # # Outgoing
    # plt.plot(df[df['direction']==1]['original_time'], 
    #         df[df['direction']==1]['time_diff_outgoing'], 
    #         label='Outgoing Pakcet Delay', color='red')

    # # Incoming 
    # plt.plot(df[df['direction']==-1]['original_time'], 
    #         df[df['direction']==-1]['time_diff_incoming'], 
    #         label='Incoming Packet Delay', color='blue')
    

    # #     # Outgoing
    # # plt.plot(df[df['direction']==1]['original_time'], 
    # #         df[df['direction']==1]['padded_time'], 
    # #         label='Outgoing Pakcet Delay', color='red')

    # # # Incoming 
    # # plt.plot(df[df['direction']==-1]['original_time'], 
    # #         df[df['direction']==-1]['padded_time'], 
    # #         label='Incoming Packet Delay', color='blue')

    # timeout = 30  
    # y_max = df[['time_diff_outgoing', 'time_diff_incoming']].max().max()

    # # Horizontal line
    # plt.axhline(y=timeout, color='black', linestyle='--', linewidth=2, label='Timeout (30s)')

    # # Shaded region
    # plt.axhspan(timeout, y_max + 5, facecolor='orange', alpha=0.3, label='Timeout Exceeded')

    # plt.title("Delays Added by RegulaTor", fontsize=16)
    # plt.xlabel("Original Time (seconds)", fontsize=14)
    # plt.ylabel("Delay Added to Packet (seconds)", fontsize=14)
    # plt.legend(fontsize=12)
    # plt.grid(True)
    # plt.tight_layout()
    # # plt.savefig(f"Delayes_added_by_RegulaTor-5.pdf", format="pdf", bbox_inches="tight")

    # plt.show()

    # === Prepare data ===
    out_df = df[df['direction']==1]
    in_df = df[df['direction']==-1]


    # === Interpolate incoming delay onto outgoing timestamps ===
    # Interpolation function
    interp_incoming = interp1d(in_df['original_time'], in_df['time_diff_incoming'], 
                            kind='linear', fill_value='extrapolate')
    
    # interp_incoming = interp1d(in_df['original_time'], in_df['time_diff_incoming'], 
    #                         kind='linear', fill_value=None , bounds_error=False)

    # Common X-axis = outgoing timestamps
    common_times = out_df['original_time'].values
    incoming_interp_values = interp_incoming(common_times)

    # === Compute GAP curve ===
    gap_curve = np.abs(incoming_interp_values - out_df['time_diff_outgoing'].values)

    # === Find first point where gap exceeds 30 ===
    gap_exceeds = np.where(gap_curve >= 30)[0]
    if len(gap_exceeds) > 0:
        first_exceed_idx = gap_exceeds[0]
        first_exceed_time = common_times[first_exceed_idx]
        print(f"GAP between delays exceeds 30s at t = {first_exceed_time:.2f} s")
    else:
        first_exceed_time = None
        print("GAP between delays never exceeds 30s")

    # === Plot everything ===
    plt.figure(figsize=(16, 7))

    xmin, xmax = plt.xlim()
    plt.xlim(xmin, 7 * 1.1)

    # Plot original delays
    plt.plot(out_df['original_time'], out_df['time_diff_outgoing'], 
            label='Delay added to interest', color='red', linewidth=4)
    plt.plot(in_df['original_time'], in_df['time_diff_incoming'], 
            label='Delay added to data', color='blue', linewidth =4)

    # Plot GAP curve
    plt.plot(common_times, gap_curve, label='Difference between delays', color='green', linestyle='-', linewidth=4)

    # Plot horizontal line at 30
    # Plot horizontal lines without legend entries
    plt.axhline(y=30, color='black', linestyle='--', linewidth=2)
    plt.axhline(y=20, color='black', linestyle='--', linewidth=2)

    # Add inline labels near the end of the lines
    x_pos = 0.05  # Use last x value to place the text on the right

    plt.text(x_pos, 26.5 , 'Interest TTL - 30s', color='black', fontsize=24, va='bottom')
    plt.text(x_pos, 16.5 , 'Interest TTL - 20s', color='black', fontsize=24, va='bottom')


    plt.fill_between(common_times, gap_curve, 20, 
                where=(gap_curve >= 20), 
                interpolate=True, 
                color='red', alpha=0.3, label='Interest Timeout Region')

    # # Vertical line where GAP exceeds 30
    # if first_exceed_time is not None:
    #     plt.axvline(x=first_exceed_time, color='green', linestyle='--', linewidth=2, label='GAP exceeds 30s')

    # Labels and grid
    plt.xlabel('Original Time (seconds)', fontsize=24)
    plt.ylabel('Added Delay (seconds)', fontsize=24)
    # plt.title('Packet Delays in RegulaTor', fontsize=24)
    plt.legend(fontsize=24)
    plt.grid(True, linestyle='--', alpha=0.6)
    # === Force axes to start at zero ===
    plt.xlim(left=0)
    plt.ylim(bottom=0)

    plt.tight_layout()

    # Access current axes
    ax = plt.gca()

    # Show only left and bottom spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Thicken the visible spines
    ax.spines['left'].set_linewidth(2)
    ax.spines['bottom'].set_linewidth(2)

    plt.savefig(f"regulator.pdf", format="pdf", bbox_inches="tight")

    plt.show()


def check_consistency(site_ids=100, num_of_traces = 9993):
    delay_data = []
    gap_data = []
    mismatch =0 
    no_outgoing_incoming =0 

    output_csv = "name.csv"

    for site_id in range(site_ids):
        if site_id == 30:
            trace_ids = 97
        elif site_id == 60:
            trace_ids = 96
        else:
            trace_ids = 100
        for trace_id in range(trace_ids):
            # padded_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/perfect-regulator-dummies/site_{site_id}_trace:{trace_id}_original.txt"
            # padded_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/full-padded-traces-for-analysis/site_{site_id}_trace:{trace_id}_original.txt"
            
            padded_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/tamaraw/results/all-with-dummy/site_{site_id}_trace_{trace_id}_original.txt"
            original_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/originals-perfect/site_{site_id}_trace_{trace_id}_original.txt"

            padded = load_trace(padded_file)
            original = load_trace(original_file)

            trace_data = []

            padded_times, padded_dir = [t for t, d in padded ]

            for i in range(1, len(padded_times)):
                t_one = padded_times[i-1]
                t_two = padded_times[i]
                gap_between_packets = t_two - t_one

                gap_data.append([site_id, trace_id, padded_dir[i], padded_times[i], gap_between_packets])


    #         for direction in [1, -1]:  
    #             padded_times = [t for t, d in padded if d == direction]
    #             original_times = [t for t, d in original if d == direction]

    #             if len(padded_times) != len(original_times):
    #                 # print(f"Mismatch in direction {direction} counts for site {site_id}, trace {trace_id} ({len(original_times)} vs {len(padded_times)})")
    #                 mismatch += 1
    #                 continue 
                
    #             num_of_packet = 0
    #             for i in range(len(original_times)):
    #                 t_orig = original_times[i]
    #                 t_pad = padded_times[i]
    #                 diff = t_pad - t_orig
    #                 num_of_packet += 1

    #                 if direction == 1:
    #                     outgoing_diff = diff
    #                     incoming_diff = np.nan
    #                 elif direction == -1:
    #                     outgoing_diff = np.nan
    #                     incoming_diff = diff

     

    #                 delay_data.append([site_id, trace_id, direction, t_orig, t_pad, diff, outgoing_diff, incoming_diff])
            
    # delay_data.sort(key=lambda x: x[3])

    # df = pd.DataFrame(delay_data, columns=["site_id", "trace_id", "direction", "original_time", "padded_time", "gap betwee" "difference", "time_diff_outgoing", "time_diff_incoming"])
    # df.to_csv(output_csv, index=False)

    df = pd.DataFrame(delay_data, columns=["site_id", "trace_id", "direction", "padded_time", "gap between packets" ])
    df.to_csv(output_csv, index=False)


def check_timeout():
    all_data = []
    site_ids = 100

    num_of_traces = 9993
    timeout = 30
    output_csv = "timestamps-dummies.csv"
    no_outgoing = []
    no_incoming = []
    traces_with_large_gap = 0

    for site_id in (site_ids):
        if site_id == 30:
            trace_ids = 97
        elif site_id == 60:
            trace_ids = 96
        else:
            trace_ids = 1

        for trace_id in range(trace_ids):

            file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/perfect-regulator-dummies/site_{site_id}_trace:{trace_id}_original.txt"
            trace = load_trace(file)
            # trace = trace[trace[:, 0].argsort()]

            interest_times = [t for t, d in trace if d == 2]
            data_times = [t for t, d in trace if d == -2]

            last_interest = interest_times[-1]
            last_data = data_times[-1]

            
            outgoing_packets = []
            gaps_in_trace = []

            has_incoming_dummy = False
            has_outgoing_dummy = False

            for t, d in trace:
                if d == 2:  
                    outgoing_packets.append(t)
                    has_outgoing_dummy = True
                elif d == -2:  
                    has_incoming_dummy = True
                    if outgoing_packets:
                        outgoing_time = outgoing_packets.pop()
                        incoming_time = t
                        gap = incoming_time - outgoing_time
                        gaps_in_trace.append(gap)

            if any(gap > timeout for gap in gaps_in_trace):
                traces_with_large_gap += 1

            if not has_incoming_dummy:
                no_incoming.append(file)

            if not has_outgoing_dummy:
                no_outgoing.append(file)

    percentage = (traces_with_large_gap / num_of_traces) * 100

    outfile = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/calculating_gap_timeout.txt"
    with open(outfile, 'w') as f:
        f.write(f"Percentage of traces that have time gap larger than {timeout}s: {percentage}%\n" \
                f"Number of traces that have time gap larger than {timeout}s: {traces_with_large_gap}\n" \
                f"Percentage of traces with no dummy data packet: {len(no_incoming) / num_of_traces * 100}%\n" \
                f"Number of traces with no dummy data packet: {len(no_incoming)}\n" \
                f"Percentage of traces with no dummy interest packet: {len(no_outgoing) / num_of_traces * 100}%\n" \
                f"Number of traces with no dummy interest packet: {len(no_outgoing)}\n")



    #         for direction in [2, -2]:  
    #             padded_times = [t for t, d in padded if d == direction]
    #             padded_times.sort(reverse=True)

    #             for i in range(len(padded_times)):
    #                 timestamp = padded_times[i]
    #                 all_data.append([site_id, trace_id, direction, timestamp])
    
    # all_data.sort(key=lambda x: x[3])

    # df = pd.DataFrame(all_data, columns=["site_id", "trace_id", "direction", "timestamp"])
    # df.to_csv(output_csv, index=False)

if __name__ == '__main__':
    
    site_id = 0
    trace_id = 12

    padded_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/front/results/front_t1_new_without_pad/site_{site_id}_trace_{trace_id}.txt"

    original_file = f"/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/RegulaTor-main/clean-perfect-dataset/site_{site_id}_trace_{trace_id}.txt"

    site_ids = 100

    padded_dir = "/Users/anhelinabodak/Desktop/mnndn/mnndn-scripts/defenses/front/results/front_t1_new_without_pad/"

    check_packets(site_ids, padded_dir) #checks if traces have more dummy interests than dummy data 

    check_how_trace_starts(padded_dir) #checks if trace starts with dummy data

    # original_trace = load_trace(original_file)

    padded_trace = load_trace(padded_file)

    # count_direction_types(original_trace)
    # count_direction_types(padded_trace)


    #three below to create csv and pdf for displaying increasing delays in regulator traces
    # create_csv_for_regulator_gap(padded_file, original_file)

    # calculate_time_diffs_all_sites()

    # csv_file = "timestamps-regula-with-delays-5.csv"
    # plot_for_regulator(csv_file)

    # plot_trace(original_trace, f"Original Trace - Site {site_id}, Trace {trace_id}", site_id, trace_id, color='blue', start_index=0, end_index=None)
    plot_trace(padded_trace, f"Padded Trace - Site {site_id}, Trace {trace_id}", site_id, trace_id, color='red', start_index=0, end_index=None)
