import csv, argparse, sys

parser = argparse.ArgumentParser(description='Sums down the columns of a CSV')

parser.add_argument('csv', help='CSV file to read')

args = parser.parse_args()

rdr = csv.DictReader(open(args.csv))
sums = {f: 0.0 for f in rdr.fieldnames}
for row in rdr:
    for k, v in row.items():
        if k not in sums:
            continue
        if not v:
            continue
        try:
            fv = float(v)
        except ValueError:
            print(f'Dropping {k} from sum (non-numeric value {v})', file=sys.stderr)
            del sums[k]
        else:
            sums[k] += fv

wr = csv.DictWriter(sys.stdout, sums.keys())
wr.writeheader()
wr.writerow(sums)
