"""Direct Flickr search fallback; verifies each photo's CC license and original size.

python src\\fetch_flickr_originals.py <staging-directory>
Writes flickr-candidates.json separately from Commons discovery.
"""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote

import requests

from upgrade_wallpapers import get, measure


def fetch(stage):
    originals = stage / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    accepted, seen = [], set()
    for query in ["vermont autumn", "new england autumn village", "oregon autumn forest", "washington larch autumn"]:
        search = get("https://www.flickr.com/search/?text=" + quote(query) + "&license=4%2C5%2C9%2C10").text
        blocks = search.split('"_flickrModelRegistry":"photo-lite-models"')[1:]
        for block in blocks[:18]:
            alias = re.search(r'"pathAlias":"([^"]+)"', block)
            identifier = re.search(r'"id":"(\d+)"', block)
            if not alias or not identifier:
                continue
            source = f"https://www.flickr.com/photos/{alias.group(1)}/{identifier.group(1)}/"
            if source in seen:
                continue
            seen.add(source)
            try:
                page = get(source).text
                license_match = re.search(r'"license"\s*:\s*"(https://creativecommons.org/(?:licenses/by(?:-sa)?/[1-4]\.0|publicdomain/zero/1\.0)/)"', page)
                original = re.search(r'"o"\s*:\s*(\{[^{}]+\})', page)
                if not license_match or not original:
                    continue
                size = json.loads(original.group(1))
                w, h = size["width"], size["height"]
                if w < 3840 or h < 2160 or not 1.3 <= w / h <= 2.0:
                    continue
                url = size["url"]
                if url.startswith("//"):
                    url = "https:" + url
                name = "fk-" + identifier.group(1) + ".jpg"
                path = originals / name
                if not path.exists():
                    path.write_bytes(get(url).content)
                info = measure(path)
                if not info["native_4k"]:
                    raise ValueError("Downloaded original too small")
                lic_url = license_match.group(1)
                lic = "CC0" if "/zero/" in lic_url else "CC " + lic_url.split("/")[-3].upper() + " " + lic_url.split("/")[-2]
                title_match = re.search(r'"title":"((?:\\.|[^"\\])*)"', block)
                artist_match = re.search(r'"realname":"((?:\\.|[^"\\])*)"', block) or re.search(r'"username":"((?:\\.|[^"\\])*)"', block)
                if not title_match or not artist_match:
                    raise ValueError("Missing photographer/title")
                decode = lambda m: html.unescape(json.loads('"' + m.group(1) + '"'))
                row = dict(info, title=decode(title_match), artist=decode(artist_match), license=lic,
                           license_url=lic_url, source=source, original_url=url, original_width=w, original_height=h,
                           provider="Flickr", retrieved=datetime.now(timezone.utc).isoformat())
                accepted.append(row)
                print("Flickr original", name, w, h, lic, flush=True)
            except (requests.RequestException, OSError, ValueError, KeyError) as e:
                print("FLICKR REJECTED", source, str(e), flush=True)
            time.sleep(1)
        print("searched", query, flush=True)
    (stage / "flickr-candidates.json").write_text(json.dumps(accepted, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Verified Flickr originals", len(accepted), flush=True)


if __name__ == "__main__":
    fetch(Path(sys.argv[1]))
