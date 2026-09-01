import numpy as np 
import argparse
import logging
import sys
import pandas as pd
import os
from os.path import join
from os import makedirs
import constants as ct
from time import strftime
import matplotlib.pyplot as plt
import multiprocessing as mp
import configparser
import time
import datetime
from pprint import pprint
import pickle
from collections import defaultdict


logger = logging.getLogger('ranpad2')
def init_directories():
    # Create a results dir if it doesn't exist yet
    if not os.path.exists(ct.RESULTS_DIR):
        makedirs(ct.RESULTS_DIR)

    # Define output directory
    timestamp = strftime('%m%d_%H%M%S')
    output_dir = join(ct.RESULTS_DIR, 'cc_front'+timestamp)
    makedirs(output_dir)

    return output_dir

def config_logger(args):
    # Set file
    log_file = sys.stdout
    if args.log != 'stdout':
        log_file = open(args.log, 'w')
    ch = logging.StreamHandler(log_file)

    # Set logging format
    ch.setFormatter(logging.Formatter(ct.LOG_FORMAT))
    logger.addHandler(ch)

    # Set level format
    logger.setLevel(logging.INFO)

def parse_arguments():

    conf_parser = configparser.RawConfigParser()
    conf_parser.read(ct.CONFIG_FILE)

    parser = argparse.ArgumentParser(description='It simulates adaptive padding on a set of web traffic traces.')

    parser.add_argument('p',
                        metavar='<traces path>',
                        help='Path to the directory with the traffic traces to be simulated.')
    parser.add_argument('-format',
                        metavar='<suffix of a file>',
                        default = '.npz',
                        help='suffix of a file.')
    parser.add_argument('-c', '--config',
                        dest="section",
                        metavar='<config name>',
                        help="Adaptive padding configuration.",
                        choices= conf_parser.sections(),
                        default="default")

    parser.add_argument('--log',
                        type=str,
                        dest="log",
                        metavar='<log path>',
                        default='stdout',
                        help='path to the log file. It will print to stdout by default.')

    # parser.add_argument('--client_dummy_pkt_num', 
    #                     type=int, 
    #                     default=500)

    # parser.add_argument('--server_dummy_pkt_num', 
    #                     type=int, 
    #                     default=600)

    # parser.add_argument('--start_padding_time', 
    #                     type=int, 
    #                     default=2)

    # parser.add_argument('--max_wnd', 
    #                     type=float, 
    #                     default=6)



    args = parser.parse_args()
    config = dict(conf_parser._sections[args.section])
    config_logger(args)
    return args,config

def load_trace(fdir, trace_id):
    site_id = int(os.path.basename(fdir).split('_')[1])
    with open(fdir, 'rb') as f:
        site_data = pickle.load(f)

        trace = site_data[site_id][trace_id]
        # print (trace)
        timestamps = np.abs(trace)
        directions = np.where(np.signbit(trace), -1, 1)

    return np.vstack((timestamps, directions)).T, trace_id, site_id

def dump(trace, fname):
    global output_dir
    with open(join(output_dir,fname), 'w') as fo:
        for packet in trace:
            fo.write("{:.4f}".format(packet[0]) +'\t' + "{}".format(int(packet[1]))\
                + ct.NL)

def simulate(finfo):
    fdir, trace_id = finfo
    if not os.path.exists(fdir):
        print(f"Missing: {fdir}")
        return
    
    np.random.seed(datetime.datetime.now().microsecond)
    original_trace, trace_id, site_id = load_trace(fdir, trace_id)
    padded_trace = RP(original_trace)

    # original_fname = f'site_{site_id}_trace_{trace_id}.txt'
    # dump(original_trace, original_fname)
    # print("trace",trace)
    fname = f'site_{site_id}_trace_{trace_id}.txt'
    dump(padded_trace, fname)

    padded_signed = convert_to_signed_trace(padded_trace)
    return site_id, (trace_id, padded_signed)

def RP(trace):
    # format: [[time, pkt],[...]]
    # trace, cpkt_num, spkt_num, cwnd, swnd
    global client_dummy_pkt_num 
    global server_dummy_pkt_num 
    global min_wnd 
    global max_wnd 
    global start_padding_time
    global client_min_dummy_pkt_num
    global server_min_dummy_pkt_num
    
    # print("min_wnd in RP",min_wnd)
    
    client_wnd = np.random.uniform(min_wnd, max_wnd)
    server_wnd = np.random.uniform(min_wnd, max_wnd)
    if client_min_dummy_pkt_num != client_dummy_pkt_num:
        client_dummy_pkt = np.random.randint(client_min_dummy_pkt_num,client_dummy_pkt_num)
        # print(f"num of interests used: {client_dummy_pkt}")
    else:
        client_dummy_pkt = client_dummy_pkt_num
    # if server_min_dummy_pkt_num != server_dummy_pkt_num:
    #     server_dummy_pkt = np.random.randint(server_min_dummy_pkt_num,server_dummy_pkt_num)
    # else:
    #     server_dummy_pkt = server_dummy_pkt_num

    #generate more data packets than interest packets
    server_dummy_pkt = np.random.randint(client_dummy_pkt,server_dummy_pkt_num)

    logger.debug("client_wnd:",client_wnd)
    logger.debug("server_wnd:",server_wnd)
    logger.debug("client pkt:", client_dummy_pkt)
    logger.debug("server pkt:", server_dummy_pkt)

    if(server_dummy_pkt < client_dummy_pkt):
        print(f"More interests than datas")

    first_incoming_pkt_time = trace[np.where(trace[:,1] <0)][0][0]

    last_pkt_time = trace[-1][0]    

    if start_padding_time > last_pkt_time:
        # print(f"Start of padding time ({start_padding_time}) exceeds last packet time ({last_pkt_time}). Returning original trace")
        return trace
    
    client_timetable = getTimestamps(client_wnd, client_dummy_pkt)

    #this may cut off packets
    client_timetable = client_timetable[np.where(start_padding_time+client_timetable[:,0] <= last_pkt_time)]

    server_timetable = getTimestamps(server_wnd, server_dummy_pkt)

    server_timetable = server_timetable[np.where(start_padding_time+server_timetable[:,0] <= last_pkt_time)]

      #to ensure that we have more data packets even if some get cut off  
    while len(server_timetable) < (len(client_timetable) + 1):
        extra_needed = len(client_timetable) - len(server_timetable) + 1
        extra_times = sorted(np.random.rayleigh(server_wnd, extra_needed))
        extra_times = np.reshape(extra_times, (len(extra_times), 1))
        
        # only keep the valid extra packets
        extra_times = extra_times[np.where(start_padding_time + extra_times[:,0] <= last_pkt_time)]
        
        if len(extra_times) > 0:
            server_timetable = np.vstack([server_timetable, extra_times])

    if len(client_timetable) > len(server_timetable):
        print(f"STILL PROBLEM Difference in timetables, interest: {len(client_timetable)}, data: {len(server_timetable)}")

    first_server_pkt_time = np.min(server_timetable[:, 0])
    
    #if no interest packets, add one new at the beginning
    if client_timetable.size == 0:
        first_pkt_time = trace[0][0]

        #avoid range errors if first dummy data packet is added before any original packets
        if first_pkt_time > first_server_pkt_time:
            first_pkt_time = 0.0 

        dummy_interest_time = np.random.uniform(first_pkt_time, first_server_pkt_time)

        client_timetable = np.array([[dummy_interest_time]])

    #if trace started with data packets, create a new interest and add it to other interests
    if client_timetable[0][0] >= first_server_pkt_time:
        first_pkt_time = trace[0][0]

        if first_pkt_time > first_server_pkt_time:
            first_pkt_time = 0.0

        # print("used to start with interest: ",client_timetable[0][0] )
        dummy_interest_time = np.random.uniform(first_pkt_time, first_server_pkt_time)

        client_timetable_row = np.array([[dummy_interest_time]])
        client_timetable = np.vstack([client_timetable_row, client_timetable])
        # print(" new first client: ", client_timetable[0][0], "server: ", first_server_pkt_time) 

    client_pkts = np.concatenate((client_timetable, 2*np.ones((len(client_timetable),1))),axis = 1)  
    server_pkts = np.concatenate((server_timetable, -2*np.ones((len(server_timetable),1))),axis = 1)

    noisy_trace = np.concatenate( (trace, client_pkts, server_pkts), axis = 0)
    noisy_trace = noisy_trace[ noisy_trace[:, 0].argsort(kind = 'mergesort')]
    return noisy_trace

def getTimestamps(wnd, num):
    # timestamps = sorted(np.random.exponential(wnd/2.0, num))   
    # print(wnd, num)
    # timestamps = sorted(abs(np.random.normal(0, wnd, num)))
    timestamps = sorted(np.random.rayleigh(wnd,num))
    # print(timestamps[:5])
    # timestamps = np.fromiter(map(lambda x: x if x <= wnd else wnd, timestamps),dtype = float)
    return np.reshape(timestamps, (len(timestamps),1))

def parallel(flist, n_jobs = 20):
    with mp.Pool(n_jobs) as pool:
        results = pool.map(simulate, flist)
    return results

def convert_to_signed_trace(trace):
    times = trace[:, 0]
    dirs = trace[:, 1]
    signed_trace = times * dirs
    return signed_trace 

def save_traces_npz_format(site_id, traces_dict, label):
    global output_dir
    filename = f"website_{site_id}_{label}.npz"
    filepath = join(output_dir, filename)
    with open(filepath, 'wb') as f:
        pickle.dump({site_id: traces_dict}, f)


if __name__ == '__main__':
    global client_dummy_pkt_num 
    global server_dummy_pkt_num 
    global client_min_dummy_pkt_num
    global server_min_dummy_pkt_num
    global max_wnd
    global min_wnd 
    global start_padding_time
    
    args, config = parse_arguments()
    logger.info(args)

    client_min_dummy_pkt_num = int(config.get('client_min_dummy_pkt_num',1))

    server_min_dummy_pkt_num = int(config.get('server_min_dummy_pkt_num',1))
    client_dummy_pkt_num = int(config.get('client_dummy_pkt_num',300))
    server_dummy_pkt_num = int(config.get('server_dummy_pkt_num',300))
    start_padding_time = int(config.get('start_padding_time', 0))
    max_wnd = float(config.get('max_wnd',10))

    # client_dummy_pkt_num = args.client_dummy_pkt_num
    # server_dummy_pkt_num = args.server_dummy_pkt_num
    # start_padding_time = args.start_padding_time
    # max_wnd = args.max_wnd
    min_wnd = float(config.get('min_wnd',10))
    
    MON_SITE_NUM = int(config.get('mon_site_num', 100))
    MON_INST_NUM = int(config.get('mon_inst_num', 100))

    site_ids = 100
    traces_per_site = 100
    flist  = []

    # Init run directories
    output_dir = init_directories()
    logger.info("Traces are dumped to {}".format(output_dir))
    start = time.time()

    for site_id in range(MON_SITE_NUM):
        fpath = join(args.p, f"website_{site_id}_processed{args.format}")
        if not os.path.exists(fpath):
            print(f"File missing for site {site_id}: {fpath}")
            continue

        with open(fpath, 'rb') as f:
            site_data = pickle.load(f)

        trace_list = site_data.get(site_id, [])
        trace_count = len(trace_list)

        if trace_count != MON_INST_NUM:
            print(f"For site {site_id} only {trace_count}")

        for trace_id in range(trace_count):
            flist.append((fpath, trace_id))

    site_traces = defaultdict(dict)

    for i, f in enumerate(flist):
        logger.debug('Simulating {}'.format(f))
        if i % 2000 == 0:
            print(f"Done for inst {i}", flush=True)

        result = simulate(f)
        if result is None:
            continue
        site_id, (trace_id, padded_signed) = result
        site_traces[site_id][trace_id] = padded_signed

    # Save to .npz format
    for site_id, trace_dict in site_traces.items():
        trace_list = [trace_dict[i] for i in sorted(trace_dict.keys())]
        save_traces_npz_format(site_id, trace_list, label="front")
        print(f"Saved npz for site {site_id}")

    #to run code, ensure that you are execution from the front directory
    #cmd format: cc_front.py -c [config name] <traces path>
    #to get defended perfect stable dataset: cc_front.py -c t1 "../../raw_datasets/nodef/"  
    #to get defended perfect unstable dataset: cc_front.py -c t1 "../../raw_datasets/nodef_unstable/"  
    #to get defended andana stable dataset: cc_front.py -c t1 "../../raw_datasets/andana/"  
    #to get defended andana unstable dataset: cc_front.py -c t1 "../../raw_datasets/andana_unstable/"  
    #resulting datasets will be saved into the subdirectory of the main one called "results"

