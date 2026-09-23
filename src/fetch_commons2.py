"""Second Commons pass: broader (no quality-category restriction), >=2560px,
PNW-focused plus cozy extras. Skips anything already fetched."""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
import fetch_wallpapers as F

OUT = sys.argv[1]
F.OUT = OUT
QUERIES = [
    ('larch autumn washington', 12), ('golden larches', 10), ('north cascades autumn', 12), ('mount rainier autumn', 12),
    ('mount baker autumn', 8), ('mount hood autumn', 8), ('columbia river gorge autumn', 10), ('multnomah falls autumn', 5),
    ('oregon autumn forest', 10), ('willamette valley autumn', 6), ('olympic national park fog', 8), ('hoh rain forest', 6),
    ('seattle autumn', 8), ('portland oregon autumn', 8), ('vancouver autumn', 8), ('british columbia autumn', 10),
    ('washington autumn', 10), ('enchantments larches', 6), ('snoqualmie autumn', 6), ('lake chelan autumn', 5),
    ('stowe vermont autumn', 8), ('woodstock vermont', 6), ('new england autumn church', 8), ('kancamagus autumn', 6),
    ('adirondack autumn', 10), ('acadia autumn', 8), ('connecticut autumn', 8), ('apple orchard autumn', 6),
    ('pumpkin patch', 6), ('autumn fog', 10), ('autumn cozy', 4),
]


def search2(q, limit=50):
    d = F.api({'action': 'query', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': limit,
               'gsrsearch': f'{q} filew:>2560 filetype:bitmap',
               'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata|mime', 'iiurlwidth': 3840,
               'iiextmetadatafilter': 'LicenseShortName|Artist'})
    return sorted(d.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 0))


if __name__ == '__main__':
    prev = json.load(open(os.path.join(OUT, '..', 'candidates.json'), encoding='utf8'))
    seen = {p['title'] for p in prev}
    stems = {}
    for p in prev:
        stems[F.stem(p['title'])] = stems.get(F.stem(p['title']), 0) + 1
    items = []
    for q, cap in QUERIES:
        got = 0
        for p in search2(q):
            if got >= cap:
                break
            t = p['title']
            if t in seen or 'imageinfo' not in p:
                continue
            ii = p['imageinfo'][0]
            w, h = ii['width'], ii['height']
            lic = ii.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '')
            if ii.get('mime') != 'image/jpeg' or w < 2560 or not (1.3 <= w / h <= 2.4) or not F.OK_LIC.match(lic):
                continue
            st = F.stem(t)
            if stems.get(st, 0) >= 2:
                continue
            seen.add(t)
            stems[st] = stems.get(st, 0) + 1
            got += 1
            items.append({'title': t, 'query': q, 'width': w, 'height': h, 'license': lic,
                          'artist': F.strip_html(ii['extmetadata'].get('Artist', {}).get('value', '')),
                          'source': ii['descriptionurl'], 'thumb': ii.get('thumburl') or ii['url']})
        print(q, got, flush=True)
        time.sleep(0.3)
    print('candidates', len(items), flush=True)
    with ThreadPoolExecutor(3) as ex:
        done = list(ex.map(F.download, list(enumerate(items, 501))))
    ok = [d for d in done if d.get('file')]
    json.dump(ok, open(os.path.join(OUT, '..', 'credits_commons2.json'), 'w', encoding='utf8'), indent=1)
    print('ok', len(ok), 'failed', len(done) - len(ok))
