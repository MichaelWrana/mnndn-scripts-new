import pickle
import csv
import time

from pathlib import Path
from difflib import SequenceMatcher

class DummyReplayer:
    def __init__(self, har_config_path):
        with har_config_path.open('rb') as f:
            self.har_config = pickle.load(f)

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


    def dummy_handler(self, route):

        #print(len(self.har_config))

        resource_path = self.match_url(route.request.url)

        if resource_path is not None:
            print(f"Resource file successfully found: {resource_path}")
            #print(f"Requesting {resource_path.resolve()} from NDN. Successful")
        else:
            pass
        
        route.fallback()

def next_experiment_dir(base):
    """Return Path for the next 'experiment_<n>' under base (does not create it)."""
    prefix = "experiment_"
    nums = [
        int(p.name[len(prefix):])
        for p in base.iterdir()
        if p.is_dir() and p.name.startswith(prefix) and p.name[len(prefix):].isdigit()
    ]
    next_dir = base / f"{prefix}{(max(nums, default=-1) + 1)}"
    next_dir.mkdir(parents=True, exist_ok=True)
    return next_dir

def log_cat_result(result, f, headers, print_header=False):
    """
    Parse a text blob from ndncatchunks and write one CSV row.

    note: Extra long and careful to avoid accidentally crashing Firefox with a silly logging error
    (has happened more then I would care to admit)

    - Never assumes fixed line numbers or exact ordering.
    - Skips unknown/malformed lines instead of crashing.
    - Fills missing fields with "" to keep column alignment stable.
    """
    if print_header:
        print(result)

    # Coerce to string and normalize lines; skip empty lines
    text = result if isinstance(result, str) else str(result)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Fixed column order for the CSV
    ordered_headers = [
        "Time elapsed",
        "Segments received",
        "Transferred size",
        "Goodput",
        "Congestion marks",
        "Timeouts",
        "Retransmitted segments",
        "RTT",
    ]

    # Default: everything empty; we only fill what we can parse
    values = {h: "" for h in ordered_headers}

    def first_token(s: str) -> str:
        if not s:
            return ""
        tok = s.strip().split()[0]
        return tok.rstrip(",")  # handle cases like "(50%),"

    for line in lines:
        try:
            low = line.lower()

            # RTT line can be either "RTT min/avg/max = A/B/C ms" or "RTT stats unavailable"
            if low.startswith("rtt"):
                if "=" in line:
                    values["RTT"] = first_token(line.split("=", 1)[1])
                # else leave blank if stats unavailable or malformed
                continue

            # Ignore lines without a colon (e.g., "All segments have been received.")
            if ":" not in line:
                continue

            key, rest = line.split(":", 1)
            k = key.strip().lower()
            rest = rest.strip()

            if k.startswith("time elapsed"):
                values["Time elapsed"] = first_token(rest)
            elif k.startswith("segments received"):
                values["Segments received"] = first_token(rest)
            elif k.startswith("transferred size"):
                values["Transferred size"] = first_token(rest)
            elif k.startswith("goodput"):
                values["Goodput"] = first_token(rest)
            elif k.startswith("congestion marks"):
                values["Congestion marks"] = first_token(rest)
            elif k.startswith("timeouts"):
                values["Timeouts"] = first_token(rest)
            elif k.startswith("retransmitted segments"):
                values["Retransmitted segments"] = first_token(rest)
            # else: unknown key; ignore it
        except Exception:
            # Any weirdness in a line should not kill the whole row
            continue

    writer = csv.writer(f, lineterminator="\n")
    if headers:
        writer.writerow(ordered_headers)
    writer.writerow([values[h] for h in ordered_headers])