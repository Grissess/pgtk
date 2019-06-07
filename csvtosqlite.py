import csv, sqlite3, argparse, os

parser = argparse.ArgumentParser(description='Converts CSV files to SQLite3 databases')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('-o', '--out', help='SQLite3 file to write (defaults to basename + .sqlite)')
parser.add_argument('-t', '--table', help='SQLite3 table to write (defaults to basename)')
parser.add_argument('-d', '--delete', action='store_true', help='Delete previous table contents')
parser.add_argument('-D', '--drop', action='store_true', help='Drop the table if it exists')

args = parser.parse_args()
if args.out is None:
    args.out = os.path.splitext(os.path.basename(args.csv))[0] + '.sqlite'
if args.table is None:
    args.table = os.path.splitext(os.path.basename(args.csv))[0]

rdr = csv.DictReader(open(args.csv))
con = sqlite3.connect(args.out)

if args.drop:
    con.execute(f'DROP TABLE IF EXISTS {args.table}')
con.execute(f'CREATE TABLE IF NOT EXISTS {args.table} ({", ".join(rdr.fieldnames)})')
if args.delete:
    con.execute(f'DELETE FROM {args.table}')

script = f'INSERT INTO {args.table} ({", ".join(rdr.fieldnames)}) VALUES ({", ".join(":" + i for i in rdr.fieldnames)})'
cur = con.cursor()
cur.executemany(script, rdr)

con.commit()
