import csv, argparse, sys

parser = argparse.ArgumentParser(description='Maps a Python function onto a column of a CSV')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-c', '--column', nargs='*', help='Column to map over')
parser.add_argument('-A', '--invert', action='store_true', help='-c specifies columns to NOT map over')
parser.add_argument('-E', '--entire', help='Function receives whole row, not just columns (overrides selectors)--parameter names output column')
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
        fn = [args.entire] if args.entire is not None else rdr.fieldnames
        out = csv.DictWriter(fo, fn)
        out.writeheader()
        cols = args.column
        if args.invert:
            cols = rdr.fieldnames[:]
            for col in args.column or ():
                try:
                    cols.remove(col)
                except ValueError:
                    print('WARNING: column', col, 'not in columns')
        if not (cols or args.entire is not None):
            print('WARNING: Empty set of columns to map, passing through.')
    if args.entire is not None:
        out.writerow({args.entire: funct(row)})
    else:
        for col in cols:
            row[col] = funct(row[col])
        out.writerow(row)
