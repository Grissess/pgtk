import csv, argparse, sys

parser = argparse.ArgumentParser(description='Sort a CSV file')

parser.add_argument('csv', help='CSV file to sort')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-c', '--column', action='append', default=[], help='Sort by this column; can be specified multiple times (left to right is outer sort to inner sort); default is CSV fields in order')
parser.add_argument('-m', '--map', action='append', default=[], help='Given column:function, map function (usually a lambda, Python syntax) over this column, effective only when determining sort order (e.g., "Column:float" to sort numerically)')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

rows = []
rdr = csv.DictReader(open(args.csv))
key = args.column
maps = {}
for spec in args.map:
    col, _, func = spec.partition(':')
    maps[col] = eval(func)
iden = lambda x: x

for row in rdr:
    if not key:
        key = rdr.fieldnames
    rows.append(row)

rows.sort(key=lambda r: tuple(maps.get(f, iden)(r[f]) for f in key))

out = csv.DictWriter(fo, rdr.fieldnames)
out.writeheader()

for row in rows:
    try:
        out.writerow(row)
    except ValueError:
        print(f'Offending row: {row}', file=sys.stderr)
        raise
