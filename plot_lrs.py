import argparse, os, sys, csv, colorsys, math, sqlite3

parser = argparse.ArgumentParser(description='Generate versus LR plots')

parser.add_argument('-t', '--title', help='Title for chart')
parser.add_argument('-s', '--series', action='append', default=[], help='Add a data series (first becomes X axis); see --help-series')
parser.add_argument('--help-series', action='store_true', help='Print help about -s/--series (and do nothing else)')
parser.add_argument('--races', default='Black,Hispanic,Caucasian,Asian', help='Races (comma separated) available in each series')
parser.add_argument('--agg', default='min', help='Aggregator function over races')
parser.add_argument('--map', default='log10', help='Mapping function over data points')
parser.add_argument('basename', help='Basename of files to generate (.ps, .data)')
parser.add_argument('--exten', default='ps', help='Output graphic file extension')
parser.add_argument('--terminal', default='postscript color', help='GNUPlot terminal to use (with options)')
parser.add_argument('--dot-size', type=int, default=2, help='Dot size (actually lw) to specify for each plot')
parser.add_argument('--xr', help='Set X range (GNUPlot syntax)')
parser.add_argument('--yr', help='Set Y range (GNUPlot syntax)')
parser.add_argument('--pt', dest='pts', action='append', default=[5, 6, 9, 2], help='Add a point style to the rotation')
parser.add_argument('--clear-pt', dest='pts', action='store_const', const=[], help='Clear all previous point styles (including default)')
parser.add_argument('--no-sanity', dest='no_sanity', action='store_true', help='Turn off some sanity checks for performance')

args = parser.parse_args()

AGGS = {
    'min': min,
    'max': max,
}
MAPS = {
    'id': lambda x: x,
    'log10': math.log10,
}
PRETTY_MAPS = {
    'id': '',
    'log10': 'log_{10}',
}

def gpesc(s):
    return s.replace('_', '\\\\_')

if args.help_series:
    print('''Series are of the form:

-s filename[:constraints]

Where constraints may be a comma separated list of equality tests between columns and values; e.g.:

-s foo.csv:Dropout=PHOM,Statistic=GEOM_MEAN,Dropin=NPC0

An empty constraint list does no filtering.''')
    exit()

aggf = AGGS.get(args.agg)
if not aggf:
    print(f'Bad aggregate function {args.agg}!', file=sys.stderr)
    exit(1)
mapf = MAPS.get(args.map)
if not mapf:
    print(f'Bad mapping function {args.map}!', file=sys.stderr)
    exit(1)
races = args.races.split(',')

print('Reading series...', file=sys.stderr)
db = sqlite3.connect('/var/tmp/plot.db')
cur = db.cursor()
cur.execute('DROP TABLE IF EXISTS series')
cur.execute('CREATE TABLE series (idx, cnum, contr, value)')
for sidx, sdesc in enumerate(args.series):
    parts = sdesc.split(':')
    fn = parts[0]
    if len(parts) < 2 or not parts[1]:
        filt = lambda row: True
    else:
        conds = [i.split('=') for i in parts[1].split(',')]
        filt = lambda row: all(row[k] == v for k, v in conds)
    
    rdr = csv.DictReader(open(fn))
    for row in rdr:
        if not filt(row):
            continue
        key = (row['Case'], row['Contributor'])
        if not args.no_sanity:
            cur.execute('SELECT * FROM series WHERE idx=? AND cnum=? AND contr=?', (sidx,) + key)
            if cur.fetchone() is not None:
                print(f'WARN: dup key {key} in series {sdesc}!', file=sys.stderr)
        cur.execute('INSERT INTO series VALUES (?, ?, ?, ?)', (sidx,) + key + (mapf(aggf(float(row[i]) for i in races)),))

cur.execute('SELECT cnum, contr FROM series WHERE idx=0')
keys = cur.fetchall()
keys.sort()
keyset = set(keys)
plots = []
colors = [
    f'#77{r:02x}{g:02x}{b:02x}'
    for r, g, b in [
        map(lambda x: int(255*x), colorsys.hsv_to_rgb(i*0.75/len(args.series), 1.0, 0.5)) for i in range(len(args.series))
    ]
]
pstyles = [args.pts[i % len(args.pts)] for i in range(len(args.series))]
titles = [
    f'{gpesc(ser.partition(":")[0])}:{gpesc(",".join(p.partition("=")[2] for p in ser.partition(":")[2].split(",")))}'
    for ser in args.series
]
print(f'generated {len(keys)} keys', file=sys.stderr)

print('Writing data files...')
for idx, sdesc in enumerate(args.series):
    if not args.no_sanity:
        cur.execute('SELECT cnum, contr FROM series WHERE idx=?', (idx,))
        dkeys = set(cur.fetchall())
        nx, ny = len(keyset - dkeys), len(dkeys - keyset)
        if nx:
            print(f'WARN: series {args.series[idx]} is missing {nx} keys', file=sys.stderr)
        if ny:
            print(f'WARN: series {args.series[idx]} has {ny} keys that won\'t be displayed', file=sys.stderr)

    dfn = args.basename + f'.{idx}.data'
    plots.append(f'"{dfn}" with points lw {args.dot_size} pt {pstyles[idx]} lc rgb "{colors[idx]}" title "{titles[idx]}"')
    df = open(dfn, 'w')
    df.write(f'# series {args.series[0]} vs {args.series[idx]}\n')
    for k in keys:
        cur.execute('SELECT value FROM series WHERE idx=? AND cnum=? AND contr=?', (idx,) + k)
        v = cur.fetchone()
        if v is None:
            continue
        v = v[0]
        cur.execute('SELECT value FROM series WHERE idx=0 AND cnum=? AND contr=?', k)
        v0 = cur.fetchone()[0]  # Shouldn't fail

        df.write(f'{v0}\t{v}\n')
    df.close()

print('Writing plot file...')
pf = open(args.basename + '.gp', 'w')
pf.write(f'''set terminal {args.terminal}
set output "{args.basename}.{args.exten}"
set zeroaxis
set key right bottom font "sans,16" tc variable
''')
if args.xr:
    pf.write(f'set xrange {args.xr}\n')
if args.yr:
    pf.write(f'set yrange {args.yr}\n')
pmapf = PRETTY_MAPS[args.map]
if pmapf:
    pf.write(f'set xlabel "{pmapf}"\nset ylabel "{pmapf}"\n')

title = f'x = {titles[0]}'
if args.title:
    title = args.title + ': ' + title
pf.write(f'set title "{title}"\n')
pf.write(f'plot {", ".join(plots)}\n')
pf.close()
