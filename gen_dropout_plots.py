import argparse, sqlite3, os, sys, colorsys
import admonitions

__version__ = (0, 0, 1)

parser = argparse.ArgumentParser(description='Generates dropout rate plots')

parser.add_argument('--db', help='Database to use (defaults to fst_dropout_rates.sqlite) in the directory of this script')
parser.add_argument('--table', help='Table in databse (default fst_dropout_rates)', default='fst_dropout_rates')
parser.add_argument('-v', '--verbose', action='store_true', help='Explain the actions taken by the program in detail')
parser.add_argument('-o', '--output', default='fdr', help='Prefix for all plot files')
parser.add_argument('--ignore', action='append', type=int, help='Ignore this quantity--pretend it does not exist in the database')
parser.add_argument('--interpolation', default='fst', help='Interpolation (FST or correct)')
parser.add_argument('--no-101-round', action='store_true', help="Don't emulate FST's logic for always rounding in 100-101pg to 101pg")
parser.add_argument('--gp-filled-circle', type=int, default=7, help='Point style for a filled point')
parser.add_argument('--gp-circle', type=int, default=6, help='Point style for a (non-filled) point')
parser.add_argument('--exten', default='ps', help='Output graphic file extension')
parser.add_argument('--terminal', default='postscript color', help='GNUPlot terminal to use (with options)')

args = parser.parse_args()

if args.db is not None or args.interpolation != 'fst' or args.no_101_round:
    print(admonitions.COMPLIANCE)
    if args.db is not None:
        print('--db: potentially non-standard DB')
    if args.interpolation != 'fst':
        print('--interpolation: Nonstandard interpolation')
    if args.no_101_round:
        print('--no-101-round: defeats a dubious measure in FST')

interpolators = {}
def interpolation_fst(x1, y1, x2, y2):
    return y1 + (y2-y1)/(x2-x1)*x2
interpolators['fst'] = interpolation_fst
def interpolation_correct(x1, y1, x2, y2):
    return y2
interpolators['correct'] = interpolation_correct

interp = interpolators[args.interpolation]

if args.db is None:
    args.db = os.path.join(os.path.dirname(sys.argv[0]), 'fst_dropout_rates.sqlite')

con = sqlite3.connect(args.db)
cur = con.cursor()

conflict = False
# Lab Kit mappings
labkits = {}
for row in cur.execute(f'SELECT DISTINCT LabKitID, LabKit FROM {args.table}'):
    lkid, lk = row
    if lkid in labkits:
        print(f'WARNING: Duplicate lkid entry detected: {lkid} is {lk} and also {labkits[lkid]}')
        conflict = True
    labkits[lkid] = lk

# Type mappings
types = {}
for row in cur.execute(f'SELECT DISTINCT typeID, Dropout FROM {args.table}'):
    typeid, typename = row
    if typeid in types:
        print(f'WARNING: Duplicate typeid entry detected: {typeid} is {typename} and also {types[typeid]}')
        conflict = True
    types[typeid] = typename

# Locus mappings
locii = {}
for row in cur.execute(f'SELECT DISTINCT LocusID, Locus FROM {args.table}'):
    lcid, lc = row
    if lcid in locii:
        print(f'WARNING: Duplicate lcid entry detected: {lcid} is {lc} and also {locii[lcid]}')
        conflict = True
    locii[lcid] = lc

# Quantity mappings
quantities = {}
for row in cur.execute(f'SELECT DISTINCT dropOptionID, Quant FROM {args.table}'):
    dpid, q = row
    if q in quantities:
        print(f'WARNING: Duplicate dpid entrt detected: {dpid} is {q} and also {quantities[dpid]}')
        conflict = True
    quantities[dpid] = q

if conflict:
    print(admonitions.UNDEFINED_BEHAVIOR)
    print('conflict: a duplicate typeid, lkid, lcid, or dpid was detected')

if args.verbose:
    print('Labkits:')
    for lkid, lk in labkits.items():
        print(f'\t{lkid}: {lk}')
    print('Types:')
    for typeid, typename in types.items():
        print(f'\t{typeid}: {typename}')
    print('Locii:')
    for lcid, lc in locii.items():
        print(f'\t{lcid}: {lc}')
    print('Quantities:')
    for dpid, q in quantities.items():
        print(f'\t{dpid}: {q}')
    print()

cur.execute(f'SELECT DISTINCT LabKitID, typeID, NoOfPersonsInvolvd, Deducible FROM {args.table}')
cases = cur.fetchall()

print(f'{len(cases)} cases to process')

rungs = [p[0] for p in sorted(((s, float(s[:-3])) for s in quantities.values()), key=lambda p: p[1])]
if args.ignore:
    for ign in args.ignore:
        try:
            rungs.remove(ign)
        except ValueError:
            print(f'(tried to remove nonexistent quantity {ign})')
    drops = f' with drops {", ".join(args.ignore)}'
else:
    drops = ''

rounding = ', no 100->101 round' if args.no_101_round else ', rounding 100->101'

print(f'considering quantities {rungs}')

colors = [
    f'#ee{r:02x}{g:02x}{b:02x}'
    for r, g, b in map(lambda p: map(lambda x: int(255*x), p), (colorsys.hsv_to_rgb(i*0.66/len(locii), 1.0, 1.0) for i in range(len(locii))))
]
print(f'colors: {colors}')

pf = open(f'{args.output}.gp', 'w')
#FIXME: Dynamic width
pf.write(f'''set terminal {args.terminal}
set output "{args.output}.{args.exten}"
set yrange [* < 0:1]
set xrange [0:550]
set object 1 rectangle from -100, -100 to 600, 0 fc rgb "#FFCCCC" behind
''')

for cid, case in enumerate(cases):
    lkid, typeid, npers, deduc = case
    lk = labkits[lkid]
    typename = types[typeid]
    deduc = deduc.lower() == 'yes'
    print(f'Case {cid}/{len(cases)}: kit {lk} type {typename} no {npers} deduc {deduc}: ', end='')

    fn = f'{args.output}c{cid}.data'
    df = open(fn, 'w')

    plots = []
    i = 0
    for lcid, lc in locii.items():
        dprs = {}
        xvs = []
        for rung in rungs:
            cur.execute(f'SELECT DropOutRate FROM {args.table} WHERE LabKitID=? AND typeID=? AND NoOfPersonsInvolvd=? AND lower(Deducible)=? AND Quant=? AND LocusID=?',
                    (lkid, typeid, npers, 'yes' if deduc else 'no', rung, lcid),
            )
            rows = cur.fetchall()
            if len(rows) != 1:
                print(f'ERROR: too many/not enough results for plot for locus {lc} rung {lrung}: {rows}')
                exit()
            if rung.endswith(' pg'):
                rung = rung[:-3]
            rung = float(rung)
            dprs[rung] = float(rows[0][0])
            xvs.append(rung)

        df.write(f'# {lc} lines\n')
        for lrung, hrung in zip(xvs[:-1], xvs[1:]):
            ldr, hdr = dprs[lrung], dprs[hrung]
            if lrung == 100 and not args.no_101_round:
                #print('[activated 101 round] ', end='')
                x1, x2, y1, y2 = float(hrung), float(hrung), hdr, hdr
            else:
                x1, y1 = float(lrung), ldr
                x2, y2 = float(hrung), interp(x1, y1, float(hrung), hdr)
            df.write(f'{x1}\t{y1}\n{x2}\t{y2}\n\n')
        df.write('\n')
        plots.append(f'"{fn}" index {i} with lines title "{lc}" lc rgb "{colors[i//2]}"')
        i += 1
        df.write(f'# {lc} points\n')
        for lrung, hrung in zip(xvs[:-1], xvs[1:]):
            ldr, hdr = dprs[lrung], dprs[hrung]
            if lrung == 100 and not args.no_101_round:
                #print('[activated 101 round] ', end='')
                x1, x2, y1, y2 = float(hrung), float(hrung), hdr, hdr
            else:
                x1, y1 = float(lrung), ldr
                x2, y2 = float(hrung), interp(x1, y1, float(hrung), hdr)
            df.write(f'{x1}\t{y1}\t{args.gp_filled_circle}\n{x2}\t{y2}\t{args.gp_circle}\n')
        df.write(f'{xvs[-1]}\t{dprs[xvs[-1]]}\t{args.gp_filled_circle}\n\n\n')
        plots.append(f'"{fn}" index {i} with dots notitle lc rgb "{colors[i//2]}" lw 5')
        i += 1

    print('Done!')
    pf.write(f'set title "{fn}: kit {lk}, type {typename}, {npers} contributors ({"deductible" if deduc else "non-deductible"}){drops}, interpolation {args.interpolation}{rounding}"\n')
    pf.write(f'plot {", ".join(plots)}\n')


