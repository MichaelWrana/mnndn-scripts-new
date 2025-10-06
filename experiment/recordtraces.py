import os
import pathlib
import pandas as pd
import time

# FIREFOX
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError

# MININDN PACKAGES
from mininet.log import setLogLevel, info
from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.nfd import Nfd
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper
# MY HELPERS

from util.ndn import *
from util.constant import *
from util.misc import *
from util.bgtraffic import *


if __name__ == "__main__":
    setLogLevel('info')



    Minindn.cleanUp()
    Minindn.verifyDependencies()
    os.system("sudo rm -rf /tmp/minindn")
    ndn = Minindn(topoFile=NETWORK_CONFIG_DIR.absolute())
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

    RESULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    experiment_dir = next_experiment_dir(RESULT_DATA_DIR)
    experiment_dir.mkdir(parents=True, exist_ok=True)

    #special_row = [{"domain":"apache.org", "load_result":1, "replay_result":1, "server_assignment":"s8"}]

    visited=0
    needed_timeout=0
    for idx, row in webpage_list.iterrows():
    #for idx, row in enumerate(special_row):

        if visited >= 100:
            break

        if row["load_result"] != 1 or row["replay_result"] != 1:
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

        #server_processes, client_threads = start_background_traffic(ndn.net.hosts, 40, 100, server_obj, url)

        pu = ndn.net["pu"]
        tcpdump_proc = start_packet_recording(pu, "pu-eth0", f"{experiment_dir.absolute()}/{url}")

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            ctx = browser.new_context(
                service_workers="block",
                extra_http_headers={"Accept-Encoding": "identity"},
            )

            ctx.route_from_har(har_path.absolute(), not_found="abort", update="False")
            
            ndnreplayer = NDNReplayer(
                ndn_host=pu,
                server_prefix=server_prefix,
                webpage_name=url,
                har_config=har_config,
                log_file = experiment_dir / f"network_log.csv"
            )

            ctx.route("**/*", ndnreplayer.ndn_handler)

            page = ctx.new_page()

            try:
                page.goto(f"https://www.{url}", timeout=REPLAY_TIMEOUT)
                page.wait_for_load_state("load", timeout=REPLAY_TIMEOUT)
            except TimeoutError:
                print("Timeout on Replay.")
                needed_timeout += 1
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

        for proc in server_process_list:
            safe_stop_process(proc)

        #stop_background_traffic(server_processes, client_threads)

        os.system("killall -15 ndnputchunks")

        visited+=1
    
    print(f"Visited {visited} webpages over ndn with {needed_timeout} timeouts")
    print(f"Done in {time.time()-start_time:.2f} sec... cleaning up\n")

    ndn.stop()