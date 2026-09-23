"""Finalize wallpaper set: warmth filter (web passes), perceptual-hash dedupe, CREDITS.md.
Usage: python finalize.py <theme_dir> <pruned_dir>"""
import glob, json, os, shutil, sys
import numpy as np
from PIL import Image
from warmth import warmth

THEME, PRUNED = sys.argv[1], sys.argv[2]
WP = os.path.join(THEME, 'Wallpapers')
MIN_WARM_WEB = 0.15


def dhash(path, n=16):
    im = Image.open(path)
    im.draft('L', (256, 256))
    a = np.asarray(im.convert('L').resize((n + 1, n), Image.LANCZOS), dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def move(f):
    shutil.move(os.path.join(WP, f), os.path.join(PRUNED, f))


files = sorted(f for f in os.listdir(WP) if f.lower().endswith('.jpg'))
removed_warm = 0
for f in files:
    if f.startswith('bi-') and int(f.split('-')[1]) >= 501:
        w, _ = warmth(os.path.join(WP, f))
        if w < MIN_WARM_WEB:
            move(f)
            removed_warm += 1
print('warmth-pruned', removed_warm)

# Prefer curated sources when resolving duplicates: Commons first, then Openverse, then Bing.
def rank(f):
    return (0 if f[0].isdigit() else 1 if f.startswith('ov-') else 2, f)

files = sorted((f for f in os.listdir(WP) if f.lower().endswith('.jpg')), key=rank)
hashes, kept, dupes = [], [], 0
for f in files:
    try:
        h = dhash(os.path.join(WP, f))
    except Exception:
        move(f)
        continue
    if hashes and (np.stack(hashes) != h).sum(1).min() <= 40:
        move(f)
        dupes += 1
        continue
    hashes.append(h)
    kept.append(f)
print('dupes', dupes, 'kept', len(kept))

credits = {}
for cj in glob.glob(os.path.join(THEME, 'credits*.json')):
    for c in json.load(open(cj, encoding='utf8')):
        if c.get('file'):
            credits[c['file']] = c
lines = ['# Cozy Autumn — wallpaper credits', '',
         'Photos are by their respective authors and used under the licenses listed below (Creative Commons / public domain).',
         'Wikimedia Commons and Openverse entries carry verified license metadata. Bing entries were found with the',
         "Bing Images Creative Commons license filter. Check each source page before any reuse beyond personal desktop use.", '',
         '| File | Title | Author | License | Source |', '|---|---|---|---|---|']
esc = lambda s: str(s or '').replace('|', '\\|').replace('\n', ' ').strip()[:120]
for f in sorted(kept):
    c = credits.get(f, {})
    lines.append(f"| {f} | {esc(c.get('title'))} | {esc(c.get('artist')) or 'unknown'} | {esc(c.get('license')) or 'see source'} | {c.get('source') or c.get('url') or ''} |")
open(os.path.join(THEME, 'CREDITS.md'), 'w', encoding='utf8').write('\n'.join(lines) + '\n')
print('credits rows', len(kept), 'missing metadata', sum(1 for f in kept if f not in credits))
