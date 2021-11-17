import csv, argparse, sys

parser = argparse.ArgumentParser(description='Sorts field (column) names of a CSV')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-f', '--first', nargs='*', help='Put these columns first, before any sorting')
parser.add_argument('-l', '--last', nargs='*', help='Put these columns last, before any sorting')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

rdr = csv.DictReader(open(args.csv))
out = None

for row in rdr:
    if out is None:
        tosort = rdr.fieldnames[:]
        firsts = []
        for f in args.first or ():
            try:
                tosort.remove(f)
            except ValueError:
                print('WARNING: first', f, 'not in columns')
            else:
                firsts.append(f)
        lasts = []
        for l in args.last or ():
            try:
                tosort.remove(l)
            except ValueError:
                print('WARNING: last', l, 'not in columns')
            else:
                lasts.append(l)
        fields = firsts + sorted(tosort) + lasts
        out = csv.DictWriter(fo, fields)
        out.writeheader()
    out.writerow(row)
