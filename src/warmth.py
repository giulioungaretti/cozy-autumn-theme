"""Score wallpapers by red/orange content.
warm = fraction of pixels with hue in red..orange (<=38 deg or >=340 deg), saturation>=0.35, value>=0.22.
Usage: python warmth.py <dir> [out.json]"""
import json, os, sys
import numpy as np
from PIL import Image


def warmth(path):
    im = Image.open(path)
    im.draft('RGB', (400, 300))
    im = im.convert('RGB')
    im.thumbnail((320, 240))
    hsv = np.asarray(im.convert('HSV'), dtype=np.float32) / 255.0
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    col = (s >= 0.35) & (v >= 0.22)
    warm = col & ((h <= 38) | (h >= 340))
    green = col & (h >= 70) & (h <= 170)
    return float(warm.mean()), float(green.mean())


if __name__ == '__main__':
    d = sys.argv[1]
    res = {f: warmth(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.lower().endswith('.jpg')}
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], 'w'), indent=0)
    ws = sorted(v[0] for v in res.values())
    for q in (10, 25, 50, 75, 90):
        print(f'p{q}', round(ws[int(len(ws) * q / 100)], 3))
    print('n', len(ws), '<0.05:', sum(w < 0.05 for w in ws), '<0.10:', sum(w < 0.10 for w in ws), '<0.15:', sum(w < 0.15 for w in ws))
