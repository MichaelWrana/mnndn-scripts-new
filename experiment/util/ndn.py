from minindn.util import getPopen
from signal import SIGINT
from difflib import SequenceMatcher

import subprocess
import pathlib
import csv
import threading
import json
import time
import random

from util.misc import *

def safe_putchunks(host, network_address, file_location, verbose=True):
    success_message = "Published"
    error_message = "Error"

    cmd = f"stdbuf -oL cat {file_location} | ndnputchunks {network_address} &"

    if verbose:
        print(cmd)

    
    proc = getPopen(
        host,
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
        )

    for line in proc.stdout:

        if success_message.casefold() in line.casefold():
            if verbose:
                print(line)
            return proc

        if error_message.casefold() in line.casefold():
            raise RuntimeError(f"ndnputchunks encountered an error trying to publish chunks: \n {line}")

    code = proc.poll()
    raise RuntimeError(f"ndnputchunks exited unexpectedly: \n {code}")

def safe_catchunks(host, network_address, file_location, verbose=None, print_header=False):
    success_message = "All segments have been received"
    error_message = "Error"

    result = host.cmd(f"ndncatchunks -r -1 {network_address} > {file_location}")

    if error_message.casefold() in result.casefold():
        raise RuntimeError(f"Ndncatchunks encountered an error trying to download chunks: \n {result}")
    
    if verbose is not None and verbose != False:
        headers = not verbose.exists()
        with verbose.open("a") as f:
            log_cat_result(result, f, headers, print_header)

    return file_location

def start_packet_recording(host, interface_name, out_file, verbose=True):
    success_message = "listening on"
    error_message = "error"
    
    cmd = f"tcpdump -U -i {interface_name} -w {out_file}.pcap"

    proc = getPopen(
        host,
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in proc.stdout:
        if success_message.casefold() in line.casefold():
            if verbose:
                print(line)
            return proc
        
        if error_message.casefold() in line.casefold():
            raise RuntimeError(f"tcpdump encountered an error trying to start packet recording: {line}")
    
    message = proc.poll()
    raise RuntimeError(f"tcpdump exited unexpectedly: \n {code}")

def safe_stop_process(proc):
    proc.send_signal(SIGINT)
    try:
        proc.wait(timeout=5)
    except Exception:
        # harsher forced shutdown
        proc.terminate()
        try:
            proc.wait(timeout=2)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

def host_website(server_obj, server_prefix, har_config, verbose=True):
    file_process_list = []

    for path in har_config.keys():
        #print(f"Hosting {path.name} on {target_server_name}")
        file_process = safe_putchunks(
            host = server_obj,
            network_address = f"{server_prefix}/{path.name}",
            file_location = f"{path.absolute()}",
            verbose = verbose
        )
        file_process_list.append(file_process)
    
    return file_process_list

def make_dns_request(user, dns, query, answer):

    dns_answer = {
        "name": f"{query}",
        "type": f"A",
        "ttl": 300,
        "data": answer
    }

    dns.cmd(f"echo '{json.dumps(dns_answer)}' > answer.txt")

    p = safe_putchunks(
        dns,
        f"ndn/{dns.name}-site/{dns.name}/{query}",
        "answer.txt"
    )  

    safe_catchunks(
        user,
        f"ndn/{dns.name}-site/{dns.name}/{query}",
        "/dev/null",
    )

    p.kill()

    return

class NDNReplayer:
    def __init__(self, ndn_host, server_prefix, webpage_name, har_config, log_file=None):
        self.ndn_host = ndn_host
        self.server_prefix = server_prefix
        self.webpage_name = webpage_name
        self.har_config = har_config
        self.log_file = log_file

    def match_url(self, browser_url_request):
        exact_match = [path for path, har_url in self.har_config.items() if har_url == browser_url_request]
        
        if len(exact_match) != 0:
            return exact_match[-1]

        best_path, best_score = None, -1
        for path, har_url in self.har_config.items():
            score = SequenceMatcher(None, har_url.casefold(), browser_url_request.casefold()).ratio()
            if score > best_score:
                best_path, best_score = path, score
        
        return best_path

    def ndn_handler(self, route):

        resource_path = self.match_url(route.request.url)

        if resource_path is not None:
            print(f"Trying to cat {resource_path.name}")
            _ = safe_catchunks(
                host = self.ndn_host,
                network_address = f"{self.server_prefix}/{resource_path.name}",
                file_location = "/dev/null",
                verbose = self.log_file,
                print_header=False
            )
        else:
            pass

        route.fallback()