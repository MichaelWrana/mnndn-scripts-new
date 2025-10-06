import os
import pathlib
import pandas as pd
import shutil

from playwright.sync_api import sync_playwright

from util.constant import *
from util.har import parse_har

for k in ("DISPLAY","WAYLAND_DISPLAY","XAUTHORITY","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS"):
    os.environ.pop(k, None)
os.environ["HOME"] = "/root"

SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)


webpage_list = pd.read_csv(TOP_SITES_PATH)
if "load_result" not in webpage_list.columns:
    webpage_list["load_result"] = 0

for i, row in webpage_list.iterrows():

    if row["load_result"] == 1: # don't access a website for a second time
        continue

    if webpage_list["load_result"].sum() >= 200: # stop after X websites
        break

    if row["domain"] == "twitter.com": # re-direct to x.com (dont want same website twice)
        continue

    url = row["domain"]
    print(f"[INFO] Trying to load {url}")

    webpage_dir = SITE_DATA_DIR / f"{url}"
    webpage_dir.mkdir(parents=True, exist_ok=True)
    har_path = webpage_dir / f"{url}.har"
    har_config_path = webpage_dir / f"{url}_har_config.pkl"
    
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            ctx = browser.new_context(
                record_har_path=har_path.absolute(),
                record_har_content="embed",   # store bodies inside HAR
                record_har_mode="full",       # capture everything
                service_workers="block",
                extra_http_headers={"Accept-Encoding": "identity"},
            )
            page = ctx.new_page()
            page.goto(f"https://www.{url}")

            page.wait_for_load_state("load")

            ctx.close()
            browser.close()

            parse_har(webpage_dir, url, har_path, har_config_path)

            print(f"[SUCCESS] {url} loaded")
            webpage_list.loc[i, "load_result"] = 1

    except Exception as e:
        print(f"[FAIL] {url} not loaded. \n")
        shutil.rmtree(webpage_dir)
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

print(f"{webpage_list["load_result"].sum()} websites successfully loaded")

webpage_list.to_csv(TOP_SITES_PATH, index=False)