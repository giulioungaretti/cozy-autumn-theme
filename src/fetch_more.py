"""Fetch more cozy autumn wallpapers from Openverse (CC aggregator) and Bing
Images (Creative Commons license filter). Min width 2560, landscape only."""
import hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from PIL import Image

OUT = sys.argv[1]
UA_API = 'CozyAutumnTheme/1.0 (personal desktop wallpaper script; contact gungaretti@microsoft.com)'
UA_WEB = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
MIN_W = 2560

OPENVERSE = [
    'larch autumn', 'north cascades fall', 'mount rainier fall', 'oregon fall colors', 'portland oregon autumn',
    'seattle autumn', 'columbia gorge fall', 'vancouver autumn', 'pacific northwest fall', 'olympic peninsula fog',
    'hoh rainforest', 'mount baker fall', 'mount hood fall', 'washington fall foliage', 'vermont fall',
    'new hampshire fall foliage', 'maine fall foliage', 'kancamagus', 'woodstock vermont', 'stowe vermont',
    'new england fall', 'covered bridge fall', 'pumpkin patch', 'apple orchard autumn', 'autumn fog forest',
    'fall leaves', 'maple leaves autumn', 'autumn lake', 'autumn cabin', 'rainy autumn', 'autumn small town',
    'autumn street', 'fall farm', 'autumn barn', 'autumn mountains', 'autumn misty morning', 'fall foliage road',
    'autumn woods path', 'autumn sunrise', 'autumn cozy',
]
BING = [
    'autumn vermont landscape', 'fall foliage new england', 'pacific northwest autumn', 'golden larches',
    'autumn forest fog', 'autumn lake reflection', 'cozy autumn', 'autumn leaves', 'autumn village church',
    'autumn country road', 'autumn cabin woods', 'autumn rain window', 'pumpkins autumn', 'autumn mountains',
    'fall foliage covered bridge', 'autumn misty forest', 'oregon autumn', 'washington state autumn',
    'maine autumn', 'new hampshire autumn', 'autumn waterfall', 'autumn park path', 'autumn farm barn',
]


def get(url, ua, as_json=False, timeout=60):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': ua})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return json.loads(data) if as_json else data
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            time.sleep(4 * (attempt + 1))
        except Exception:
            time.sleep(2)
    return None


def openverse(q, pages=2):
    out = []
    for page in range(1, pages + 1):
        u = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode(
            {'q': q, 'size': 'large', 'aspect_ratio': 'wide', 'page_size': 20, 'page': page})
        d = get(u, UA_API, as_json=True)
        if not d:
            break
        for r in d.get('results', []):
            w, h = r.get('width') or 0, r.get('height') or 0
            if r.get('source') == 'wikimedia' or (w and w < MIN_W):
                continue
            out.append({'url': r['url'], 'source': r.get('foreign_landing_url') or r['url'],
                        'artist': r.get('creator') or '', 'license': f"CC {r.get('license', '').upper()} {r.get('license_version') or ''}".strip(),
                        'title': r.get('title') or q, 'query': q, 'provider': 'openverse/' + (r.get('source') or '')})
        time.sleep(1.2)
    return out


def bing(q, n=70):
    out = []
    for first in (0, 35):
        u = 'https://www.bing.com/images/async?' + urllib.parse.urlencode({
            'q': q, 'first': first, 'count': 35, 'mmasync': 1,
            'qft': '+filterui:license-L2_L3_L4+filterui:imagesize-wallpaper+filterui:aspect-wide'})
        page = get(u, UA_WEB)
        if not page:
            break
        for m in re.finditer(r'\bm="(\{[^"]+\})"', page.decode('utf8', 'ignore')):
            try:
                j = json.loads(html.unescape(m.group(1)))
            except Exception:
                continue
            if j.get('murl'):
                out.append({'url': j['murl'], 'source': j.get('purl', ''), 'artist': '', 'license': 'Creative Commons (per Bing license filter)',
                            'title': j.get('t', q), 'query': q, 'provider': 'bing'})
        time.sleep(1.5)
    return out[:n]


def download(args):
    i, it = args
    name = f"{it['provider'].split('/')[0][:2]}-{i:03d}-{re.sub(r'[^A-Za-z0-9]+', '-', it['query']).strip('-')}.jpg"
    path = os.path.join(OUT, name)
    it['file'] = None
    data = get(it['url'], UA_WEB if it['provider'] == 'bing' else UA_API, timeout=90)
    if not data:
        return it
    try:
        im = Image.open(BytesIO(data))
        im.load()
        im = im.convert('RGB')
    except Exception:
        return it
    if im.width < MIN_W or not (1.3 <= im.width / im.height <= 2.4):
        return it
    if im.width > 3840:
        im = im.resize((3840, round(im.height * 3840 / im.width)), Image.LANCZOS)
    im.save(path, 'JPEG', quality=92, optimize=True, progressive=True)
    it['file'] = name
    it['md5'] = hashlib.md5(data).hexdigest()
    return it


if __name__ == '__main__':
    items, seen = [], set()
    for q in OPENVERSE:
        got = [x for x in openverse(q) if x['url'] not in seen]
        for x in got[:12]:
            seen.add(x['url'])
            items.append(x)
        print('ov', q, len(got[:12]), flush=True)
    for q in BING:
        got = [x for x in bing(q) if x['url'] not in seen and 'wikimedia.org' not in x['url']]
        for x in got[:15]:
            seen.add(x['url'])
            items.append(x)
        print('bing', q, len(got[:15]), flush=True)
    print('candidates', len(items), flush=True)
    done = []
    with ThreadPoolExecutor(6) as ex:
        for k, it in enumerate(ex.map(download, list(enumerate(items, 1)))):
            done.append(it)
            if k % 25 == 0:
                print('processed', k, flush=True)
    ok = [d for d in done if d.get('file')]
    json.dump(ok, open(os.path.join(OUT, '..', 'credits_more.json'), 'w', encoding='utf8'), indent=1)
    print('ok', len(ok), 'rejected/failed', len(done) - len(ok))
