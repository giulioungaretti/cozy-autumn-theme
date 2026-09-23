"""Fetch cozy autumn 4K wallpapers from Wikimedia Commons (freely licensed).

Writes JPEGs to OUT and a credits.json with author/license/source for each.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from PIL import Image

OUT = sys.argv[1]
UA = 'CozyAutumnTheme/1.0 (personal desktop wallpaper script; contact gungaretti@microsoft.com)'
API = 'https://commons.wikimedia.org/w/api.php'
OK_LIC = re.compile(r'^(CC0|Public domain|PD|CC BY(-SA)? [1-4]\.0|CC BY(-SA)? 2\.5|CC BY(-SA)? 3\.0.*)', re.I)

QUALITY = ['"Quality images"', '"Featured pictures on Wikimedia Commons"', '"Valued images sorted by promotion date"']
QUERIES = [
    # Vermont / New England
    ('autumn vermont', 30), ('fall foliage vermont', 20), ('vermont october', 20), ('stowe autumn', 8),
    ('new hampshire autumn', 20), ('white mountains autumn', 15), ('maine autumn', 15), ('acadia autumn', 10),
    ('massachusetts autumn', 12), ('berkshires autumn', 8), ('connecticut autumn', 10), ('covered bridge autumn', 12),
    ('new england church autumn', 8), ('adirondacks autumn', 12), ('catskills autumn', 8), ('hudson valley autumn', 8),
    # Pacific Northwest
    ('larches autumn washington', 12), ('north cascades autumn', 12), ('mount rainier autumn', 12),
    ('mount baker autumn', 10), ('oregon autumn', 15), ('columbia river gorge autumn', 10), ('olympic national park fog', 8),
    ('british columbia autumn', 12), ('pacific northwest forest fog', 8), ('mount hood autumn', 8),
    # general cozy autumn
    ('autumn forest fog', 20), ('autumn lake reflection', 20), ('autumn leaves maple', 15), ('autumn road trees', 15),
    ('autumn trail forest', 15), ('autumn colors mountain', 15), ('autumn morning mist', 15), ('autumn river', 15),
    ('pumpkins', 8), ('autumn cabin', 6), ('autumn rain', 6), ('autumn village', 10), ('autumn park', 12),
    ('quebec autumn', 12), ('algonquin autumn', 8), ('great smoky mountains autumn', 10), ('blue ridge autumn', 10),
    ('autumn waterfall', 12), ('autumn aspen', 10), ('autumn birch', 8), ('golden hour autumn', 8),
]


def api(params):
    params = dict(params, format='json')
    url = API + '?' + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(2 + attempt * 3)
    return {}


def search(q, cat, limit=50):
    s = f'{q} filew:>3800 filetype:bitmap incategory:{cat}'
    d = api({'action': 'query', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': limit, 'gsrsearch': s,
             'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata|mime', 'iiurlwidth': 3840,
             'iiextmetadatafilter': 'LicenseShortName|Artist|ImageDescription'})
    pages = d.get('query', {}).get('pages', {})
    return sorted(pages.values(), key=lambda p: p.get('index', 0))


def strip_html(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()


def stem(title):
    t = re.sub(r'^File:', '', title)
    t = re.sub(r'\.\w+$', '', t)
    t = re.sub(r'[\d_\-\s\(\)]+$', '', t)
    t = re.sub(r'\d{2,}', '#', t)
    return t.lower()


def collect():
    chosen, seen, stems = [], set(), {}
    for q, cap in QUERIES:
        got = 0
        for cat in QUALITY:
            if got >= cap:
                break
            for p in search(q, cat):
                if got >= cap:
                    break
                t = p['title']
                if t in seen or 'imageinfo' not in p:
                    continue
                ii = p['imageinfo'][0]
                w, h = ii['width'], ii['height']
                lic = ii.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '')
                if ii.get('mime') != 'image/jpeg' or w < 3800 or not (1.3 <= w / h <= 2.4) or not OK_LIC.match(lic):
                    continue
                st = stem(t)
                if stems.get(st, 0) >= 2:
                    continue
                seen.add(t)
                stems[st] = stems.get(st, 0) + 1
                got += 1
                chosen.append({'title': t, 'query': q, 'width': w, 'height': h, 'license': lic,
                               'artist': strip_html(ii['extmetadata'].get('Artist', {}).get('value', '')),
                               'source': ii['descriptionurl'], 'thumb': ii['thumburl']})
            time.sleep(0.3)
        print(f'{q!r}: {got}', flush=True)
    return chosen


def fname(item, i):
    base = re.sub(r'[^A-Za-z0-9]+', '-', re.sub(r'^File:|\.\w+$', '', item['title'])).strip('-')[:70]
    return f'{i:03d}-{base}.jpg'


def download(args):
    i, item = args
    path = os.path.join(OUT, fname(item, i))
    item['file'] = os.path.basename(path)
    if os.path.exists(path):
        return item
    for attempt in range(6):
        try:
            req = urllib.request.Request(item['thumb'], headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            im = Image.open(BytesIO(data)).convert('RGB')
            if im.width > 3840:
                im = im.resize((3840, round(im.height * 3840 / im.width)), Image.LANCZOS)
            im.save(path, 'JPEG', quality=92, optimize=True, progressive=True)
            return item
        except urllib.error.HTTPError as e:
            time.sleep(5 * (attempt + 1) if e.code == 429 else 2)
        except Exception:
            time.sleep(2)
    item['file'] = None
    return item


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cand_path = os.path.join(OUT, '..', 'candidates.json')
    if os.path.exists(cand_path):
        items = json.load(open(cand_path, encoding='utf8'))
    else:
        items = collect()
        json.dump(items, open(cand_path, 'w', encoding='utf8'), indent=1)
    print('candidates:', len(items), flush=True)
    done = []
    with ThreadPoolExecutor(3) as ex:
        for k, it in enumerate(ex.map(download, list(enumerate(items, 1)))):
            done.append(it)
            if k % 20 == 0:
                print('downloaded', k, flush=True)
    ok = [d for d in done if d.get('file')]
    json.dump(ok, open(os.path.join(OUT, '..', 'credits.json'), 'w', encoding='utf8'), indent=1)
    print('ok', len(ok), 'failed', len(done) - len(ok))
