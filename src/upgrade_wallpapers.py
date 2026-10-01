"""Recover licensed originals and discover autumn photographs; never upscale.

Usage: python src\\upgrade_wallpapers.py discover <staging-directory>
       python src\\upgrade_wallpapers.py audit <image-directory> <report.json>
Discovery writes candidates.json and originals outside the active slideshow.
Selection is deliberately a separate, human-reviewed step.
Requires Pillow, numpy and requests.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import html
from io import BytesIO
import json
from pathlib import Path
import re
import time
from urllib.parse import unquote

import numpy as np
from PIL import Image, ImageOps
import requests

ROOT = Path(__file__).resolve().parents[1]
UA = "CozyAutumnTheme/2.0 (https://github.com/giulioungaretti/cozy-autumn-theme; license verification)"
API = "https://commons.wikimedia.org/w/api.php"
QUERIES = [
    "Vermont autumn", "Vermont fall foliage", "Woodstock Vermont autumn",
    "Stowe Vermont autumn", "New Hampshire autumn", "Kancamagus autumn",
    "New England autumn village", "Maine autumn", "Connecticut autumn",
    "Massachusetts autumn", "covered bridge autumn", "autumn barn",
    "North Cascades autumn", "Mount Rainier autumn", "Oregon autumn",
    "Washington larch autumn", "Pacific Northwest forest", "Hoh rainforest",
    "Columbia gorge autumn", "Portland autumn", "Adirondacks autumn",
    "autumn maple forest", "autumn lake reflection", "autumn forest path",
]
LICENSE = re.compile(r"^(CC0|Public domain|PD|CC BY(?:-SA)? (?:[1-4]\.0|2\.5))$", re.I)


def get(url, params=None):
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=90)
            r.raise_for_status()
            return r
        except requests.RequestException as error:
            if attempt == 2:
                raise
            limited = error.response is not None and error.response.status_code == 429
            time.sleep((30 if limited else 2) * (attempt + 1))


def text(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def metadata(pages, recovered=None):
    result = []
    for page in pages:
        if "imageinfo" not in page:
            continue
        ii = page["imageinfo"][0]
        ext = ii.get("extmetadata", {})
        field = lambda key: text(ext.get(key, {}).get("value", ""))
        lic = field("LicenseShortName")
        w, h = ii["width"], ii["height"]
        if ii.get("mime") != "image/jpeg" or not LICENSE.fullmatch(lic):
            continue
        if w < 3840 or h < 2160 or not 1.3 <= w / h <= 2.0:
            continue
        if not field("Artist") or not field("LicenseUrl"):
            continue
        result.append({
            "title": page["title"], "artist": field("Artist"),
            "license": lic, "license_url": field("LicenseUrl"),
            "source": ii["descriptionurl"], "original_url": ii["url"],
            "original_width": w, "original_height": h,
            "provider": "Wikimedia Commons", "retrieved": datetime.now(timezone.utc).isoformat(),
            "recovered_file": (recovered or {}).get(page["title"]),
            "description": field("ImageDescription"),
        })
    return result


def measure(path):
    with Image.open(path) as opened:
        opened.load()
        im = ImageOps.exif_transpose(opened).convert("RGB")
        w, h = im.size
        small = im.copy()
        small.thumbnail((768, 512))
        gray = np.asarray(small.convert("L"), dtype=np.float32)
        lap = -4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
        a = np.asarray(im.resize((17, 16)).convert("L"))
        phash = np.packbits(a[:, 1:] > a[:, :-1]).tobytes().hex()
        # Pixel-scale crops complement this heuristic; fog/bokeh are not defects.
        return {"file": path.name, "width": w, "height": h,
                "fills_primary": w >= 2496 and h >= 1664,
                "native_4k": w >= 3840 and h >= 2160,
                "sharpness_768": round(float(lap.var()), 2),
                "dhash": phash, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def audit(folder, output):
    rows = [measure(p) for p in sorted(folder.glob("*.jpg"))]
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(rows), "below_primary": sum(not r["fills_primary"] for r in rows),
                      "native_4k": sum(r["native_4k"] for r in rows)}), flush=True)


def discover(stage):
    stage.mkdir(parents=True, exist_ok=True)
    images = stage / "originals"
    images.mkdir(exist_ok=True)
    rows = []
    recovered = {}
    for line in (ROOT / "CREDITS.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 7 and cells[1][:1].isdigit() and cells[5].startswith("https://commons.wikimedia.org/wiki/File:"):
            title = unquote(cells[5].split("/wiki/")[1]).replace("_", " ")
            recovered[title] = cells[1]
    titles = list(recovered)
    for start in range(0, len(titles), 20):
        data = get(API, {"action": "query", "format": "json", "titles": "|".join(titles[start:start + 20]),
                         "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime"}).json()
        rows.extend(metadata(data.get("query", {}).get("pages", {}).values(), recovered))
    print("eligible recovered originals", len(rows), flush=True)
    for query in QUERIES:
        try:
            data = get(API, {"action": "query", "format": "json", "generator": "search",
                             "gsrnamespace": 6, "gsrlimit": 20,
                             "gsrsearch": query + " filew:>3839 fileh:>2159 filetype:bitmap",
                             "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime"}).json()
            found = metadata(data.get("query", {}).get("pages", {}).values())
            rows.extend(found)
            print("Commons", query, len(found), flush=True)
        except (requests.RequestException, ValueError) as e:
            print("SOURCE FAILED", query, str(e), flush=True)
        time.sleep(0.3)
    # Openverse is discovery only. Verify the license on the photographer's page.
    for query in ["Vermont autumn", "New England fall", "Oregon autumn", "Washington larch"]:
        try:
            data = get("https://api.openverse.org/v1/images/", {"q": query, "page_size": 30}).json()
            for item in data.get("results", []):
                if item.get("source") != "flickr" or item.get("license") not in ("by", "by-sa", "cc0"):
                    continue
                source = item.get("foreign_landing_url", "")
                page = get(source).text
                slug = "publicdomain/zero" if item["license"] == "cc0" else "licenses/" + item["license"]
                version = item.get("license_version") or "1.0"
                license_url = "https://creativecommons.org/" + slug + "/" + version + "/"
                if license_url not in html.unescape(page).replace("http://", "https://"):
                    print("unverified Flickr license", source, flush=True)
                    continue
                original = re.search(r'"o"\s*:\s*\{[^{}]*"url"\s*:\s*"([^"]+)"', page)
                if not original:
                    continue
                url = original.group(1).replace("\\/", "/")
                if url.startswith("//"):
                    url = "https:" + url
                rows.append({"title": item["title"], "artist": item["creator"], "source": source,
                             "license": "CC0" if item["license"] == "cc0" else "CC " + item["license"].upper() + " " + version,
                             "license_url": license_url, "original_url": url, "provider": "Flickr",
                             "retrieved": datetime.now(timezone.utc).isoformat()})
            print("Flickr search complete", query, flush=True)
        except (requests.RequestException, ValueError) as e:
            print("SOURCE FAILED", query, str(e), flush=True)
    unique = {r["source"]: r for r in reversed(rows)}
    rows = sorted(unique.values(), key=lambda r: (not bool(r.get("recovered_file")), r["source"]))
    def download(row):
        name = row.get("recovered_file") or "new-" + hashlib.sha256(row["source"].encode()).hexdigest()[:12] + ".jpg"
        path = images / name
        try:
            if not path.exists():
                content = get(row["original_url"]).content
                with Image.open(BytesIO(content)) as im:
                    im.load()
                    if im.format != "JPEG":
                        raise ValueError("Original is not JPEG")
                path.write_bytes(content)
            info = measure(path)
            if not info["native_4k"] or not 1.3 <= info["width"] / info["height"] <= 2.0:
                path.unlink()
                return None
            row.update(info)
            return row
        except (requests.RequestException, OSError, ValueError) as e:
            print("DOWNLOAD FAILED", row["source"], str(e), flush=True)
            return None
    with ThreadPoolExecutor(max_workers=1) as pool:
        accepted = [r for r in pool.map(download, rows) if r]
    (stage / "candidates.json").write_text(json.dumps(accepted, indent=2, ensure_ascii=False), encoding="utf-8")
    print("downloaded originals", len(accepted), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["discover", "audit"])
    parser.add_argument("folder", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    args = parser.parse_args()
    if args.command == "discover":
        discover(args.folder)
    else:
        if args.output is None:
            parser.error("audit requires a report path")
        audit(args.folder, args.output)
