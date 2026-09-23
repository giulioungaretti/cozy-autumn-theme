"""Bing pass 3: red/orange-focused queries; keeps only images with >=18% red/orange pixels."""
import glob, json, os, sys
from concurrent.futures import ThreadPoolExecutor
import fetch_more as F
import fetch_bing2 as B
from warmth import warmth

OUT = sys.argv[1]
F.OUT = OUT
F.MIN_W = 1920
MIN_WARM = 0.18
QUERIES = [
    'red maple tree fall', 'orange autumn forest', 'red autumn leaves forest', 'vine maple red autumn',
    'sugar maple orange', 'vermont red fall foliage', 'fiery autumn colors', 'orange autumn road',
    'red autumn trees lake', 'autumn sunset orange forest', 'red maple leaves', 'red leaves forest path',
    'orange leaves on ground', 'peak foliage new england', 'red barn fall foliage', 'orange pumpkins field',
    'autumn golden hour forest', 'red oak autumn', 'red huckleberry mountain autumn', 'red maple swamp autumn',
    'algonquin park fall colors', 'quebec autumn red', 'orange larches sunset', 'new hampshire red foliage',
    'maine red maple', 'autumn red hillside', 'blazing fall colors', 'autumn orange lake reflection',
    'red covered bridge autumn', 'crimson autumn forest', 'orange fall foliage mountains', 'red autumn park',
    'autumn copper beech', 'orange autumn village', 'cozy autumn orange', 'red leaves rain',
    'mount rainier red huckleberry', 'north cascades red fall color', 'oregon red vine maple', 'autumn orange sunrise mist',
]


def download(args):
    it = F.download(args)
    if it.get('file'):
        p = os.path.join(OUT, it['file'])
        w, g = warmth(p)
        it['warm'] = w
        if w < MIN_WARM:
            os.remove(p)
            it['file'] = None
    return it


if __name__ == '__main__':
    base = os.path.join(OUT, '..')
    seen = set()
    for cj in glob.glob(os.path.join(base, 'credits*.json')):
        for c in json.load(open(cj, encoding='utf8')):
            seen.add(c.get('url') or c.get('source'))
    items = []
    for q in QUERIES:
        got = [x for x in B.bing(q) if x['url'] not in seen and 'wikimedia.org' not in x['url']
               and 'staticflickr' not in x['url']]
        for x in got[:45]:
            seen.add(x['url'])
            items.append(x)
        print('bing3', q, len(got[:45]), flush=True)
    print('candidates', len(items), flush=True)
    done = []
    with ThreadPoolExecutor(8) as ex:
        for k, it in enumerate(ex.map(download, list(enumerate(items, 5001)))):
            done.append(it)
            if k % 100 == 0:
                print('processed', k, flush=True)
    ok = [d for d in done if d.get('file')]
    json.dump(ok, open(os.path.join(base, 'credits_bing3.json'), 'w', encoding='utf8'), indent=1)
    print('ok', len(ok), 'rejected/failed', len(done) - len(ok))
