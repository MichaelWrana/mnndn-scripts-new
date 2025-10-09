# GLOBAL PYTHON PACKAGES
import time
import os

from pathlib import Path

# MININDN PACKAGES
from mininet.log import setLogLevel, info
from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.nfd import Nfd
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper

from playwright.sync_api import sync_playwright
from playwright._impl._errors import TimeoutError

# MY LOCAL PACKAGES
from util.ndn import *
from util.misc import *
from util.bgtraffic import *
from util.andana import *

if __name__ == '__main__':
    setLogLevel('info')

    Minindn.cleanUp()
    Minindn.verifyDependencies()
    os.system("sudo rm -rf /tmp/minindn")
    ndn = Minindn(topoFile="line.conf")
    ndn.start()

    print("Starting Routing Daemon on Nodes ...\n")
    start_time = time.time()

    nfds = AppManager(ndn, ndn.net.hosts, Nfd, csSize=5)

    print(f"Daemons Started after {time.time()-start_time:.2f}sec\n")

    print("Calculating Routes...\n")
    grh = NdnRoutingHelper(ndn.net, 'udp', 'link-state')
    grh.calculateNPossibleRoutes()

    print(f"Found Routes after {time.time()-start_time:.2f}sec\n")

    url = "microsoft.com"
    timeout = 30000

    har_path = SITE_DATA_DIR / f"{url}/{url}.har"
    har_config_path = SITE_DATA_DIR / f"{url}/{url}_har_config.pkl"
    with har_config_path.open('rb') as f:
        har_config = pickle.load(f)

    target_server = ndn.net["n"]
    server_prefix = f"ndn/{target_server.name}-site/{target_server.name}"
    server_process_list = host_website(target_server, server_prefix, har_config)

    andana=True

    

    for k in ("DISPLAY","WAYLAND_DISPLAY","XAUTHORITY","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS"):
        os.environ.pop(k, None)
    os.environ["HOME"] = "/root"

    pu = ndn.net["a"]
    if andana:
        andana_relays = [ndn.net[f"r{i}"] for i in range(3)]
        for user in [pu] + andana_relays:
            user.cmd(f"mkdir -p andana/interest")
            user.cmd(f"mkdir -p andana/data")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        ctx = browser.new_context(
            service_workers="block",
            extra_http_headers={"Accept-Encoding": "identity"},
        )

        ctx.route_from_har(har_path.absolute(), not_found="abort", update="False")


        ndnreplayer = AndanaReplayer(
            ndn_host = pu,
            server_prefix = server_prefix,
            webpage_name = url,
            har_config = har_config,
            relays = andana_relays,
            log_file = Path(f"network_log.csv"),
            num_relays = 3
        )

        ctx.route("**/*", ndnreplayer.ndn_handler)

        page = ctx.new_page()

        make_dns_request(pu, ndn.net["j"], url, target_server.name)

        try:
            page.goto(f"https://www.{url}", timeout=timeout)
            page.wait_for_load_state("load", timeout=timeout)
        except TimeoutError:
            print("Timeout on Replay.")
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

    if andana:
        for user in [pu] + andana_relays:
            user.cmd("sudo rm -rf andana/interest")
            user.cmd("sudo rm -rf andana/data")

    os.system("killall -15 ndncatchunks")
    os.system("killall -15 ndnputchunks")

    # server_processes, client_threads = start_background_traffic(
    #             ndn.net.hosts,
    #             num_bg_users=40,
    #             avg_interval_ms=6000,
    #             max_resources=50,
    #             target_server=target_server,
    #             target_url=url
    #         )

    # time.sleep(30)

    # stop_background_traffic(server_processes, client_threads)


    #os.system("killall -15 ndnputchunks")

    #bg_data = find_large_files(pathlib.Path("webpage_data"))

    #bg_server_list = [ndn.net.host for host in ndn.net.hosts if "j" in host.name and host.name != "pu"]
    #bg_user_list = [ndn.net.host for host in ndn.net.hosts if "a" in host.name and host.name != "pu"]

    
    #bg_server_proc = start_background_servers([ndn.net[f"s{server_id}"] for se])
    #bg_client_proc = start_background_clients(pathlib.Path("bgtraffic.conf"), [ndn.net.])



    # producer = ndn.net["j"]
    # consumer = ndn.net["a"]
    # producer_name = "j"
    # consumer_name = "a"

    # for filename in ["1-test","5-test","10-test"]:
    #     p = safe_putchunks(producer, f"ndn/{producer_name}-site/{producer_name}/{filename}", f"/tmp/{filename}", verbose=True)
    #     _ = safe_catchunks(consumer, f"ndn/{producer_name}-site/{producer_name}/{filename}", f"/tmp/{filename}-out", verbose=pathlib.Path("demo.log"))
    #     safe_stop_process(p)

    

    #MiniNDNCLI(ndn.net)
    ndn.stop()
