import csv, argparse, sys

parser = argparse.ArgumentParser(description='Merges multiple CSVs together')

parser.add_argument('csvs', nargs='+', help='CSV files to read (optionally with :label appended)')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-d', '--default', default='', help='Default value for merged columns not present in input')
parser.add_argument('-D', '--delete', action='store_true', help='Instead of storing default, delete rows that have no data in at least one column')
parser.add_argument('-c', '--column', required=True, help='Column to store source filename or label into')
parser.add_argument('-I', '--intersect', action='store_true', help='Output the intersection, not the union, of fields found in input files (overrides -d/-D)')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

csv_data = {}
csv_fields = {}

for csvf in args.csvs:
    if ':' in csvf:
        csvf, _, label = csvf.partition(':')
    else:
        label = csvf
    csv_data[label] = list(csv.DictReader(open(csvf)))
    csv_fields[label] = set(csv_data[label][0].keys())
    
if args.intersect:
    fields = list(csv_fields.values())[0]
else:
    fields = set()
for fld in csv_fields.values():
    if args.intersect:
        fields = fields & fld
    else:
        fields = fields | fld
fields = list(fields)

out = csv.DictWriter(fo, [args.column] + fields)
out.writeheader()

for label, data in csv_data.items():
    for row in data:
        outrow = {args.column: label}
        ok = True
        for fld in fields:
            if args.delete and fld not in row:
                ok = False
                break
            outrow[fld] = row.get(fld, args.default)
        if not ok:
            continue
        out.writerow(outrow)
