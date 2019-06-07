import csv, sys, argparse, sqlite3, os
import admonitions, fst_dropoutrate

__version__ = (0, 0, 1)

parser = argparse.ArgumentParser(description='Copies FSTs dropout rates into a CSV file')

parser.add_argument('file', help='CSV file to generate')
parser.add_argument('--db', help='Database to use (defaults to fst_dropout_rates.sqlite) in the directory of this script')
parser.add_argument('--table', default='fst_dropout_rates', help='Table to use in database')
parser.add_argument('-k', '--kit', default='Identifiler', help='Kit used in validation study')

args = parser.parse_args()

if args.db is None:
    args.db = os.path.join(os.path.dirname(sys.argv[0]), 'fst_dropout_rates.sqlite')

con = sqlite3.connect(args.db)
cur = con.cursor()
out = None
rdr = csv.DictReader(open(args.file))
casecache = {}
locmap = {}

cur.execute(f'SELECT DISTINCT Locus FROM {args.table}')
locii = sorted(map(lambda x: x[0], cur.fetchall()))
cur.execute(f'SELECT DISTINCT Dropout FROM {args.table}')
types = sorted(map(lambda x: x[0], cur.fetchall()))

for row in rdr:
    #print(row)

    if out is None:
        out = csv.DictWriter(sys.stdout, rdr.fieldnames + types)
        out.writeheader()

    caseno = int(row['Case Name'])
    if caseno not in casecache:
        casecache[caseno] = fst_dropoutrate.calc_dropout(
            float(row['Quant']),
            args.kit,
            int(row['Contributors']),
            row['D/ND'].upper() == 'D',
            con = con,
        )
        #print('New case', caseno)
        #print(casecache[caseno])
    rates = casecache[caseno]

    loc = locmap.get(row['Locus'], row['Locus'])
    if loc not in rates:
        for k in locii:
            if k.startswith(loc):
                locmap[row['Locus']] = k
                loc = k

    new = row.copy()
    for t in types:
        rate = rates.get(loc, {}).get(t)
        new[t] = str(rate) if rate is not None else 'ERROR'

    out.writerow(new)
