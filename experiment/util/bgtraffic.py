import random
import threading

from pathlib import Path
from typing import Iterable

from util.constant import *
from util.ndn import *

def find_large_files(root, min_bytes= 200*1024, exclude_substrs=["har"]):
    ex = [s.lower() for s in exclude_substrs] if exclude_substrs else []
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if any(s in name for s in ex):
            continue
        try:
            if p.stat().st_size > min_bytes:  # strictly larger than 500 KiB by default
                out.append(p.resolve())
        except OSError:
            # unreadable or vanished; skip
            continue
    return out

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

def generate_config(config_path, target_resources, bg_resources):
    target_weight=2
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
    

def start_background_traffic_thread(client, names, weights, interval_ms):
    period = interval_ms / 1000.0
    stop = threading.Event()

    def worker():
        while not stop.is_set():
            name = random.choices(names, weights=weights, k=1)[0]
            safe_catchunks(client, name, "/dev/null", verbose=BG_LOG / f"{client.name}.csv", )
            stop.wait(period)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return stop, t


def start_background_traffic(hosts, num_bg_users, interval_ms, target_server, target_url):

    bg_resources = find_large_files(SITE_DATA_DIR, exclude_substrs=["har"])
    target_resources = [f"ndn/{target_server.name}-site/{target_server.name}/{resource.name}" for resource in bg_resources if target_url in str(resource)]
    bg_resources[:]  = [resource for resource in bg_resources if target_url not in str(resource)]

    bg_servers = [host for host in hosts if "s" in host.name and host.name != target_server.name]
    bg_clients = [host for host in hosts if "u" in host.name and host.name != "pu"]

    server_processes, bg_resources = start_background_servers(bg_servers, bg_resources)

    bg_config_dir = BG_LOG
    bg_config_dir.mkdir(parents=True, exist_ok=True)

    client_threads = []
    for client in bg_clients[:num_bg_users]:
        config_path = bg_config_dir / f"{client.name}.conf"
        names, weights = generate_config(config_path, target_resources, bg_resources)

        proc = start_background_traffic_thread(client,names, weights, interval_ms)
        client_threads.append(proc)


    return server_processes, client_threads

def stop_background_traffic(server_processes, client_threads):
    for proc in server_processes:
        safe_stop_process(proc)
    
    for stop, t in client_threads:
        stop.set()
        t.join(2.0)
    
    return