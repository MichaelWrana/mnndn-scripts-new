import os
import pathlib
import pandas as pd
import shutil

from util.misc import DummyReplayer
from util.constant import *
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError

for k in ("DISPLAY","WAYLAND_DISPLAY","XAUTHORITY","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS"):
    os.environ.pop(k, None)
os.environ["HOME"] = "/root"

webpage_list = pd.read_csv(TOP_SITES_PATH)
if "replay_result" not in webpage_list.columns:
    webpage_list["replay_result"] = 0

if "server_assignment" not in webpage_list.columns:
    webpage_list["server_assignment"] = "s0"


#special_row = [{"domain":"apache.org", "load_result":1, "replay_result":0, "server_assignment":"s8"}]

replay_attempts = 0

for i, row in webpage_list.iterrows():
#for i, row in enumerate(special_row):

    if row["load_result"] == 0: # don't try and replay a website that failed to load
        continue

    #if row["replay_result"] == 1: # dont replay again if we already know it worked
    #    continue

    #if webpage_list["replay_result"].sum() >= 100: # stop after X websites
    #   break

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
            page.goto(f"https://www.{url}")

            page.wait_for_load_state("load")

            print(f"[SUCCESS] {url} replay succeeded. \n")
            webpage_list.loc[i, "replay_result"] = 1
            webpage_list.loc[i, "server_assignment"] = f"s{i % NUM_SERVERS}"

            ctx.close()
            browser.close()
    except Exception as e:
        print(f"[FAIL] {url} replay failed. \n")
        #shutil.rmtree(webpage_dir)
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

print(f"{webpage_list["replay_result"].sum()}/{replay_attempts} websites successfully replayed")

webpage_list.to_csv(TOP_SITES_PATH, index=False)