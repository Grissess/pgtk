import csv, argparse, sys

parser = argparse.ArgumentParser(description='Maps a Python function onto a column of a CSV')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--output', help='File to write (defaults to stdout)')
parser.add_argument('-H', '--header', help='Macro to invoke with header names')
parser.add_argument('-c', '--column', nargs='*', help='name:macro for a column name, wrap each value in a call to macro')
parser.add_argument('-T', '--transpose', action='store_true', help='Transpose the table, swapping rows and columns (requires more memory)')

args = parser.parse_args()

fo = sys.stdout
if args.output is not None:
    fo = open(args.output, 'w')

rdr = csv.DictReader(open(args.csv))
out = None
colmacs = {}
for c in args.column or ():
    col, _, mac = c.partition(':')
    colmacs[col] = mac

hf = lambda x: x
if args.header:
    hf = lambda x: f'\\{args.header}{{{x}}}'

if args.transpose:
    data = list(rdr)
    fields = rdr.fieldnames
    fo.write(f'\\begin{{tabular}}{{ c|{"".join("c" for _ in fields)} }}\n')
    for frow in fields:
        row = [
            (hf(frow) if i == 0 else (
                f'\\{colmacs[frow]}{{{data[i-1][frow]}}}' if frow in colmacs else data[i-1][frow]
            ))
            for i in range(len(data)+1)
        ]
        fo.write(f'\t{" & ".join(row)} \\\\\n')
else:
    for row in rdr:
        if out is None:
            out = True
            fo.write(f'\\begin{{tabular}}{{ {"".join("c" for _ in rdr.fieldnames)} }}\n')
            fo.write(f'\t{" & ".join(hf(f) for f in rdr.fieldnames)} \\\\ \\hline \n')
        vals = [(f'\\{colmacs[f]}{{{row[f]}}}' if f in colmacs else row[f]) for f in rdr.fieldnames]
        fo.write(f'\t{" & ".join(vals)} \\\\\n')
fo.write('\\end{tabular}\n')
