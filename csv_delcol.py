import csv, argparse, sys

parser = argparse.ArgumentParser(description='Deletes columns in a CSV')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-d', '--delete', nargs='+', default=[], help='Column(s) to delete')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

rdr = csv.DictReader(open(args.csv))
out = None

for row in rdr:
    if out is None:
        fields = list(rdr.fieldnames)
        for d in args.delete:
            try:
                fields.remove(d)
            except ValueError:
                print(f'Couldn\'t find column {d} to delete', file=sys.stderr)
        out = csv.DictWriter(fo, fields)
        out.writeheader()
    for d in args.delete:
        if d in row:
            del row[d]
    out.writerow(row)
