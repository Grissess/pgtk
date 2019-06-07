import argparse, sqlite3, os, sys
import admonitions

__version__ = (0, 0, 1)

con = None
args = None

def verbose_print(*a, **k):
    if args and args.verbose:
        print(*a, **k)

def init():
    global con, args

    parser = argparse.ArgumentParser(description='Calculates dropout rates used by NYS OCME\'s FST')

    parser.add_argument('-q', '--quantity', type=float, help='Amount of DNA material in picograms (pg)')
    parser.add_argument('-n', '--number', type=int, help='Number of presumably involved persons')
    parser.add_argument('-d', '--deducible', action='store_true', help='Set if the number of contributors is deducible (default non-deducible)')
    parser.add_argument('-k', '--kit', help='Lab Kit used (name or ID)')
    parser.add_argument('--kits', action='store_true', help='List all kits used in the local data file')
    parser.add_argument('--no-101-round', action='store_true', help='Don\'t emulate FST\'s logic for always rounding 100pg-101pg to 101pg')
    parser.add_argument('--db', help='Database to use (defaults to fst_dropout_rates.sqlite) in the directory of this script')
    parser.add_argument('-V', '--version', action='store_true', help='Instead of doing anything else, print out version and regulatory information')
    parser.add_argument('-v', '--verbose', action='store_true', help='Explain the actions taken by the program in detail')
    parser.add_argument('--table', default='fst_dropout_rates', help='Table to use in database')

    args = parser.parse_args()

    if args.version:
        print('FST Dropout Rate Tool version', '.'.join(map(str, __version__)))
        print(admonitions.LICENSE)

    print(admonitions.UNVERIFIED)

    if args.version:
        exit()

    if args.no_101_round or args.db:
        print(admonitions.COMPLIANCE)
        if args.no_101_round:
            print('--no-101-round: defeats a dubious measure in FST')
        if args.db:
            print('--db: potentially nonstandard DB specified')
        print()

    if args.db is None:
        args.db = os.path.join(os.path.dirname(sys.argv[0]), 'fst_dropout_rates.sqlite')

    con = sqlite3.connect(args.db)

    if args.kits:
        for row in con.execute(f'SELECT DISTINCT LabKitID, LabKit FROM {args.table}'):
            print(f'Kit "{row[1]}" ID {row[0]}')
        exit()

    if args.quantity is None or args.number is None or args.kit is None:
        print('Need all of -q/--quantity, -n/--number, -k/--kit')
        exit(1)

# These variable names more or less match the source code from FST; apologies for their lack of objective clarity
def calc_dropout(quant, kit, number, deducible, no_101_round=False, con=None, tbl='fst_dropout_rates'):
    if quant > 500:
        verbose_print('quantity capped to 500pg')
        quant = 500

    if 100 < quant < 101:
        if no_101_round:
            verbose_print(f'dropout would have been rounded to 101, but remains at {dropout} because you asked (--no-101-round)')
        else:
            verbose_print('dropout rounded to 101')
            quant = 101

    rungs = (6.25, 12.5, 25, 50, 100, 101, 150, 250, 500)
    if quant in rungs:
        verbose_print(f'quantity is a standard value in {rungs}')
        runglow = quant
        runghigh = quant
    else:
        # Find the interval into which the rate fits
        if quant < rungs[0]:
            print(f'ERROR: quantity {quant} is less than the lowest rung {rungs[0]}; FST would fail in this instance.')
            exit(2)

        for ridx, rung in enumerate(rungs[:-1]):
            if quant > rung and quant < rungs[ridx + 1]:
                verbose_print(f'selected rate interval {rung}, {rungs[ridx + 1]}')
                runglow = rung
                runghigh = rungs[ridx + 1]

    def to_rate(rung):
        if rung == int(rung):
            return f'{int(rung)} pg'
        return f'{rung} pg'

    ratelow, ratehigh = to_rate(runglow), to_rate(runghigh)

    verbose_print(f'selected rates are {ratelow}, {ratehigh}')

    cur = con.cursor()

    def get_rates(r):
        cur.execute(f'SELECT Locus, Dropout, DropOutRate FROM {tbl} WHERE (LabKitID=? OR LabKit=?) AND NoOfPersonsInvolvd=? AND lower(Deducible)=? AND Quant=?', (kit, kit, str(number), 'yes' if deducible else 'no', r))
        rates = {}
        rows = cur.fetchall()
        verbose_print(f'rows queried: {rows}')
        for row in rows:
            lc, typename, rate = row
            if lc not in rates:
                rates[lc] = {}
            if typename in rates[lc]:
                print(f'WARNING: duplicate entryat {lc}/{typename}, overwriting {rates[lc][typename]} with {rate}')
            rates[lc][typename] = float(rate)
        return rates

    lrates = get_rates(ratelow)
    if runglow != runghigh:
        hrates = get_rates(ratehigh)

        frac = (quant - runglow) / (runghigh - runglow)
        orates = {}
        for lc in lrates.keys():
            orates[lc] = {}
            for tn in lrates[lc].keys():
                orates[lc][tn] = lrates[lc][tn] + (hrates[lc][tn] - lrates[lc][tn]) * frac
    else:
        orates = lrates

    return orates

if __name__ == '__main__':
    init()
    orates = calc_dropout(args.quantity, args.kit, args.number, args.deducible, args.no_101_round, con, args.table)

    print('Results:')
    for lc in sorted(orates.keys()):
        for tn in sorted(orates[lc].keys()):
            print(f'{lc}/{tn} = {orates[lc][tn]}')
