import argparse, os, sys, csv, colorsys, math, sqlite3

parser = argparse.ArgumentParser(description='Generate versus LR plots')

parser.add_argument('-t', '--title', help='Title for chart')
parser.add_argument('--no-title', action='store_true', help="Don't generate a title")
parser.add_argument('-s', '--series', action='append', default=[], help='Add a data series (first becomes X axis); see --help-series')
parser.add_argument('--help-series', action='store_true', help='Print help about -s/--series (and do nothing else)')
parser.add_argument('--races', default='Black,Hispanic,Caucasian,Asian,LR', help='Races (comma separated) possibly available in each series (ignored if not available)')
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
parser.add_argument('--quartile-pt', dest='quartile_pts', action='append', default=[7, 5, 9, 13], help='Add a point style to the quartile point rotation')
parser.add_argument('--clear-quartile-pt', dest='quartile_pts', action='store_const', const=[], help='Clear all previous quartile point styles (including the defaults)')
parser.add_argument('--no-sanity', dest='no_sanity', action='store_true', help='Turn off some sanity checks for performance')
parser.add_argument('--col-offset', dest='col_offset', type=float, default=0.33, help='Hue offset in [0, 1] for graph series colors')
parser.add_argument('--quads', dest='quads', action='store_true', help='Enumerate keys for quadrants in the non-primary series')
parser.add_argument('--verbeq', dest='verbeq', action='store_true', help='Show verbal equivalency lines on the LR axes (check the defaults!)')
parser.add_argument('--verbeq-steps', dest='verbeq_steps', type=int, default=3, help='Steps in the verbal equivalency in either direction (default 3)')
parser.add_argument('--verbeq-range', dest='verbeq_range', type=float, default=1.0, help='Difference in log10 LR considered a step (default 1.0)')
parser.add_argument('--every', dest='every', type=int, help='Provide progress after importing this many rows from each series')
parser.add_argument('--mode', dest='mode', default='scatter', help='Graph mode (default: scatter)')
parser.add_argument('--backing', dest='backing', help='Use this file as data backing (if RAM is insufficient)')

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
db = sqlite3.connect(args.backing if args.backing else ':memory:')
cur = db.cursor()
cur.execute('DROP INDEX IF EXISTS series_key')
cur.execute('DROP TABLE IF EXISTS series')
cur.execute('CREATE TABLE series (idx, cnum, contr, value)')
cur.execute('CREATE INDEX series_key ON series (cnum, contr)')
titles = []
for sidx, sdesc in enumerate(args.series):
    parts = sdesc.split(':')
    fn = parts[0]
    if len(parts) < 2 or not parts[1]:
        filt = lambda row: True
    else:
        conds = [i.split('=') for i in parts[1].split(',')]
        filt = lambda row: all(row[k] == v for k, v in conds)
    if len(parts) < 3 or not parts[2]:
        titles.append(gpesc(sdesc))
    else:
        titles.append(gpesc(parts[2]))
    
    drops = 0
    rdr = csv.DictReader(open(fn))
    for idx, row in enumerate(rdr):
        if args.every is not None and idx % args.every == 0:
            print(f'Series {sidx} ({sdesc}): imported {idx} so far...')
        if not filt(row):
            continue
        key = (row['Case'], row['Contributor'])
        if not args.no_sanity:
            cur.execute('SELECT * FROM series WHERE idx=? AND cnum=? AND contr=?', (sidx,) + key)
            if cur.fetchone() is not None:
                print(f'WARN: dup key {key} in series {sdesc}!', file=sys.stderr)
        try:
            cur.execute('INSERT INTO series VALUES (?, ?, ?, ?)', (sidx,) + key + (mapf(aggf(float(row[i]) for i in races if i in rdr.fieldnames)),))
        except ValueError:
            drops += 1
    print(f'Series {sidx} ({sdesc}) imported with {drops} drops')
    db.commit()

#titles = [
#    f'{gpesc(ser.partition(":")[0])}:{gpesc(",".join(p.partition("=")[2] for p in ser.partition(":")[2].split(",")))}'
#    for ser in args.series
#]
colors = [
    f'#77{r:02x}{g:02x}{b:02x}'
    for r, g, b in [
        map(lambda x: int(255*x), colorsys.hsv_to_rgb(args.col_offset + i/(1+len(args.series)), 1.0, 0.5)) for i in range(len(args.series))
    ]
]
if args.mode == 'scatter':
    cur.execute('SELECT cnum, contr FROM series WHERE idx=0')
    keys = cur.fetchall()
    keys.sort()
    keyset = set(keys)
    plots = []
    pstyles = [args.pts[i % len(args.pts)] for i in range(len(args.series))]
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
        if idx != 0:
            plots.append(f'"{dfn}" with points lw {args.dot_size} pt {pstyles[idx-1]} lc rgb "{colors[idx-1]}" title "{titles[idx]}"')
        df = open(dfn, 'w', 4194304)  # 4M buffer
        df.write(f'# series {args.series[0]} vs {args.series[idx]}\n')
        for kidx, k in enumerate(keys):
            if args.every is not None and kidx % args.every == 0:
                print(f'Series {idx} ({sdesc}): writeout progress {kidx}...')
            cur.execute('SELECT value FROM series WHERE idx=? AND cnum=? AND contr=?', (idx,) + k)
            v = cur.fetchone()
            if v is None:
                continue
            v = v[0]
            cur.execute('SELECT value FROM series WHERE idx=0 AND cnum=? AND contr=?', k)
            v0 = cur.fetchone()[0]  # Shouldn't fail

            df.write(f'{v0}\t{v}\n')
        print(f'Series {idx} ({sdesc}) done writing')
        df.close()

    plots.append(f'ident(x) with lines lc rgb "#77000000" lw 1 title "y=x ({titles[0]})"')

    print('Writing plot file...')
    pf = open(args.basename + '.gp', 'w')
    pf.write(f'''set terminal {args.terminal}
set output "{args.basename}.{args.exten}"
set zeroaxis
set key right bottom font "sans,8" tc variable
set size square
ident(x) = x
''')
    if args.verbeq:
        for eqr in range(args.verbeq_steps):
            val = (eqr+1) * args.verbeq_range
            for v in (val, -val):
                pf.write(f'set arrow from graph 0, first {v} to graph 1, first {v} nohead lw 0.5 lt 2\n')
                pf.write(f'set arrow from {v}, graph 0 to {v}, graph 1 nohead lw 0.5 lt 2\n')
    if args.xr:
        pf.write(f'set xrange {args.xr}\n')
    if args.yr:
        pf.write(f'set yrange {args.yr}\n')
    pmapf = PRETTY_MAPS[args.map]
    if pmapf:
        pf.write(f'set xlabel "LR of {titles[0]} ({pmapf})"\nset ylabel "LR ({pmapf})"\n')

    title = f'x = {titles[0]}'
    if args.title:
        title = args.title + ': ' + title
    if args.no_title:
        pf.write(f'set notitle\n')
    else:
        pf.write(f'set title "{title}"\n')
    pf.write(f'plot {", ".join(plots)}\n')
    pf.close()
elif args.mode in ('percentile', 'percentile-nocmp'):
    comparing = (args.mode == 'percentile')
    print('Writing data files...')
    plots = []
    for idx, sdesc in enumerate(args.series):
        if idx == 0 and comparing:
            continue
        dfn = args.basename + f'.{idx}.data'
        df = open(dfn, 'w', 4194304)
        df.write(f'# series {sdesc} percentile\n')
        kidx = 0
        if comparing:
            cur.execute('SELECT count(*) FROM series AS s1 JOIN series AS s2 USING (cnum, contr) WHERE s1.idx = 0 AND s2.idx = ?', (idx,))
        else:
            cur.execute('SELECT count(*) FROM series WHERE idx = ?', (idx,))
        total = cur.fetchone()[0]
        for row in cur.execute(
                'SELECT s2.value - s1.value FROM series AS s1 JOIN series AS s2 USING (cnum, contr) WHERE s1.idx = 0 AND s2.idx = ? ORDER BY (s2.value - s1.value)'
                if comparing else
                'SELECT value FROM series WHERE idx = ? ORDER BY value', (idx,)):
            if args.every is not None and kidx % args.every == 0:
                print(f'Series {idx} ({sdesc}): writeout progress {kidx}/{total}...')
            df.write(f'{2*(kidx/total)-1}\t{row[0]}\n')
            kidx += 1
        ddfn = args.basename + f'.{idx}.dots.data'
        ddf = open(ddfn, 'w', 4194304)
        ddf.write(f'#series {sdesc} points\n')
        for quart in (0, total // 4, total // 2, 3 * total // 4, total - 1):
            cur.execute(
                'SELECT s2.value - s1.value FROM series AS s1 JOIN series AS s2 USING (cnum, contr) WHERE s1.idx = 0 AND s2.idx = ? ORDER BY (s2.value - s1.value) LIMIT 1 OFFSET ?'
                if comparing else
                'SELECT value FROM series WHERE idx = ? ORDER BY value LIMIT 1 OFFSET ?', (idx, quart))
            ddf.write(f'{2*(quart/total)-1}\t{cur.fetchone()[0]}\n')
        print(f'Series {idx} ({sdesc}) done writing {total} points')
        effidx = idx - 1 if comparing else idx
        style = args.quartile_pts[effidx % len(args.quartile_pts)]
        plots.append(f'"{dfn}" using 1:2:(0) with linespoints pt {style} pi {total} ps variable lc rgb "{colors[idx-1]}" title "{titles[idx]}"')
        plots.append(f'"{ddfn}" with points lc rgb "{colors[idx-1]}" pt {style} notitle')

    print('Writing plot file...')
    pf = open(args.basename + '.gp', 'w')
    pf.write(f'''set terminal {args.terminal}
set output "{args.basename}.{args.exten}"
set zeroaxis
set key right bottom font "sans,8" tc variable
set size square
set xtics ("0%%" -1, "50%%" 0, "100%%" 1)
set xrange [-1:1]
''')
    if args.xr:
        pf.write(f'set xrange {args.xr}\n')
    if args.yr:
        pf.write(f'set yrange {args.yr}\n')
    pmapf = PRETTY_MAPS[args.map]
    if pmapf:
        pf.write(f'set xlabel "Percentile"\nset ylabel "LR {" - (LR_{" + titles[0] + "})" if comparing else ""} ({pmapf})"\n')

    if comparing:
        title = f'{titles[0]} as x = 0'
        if args.title:
            title = args.title + ': ' + title
    else:
        title = ''
        if args.title:
            title = args.title
    if args.no_title:
        pf.write(f'set notitle\n')
    else:
        pf.write(f'set title "{title}"\n')
    pf.write(f'plot {", ".join(plots)}\n')
    pf.close()
elif args.mode == 'changeover':
    print('Writing data files...')
    if len(args.series) != 2:
        print('This mode only supports two series; aborting.')
        exit()
else:
    raise ValueError('Unknown plot mode')

if args.quads:
    QUADS = {
        1: ('>', '>'),
        2: ('<', '>'),
        3: ('<', '<'),
        4: ('>', '<'),
    }

    print('Writing quadrants...')

    for sidx in range(1, len(args.series)):
        for quad, ops in QUADS.items():
            print(f'Series {sidx} ({args.series[sidx]}) quadrant {quad}')
            s1o, s2o = ops
            f = open(f'{args.basename}.ser{sidx}.quad{quad}.csv', 'w')
            f.write('Case,Contributor,PrimValue,SeriesValue\n')
            for case, contr, s1v, s2v in cur.execute(f'SELECT s1.cnum, s1.contr, s1.value, s2.value FROM series AS s1 JOIN series AS s2 USING (cnum, contr) WHERE s1.idx=0 AND s2.idx=? AND s1.value{s1o}0 AND s2.value{s2o}0', (sidx,)):
                f.write(f'{case},{contr},{s1v},{s2v}\n')
            f.close()
