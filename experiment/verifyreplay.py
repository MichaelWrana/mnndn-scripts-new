import os
import pathlib
import pandas as pd
import shutil
import argparse

from util.misc import DummyReplayer
from util.constant import *
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError

def parse_args():
    p = argparse.ArgumentParser(
        description="Verify that HAR recordings made with scraper.py can be successfully replayed.  Requred to run before recordtraces.py",
        epilog="Additionally Requires input files with locations specified in constant.py\n SITE_DATA_DIR:output folder to dump webpage recordings\n TOP_SITES_PATH: List of domains to visit (Expecting a csv with a header line, urls slugified under 'domain' column)"
        )

    p.add_argument("--overwrite", action="store_true", help="When set, overwrites existing records and website traces with new recording (default=False)")
    p.add_argument("--maxpages", type=int, default=100, help="Maximum number of webpages to visit (default=100)")
    p.add_argument("--timeout", type=int, default=30000, help="Maximum time waiting for page to load in ms (default=30000)")
    p.add_argument("--rmfail", action="store_true", help="After failing a replay, remove existing data on disk (default=False)")
    p.add_argument("--numservers", type=int, default=20, help="Number of servers in network topology (expected labels s0,...,si)")

    args = p.parse_args()

    return args


args = parse_args()
max_pages = args.maxpages
timeout = args.timeout
rmfail = args.rmfail
num_servers = args.numservers

webpage_list = pd.read_csv(TOP_SITES_PATH)

if args.overwrite:
    webpage_list["replay_result"] = 0
    webpage_list["server_assignment"] = "s?"

if "replay_result" not in webpage_list.columns:
    webpage_list["load_result"] = 0

if "server_assignment" not in webpage_list.columns:
    webpage_list["server_assignment"] = "s?"


replay_attempts = 0

for k in ("DISPLAY","WAYLAND_DISPLAY","XAUTHORITY","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS"):
    os.environ.pop(k, None)
os.environ["HOME"] = "/root"

for i, row in webpage_list.iterrows():

    if row["load_result"] == 0: # don't try and replay a website that failed to load
        continue

    if row["replay_result"] == 1: # dont replay again if we already know it worked
        continue

    if webpage_list["replay_result"].sum() >= max_pages: # stop after X websites
       break

    replay_attempts += 1

    url = row["domain"]
    print(f"[INFO] Trying to replay {url}")

    webpage_dir = SITE_DATA_DIR / f"{url}"
    har_path = webpage_dir / f"{url}.har"
    har_config_path = webpage_dir / f"{url}_har_config.pkl"

    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            ctx = browser.new_context(
                service_workers="block",
                extra_http_headers={"Accept-Encoding": "identity"},
            )

            ctx.route_from_har(har_path.absolute(), not_found="abort", update="False")  # or "abort" for strict offline
            
            replayer = DummyReplayer(har_config_path)
            ctx.route("**/*", replayer.dummy_handler)
            

            page = ctx.new_page()
            page.goto(f"https://www.{url}", timeout=timeout)

            page.wait_for_load_state("load", timeout=timeout)

            print(f"[SUCCESS] {url} replay succeeded. \n")
            webpage_list.loc[i, "replay_result"] = 1
            webpage_list.loc[i, "server_assignment"] = f"s{i % num_servers}"

            ctx.close()
            browser.close()
    except Exception as e:
        print(f"[FAIL] {url} replay failed. \n")
        if rmfail:
            shutil.rmtree(webpage_dir)
        print(e)
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass

print(f"{webpage_list["replay_result"].sum()} webpages replayed.  Attempted {replay_attempts} replays.")

if webpage_list["replay_result"].sum() < max_pages:
    print(f"WARNING: Number of successful replays less than the requested {max_pages}")

webpage_list.to_csv(TOP_SITES_PATH, index=False)