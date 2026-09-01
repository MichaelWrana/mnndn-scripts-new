from os import listdir
from os.path import isfile, join
from multiprocessing import Pool
import random
import sys
import numpy as np
import argparse
from defense_utils import *
from tqdm import tqdm
from collections import defaultdict


parser = argparse.ArgumentParser()
parser.add_argument('source_path', help='Undefended dataset')
parser.add_argument('output_path', help='Output path')
parser.add_argument('--n_processes', type=int, help='Number of python processes to run in parallel', default='4')
parser.add_argument('--orig_rate', help='Original packet surge rate', default='277')
parser.add_argument('--dep_rate', help='Packet sending depreciation rate', default='.94') 
parser.add_argument('--min_budget', type=int, help='Minimum possible padding budget', default='550') 
parser.add_argument('--max_budget', type=int, help='Maximum possible padding budget', default='3550')
parser.add_argument('--threshold', help='Burst threshold', default='3.55')
parser.add_argument('--upload_ratio', help='Ratio of download packets to upload packets', default='3.95')
parser.add_argument('--delay_cap', help='Maximum upload packet delay', default='1.77')
args = parser.parse_args()

# CUTOFF_LENGTH = 20000
# CUTOFF_TIME = 120

CUTOFF_LENGTH = 80000
CUTOFF_TIME = 1500

SAVE_PICKLE = True

def regulator_download(target_trace):
    orig_rate = float(args.orig_rate)
    depreciation_rate = float(args.dep_rate)
    max_padding_budget = int(args.max_budget)
    min_padding_budget = int(args.min_budget)
    burst_threshold = float(args.threshold)

    padding_budget = np.random.randint(min_padding_budget,max_padding_budget)

    output_trace = []
    upload_trace = []
 
    position = 10

    #send packets at a constant rate initially (to construct circuit)
    download_start = target_trace[position]
    added_packets = int(download_start*10)
    for i in range(added_packets):
        pkt_time = i*.1
        output_trace.append((pkt_time, -2))  # Dummy packet

    output_trace.append((target_trace[position], -1))  # Real packet
    current_time = download_start
    burst_time = target_trace[position]
    
    padding_packets = 0
    position = 1
    
    while True:
        # calculate target rate
        target_rate = orig_rate * (depreciation_rate ** (current_time - burst_time))
        if target_rate < 1:
            target_rate = 1

        # check if done sending all real packets
        if position == len(target_trace):
            break

        # count real packets that are waiting (due by now)
        queue_length = 0
        for c in range(position, len(target_trace)):
            if target_trace[c] < current_time:
                queue_length += 1
            else:
                break

        # start new burst if too many are waiting
        if queue_length > (burst_threshold * target_rate):
            burst_time = current_time

        # regular gap
        gap = 1 / float(target_rate)

        #NEW PART
        remaining_dummies = padding_budget - padding_packets
        total_packets_left = queue_length + remaining_dummies + 1  
        total_time_left = max(0.001, 20.0 - current_time)  

        adaptive_gap = total_time_left / total_packets_left
        gap = min(gap, adaptive_gap)

        current_time += gap

        # send packet
        if queue_length == 0 and padding_packets >= padding_budget:
            continue
        elif queue_length == 0 and padding_packets < padding_budget:
            output_trace.append((current_time, -2))  # Dummy download
            padding_packets += 1
        else:
            output_trace.append((current_time, -1))  # Real download
            position += 1


    return output_trace

def regulator_upload_full(download_trace, upload_trace):

    upload_ratio = float(args.upload_ratio)
    delay_cap = float(args.delay_cap)

    output_trace = []

    #send one upload packet for every $upload_ratio download packets 
    upload_size = int(len(download_trace)/upload_ratio)
    # print(f"upload_size : {(upload_size)}")
    download_times = [t for t, _ in download_trace] 
    dummy_uploads = list(np.random.choice(download_times, upload_size, replace=False))

    output_trace = [(t, 2) for t in dummy_uploads]

    #send at constant rate at first
    download_start = download_trace[10][0]
    added_packets = int(download_start*5)
    for i in range(added_packets):
        pkt_time = i*.2
        output_trace.append((pkt_time, 2)) #dummy uploads

    #assign each packet to the next scheduled sending time in the output trace
    output_trace = sorted(output_trace, key=lambda x: x[0]) 
    delay_packets = []
    packet_position = 0

    used_uploads = []
    for t, direction in upload_trace:
        found_packet = False
        for p in range(packet_position + 1, len(output_trace)):
            if output_trace[p][0] >= t and (output_trace[p][0] - t) < delay_cap:
                packet_position = p
                found_packet = True
                break

        if found_packet:
            output_trace[p] = (output_trace[p][0], 1)
        else:
            delay_packets.append((t + delay_cap, 1))  # Delayed original

    upload_trace = [item for item in upload_trace if item not in used_uploads]
    return sorted(output_trace + delay_packets, key=lambda x: x[0])

def cost_calc(orig_trace, alt_trace):
    '''calculate the bandwidth and latency overhead for download traces'''
    dummy_padding = len(alt_trace) - len(orig_trace)

    latency_cost = 0.0
    sending_time = 0.0
    last_packet_sent = 0
    last_packet_latency = 0.0

    # Extract just the times from the labeled alt_trace
    alt_times = [p[0] for p in alt_trace]

    for t in orig_trace:
        # Find next available packet in sending schedule
        available = alt_times[last_packet_sent:]
        for p in available:
            if(p >= t):
                sending_time = p
                last_packet_sent = alt_times.index(p)+1
                break

        latency_cost += (sending_time - t)
        last_packet_latency = (sending_time - t)

    return (dummy_padding, latency_cost, last_packet_latency)


def cost_calc_max_latency(orig_trace, alt_trace):
    '''calculates latency overhead for upload trace using a more pessimistic method'''
    dummy_padding = len(alt_trace) - len(orig_trace)
    
    latency_cost = 0.0
    sending_time = 0.0
    last_packet_sent = 0
    last_packet_latency = 0.0
    max_packet_latency = 0.0
    counter = 0
    location = 0
    for t in orig_trace:
        #find next available packet in sending schedule
        alt_times = [p[0] for p in alt_trace]
        available = alt_times[last_packet_sent:]

        for p in available:
            if(p > t or p == t):
                sending_time = p
                last_packet_sent = alt_times.index(p) + 1
                break
        
        latency_cost += (sending_time - t)
        
        #find packet with largest delay
        if((sending_time - t) > max_packet_latency and counter > 10):
            max_packet_latency = (sending_time - t)
            location = counter
        counter += 1
        last_packet_latency = (sending_time-t)

    
    return max_packet_latency, location


def simulate(file_name):
    trace = get_trace(args.source_path + str(file_name), CUTOFF_TIME, CUTOFF_LENGTH)
    website = int(file_name.split('_')[1])
    
    #get download and upload separately
    download_packets = get_download_packets(trace)
    upload_packets = get_upload_packets(trace)

    if upload_packets[0] <= download_packets[0]: first_pkt = upload_packets[0] 
    else: first_pkt = download_packets[0]
    
    first_interest = upload_packets[0]
    original_bandwidth = len(upload_packets) + len(download_packets)

    #get defended traces
    padded_download = regulator_download(download_packets)
    upload_packets_tagged = [(t, 1) for t in upload_packets]
    padded_upload = regulator_upload_full(padded_download, upload_packets_tagged)

    padded_bandwidth = len(padded_download) + len(padded_upload)

    #calculate latency overhead
    _, _, download_latency_overhead = cost_calc(download_packets, padded_download) 
    upload_latency_overhead, _ = cost_calc_max_latency(upload_packets, padded_upload)
    latency_overhead = download_latency_overhead + upload_latency_overhead

    download_packets = padded_download
    upload_packets = padded_upload


    both_output = sorted(download_packets + upload_packets, key=lambda x: x[0])

    # balance outgoing vs incoming by inserting dummy incoming at random times
    incoming_count = sum(1 for _, d in both_output if d == -2)
    outgoing_count = sum(1 for _, d in both_output if d == 2)

    if outgoing_count > incoming_count:
        needed_dummies = outgoing_count - incoming_count
        existing_times = [t for t, _ in both_output]
        existing_times_set = set(existing_times)

        for _ in range(needed_dummies):
            sampled_time = random.choice(existing_times)
            # add tiny jitter to ensure uniqueness
            while sampled_time in existing_times_set:
                sampled_time += random.uniform(0.0001, 0.001)
            both_output.append((sampled_time, -2))
            existing_times_set.add(sampled_time)

    both_output = sorted(both_output, key=lambda x: x[0])
    # print(f"Added {needed_dummies} dummy incoming packets at random times to balance.")

    for idx, (time, direction) in enumerate(both_output):
        if direction == -2:
            if time == 0.0:
                #postpone 
                for packet, (t, d) in enumerate(both_output):
                    if t == 0.0 and d == 2:
                        new_time = time + 0.00005
                        both_output[idx] = (new_time, -2)
                        break
                    elif d == 2:
                        both_output.pop(packet)
                        both_output.insert(0, (0.0, 2))  # insert dummy outgoing at start
                        both_output[idx + 1] = (0.00005, -2)  # postpone incoming
                        
                # print(f"Postponed first dummy data to {new_time} ")
            else:
                for packet, (_, d) in enumerate(both_output):
                    if d == 2:
                        removed_packet = both_output.pop(packet)
                        # print(f"Removed existing dummy outgoing")
                        break
                #insert interest slightly before
                new_time = time - 0.00001
                both_output.insert(idx, (new_time, 2))
                # print(f"Inserted dummy outgoing at time {new_time} before first dummy incoming at {time}.")
            break
        elif direction == 2:
            break

    both_output = sorted(both_output, key=lambda x: x[0])
    #output to file
    path = args.output_path + str(file_name)
    with open(path, 'w') as w:
        for p in both_output:
            w.write(str(p[0]) + '\t' + str(p[1]) + '\n')

    if(SAVE_PICKLE):
        signed_trace = [np.float32(t * np.sign(d)) for t, d in both_output]

        if len(signed_trace) > 5000:
            padded_signed_trace = signed_trace[:5000]
        else:
            padded_signed_trace = signed_trace + [0.0] * (5000 - len(signed_trace))
        return np.asarray(padded_signed_trace), np.int64(website), np.asarray(signed_trace)


if __name__ == '__main__':   
    print(args)
    file_list = sorted([f for f in listdir(args.source_path) if isfile(join(args.source_path, f))])
    print(len(file_list))
    
    p = Pool(args.n_processes)
    
    if(SAVE_PICKLE):
        all_indiv_streams = []
        all_indiv_streams = list(tqdm(p.imap(simulate, file_list), total=len(file_list)))
        all_indiv_streams_real = []
        for x in all_indiv_streams:
            if x is not None:
                all_indiv_streams_real.append(x)
        all_indiv_streams = all_indiv_streams_real

        website_list = [x[1] for x in all_indiv_streams]
        trace_list = [x[0] for x in all_indiv_streams] 
        unpadded_trace_list = [x[2] for x in all_indiv_streams] 
        
        output_pkl(trace_list, website_list, args.output_path) 

        # Group traces by website
        traces_by_website = defaultdict(list)
        for trace, website in zip(unpadded_trace_list, website_list):
            traces_by_website[website].append(trace)

        # Save one npz file per website 
        for website, traces in traces_by_website.items():
            out_dict = {website: traces}
            out_path = os.path.join(args.output_path, f"website_{website}_processed.npz")  
            with open(out_path, 'wb') as f:
                pickle.dump(out_dict, f)

    else:
        list(tqdm(p.imap(simulate, file_list), total=len(file_list)))

    #to run code, ensure that you are executing from the RegulaTor-main directory
    #creating results directory: mkdir results/nodef
                                #mkdir results/nodef_unstable
                                #mkdir results/andana
                                #mkdir results/andana_unstable
    #cmd format: cc_regulator.py -c [config name] <traces path>
    #to get defended perfect stable dataset: cc_regulator.py "../../txt_datasets/nodef/" results/nodef/
    #to get defended perfect unstable dataset: cc_regulator.py "../../txt_datasets/nodef_unstable/" results/nodef_unstable/
    #to get defended andana stable dataset: cc_regulator.py "../../txt_datasets/andana/" results/andana/
    #to get defended andana unstable dataset: cc_regulator.py "../../txt_datasets/andana_unstable/" results/andana_unstable/
