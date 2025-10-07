# GLOBAL PYTHON PACKAGES
import time

from pathlib import Path

# MININDN PACKAGES
from mininet.log import setLogLevel, info
from minindn.minindn import Minindn
from minindn.util import MiniNDNCLI
from minindn.apps.app_manager import AppManager
from minindn.apps.nfd import Nfd
from minindn.helpers.ndn_routing_helper import NdnRoutingHelper

# MY LOCAL PACKAGES
from util.ndn import *
from util.misc import *
from util.bgtraffic import *

if __name__ == '__main__':
    setLogLevel('info')

    Minindn.cleanUp()
    Minindn.verifyDependencies()
    ndn = Minindn(topoFile="line2.conf")
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
    har_config_path = SITE_DATA_DIR / f"{url}/{url}_har_config.pkl"
    with har_config_path.open('rb') as f:
        har_config = pickle.load(f)

    target_server = ndn.net["j"]
    server_process_list = host_website(target_server, f"ndn/{target_server}-site/{target_server}", har_config)

    #make_dns_request(ndn.net["a"], ndn.net["h"], url, "j")

    #make_dns_request(ndn.net["a"], ndn.net["dns"], url, server_name)

    server_processes, client_threads = start_background_traffic(
                ndn.net.hosts,
                num_bg_users=40,
                avg_interval_ms=6000,
                max_resources=50,
                target_server=target_server,
                target_url=url
            )

    time.sleep(30)

    stop_background_traffic(server_processes, client_threads)


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

    

    MiniNDNCLI(ndn.net)
    ndn.stop()
