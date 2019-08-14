import csv, argparse, sys

parser = argparse.ArgumentParser(description='Count predicate-matching lines in a CSV')

parser.add_argument('csv', nargs='?', help='CSV file to read (default stdin)')
parser.add_argument('-p', '--predicate', help='Matching predicate (compiled as lambda row: ...)')

args = parser.parse_args()

fi = sys.stdin
if args.csv is not None:
    fi = open(args.csv, 'r')

rdr = csv.DictReader(fi)
pred = lambda _: True
if args.predicate:
    pred = eval('lambda row: ' + args.predicate)

counter = 0
total = 0

for row in rdr:
    total += 1
    if pred(row):
        counter += 1

print('Matched,Total')
print(f'{counter},{total}')
