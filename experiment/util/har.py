import pathlib
import json
import re
import pickle

def parse_har(webpage_dir, webpage_url, har_path, har_config_path):
    with har_path.open("r", encoding="utf-8") as f:
        har_data = json.load(f)

    entries = (har_data.get("log") or {}).get("entries")

    url_to_file_id = {}
    rid = 0

    if len(entries) < 20:
        raise Exception("Website too small...skipping")

    for e in entries:
        req = e.get("request")
        resp = e.get("response")
        url = req.get("url")

        content = resp.get("content").get("text")

        if content is None:
            content = "".join(str(header) for header in resp.get("headers"))

        content_file_path = webpage_dir.absolute() / f"{webpage_url}_{rid}"
        with content_file_path.open('wb') as f:
            try:
                f.write(content)
            except TypeError:
                f.write(content.encode('utf-8'))

        url_to_file_id[content_file_path.absolute()] = url
        rid += 1

    with har_config_path.open('wb') as f:
        pickle.dump(url_to_file_id, f)