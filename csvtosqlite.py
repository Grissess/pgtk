import csv, sqlite3, argparse, os, sys

parser = argparse.ArgumentParser(description='Converts CSV files to SQLite3 databases')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--out', help='SQLite3 file to write (defaults to basename + .sqlite)')
parser.add_argument('-t', '--table', help='SQLite3 table to write (defaults to basename)')
parser.add_argument('-d', '--delete', action='store_true', help='Delete previous table contents')
parser.add_argument('-D', '--drop', action='store_true', help='Drop the table if it exists')

KEYWORDS = {'case'}

args = parser.parse_args()
if args.out is None:
    args.out = os.path.splitext(os.path.basename(args.csv))[0] + '.sqlite'
if args.table is None:
    args.table = os.path.splitext(os.path.basename(args.csv))[0]

rdr = csv.DictReader(open(args.csv))
con = sqlite3.connect(args.out)

if args.drop:
    con.execute(f'DROP TABLE IF EXISTS {args.table}')
fnames = [fn + '_' if fn.lower() in KEYWORDS else fn for fn in rdr.fieldnames]
print(fnames, file=sys.stderr)
con.execute(f'CREATE TABLE IF NOT EXISTS {args.table} ({", ".join(fnames)})')
if args.delete:
    con.execute(f'DELETE FROM {args.table}')

script = f'INSERT INTO {args.table} ({", ".join(fnames)}) VALUES ({", ".join(":" + i for i in rdr.fieldnames)})'
print(script, file=sys.stderr)
cur = con.cursor()
cur.executemany(script, rdr)

con.commit()
