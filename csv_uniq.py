import csv, argparse, sys

parser = argparse.ArgumentParser(description='Remove duplicate entries from a CSV')

parser.add_argument('csv', help='CSV file to remove duplicates from')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-I', '--ignore', action='append', default=[], help='Ignore values in this column when checking for duplicates (given a collision amongst other columns, only the first encountered value in this column will be preserved)')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

rows = {}
key = None
rdr = csv.DictReader(open(args.csv))
drops = 0

for row in rdr:
    if key is None:
        key = tuple(f for f in rdr.fieldnames if f not in args.ignore)
    val = tuple(row[i] for i in key)
    if val not in rows:
        rows[val] = row
    else:
        drops += 1

out = csv.DictWriter(fo, rdr.fieldnames)
out.writeheader()

for row in rows.values():
    out.writerow(row)

print(f'Done, {drops} dropped.', file=sys.stderr)
