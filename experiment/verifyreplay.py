import os
import pathlib
import pandas as pd

from util.misc import DummyReplayer
from util.constant import *
from playwright.sync_api import sync_playwright

for k in ("DISPLAY","WAYLAND_DISPLAY","XAUTHORITY","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS"):
    os.environ.pop(k, None)
os.environ["HOME"] = "/root"

webpage_list = pd.read_csv(TOP_SITES_PATH)
if "replay_result" not in webpage_list.columns:
    webpage_list["replay_result"] = 0

if "server_assignment" not in webpage_list.columns:
    webpage_list["server_assignment"] = "s0"

for i, row in webpage_list.iterrows():

    if row["load_result"] == 0: # don't try and replay a website that failed to load
        continue

    if row["replay_result"] == 1: # dont replay again if we already know it worked
        continue

    if webpage_list["replay_result"].sum() >= 10: # stop after X websites
        break

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

            ctx.route_from_har(har_path.resolve(), not_found="abort")  # or "abort" for strict offline
            
            replayer = DummyReplayer(webpage_dir, har_path, har_config_path)
            ctx.route("**/*", replayer.dummy_handler)
            
            page = ctx.new_page()
            page.goto(f"https://www.{url}", wait_until="domcontentloaded")

            # If you want to ensure no real network after HAR is wired up:
            # ctx.set_offline(True)  # do this AFTER route_from_har
            page.wait_for_load_state("networkidle")

            print(f"[SUCCESS] {url} replay succeeded. \n")
            webpage_list.loc[i, "replay_result"] = 1
            webpage_list.loc[i, "server_assignment"] = f"s{i % NUM_SERVERS}"


            ctx.close()
            browser.close()
    except Exception as e:
        print(f"[FAIL] {url} replay failed. \n")
        print(e)
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

print(f"{webpage_list["replay_result"].sum()}/{webpage_list["load_result"].sum()} websites successfully replayed")

webpage_list.to_csv(TOP_SITES_PATH, index=False)