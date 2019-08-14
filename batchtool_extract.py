import sqlite3, csv, argparse, sys, os, json, ntpath, re

parser = argparse.ArgumentParser(description='Stand-in for a full extraction from the batch tool')

parser.add_argument('db', help='batcher database')
#parser.add_argument('--cols', default='Asian,Black,Caucasian,Hispanic,LociSum,UsedRare', help='CSV columns to read from odata (comma separated)')
parser.add_argument('--cols', default='Asian,Black,Caucasian,Hispanic', help='CSV columns to read from odata (comma separated)')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')

args = parser.parse_args()

db = sqlite3.connect(args.db)

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

NUM_RE = re.compile(r'\d+')
def map_casename(cn):
    #return ntpath.splitext(ntpath.basename(cn))[0]
    return NUM_RE.search(cn).group(0)

def map_ncont_cont(co):
    ident = ntpath.splitext(ntpath.basename(co))[0]
    dirn = ntpath.basename(ntpath.dirname(co))
    return f'{dirn}_{ident}'

def map_cont_cont(co):
    return ntpath.splitext(ntpath.basename(co))[0]

map_cont = map_cont_cont  # TODO: make configurable

cols = args.cols.split(',')
fns = ['Case', 'Contributor'] + cols
wr = csv.DictWriter(fo, fns)
wr.writeheader()

for row in db.execute('SELECT evidence, profile, odata FROM batch_data'):
    if not row[2]:
        continue
    cname = map_casename(row[0])
    cont = map_cont(row[1])
    odata = json.loads(row[2])
    row = {'Case': cname, 'Contributor': cont}
    for k in cols:
        v = odata[k]
        if isinstance(v, float):
            row[k] = 10.0**v
        elif isinstance(v, list):
            row[k] = ';'.join(v)
        else:
            raise TypeError(type(v))
    wr.writerow(row)
