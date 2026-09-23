"""Bing Images (Creative Commons filter) pass with an explicit minimum pixel size.
Reuses helpers from fetch_more. Min width 1920, landscape only; exact dupes skipped by md5."""
import glob, hashlib, json, os, re, sys, time, html, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import fetch_more as F

OUT = sys.argv[1]
F.OUT = OUT
F.MIN_W = 1920
QFT = '+filterui:licenseType-Any+filterui:imagesize-wallpaper+filterui:aspect-wide'
QUERIES = [
    'vermont fall foliage', 'vermont autumn village', 'vermont covered bridge autumn', 'stowe vermont fall',
    'new hampshire fall foliage', 'white mountains autumn', 'maine autumn coast', 'massachusetts autumn',
    'connecticut autumn town', 'new england church fall', 'autumn farmhouse', 'red barn autumn',
    'pacific northwest fall forest', 'oregon fall foliage', 'washington larches', 'north cascades autumn',
    'mount rainier autumn', 'columbia river gorge autumn', 'olympic national park fog', 'misty evergreen forest',
    'autumn rain forest moss', 'rainy autumn street', 'autumn cafe', 'autumn bookstore street',
    'small town autumn main street', 'autumn maple tree', 'maple leaves close up', 'autumn leaves on ground',
    'autumn forest path', 'foggy autumn morning', 'autumn river', 'autumn pond reflection', 'autumn lake cabin',
    'log cabin autumn', 'autumn hills sunrise', 'autumn valley', 'blue ridge autumn', 'adirondacks fall',
    'smoky mountains fall', 'autumn birch forest', 'aspen autumn', 'autumn orchard apples', 'pumpkins farm',
    'autumn harvest field', 'autumn country lane', 'autumn stone wall', 'autumn waterfall forest',
    'autumn park bench', 'autumn sunset mountains', 'fall colors lake', 'autumn scenery', 'fall landscape',
]


def bing(q, pages=3):
    out = []
    for p in range(pages):
        u = 'https://www.bing.com/images/async?' + urllib.parse.urlencode(
            {'q': q, 'first': p * 35, 'count': 35, 'mmasync': 1, 'qft': QFT})
        page = F.get(u, F.UA_WEB)
        if not page:
            break
        for m in re.finditer(r'\bm="(\{[^"]+\})"', page.decode('utf8', 'ignore')):
            try:
                j = json.loads(html.unescape(m.group(1)))
            except Exception:
                continue
            if j.get('murl'):
                out.append({'url': j['murl'], 'source': j.get('purl', ''), 'artist': '',
                            'license': 'Creative Commons (per Bing license filter)',
                            'title': j.get('t', q), 'query': q, 'provider': 'bing'})
        time.sleep(1.2)
    return out


if __name__ == '__main__':
    base = os.path.join(OUT, '..')
    seen = set()
    for cj in glob.glob(os.path.join(base, 'credits*.json')):
        for c in json.load(open(cj, encoding='utf8')):
            seen.add(c.get('url') or c.get('source'))
    md5s = {hashlib.md5(open(p, 'rb').read()).hexdigest() for p in glob.glob(os.path.join(OUT, 'bi-*.jpg'))}
    items = []
    for q in QUERIES:
        got = [x for x in bing(q) if x['url'] not in seen and 'wikimedia.org' not in x['url']
               and 'staticflickr' not in x['url']]
        for x in got[:45]:
            seen.add(x['url'])
            items.append(x)
        print('bing', q, len(got[:45]), flush=True)
    print('candidates', len(items), flush=True)
    done = []
    with ThreadPoolExecutor(8) as ex:
        for k, it in enumerate(ex.map(F.download, list(enumerate(items, 501)))):
            if it.get('file') and it.get('md5') in md5s:
                os.remove(os.path.join(OUT, it['file']))
                it['file'] = None
            if it.get('file'):
                md5s.add(it['md5'])
            done.append(it)
            if k % 50 == 0:
                print('processed', k, flush=True)
    ok = [d for d in done if d.get('file')]
    json.dump(ok, open(os.path.join(base, 'credits_bing2.json'), 'w', encoding='utf8'), indent=1)
    print('ok', len(ok), 'rejected/failed', len(done) - len(ok))
