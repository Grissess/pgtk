import csv, argparse, os, sys, itertools

parser = argparse.ArgumentParser(description='Transposes one CSV column\'s values into one column per value, or vice versa')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--output', help='File to write (defaults to standard out for redirection)')
parser.add_argument('--to-columns', help='Column with values to transpose (row -> column transposition)')
parser.add_argument('--receiver', help='Column with value to fill into the new column created by --to-columns')
parser.add_argument('--fill-value', default='', help='Value used to fill --to-columns columns when no matching datum exists')
parser.add_argument('--from-column', nargs='*', help='Column to transpose into a row (column -> row transposition--give multiple times)')
parser.add_argument('--name', help='Name of the new column containing the old-column-name as a value (for --from-column)')

args = parser.parse_args()

if not (args.from_column or args.to_columns):
    print('Invalid configuration: specify either --to-columns or --from-column many times', file=sys.stderr)
    parser.print_help(sys.stderr)
    exit()

if (args.name or args.from_column) and (args.to_columns or args.fill_value or args.receiver):
    print('Invalid configuration: specify either --to-columns + --receiver once (optionally with --fill-value), or --from-column many times + --name', file=sys.stderr)
    exit()
if args.from_column and not args.name:
    print('Invalid configuration: specify --name to name the column from which the --from-column values will be extracted as data', file=sys.stderr)
    exit()
if args.to_columns and not args.receiver:
    print('Invalid configuration: specify --receiver to name the column from which --to-columns data will be gathered', file=sys.stderr)
    exit()

if args.output is None:
    fo = sys.stdout
else:
    fo = open(args.output, 'w')

rdr = csv.DictReader(open(args.csv))
rows = list(rdr)
if not rows:
    print('Input is empty! No operation can be performed.', file=sys.stderr)
    exit()

if args.to_columns:
    if args.to_columns not in rows[0]:
        print(f'Column {args.to_columns} not found in data (columns: {list(rows[0].keys())}', file=sys.stderr)
        exit()
    if args.receiver not in rows[0]:
        print(f'Column {args.receiver} not found in data (columns: {list(rows[0].keys())}', file=sys.stderr)
        exit()

    values = set(row[args.to_columns] for row in rows)
    headers = list(rows[0].keys())
    headers.remove(args.to_columns)
    headers.remove(args.receiver)
    old_headers = headers[:]
    headers += list(values)

    newrows = {} # (tuple of old_headers) -> {dict mapping member of values -> {set of receiving values}}

    for row in rows:
        key = tuple(row[v] for v in old_headers)
        if key not in newrows:
            newrows[key] = {}
        nr = newrows[key]
        cn = row[args.to_columns]
        cv = row[args.receiver]
        if cn not in nr:
            nr[cn] = set()
        else:
            print(f'WARN: possibly ambiguous (multivalued) for column {cn} values {nr[cn]} plus {cv}', file=sys.stderr)
        nr[cn].add(cv)

    out = csv.DictWriter(fo, headers)
    out.writeheader()

    print(f'{len(newrows)} base rows to output', file=sys.stderr)
    for key, cols in newrows.items():
        for v in values:
            if v not in cols:
                cols[v] = {args.fill_value}
        baserow = {k: v for k, v in zip(old_headers, key)}
        kvs = list(cols.items())
        for vs in itertools.product(*(kv[1] for kv in kvs)):
            row = baserow.copy()
            row.update({k: v for k, v in zip((kv[0] for kv in kvs), vs)})
            out.writerow(row)

else:
    print('TODO: column -> row transposition', file=sys.stderr)
