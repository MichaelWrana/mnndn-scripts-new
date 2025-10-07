import random
import threading

from pathlib import Path
from typing import Iterable
from minindn.util import getPopen

from util.constant import *
from util.ndn import *

# this function gets a list of all the resource files in a folder (e.g. google.com_1, google.com_2, etc...)  Also checks subfolders
def get_resource_files(root, min_bytes, exclude_substrs=[], include_substrs=[]):
    ex = [s.lower() for s in exclude_substrs] if exclude_substrs else []
    inc = [s.lower() for s in include_substrs] if include_substrs else []
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if any(s in name for s in ex):
            continue
        if any(s in name for s in inc):
            try:
                if p.stat().st_size > min_bytes:
                    out.append(p.resolve())
            except OSError:
                continue
    return out

# this function takes a list of NDN server objects, and a list of paths to resources
#(e.g. [/webpage_data/google.com/google.com_0, /webpage_data/google.com/google.com_1]
# hosts those resources on a random server chosen from the server list
# returns the NDN address of the resource that was hosted, and the process object running the hosting of the resource
def start_background_servers(bg_servers, bg_resources):
    bg_processes = []
    bg_resource_addresses = []
    for i, resource in enumerate(bg_resources):
        server = random.choice(bg_servers)
        resource_addr = f"ndn/{server.name}-site/{server.name}/{resource.name}"

        proc = safe_putchunks(server, resource_addr, resource.absolute())

        bg_processes.append(proc)
        bg_resource_addresses.append(resource_addr)
    
    return bg_processes, bg_resource_addresses

# determines weights for how often particular resources are requested by background users
# target_weight and bg_weight configure how likely a user is to request a random resource vs the one we are currently evaluating
# returns a list containing the names of resources this user will request, and the chance to request each one
def generate_config(target_resources, bg_resources):
    target_weight=1
    bg_weight=1

    names = []
    weights = []
    for resource in target_resources:
        names.append(resource)
        weights.append(target_weight)

    for resource in bg_resources:
        names.append(resource)
        weights.append(bg_weight)

    total = sum(weights)
    weights = [(weight/total) * 100.0 for weight in weights]

    return names, weights
    

# starts a user in the background as a thread who will periodically request resources from the network
# avg_interval_ms * 0.5 and *1.5 is the delay between requests
# names is the names of each resource this user will try to request
# weights is how likely they are to choose it (sum of weights = 100)
# returns object to tell this background user to stop, and the thread to kill them
def start_background_traffic_thread(client, names, weights, avg_interval_ms, dump_file_path):
    avg_interval = avg_interval_ms / 1000.0
    stop = threading.Event()

    def worker():
        while not stop.is_set():
            name = random.choices(names, weights=weights, k=1)[0]
            try:
                bg_process = safe_catchunks(
                    client,
                    name,
                    "/dev/null",
                    dump_file_path,
                    False
                )
            except RuntimeError:
                break
            stop.wait(avg_interval * random.uniform(0.5, 1.5))
            

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return stop, t

# hosts is all the devices in the NDN network
# sets up num_bg_users to request random resources every avg_interval_ms
# the network will host up to max_resources additional files.
# target server is special, we will try and make sure 15% of this webpage is randomly requested by background users
# will not re-host the files, since they are already active on the network
def start_background_traffic(hosts, num_bg_users, avg_interval_ms, max_resources, target_server, target_url):

    print("Starting Background Traffic...")

    bg_resources = get_resource_files(SITE_DATA_DIR, min_bytes=150*1024,exclude_substrs=["har", target_url], include_substrs=["_"])
    bg_resources = random.sample(bg_resources, min(max_resources, len(bg_resources)))

    target_resources = get_resource_files(SITE_DATA_DIR / target_url, min_bytes=0, exclude_substrs=["har"], include_substrs=["_"])
    target_resources = random.sample(target_resources, int(len(target_resources)*0.15)+1)
    target_resource_addresses = [f"ndn/{target_server.name}-site/{target_server.name}/{resource.name}" for resource in target_resources]

    all_servers = [host for host in hosts if "s" in host.name and host.name != target_server.name]
    all_users = [host for host in hosts if "u" in host.name and host.name != "pu"]

    bg_server_processes, bg_resource_addresses = start_background_servers(all_servers, bg_resources)

    bg_config_dir = BG_LOG
    bg_config_dir.mkdir(parents=True, exist_ok=True)

    client_threads = []
    for client in all_users[:num_bg_users]:
        config_path = bg_config_dir / f"{client.name}.conf"

        names, weights = generate_config(target_resource_addresses, bg_resource_addresses)

        proc = start_background_traffic_thread(client, names, weights, avg_interval_ms, config_path)
        client_threads.append(proc)


    return bg_server_processes, client_threads

# kills bg user processes
def stop_background_traffic(server_processes, client_threads):
    for proc in server_processes:
        safe_stop_process(proc)
    
    for stop, t in client_threads:
        stop.set()
        t.join()
    
    return