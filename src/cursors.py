"""Build the Cozy Autumn cursor sets (.cur / .ani) in three art scales, each multi-resolution.

Art scale is relative to the 32-unit design grid, applied about each cursor's hotspot.
Calibrated against Windows Aero: arrow height / canvas = 0.59 (standard), 0.78 (_l), 0.92 (_xl)."""
import math, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1]
# Every size Windows may ask for (pointer-size slider x DPI); it picks the closest frame.
SIZES = [32, 40, 48, 56, 64, 72, 80, 96, 112, 128, 160, 192, 256]
ANI_SIZES = [32, 40, 48, 56, 64]  # LoadCursorFromFile rejects ANI frames >64px (Aero's .ani files stop at 64 too)
VARIANTS = [('', 0.66), ('Large', 0.88), ('ExtraLarge', 0.95)]
SS = 8
CREAM = (255, 244, 227, 255)
ESPRESSO = (59, 36, 24, 255)
ORANGE = (217, 98, 43, 255)
RUST = (178, 58, 36, 255)
GOLD = (236, 170, 60, 255)
FONT = 'C:/Windows/Fonts/segoeuib.ttf'


# ------------------------------------------------------------ geometry (32-unit space)

ARROW = [(2, 2), (2, 24.5), (7.3, 19.6), (10.8, 27.6), (14.4, 26.1), (11.0, 18.4), (17.9, 18.4)]


def rot(pts, ang, c=(16, 16)):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def double_arrow(L=13, head=5.5, hw=5.2, sw=1.6):
    c = 16
    return [(c, c - L), (c + hw, c - L + head), (c + sw, c - L + head), (c + sw, c + L - head), (c + hw, c + L - head),
            (c, c + L), (c - hw, c + L - head), (c - sw, c + L - head), (c - sw, c - L + head), (c - hw, c - L + head)]


def maple(cx, cy, R, ang=0.0, n=240):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    a = (th - np.pi / 2 + np.pi) % (2 * np.pi) - np.pi
    r = np.full(n, 0.22)
    for a0, L, w in [(0, 1.0, 0.55), (1.0, 0.9, 0.5), (-1.0, 0.9, 0.5), (2.05, 0.55, 0.42), (-2.05, 0.55, 0.42)]:
        d = np.abs(((a - a0) + np.pi) % (2 * np.pi) - np.pi)
        g = np.clip(1 - d / w, 0, 1) ** 0.95
        teeth = 0.1 * np.clip(1 - np.abs(np.sin((a - a0) * 9)) * 1.6, 0, 1) * (g > 0.05)
        r = np.maximum(r, 0.22 + L * 0.8 * g + teeth * L)
    pts = [(math.cos(t + ang) * rr, -math.sin(t + ang) * rr) for t, rr in zip(th, r)]
    return [(cx + x * R, cy + y * R + 0.12 * R) for x, y in pts]


# ------------------------------------------------------------ rendering

class Canvas:
    def __init__(self, size, hot=(16, 16), scale=1.0):
        self.size = size
        self.S = size * (SS if size <= 64 else 4 if size <= 128 else 2)
        self.k = self.S / 32 * scale  # pixels per design unit
        self.ox = hot[0] * self.S / 32 * (1 - scale)
        self.oy = hot[1] * self.S / 32 * (1 - scale)
        self.parts = []  # (mask, color)

    def _new(self):
        m = Image.new('L', (self.S, self.S), 0)
        return m, ImageDraw.Draw(m)

    def _xy(self, x, y):
        return self.ox + x * self.k, self.oy + y * self.k

    def _p(self, pts):
        return [self._xy(x, y) for x, y in pts]

    def poly(self, pts, color):
        m, d = self._new()
        d.polygon(self._p(pts), fill=255)
        self.parts.append((m, color))

    def ellipse(self, cx, cy, rx, ry, color, width=None):
        m, d = self._new()
        (x0, y0), (x1, y1) = self._xy(cx - rx, cy - ry), self._xy(cx + rx, cy + ry)
        if width:
            d.ellipse([x0, y0, x1, y1], outline=255, width=max(1, int(width * self.k)))
        else:
            d.ellipse([x0, y0, x1, y1], fill=255)
        self.parts.append((m, color))

    def rrect(self, x0, y0, x1, y1, r, color):
        m, d = self._new()
        (a, b), (c, e) = self._xy(x0, y0), self._xy(x1, y1)
        d.rounded_rectangle([a, b, c, e], radius=r * self.k, fill=255)
        self.parts.append((m, color))

    def line(self, pts, w, color):
        m, d = self._new()
        d.line(self._p(pts), fill=255, width=max(1, int(w * self.k)), joint='curve')
        rr = w * self.k / 2
        for x, y in self._p([pts[0], pts[-1]]):
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
        self.parts.append((m, color))

    def text(self, s, x, y, h, color):
        m, d = self._new()
        f = ImageFont.truetype(FONT, int(h * self.k))
        d.text(self._xy(x, y), s, font=f, fill=255, anchor='mm')
        self.parts.append((m, color))

    def render(self, outline=1.25, shadow=True):
        S, k = self.S, self.k
        union = Image.new('L', (S, S), 0)
        for m, _ in self.parts:
            union = Image.fromarray(np.maximum(np.asarray(union), np.asarray(m)))
        r = outline * k
        dil = np.asarray(union.filter(ImageFilter.GaussianBlur(r * 0.55)), np.float32)
        dil = np.clip((dil - 20) * 4, 0, 255).astype(np.uint8)
        dil = Image.fromarray(np.maximum(dil, np.asarray(union)))
        out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        if shadow:
            sh = dil.filter(ImageFilter.GaussianBlur(1.2 * k))
            sh = Image.fromarray((np.asarray(sh, np.float32) * 0.38).astype(np.uint8))
            layer = Image.new('RGBA', (S, S), (20, 10, 5, 0))
            layer.putalpha(sh)
            out.alpha_composite(layer, (int(0.8 * k), int(1.1 * k)))
        ol = Image.new('RGBA', (S, S), ESPRESSO)
        ol.putalpha(dil)
        out.alpha_composite(ol)
        for m, color in self.parts:
            fill = Image.new('RGBA', (S, S), color)
            fill.putalpha(m)
            out.alpha_composite(fill)
        return out.convert('RGBa').resize((self.size, self.size), Image.LANCZOS).convert('RGBA')


# ------------------------------------------------------------ file writers

def dib(img):
    w, h = img.size
    a = np.asarray(img)
    bgra = a[::-1][:, :, [2, 1, 0, 3]].tobytes()
    mask_row = ((w + 31) // 32) * 4
    header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, len(bgra) + mask_row * h, 0, 0, 0, 0)
    return header + bgra + b'\x00' * (mask_row * h)


def cur_bytes(images, hot):
    """images: list of (PIL RGBA); hot: hotspot in 32-unit space."""
    n = len(images)
    head = struct.pack('<HHH', 0, 2, n)
    entries, blobs = b'', b''
    off = 6 + 16 * n
    for im in images:
        data = dib(im)
        s = im.width
        hx_, hy_ = int(round(hot[0] * s / 32)), int(round(hot[1] * s / 32))
        entries += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, hx_, hy_, len(data), off)
        blobs += data
        off += len(data)
    return head + entries + blobs


def chunk(tag, data):
    pad = b'\x00' if len(data) % 2 else b''
    return tag + struct.pack('<I', len(data)) + data + pad


def ani_bytes(frames, hot, jiffies, title='Cozy Autumn'):
    anih = struct.pack('<9I', 36, len(frames), len(frames), 0, 0, 0, 0, jiffies, 1)
    fram = b'fram' + b''.join(chunk(b'icon', cur_bytes(f, hot)) for f in frames)
    info = b'INFO' + chunk(b'INAM', title.encode() + b'\x00') + chunk(b'IART', b'Cozy Autumn theme\x00')
    body = b'ACON' + chunk(b'LIST', info) + chunk(b'anih', anih) + chunk(b'LIST', fram)
    return b'RIFF' + struct.pack('<I', len(body)) + body


DEST, SCALE = OUT, 1.0  # set per variant in __main__


def write_cur(name, draw, hot):
    ims = []
    for s in SIZES:
        c = Canvas(s, hot, SCALE)
        draw(c)
        ims.append(c.render())
    open(os.path.join(DEST, name + '.cur'), 'wb').write(cur_bytes(ims, hot))
    return ims[SIZES.index(64)]


def write_ani(name, draw_frame, hot, nframes=18, jiffies=3):
    frames = []
    for i in range(nframes):
        ims = []
        for s in ANI_SIZES:
            c = Canvas(s, hot, SCALE)
            draw_frame(c, i / nframes)
            ims.append(c.render())
        frames.append(ims)
    open(os.path.join(DEST, name + '.ani'), 'wb').write(ani_bytes(frames, hot, jiffies))
    return frames[0][ANI_SIZES.index(64)]


# ------------------------------------------------------------ cursor designs

def arrow(c):
    c.poly(ARROW, CREAM)


def leaf_spin(c, f, cx=16, cy=16, R=12.5, color=ORANGE):
    c.poly(maple(cx, cy, R, ang=f * 2 * math.pi), color)
    c.ellipse(cx, cy, R * 0.13, R * 0.13, GOLD)


def help_(c):
    arrow(c)
    c.ellipse(24.5, 23.5, 6.2, 6.2, ORANGE)
    c.text('?', 24.6, 22.7, 10, CREAM)


def working(c, f):
    arrow(c)
    leaf_spin(c, f, 23.5, 24, 7.2)


def crosshair(c):
    for pts in ([(16, 3), (16, 12)], [(16, 20), (16, 29)], [(3, 16), (12, 16)], [(20, 16), (29, 16)]):
        c.line(pts, 1.6, CREAM)
    c.ellipse(16, 16, 1.6, 1.6, ORANGE)


def ibeam(c):
    c.line([(16, 6), (16, 26)], 1.8, CREAM)
    c.line([(11.5, 4.5), (14.5, 5.5), (17.5, 5.5), (20.5, 4.5)], 1.6, CREAM)
    c.line([(11.5, 27.5), (14.5, 26.5), (17.5, 26.5), (20.5, 27.5)], 1.6, CREAM)


def pen(c):
    body = [(8.5, 19.5), (22.5, 5.5), (26.5, 9.5), (12.5, 23.5)]
    c.poly(body, ORANGE)
    c.poly([(22.5, 5.5), (24.5, 3.5), (28.5, 7.5), (26.5, 9.5)], (232, 150, 150, 255))
    c.poly([(8.5, 19.5), (12.5, 23.5), (3, 29)], CREAM)
    c.poly([(5.2, 25.1), (6.9, 26.8), (3, 29)], ESPRESSO)


def no(c):
    c.ellipse(16, 16, 11.5, 11.5, RUST, width=3.4)
    c.line([(8.3, 8.3), (23.7, 23.7)], 3.4, RUST)


def size_rot(angle):
    return lambda c: c.poly(rot(double_arrow(), angle), CREAM)


def size_all(c):
    c.poly(double_arrow(13.5, 5, 4.6, 1.5), CREAM)
    c.poly(rot(double_arrow(13.5, 5, 4.6, 1.5), math.pi / 2), CREAM)
    c.ellipse(16, 16, 1.6, 1.6, ORANGE)


def up(c):
    c.poly([(16, 2), (23, 11), (18, 11), (18, 29), (14, 29), (14, 11), (9, 11)], CREAM)


def hand(c):
    # index finger up, three curled fingers, thumb, orange knit cuff
    c.rrect(10.2, 1.8, 14.8, 18, 2.3, CREAM)
    c.rrect(14.2, 10.2, 18.6, 19, 2.2, CREAM)
    c.rrect(18.0, 11.2, 22.2, 19.5, 2.1, CREAM)
    c.rrect(21.6, 12.8, 25.4, 20, 1.9, CREAM)
    c.poly([(5.2, 15.8), (7.4, 14.2), (10.8, 17.8), (10.8, 22)], CREAM)
    c.rrect(8.6, 15.5, 25.4, 26.5, 5, CREAM)
    for x in (18.3, 21.9):
        c.line([(x, 14.5), (x, 18.2)], 0.6, ESPRESSO)
    c.line([(14.6, 13.5), (14.6, 18.2)], 0.6, ESPRESSO)
    c.rrect(9.6, 25, 24.4, 30.5, 1.2, ORANGE)
    for x in (12, 15, 18, 21):
        c.line([(x, 26.2), (x, 29.3)], 0.7, (236, 150, 80, 255))


def pin(c):
    arrow(c)
    pts = []
    cx, cy, r = 24, 20, 5
    for k in range(40):
        a = math.pi * 0.85 + k / 39 * (2 * math.pi - math.pi * 0.7)
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    c.poly(pts + [(cx, 30.5)], ORANGE)
    c.ellipse(cx, cy, 1.9, 1.9, CREAM)


def person(c):
    arrow(c)
    c.ellipse(24, 19, 3.2, 3.2, ORANGE)
    c.poly([(18.2, 30.5), (18.6, 26.5), (21, 23.4), (27, 23.4), (29.4, 26.5), (29.8, 30.5)], ORANGE)


def build_set():
    previews = {}
    previews['Arrow'] = write_cur('Arrow', arrow, (2, 2))
    previews['Help'] = write_cur('Help', help_, (2, 2))
    previews['Working'] = write_ani('Working', working, (2, 2))
    previews['Busy'] = write_ani('Busy', lambda c, f: leaf_spin(c, f), (16, 16))
    previews['Precision'] = write_cur('Precision', crosshair, (16, 16))
    previews['Text'] = write_cur('Text', ibeam, (16, 16))
    previews['Handwriting'] = write_cur('Handwriting', pen, (3, 29))
    previews['Unavailable'] = write_cur('Unavailable', no, (16, 16))
    previews['SizeNS'] = write_cur('SizeNS', size_rot(0), (16, 16))
    previews['SizeWE'] = write_cur('SizeWE', size_rot(math.pi / 2), (16, 16))
    previews['SizeNWSE'] = write_cur('SizeNWSE', size_rot(-math.pi / 4), (16, 16))
    previews['SizeNESW'] = write_cur('SizeNESW', size_rot(math.pi / 4), (16, 16))
    previews['Move'] = write_cur('Move', size_all, (16, 16))
    previews['Alternate'] = write_cur('Alternate', up, (16, 2))
    previews['Link'] = write_cur('Link', hand, (12.5, 2))
    previews['Pin'] = write_cur('Pin', pin, (2, 2))
    previews['Person'] = write_cur('Person', person, (2, 2))
    return previews


if __name__ == '__main__':
    rows = []
    for sub, scale in VARIANTS:
        DEST, SCALE = os.path.join(OUT, sub), scale
        os.makedirs(DEST, exist_ok=True)
        rows.append(build_set())
        print('built', sub or 'Standard', scale)
    n = len(rows[0])
    sheet = Image.new('RGBA', (n * 76 + 12, len(rows) * 76 + 12), (120, 110, 100, 255))
    for r, previews in enumerate(rows):
        for i, im in enumerate(previews.values()):
            sheet.alpha_composite(im, (12 + i * 76, 12 + r * 76))
    sheet.save(os.path.join(sys.argv[2] if len(sys.argv) > 2 else OUT, 'cursors_preview.png'))
    print('ok')
