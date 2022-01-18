import csv, argparse, sys

parser = argparse.ArgumentParser(description='Remove duplicate entries from a CSV')

parser.add_argument('csv', help='CSV file to remove duplicates from')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-I', '--ignore', action='append', default=[], help='Ignore values in this column when checking for duplicates (given a collision amongst other columns, only the first encountered value in this column will be preserved)')
parser.add_argument('-O', '--only', action='append', default=[], help='If specified, only these columns will be considered (overrides --ignore)')
parser.add_argument('-W', '--where', action='append', default=[], help='Given Column=Value, only consider rows where this equality holds')
parser.add_argument('--output-all', action='store_true', help='Write all columns, not just the unique ones, to the output')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

rows = {}
key = None
rdr = csv.DictReader(open(args.csv))
drops = 0
filts = 0

for row in rdr:
    if args.where:
        skip = False
        for wc in args.where:
            col, _, cond = wc.partition('=')
            if row[col] != cond:
                skip = True
                break
        if skip:
            filts += 1
            continue
    if key is None:
        if args.only:
            key = args.only
        else:
            key = tuple(f for f in rdr.fieldnames if f not in args.ignore)
    val = tuple(row[i] for i in key)
    if val not in rows:
        rows[val] = row
    else:
        drops += 1

if args.output_all:
    out = csv.DictWriter(fo, rdr.fieldnames)
else:
    out = csv.DictWriter(fo, key)
out.writeheader()

for row in rows.values():
    if not args.output_all:
        row = {k: v for k, v in row.items() if k in key}
    out.writerow(row)

print(f'Done, {drops} dropped, {filts} filtered.', file=sys.stderr)
