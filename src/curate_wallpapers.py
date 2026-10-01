"""Contact-sheet review and exact-byte publication of licensed originals.

python src\\curate_wallpapers.py sheets <staging-directory>
python src\\curate_wallpapers.py publish <staging-directory> <review.json>
review.json must list approved filenames, default_wallpaper and lock_screen.
The previous worktree collection is moved to staging/legacy-original, never
deleted. This script does not touch installed theme assets or personalization.
"""
import argparse
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont, ImageOps

from upgrade_wallpapers import ROOT, measure

FONT = ImageFont.truetype("C:\\Windows\\Fonts\\segoeuib.ttf", 16)


def sheets(stage):
    rows = json.loads((stage / "candidates.json").read_text(encoding="utf-8"))
    rows.sort(key=lambda r: (not bool(r.get("recovered_file")), r["file"]))
    (stage / "review-index.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    for start in range(0, len(rows), 30):
        sheet = Image.new("RGB", (1800, 1100), "#201a16")
        draw = ImageDraw.Draw(sheet)
        for k, row in enumerate(rows[start:start + 30]):
            with Image.open(stage / "originals" / row["file"]) as im:
                im = ImageOps.exif_transpose(im)
                thumb = ImageOps.fit(im, (294, 178))
                x, y = k % 6 * 300, k // 6 * 220
                sheet.paste(thumb, (x, y))
                draw.text((x + 3, y + 180), f"{start+k}  {row['width']}x{row['height']}  S:{row['sharpness_768']}", font=FONT, fill="white")
                draw.text((x + 3, y + 200), row["title"].replace("File:", "")[:30], font=FONT, fill="#f4b76e")
        sheet.save(stage / f"review-{start//30:02d}.jpg", quality=92)
    # Inspect real pixels in the softest candidates, not just downscaled tiles.
    soft = sorted(rows, key=lambda r: r["sharpness_768"])[:30]
    for start in range(0, len(soft), 10):
        sheet = Image.new("RGB", (1800, 840), "#201a16")
        draw = ImageDraw.Draw(sheet)
        for k, row in enumerate(soft[start:start + 10]):
            with Image.open(stage / "originals" / row["file"]) as opened:
                im = ImageOps.exif_transpose(opened)
                x, y = (im.width - 350) // 2, (im.height - 380) // 2
                crop = im.crop((x, y, x + 350, y + 380))
                tx, ty = k % 5 * 360, k // 5 * 420
                sheet.paste(crop, (tx, ty))
                index = next(i for i, r in enumerate(rows) if r["file"] == row["file"])
                draw.text((tx, ty+383), f"{index}: 1:1 center pixels S:{row['sharpness_768']}", font=FONT, fill="white")
        sheet.save(stage / f"pixels-{start//10:02d}.jpg", quality=95)
    print(len(rows), "candidates;", (len(rows) + 29) // 30, "contact sheets")


def publish(stage, review):
    decision = json.loads(review.read_text(encoding="utf-8"))
    candidates = {r["file"]: r for r in json.loads((stage / "candidates.json").read_text(encoding="utf-8"))}
    if "approved" in decision:
        approved = decision["approved"]
    else:
        reviewed = json.loads((stage / "review-index.json").read_text(encoding="utf-8"))
        if decision["reviewed_candidates"] != len(reviewed):
            raise ValueError("Review does not cover the current candidate inventory")
        rejected = set(decision["rejected_indices"])
        approved = [row["file"] for i, row in enumerate(reviewed) if i not in rejected]
        hashes = []
        deduplicated = []
        for name in approved:
            h = int(candidates[name]["dhash"], 16)
            if any((h ^ previous).bit_count() <= 12 for previous in hashes):
                print("Near-duplicate excluded", name)
                continue
            hashes.append(h)
            deduplicated.append(name)
        approved = deduplicated
        for key in ("default_wallpaper", "lock_screen"):
            decision[key] = reviewed[decision[key]]["file"]
    if not approved or len(set(approved)) != len(approved):
        raise ValueError("Empty or duplicate approved filenames")
    rows = []
    for name in sorted(approved):
        row = candidates[name]
        if name != Path(name).name or not row["artist"] or not row["license_url"]:
            raise ValueError("Unsafe filename or missing license")
        info = measure(stage / "originals" / name)
        if not info["native_4k"] or info["sha256"] != row["sha256"]:
            raise ValueError(f"Original changed or too small: {name}")
        rows.append(row)
    for key in ("default_wallpaper", "lock_screen"):
        if decision[key] not in approved:
            raise ValueError(f"{key} not approved")
    archive = stage / "legacy-original"
    if archive.exists():
        raise FileExistsError("Legacy backup already exists; refusing to overwrite it")
    archive.mkdir()
    shutil.copy2(ROOT / "CREDITS.md", archive / "CREDITS.md")
    for path in sorted((ROOT / "Wallpapers").glob("*.jpg")):
        shutil.move(str(path), archive / path.name)
    for row in rows:
        shutil.copy2(stage / "originals" / row["file"], ROOT / "Wallpapers" / row["file"])
    manifest = {"policy": "Native original JPEG; at least 3840x2160; no enlargement or recompression",
                "review": decision["review"], "default_wallpaper": decision["default_wallpaper"],
                "lock_screen": decision["lock_screen"], "photos": rows}
    (ROOT / "wallpapers.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Cozy Autumn wallpaper credits", "",
             "The active collection contains source-verified CC BY, CC BY-SA, CC0 or public-domain photographs.",
             "Original JPEG bytes are preserved: no resizing, upscaling, generation or recompression.",
             "Each license link states its attribution and (where applicable) ShareAlike obligations.",
             "Verification dates, original download URLs, dimensions and SHA-256 hashes are recorded in `wallpapers.json`.",
             "Openverse was used only for discovery; Flickr licenses were checked on the photographer's page.",
             "", "Legacy Bing license-filter results are NOT verified licenses, even for personal use.",
             "The installed legacy collection is not changed by curation; the installer backs it up before replacement.",
             "", "| File | Photograph | Author | License | Source |", "|---|---|---|---|---|"]
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    for r in rows:
        lines.append(f"| {r['file']} | {esc(r['title'])} | {esc(r['artist'])} | [{r['license']}]({r['license_url']}) | [{r['provider']}]({r['source']}) |")
    lines.extend(["", "## Preview derivatives", "",
                  f"`docs/desktop.jpg` uses `{decision['default_wallpaper']}`; `docs/lockscreen.jpg` uses `{decision['lock_screen']}`.",
                  "`docs/wallpapers.jpg` is a labeled contact sheet of active photographs. These resized previews",
                  "are derivatives under each source photograph's linked license, including ShareAlike where required.",
                  "Desktop/lock-screen overlays are illustrative, not screenshots of an installed upgrade.", ""])
    (ROOT / "CREDITS.md").write_text("\n".join(lines), encoding="utf-8")
    for key, output, label in [("default_wallpaper", "desktop.jpg", "Cozy Autumn | Native-resolution photographs"),
                               ("lock_screen", "lockscreen.jpg", "Cozy Autumn | Lock screen preview")]:
        with Image.open(ROOT / "Wallpapers" / decision[key]) as source:
            preview = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), (1500, 1000))
        draw = ImageDraw.Draw(preview)
        draw.rectangle((0, 955, 1500, 1000), fill="#201a16")
        draw.text((24, 967), label, font=FONT, fill="white")
        preview.save(ROOT / "docs" / output, quality=94)
    sample = rows[::max(1, len(rows) // 20)][:20]
    sheet = Image.new("RGB", (1500, 1000), "#201a16")
    draw = ImageDraw.Draw(sheet)
    for k, row in enumerate(sample):
        with Image.open(ROOT / "Wallpapers" / row["file"]) as source:
            thumb = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), (294, 215))
        x, y = k % 5 * 300, k // 5 * 250
        sheet.paste(thumb, (x, y))
        draw.text((x+3, y+219), row["file"][:27], font=FONT, fill="white")
    sheet.save(ROOT / "docs" / "wallpapers.jpg", quality=94)
    print("Published", len(rows), "originals; legacy preserved at", archive)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sheets", "publish"])
    parser.add_argument("stage", type=Path)
    parser.add_argument("review", nargs="?", type=Path)
    args = parser.parse_args()
    if args.command == "sheets":
        sheets(args.stage)
    elif args.review is None:
        parser.error("publish requires review.json")
    else:
        publish(args.stage, args.review)
