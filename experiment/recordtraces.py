import os
import pathlib
import pandas as pd
import time
import argparse

# FIREFOX
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError
from playwright._impl._errors import Error

# MININDN PACKAGES
from mininet.log import setLogLevel, info
from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.nfd import Nfd
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper

# MY HELPERS
from util.ndn import *
from util.andana import *
from util.constant import *
from util.misc import *
from util.bgtraffic import *

def parse_args():
    p = argparse.ArgumentParser(
        description="This is the 'big one' which actually simulates everything over NDN",
        epilog="Additionally Requires input files with locations specified in constant.py\n SITE_DATA_DIR:output folder to dump webpage recordings\n TOP_SITES_PATH: List of domains to visit (Expecting a csv with a header line, urls slugified under 'domain' column)\nRESULT_DATA_DIR: folder where output pcaps will be dumped.  BG_LOG: folder where logs created from background users will be dumped"
        )

    p.add_argument("--config", type=pathlib.Path,default=NETWORK_CONFIG_PATH, help="Location of network mininet config file. For correct behaviour naming convention is: Users must be named u0,...,ui.  Servers must be named s0,...,si.  ANDaNA relays must be named r0,...,ri.  Target user must be named pu and DNS server must be named dns.  ")
    p.add_argument("--dns", action="store_true", help="When set, the user will issue NDN-DNS queries to find server locations")
    p.add_argument("--bgtraffic", action="store_true", help="When set, up to 40 users will periodically fill the network with random data.")
    p.add_argument("--andana", action="store_true", help="When set, primary user routes via andana relays.  Expects relays to be named as r0,...,r9")
    p.add_argument("--maxreplay", type=int, default=100, help="Will skip websites that have been replayed this many times.  (Mainly used for open-world data) (default=100)")
    p.add_argument("--maxpages", type=int, default=100, help="Maximum number of webpages to visit (default=100)")
    p.add_argument("--timeout", type=int, default=45000, help="Maximum time waiting for page to load in ms (default=45000)")
    p.add_argument("--overwrite", action="store_true", help="When set, overwrites existing records and website traces with new recording.  DOES NOT delete pcaps due to high risk. (default=False)")

    args = p.parse_args()

    return p, args


if __name__ == "__main__":
    setLogLevel('info')

    parser, args = parse_args()
    network_config_path = args.config
    max_pages = args.maxpages
    max_replay = args.maxreplay
    timeout = args.timeout

    Minindn.cleanUp()
    Minindn.verifyDependencies()
    os.system("sudo rm -rf /tmp/minindn")
    ndn = Minindn(parser=parser, topoFile=network_config_path.absolute())
    ndn.start()

    print("Starting Routing Daemon on Nodes ...\n")
    start_time = time.time()

    nfds = AppManager(ndn, ndn.net.hosts, Nfd, csSize=5)

    print(f"Daemons Started after {time.time()-start_time:.2f} sec\n")

    print("Computing Routes...\n")
    grh = NdnRoutingHelper(ndn.net, 'udp', 'link-state')
    grh.calculateNPossibleRoutes()

    print(f"Inserted routing tables after {time.time()-start_time:.2f} sec\n")

    webpage_list = pd.read_csv(TOP_SITES_PATH)

    if args.overwrite:
        webpage_list["replay_count"] = 0
        os.system(f"sudo rm {BG_LOG}/*.conf")

    if "load_result" not in webpage_list.columns:
        webpage_list["load_result"] = 0

    RESULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    experiment_dir = next_experiment_dir(RESULT_DATA_DIR)
    experiment_dir.mkdir(parents=True, exist_ok=True)

    visited=0
    needed_timeout=0
    for i, row in webpage_list.iterrows():

        if visited >= max_pages:
            break

        if row["load_result"] != 1 or row["replay_result"] != 1:
            continue

        if row["replay_count"] >= max_replay:
            continue
        
        url = row["domain"]
        
        print(f"Replaying {url}...")

        har_path = SITE_DATA_DIR / f"{url}/{url}.har"
        har_config_path = SITE_DATA_DIR / f"{url}/{url}_har_config.pkl"
        with har_config_path.open('rb') as f:
            har_config = pickle.load(f)
        
        server_name = row["server_assignment"]
        server_prefix = f"ndn/{server_name}-site/{server_name}"
        server_obj = ndn.net[server_name]

        print(f"Hosting {url} on NDN at {server_prefix}...")

        server_process_list = host_website(server_obj, server_prefix, har_config)
        
        for k in ("DISPLAY","WAYLAND_DISPLAY","XAUTHORITY","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS"):
            os.environ.pop(k, None)
        os.environ["HOME"] = "/root"

        if args.bgtraffic:
            server_processes, client_threads = start_background_traffic(
                ndn.net.hosts,
                num_bg_users=40,
                avg_interval_ms=6000,
                max_resources=50,
                target_server=server_obj,
                target_url=url
            )

        pu = ndn.net["pu"]
        tcpdump_proc = start_packet_recording(pu, "pu-eth0", f"{experiment_dir.absolute()}/{url}")

        if args.andana:
            andana_relays = [ndn.net[f"r{i}"] for i in range(10)]
            for user in [pu] + andana_relays:
                user.cmd(f"mkdir -p andana")

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            ctx = browser.new_context(
                service_workers="block",
                extra_http_headers={"Accept-Encoding": "identity"},
            )

            ctx.route_from_har(har_path.absolute(), not_found="abort", update="False")

            if args.andana:
                ndnreplayer = AndanaReplayer(
                    ndn_host = pu,
                    server_prefix = server_prefix,
                    webpage_name = url,
                    har_config = har_config,
                    relays = andana_relays,
                    num_relays = 2
                )
            else:
                ndnreplayer = NDNReplayer(
                    ndn_host=pu,
                    server_prefix=server_prefix,
                    webpage_name=url,
                    har_config=har_config,
                    log_file = experiment_dir / f"network_log.csv"
                )

            ctx.route("**/*", ndnreplayer.ndn_handler)

            page = ctx.new_page()

            if args.dns:
                make_dns_request(pu, ndn.net["dns"], url, server_name)

            try:
                page.goto(f"https://www.{url}", timeout=timeout)
                page.wait_for_load_state("load", timeout=timeout)
            except TimeoutError:
                print("Timeout on Replay.")
                needed_timeout += 1
                pass
            except Error:
                pass
            finally:
                try:
                    if ctx:
                        ctx.close()
                except Exception:
                    pass
                try:
                    if browser:
                        browser.close()
                except Exception:
                    pass
        
        print(f"Finished visitng {url}...cleaning up")

        safe_stop_process(tcpdump_proc)

        if args.andana:
            for user in [pu] + andana_relays:
                user.cmd("sudo rm -rf andana/")

        if args.bgtraffic:
            for stop,_ in client_threads:
                stop.set()

        os.system("killall -15 ndncatchunks")
        os.system("killall -15 ndnputchunks")

        if args.bgtraffic:
            for _, t in client_threads:
                t.join()

        
        webpage_list.loc[i, "replay_count"] += 1
        visited+=1
    
    print(f"Visited {visited} webpages over ndn with {needed_timeout} timeouts")
    print(f"Done in {time.time()-start_time:.2f} sec... cleaning up\n")

    webpage_list.to_csv(TOP_SITES_PATH, index=False)

    ndn.stop()
