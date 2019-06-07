import csv, argparse, sys

parser = argparse.ArgumentParser(description='Maps a Python function onto a column of a CSV')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-c', '--column', required=True, help='Column to map over')
parser.add_argument('-f', '--function', required=True, help='Function to apply (lambda is useful here--receives column value as string as only argument)')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

funct = eval(args.function)

rdr = csv.DictReader(open(args.csv))
out = None

for row in rdr:
    if out is None:
        out = csv.DictWriter(fo, rdr.fieldnames)
        out.writeheader()
    row[args.column] = funct(row[args.column])
    out.writerow(row)
