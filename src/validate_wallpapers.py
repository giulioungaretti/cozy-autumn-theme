"""Read-only validation of the shipped originals, attribution and references."""
import json
import re

from upgrade_wallpapers import LICENSE, ROOT, measure


def validate():
    manifest = json.loads((ROOT / "wallpapers.json").read_text(encoding="utf-8"))
    rows = manifest["photos"]
    expected = {r["file"] for r in rows}
    actual = {p.name for p in (ROOT / "Wallpapers").iterdir() if p.is_file()}
    assert expected == actual and len(expected) == len(rows), "Inventory mismatch"
    credits = (ROOT / "CREDITS.md").read_text(encoding="utf-8")
    hashes, perceptual = set(), []
    for row in rows:
        path = ROOT / "Wallpapers" / row["file"]
        info = measure(path)
        assert info["native_4k"] and info["fills_primary"], row["file"]
        assert info["sha256"] == row["sha256"], "Original bytes changed"
        assert (info["width"], info["height"]) == (row["width"], row["height"])
        assert LICENSE.fullmatch(row["license"]), "Unapproved license"
        assert row["artist"] and row["license_url"].startswith(("https://", "http://"))
        assert row["source"].startswith("https://") and row["original_url"].startswith("https://")
        assert row["retrieved"] and row["file"] in credits and row["source"] in credits and row["license_url"] in credits
        assert info["sha256"] not in hashes, "Identical image"
        hashes.add(info["sha256"])
        h = int(info["dhash"], 16)
        assert all((h ^ previous).bit_count() > 12 for previous in perceptual), "Near-identical image"
        perceptual.append(h)
    for key in ("default_wallpaper", "lock_screen"):
        assert manifest[key] in expected, "Dangling default"
    for preview in ("desktop.jpg", "lockscreen.jpg", "wallpapers.jpg"):
        measure(ROOT / "docs" / preview)
    for script in ("install.ps1", "set-lockscreen.ps1"):
        contents = (ROOT / script).read_text(encoding="utf-8")
        assert "bi-501" not in contents and "Stop-Process" not in contents
        for filename in re.findall(r"Wallpapers\\([^'\"\r\n]+\.jpg)", contents):
            assert filename in expected, "Dangling script reference"
    print(f"PASS: {len(rows)} readable native 4K originals; hashes, licenses, credits, duplicate checks, defaults and previews")


if __name__ == "__main__":
    validate()
