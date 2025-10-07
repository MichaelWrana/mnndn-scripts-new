import pandas as pd
import numpy as np
import  sys

from util.constant import *

try:
    network_log_paths = []
    if len(sys.argv) == 2:
        network_log_paths.append(RESULT_DATA_DIR / f"experiment_{sys.argv[1]}/network_log.csv")
        if not network_log_paths[0].exists():
            raise FileNotFoundError("Error: Cannot find experiment log file")
    elif sys.argv[1] == "range":
        for i in range(int(sys.argv[2]), int(sys.argv[3])):
            network_log_paths.append(RESULT_DATA_DIR / f"experiment_{i}/network_log.csv")
            if not network_log_paths[i].exists():
                print(f"Warning: Experiment log file: {network_log_paths.absolute()} missing.  skipping...")
                del network_log_paths[-1]
    elif sys.argv[1] == "list":
        experiment_nums_list = [int(arg) for arg in sys.argv[2:]]
        print(experiment_nums_list)
        for i,experiment_num in enumerate(experiment_nums_list):
            network_log_paths.append(RESULT_DATA_DIR / f"experiment_{experiment_num}/network_log.csv")
            if not network_log_paths[i].exists():
                print(f"Warning: Experiment log file: {network_log_paths.absolute()} missing.  skipping...")
                del network_log_paths[-1] 
except Exception as e:
    print(e)
    raise TypeError("Could not parse command-line args")

network_log_summary = {
    "total_recv":0,
    "total_retransmit":0,
    "retransmit":[],
    "rtt": []
}
for network_log_path in network_log_paths:
    network_log = pd.read_csv(network_log_path, usecols=["Segments received","Retransmitted segments","RTT"])
    received = network_log["Segments received"]
    retransmitted = network_log["Retransmitted segments"]
    total_received = received.sum()
    total_retransmitted = retransmitted.sum()

    rtt_total = []
    for rtt_set in network_log["RTT"]:
        try:
            rtt = float(rtt_set.split("/")[1])
            rtt_total.append(rtt)
        except AttributeError:
            rtt_total.append(-1)
            continue

    rtt_mean = np.mean([x for x in rtt_total if x != -1])
    rtt_total = [rtt_mean if rtt == -1 else rtt for rtt in rtt_total]

    network_log_summary["total_recv"] = network_log_summary["total_recv"] + total_received
    network_log_summary["total_retransmit"] = network_log_summary["total_retransmit"] + total_retransmitted
    network_log_summary["retransmit"] = network_log_summary["retransmit"] + [np.count_nonzero(retransmitted)/len(retransmitted)]
    network_log_summary["rtt"] = network_log_summary["rtt"] + [np.average(rtt_total)]

    print(f"Summary statistics for {network_log_path.parts[-2]}:")
    print(f"\tTotal segments received: {total_received}")
    print(f"\tTotal segments retransmitted: {total_retransmitted}")
    print(f"\tRetransmissions (%) (weighted sum): {total_retransmitted/total_received*100:.2f}%")
    print(f"\tRetransmissions (%) (flat sum): {np.count_nonzero(retransmitted)/len(retransmitted)*100:.2f}%")
    print(f"\tRTT (weighted average): {np.average(rtt_total, weights=received):.2f}ms")
    print(f"\tRTT (flat average): {np.mean(rtt_total):.2f}ms")
    print(f"\tRTT (variance): {np.var(rtt_total):.2f}ms")

print(network_log_summary["rtt"])

print("Overall Summary of Packet Transmissions")
print(f"\tTotal segments received: {network_log_summary["total_recv"]:,}")
print(f"\tTotal segments retransmitted: {network_log_summary["total_retransmit"]:,}")
print(f"\tRetransmissions (%) (flat sum): {np.mean(network_log_summary["retransmit"])*100:.2f}%")
print(f"\tRTT (flat average): {np.mean(network_log_summary["rtt"]):.2f}ms")