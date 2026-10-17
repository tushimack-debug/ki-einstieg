"""Find public ATS job-board slugs in the Common Crawl URL index (public dataset, data.commoncrawl.org).
Reads parquet footers via HTTP range requests, then only row groups whose url_surtkey range overlaps the ATS prefixes."""
import io, sys, time, urllib.request
import pyarrow.parquet as pq
from concurrent.futures import ThreadPoolExecutor
PREFIXES = ['de,personio,jobs,', 'com,personio,jobs,', 'io,greenhouse,boards)/', 'io,greenhouse,job-boards)/', 'io,greenhouse,eu,job-boards)/',
            'co,lever,jobs)/', 'com,ashbyhq,jobs)/', 'com,smartrecruiters,jobs)/', 'com,smartrecruiters,careers)/', 'com,recruitee,', 'com,workable,apply)/', 'com,join)/companies/']

class RangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method='HEAD')
        self.size = int(urllib.request.urlopen(req, timeout=60).headers['Content-Length'])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b''
        end = min(self.size, self.pos + n) - 1
        for attempt in range(5):
            try:
                req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{end}'})
                data = urllib.request.urlopen(req, timeout=120).read(); break
            except Exception:
                time.sleep(2 * (attempt + 1))
        else: raise OSError('range read failed')
        self.pos += len(data); return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

def overlaps(lo, hi):
    return any(hi >= p and lo < p + '\xff' for p in PREFIXES)

def scan(item):
    i, url = item
    for attempt in range(3):
        try:
            f = pq.ParquetFile(RangeFile(url))
            break
        except Exception as e:
            err = e; time.sleep(5)
    else: return i, [], f'ERR {err}'
    col = f.schema_arrow.get_field_index('url_surtkey')
    groups = []
    for g in range(f.num_row_groups):
        st = f.metadata.row_group(g).column(col).statistics
        if st and st.has_min_max and overlaps(st.min, st.max): groups.append(g)
    rows = []
    for g in groups:
        t = f.read_row_group(g, columns=['url_surtkey', 'url'])
        for s, u in zip(t.column(0).to_pylist(), t.column(1).to_pylist()):
            if any(s.startswith(p) for p in PREFIXES): rows.append(u)
    return i, rows, f'{len(groups)} groups'

paths = ['https://data.commoncrawl.org/' + p.strip() for p in open(sys.argv[1] if len(sys.argv) > 1 else 'paths.txt')]
with open('cc_urls.txt', 'a') as out, ThreadPoolExecutor(6) as ex:
    for i, rows, msg in ex.map(scan, enumerate(paths)):
        out.write(''.join(u + '\n' for u in rows)); out.flush()
        if rows or msg.startswith('ERR'): print(i, len(rows), msg, flush=True)
print('done', flush=True)
