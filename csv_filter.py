import csv, argparse, sys

parser = argparse.ArgumentParser(description='Filters rows in a CSV according to a predicate')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--output', help='File to write (default stdout)')
parser.add_argument('-p', '--predicate', required=True, help='Function to apply (Python syntax), receiving row dict as argument')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

pred = eval(args.predicate)

rdr = csv.DictReader(open(args.csv))
out = None

for row in rdr:
    if out is None:
        out = csv.DictWriter(fo, rdr.fieldnames)
        out.writeheader()
    if pred(row):
        out.writerow(row)
