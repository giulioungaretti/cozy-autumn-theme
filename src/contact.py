"""Contact sheets for reviewing wallpapers. Labels each tile with its index."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
prefix = sys.argv[3] if len(sys.argv) > 3 else ''
files = sorted(f for f in os.listdir(src) if f.lower().endswith('.jpg') and f.startswith(prefix))
os.makedirs(out, exist_ok=True)
TW, TH, COLS, ROWS = [int(x) for x in os.environ.get('SHEET', '300,190,7,6').split(',')]
font = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 22)
index = {}
per = COLS * ROWS
for s in range(0, len(files), per):
    sheet = Image.new('RGB', (COLS * TW, ROWS * TH), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for k, f in enumerate(files[s:s + per]):
        i = s + k
        index[i] = f
        try:
            im = Image.open(os.path.join(src, f))
            im.draft('RGB', (TW * 2, TH * 2))
            im = im.convert('RGB')
            im.thumbnail((TW - 6, TH - 6))
        except Exception:
            continue
        x, y = (k % COLS) * TW + 3, (k // COLS) * TH + 3
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 50, y + 28], fill=(0, 0, 0))
        d.text((x + 4, y + 1), str(i), font=font, fill=(255, 200, 120))
    sheet.save(os.path.join(out, f'{prefix or "all"}_sheet_{s // per:02d}.jpg'), quality=85)
json.dump(index, open(os.path.join(out, f'{prefix or "all"}_index.json'), 'w'), indent=0)
print(len(files), 'files,', (len(files) + per - 1) // per, 'sheets')
