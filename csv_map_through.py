import csv, argparse, os, sys

parser = argparse.ArgumentParser(description='Map the values in the columns of a CSV file through the fields of another CSV')

parser.add_argument('csv', help='CSV file to map')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-c', '--column', required=True, help='Column in input file to map')
parser.add_argument('-m', '--map-file', required=True, help='CSV to use as mapping source')
parser.add_argument('-f', '--from', required=True, help='Column in map-file to use as source')
parser.add_argument('-t', '--to', required=True, help='Column in map-file to use as result')
parser.add_argument('-d', '--default', default='', help='Value to insert if no source was found in map-file')
parser.add_argument('-D', '--delete', action='store_true', help='Instead of using a default, delete rows for which no source was found in map-file')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

mappings = {}

for row in csv.DictReader(open(args.map_file)):
    mappings[row[getattr(args, 'from')]] = row[args.to]

out = None
rdr = csv.DictReader(open(args.csv))
skips = 0

for row in rdr:
    if out is None:
        out = csv.DictWriter(fo, rdr.fieldnames)
        out.writeheader()
    if args.delete:
        if row[args.column] not in mappings:
            skips += 1
            continue
    row[args.column] = mappings.get(row[args.column], args.default)
    out.writerow(row)

print(f'Done, {skips} skipped.')
