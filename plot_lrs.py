import argparse, os, sys, csv, colorsys, math, sqlite3

parser = argparse.ArgumentParser(description='Generate versus LR plots')

parser.add_argument('-t', '--title', help='Title for chart')
parser.add_argument('--no-title', action='store_true', help="Don't generate a title")
parser.add_argument('-s', '--series', action='append', default=[], help='Add a data series (first becomes X axis); see --help-series')
parser.add_argument('--help-series', action='store_true', help='Print help about -s/--series (and do nothing else)')
parser.add_argument('--races', default='Black,Hispanic,Caucasian,Asian,LR', help='Races (comma separated) possibly available in each series (ignored if not available)')
parser.add_argument('--agg', default='min', help='Aggregator function over races')
parser.add_argument('--map', default='log10', help='Mapping function over data points')
parser.add_argument('--series-map', action='append', default=[], help='"idx:func"--set the mapping function for one series')
parser.add_argument('--series-top', action='append', default=[], help='"idx:num"--select only the top num values from the series')
parser.add_argument('--series-bottom', action='append', default=[], help='"idx:num"--select only the bottom num values from the series')
parser.add_argument('basename', help='Basename of files to generate (.ps, .data)')
parser.add_argument('--exten', default='ps', help='Output graphic file extension')
parser.add_argument('--terminal', default='postscript color', help='GNUPlot terminal to use (with options)')
parser.add_argument('--dot-size', type=int, default=2, help='Dot size (actually lw) to specify for each plot')
parser.add_argument('--xr', help='Set X range (GNUPlot syntax)')
parser.add_argument('--yr', help='Set Y range (GNUPlot syntax)')
parser.add_argument('--xl', help='Set X label (default none)')
parser.add_argument('--yl', help='Set Y label (default none)')
parser.add_argument('--pt', dest='pts', action='append', default=[5, 6, 9, 2], help='Add a point style to the rotation')
parser.add_argument('--clear-pt', dest='pts', action='store_const', const=[], help='Clear all previous point styles (including default)')
parser.add_argument('--quartile-pt', dest='quartile_pts', action='append', default=[7, 5, 9, 13], help='Add a point style to the quartile point rotation')
parser.add_argument('--clear-quartile-pt', dest='quartile_pts', action='store_const', const=[], help='Clear all previous quartile point styles (including the defaults)')
parser.add_argument('--no-sanity', dest='no_sanity', action='store_true', help='Turn off some sanity checks for performance')
parser.add_argument('--no-drop', dest='no_drop', action='store_true', help='Fail immediately if a data point is dropped')
parser.add_argument('--col-offset', dest='col_offset', type=float, default=0.33, help='Hue offset in [0, 1] for graph series colors')
parser.add_argument('--quads', dest='quads', action='store_true', help='Enumerate keys for quadrants in the non-primary series')
parser.add_argument('--verbeq', dest='verbeq', action='store_true', help='Show verbal equivalency lines on the LR axes (check the defaults!)')
parser.add_argument('--verbeq-steps', dest='verbeq_steps', type=int, default=3, help='Steps in the verbal equivalency in either direction (default 3)')
parser.add_argument('--verbeq-range', dest='verbeq_range', type=float, default=1.0, help='Difference in log10 LR considered a step (default 1.0)')
parser.add_argument('--every', dest='every', type=int, help='Provide progress after importing this many rows from each series')
parser.add_argument('--mode', dest='mode', default='scatter', help='Graph mode (default: scatter)')
parser.add_argument('--backing', dest='backing', help='Use this file as data backing (if RAM is insufficient)')
parser.add_argument('--veq', action='store_true', help='Add "verbal equivalence" lines (only for non-comparative plots)')
parser.add_argument('--veq-schema', help='"Verbal equivalence" schema (usually per program)')
parser.add_argument('--veq-schemas', help='Instead of doing anything else, print out the known schemata and exit')
parser.add_argument('--veq-add', action='append', default=[], help='"name:value:color"--add an equivalence with the given name for the given value')
parser.add_argument('--zc', action='store_true', help='Annotate the zero crossing of each series on percentile plots')
parser.add_argument('--zc-veq', action='store_true', help='Annotate the verbal equivalent crossings of each series on percentile plots')
parser.add_argument('--zc-add', action='append', default=[], help='"sidx:value[:label[:color]]"--add a crossing mark for this series at this exact value')

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
VEQS = {
        'FST': [('"limited incl."', 1, '#44ffff00'), ('"moderate incl."', 2, '#88ff7700'), ('"strong incl."', 3, '#bbff0000'), ('"limited excl."', -1, '#4400ffff'), ('"moderate excl."', -2, '#8800ff77'), ('"strong excl."', -3, '#bb00ff00')],
}

if args.veq_schemas:
    for key in VEQS.keys():
        print(key)
    exit()

veqs = []
if args.veq_schema:
    veqs.extend(VEQS[args.veq_schema])

if args.veq_add:
    for val in args.veq_add:
        name, value, col = val.split(':')
        veqs.append((name, float(value), col))

if args.veq and not veqs:
    print('WARN: --veq specified but no --veq-add or --veq-schema; nothing will be added')

def gpesc(s):
    return s.replace('_', '\\\\_')

if args.help_series:
    print('''Series are of the form:

-s filename[:constraints]

Where constraints may be a comma separated list of:
- equality tests between columns and values; e.g.:

    -s foo.csv:Dropout=PHOM,Statistic=GEOM_MEAN,Dropin=NPC0

- matches at the beginning of the string, using ^ as the separator:

    -s foo.csv:Contributor^D73

- matches at the end of the string, using $ as the separator:

    -s foo.csv:Contributor$-0

  (remember to shell-quote this one!)

Any of these may be combined in the same list.

After all conditions, a further ':Title' is allowed, setting a custom legend
title.

An empty constraint list does no filtering.

If, after filtering, a series consists of a single sample and the mode is
percentile, a single horizontal line is plotted instead.''')
    exit()

aggf = AGGS.get(args.agg)
if not aggf:
    print(f'Bad aggregate function {args.agg}!', file=sys.stderr)
    exit(1)
mapf = MAPS.get(args.map)
if not mapf:
    print(f'Bad mapping function {args.map}!', file=sys.stderr)
    exit(1)
smap = {}
for sm in args.series_map:
    ix, _, mf = sm.partition(':')
    ix = int(ix)
    if mf not in MAPS:
        print(f'Bad mapping function {mf}!', file=sys.stderr)
        exit(1)
    smap[ix] = MAPS[mf]
stop, sbot = {}, {}
for st in args.series_top:
    ix, _, v = st.partition(':')
    stop[int(ix)] = int(v)
for sb in args.series_bottom:
    ix, _, v = st.partition('_')
    sbot[int(ix)] = int(v)
races = args.races.split(',')
colors = [
    f'#77{r:02x}{g:02x}{b:02x}'
    for r, g, b in [
        map(lambda x: int(255*x), colorsys.hsv_to_rgb(args.col_offset + i/(1+len(args.series)), 1.0, 0.5)) for i in range(len(args.series))
    ]
]
series_crossings = {}
for cross in args.zc_add:
    parts = cross.split(':')
    idx = int(parts[0])
    val = float(parts[1])
    lbl = str(val) if len(parts) < 3 else parts[2]
    col = colors[idx] if len(parts) < 4 else parts[3]
    if col == 'COMPLEMENT':
        col = colors[idx]
        r, g, b = int(col[3:5], 16), int(col[5:7], 16), int(col[7:9], 16)
        col = f'#77{255-r:02x}{255-g:02x}{255-b:02x}'
    if idx not in series_crossings:
        series_crossings[idx] = []
    series_crossings[idx].append((val, lbl, col))

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
    mf = smap.get(sidx, mapf)
    if len(parts) < 2 or not parts[1]:
        filt = lambda row: True
    else:
        conds = []
        for part in parts[1].split(','):
            if '=' in part:
                col, _, val = part.partition('=')
                print(f'Series {sidx}: {sdesc}: condition {col} == {val}')
                conds.append(lambda row, col=col, val=val: row[col] == val)
            elif '^' in part:
                col, _, val = part.partition('^')
                print(f'Series {sidx}: {sdesc}: condition {col} startswith {val}')
                conds.append(lambda row, col=col, val=val: row[col].startswith(val))
            elif '$' in part:
                col, _, part = part.partition('$')
                print(f'Series {sidx}: {sdesc}: condition {col} endswith {val}')
                conds.append(lambda row, col=col, val=val: row[col].endswith(val))
            else:
                raise ValueError(f"Couldn't interpret condition {part} of series {sdesc}")
        filt = lambda row, conds=conds: all(c(row) for c in conds)
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
            cur.execute('INSERT INTO series VALUES (?, ?, ?, ?)', (sidx,) + key + (mf(aggf(float(row[i]) for i in races if i in rdr.fieldnames)),))
        except ValueError:
            drops += 1
            if args.no_drop:
                print(f'FATAL: Failed to add key {key} in series {sdesc}:')
                raise
    print(f'Series {sidx} ({sdesc}) imported with {drops} drops')
    db.commit()

print('Postprocessing series...')
for sidx, bot in sbot.items():
    print(f'Series {sidx}: bottom {bot}')
    cur.execute('SELECT cnum, contr, value FROM series WHERE idx=? ORDER BY value ASC LIMIT ?', (sidx, bot))
    rows = cur.fetchall()
    print(f'... selected {len(rows)} rows')
    cur.execute('DELETE FROM series WHERE idx=?', (sidx,))
    for cnum, contr, value in rows:
        cur.execute('INSERT INTO series (idx, cnum, contr, value) VALUES (?, ?, ?, ?)', (sidx, cnum, contr, value))
    db.commit()

for sidx, top in stop.items():
    print(f'Series {sidx}: top {top}')
    cur.execute('SELECT cnum, contr, value FROM series WHERE idx=? ORDER BY value DESC LIMIT ?', (sidx, top))
    rows = cur.fetchall()
    print(f'... selected {len(rows)} rows')
    cur.execute('DELETE FROM series WHERE idx=?', (sidx,))
    for cnum, contr, value in rows:
        cur.execute('INSERT INTO series (idx, cnum, contr, value) VALUES (?, ?, ?, ?)', (sidx, cnum, contr, value))
    db.commit()

#titles = [
#    f'{gpesc(ser.partition(":")[0])}:{gpesc(",".join(p.partition("=")[2] for p in ser.partition(":")[2].split(",")))}'
#    for ser in args.series
#]
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
    pmaps = ''
    if pmapf:
        pmaps = f' ({pmapf})'
    if args.xl is None:
        args.xl = f"LR of {titles[0]}{pmaps}"
    if args.yl is None:
        args.yl = f"LR{pmaps}"
    if args.xl is not None:
        pf.write(f'set xlabel "{args.xl}"\n')
    if args.yl is not None:
        pf.write(f'set ylabel "{args.yl}"\n')

    title = f'x = {titles[0]}'
    if args.title:
        title = args.title + ': ' + title
    if args.no_title:
        pf.write(f'set notitle\n')
    else:
        pf.write(f'set title "{title}"\n')
    if args.veq and veqs:
        for name, val, col in veqs:
            plots.append(f'{val} title {name!r} lc rgbcolor "{col}"')
    pf.write(f'plot {", ".join(plots)}\n')
    pf.close()
elif args.mode in ('percentile', 'percentile-nocmp'):
    comparing = (args.mode == 'percentile')
    print('Writing data files...')
    plots = []
    labels = []
    for idx, sdesc in enumerate(args.series):
        if idx == 0 and comparing:
            continue
        dfn = args.basename + f'.{idx}.data'
        df = open(dfn, 'w', 4194304)
        df.write(f'# series {sdesc} percentile\n')
        kidx = 0
        zpt = None
        zpts = [None for i in veqs]
        if comparing:
            cur.execute('SELECT count(*) FROM series AS s1 JOIN series AS s2 USING (cnum, contr) WHERE s1.idx = 0 AND s2.idx = ?', (idx,))
        else:
            cur.execute('SELECT count(*) FROM series WHERE idx = ?', (idx,))
        total = cur.fetchone()[0]
        write_twice = total == 1
        saw_neg = None
        saw_negs = [None for i in veqs]
        crossings = series_crossings.get(idx, [])
        c_negs = [None for i in crossings]
        cpts = [None for i in crossings]
        for row in cur.execute(
                'SELECT s2.value - s1.value FROM series AS s1 JOIN series AS s2 USING (cnum, contr) WHERE s1.idx = 0 AND s2.idx = ? ORDER BY (s2.value - s1.value)'
                if comparing else
                'SELECT value FROM series WHERE idx = ? ORDER BY value', (idx,)):
            if args.every is not None and kidx % args.every == 0:
                print(f'Series {idx} ({sdesc}): writeout progress {kidx}/{total}...')
            df.write(f'{2*(kidx/(total-1))-1}\t{row[0]}\n')
            if write_twice:
                df.write(f'1\t{row[0]}\n')
                break
            if args.zc:
                if saw_neg is False and row[0] >= 0:
                    zpt = (kidx/(total-1), row[0])
                saw_neg = row[0] >= 0
            if args.zc_veq:
                for i, elem in enumerate(veqs):
                    val = elem[1]
                    if saw_negs[i] is False and (row[0]-val) >= 0:
                        zpts[i] = (kidx/(total-1), row[0])
                    saw_negs[i] = (row[0]-val) >= 0
            if crossings:
                for i, parts in enumerate(crossings):
                    val = parts[0]
                    if c_negs[i] is False and row[0] >= val:
                        cpts[i] = (kidx/(total-1), row[0])
                    c_negs[i] = row[0] >= val
            kidx += 1
        ddfn = args.basename + f'.{idx}.dots.data'
        ddf = open(ddfn, 'w', 4194304)
        ddf.write(f'#series {sdesc} points\n')
        for quart in (0, total // 4, total // 2, 3 * total // 4, total - 1):
            cur.execute(
                'SELECT s2.value - s1.value FROM series AS s1 JOIN series AS s2 USING (cnum, contr) WHERE s1.idx = 0 AND s2.idx = ? ORDER BY (s2.value - s1.value) LIMIT 1 OFFSET ?'
                if comparing else
                'SELECT value FROM series WHERE idx = ? ORDER BY value LIMIT 1 OFFSET ?', (idx, quart))
            ddf.write(f'{2*(quart/(total-1))-1}\t{cur.fetchone()[0]}\n')
        print(f'Series {idx} ({sdesc}) done writing {total} points')
        effidx = idx - 1 if comparing else idx
        style = args.quartile_pts[effidx % len(args.quartile_pts)]
        plots.append(f'"{dfn}" using 1:2:(0) with linespoints pt {style} pi {total} ps variable lc rgb "{colors[idx-1]}" title "{titles[idx]}"')
        plots.append(f'"{ddfn}" with points lc rgb "{colors[idx-1]}" pt {style} notitle')
        chroff = -0.5 if idx % 2 == 0 else 0.0
        if args.zc and zpt is not None:
            labels.append(f'"{100*zpt[0]:.3f}%" at {2*zpt[0]-1},{zpt[1]} tc rgb "{colors[idx-1]}" font ",6" offset character 0,{chroff} point pt 1 lc rgb "{colors[idx-1]}"')
        if args.zc_veq and zpts:
            for i, pt in enumerate(zpts):
                if pt is None:
                    continue
                labels.append(f'"{100*pt[0]:.3f}%" at {2*pt[0]-1},{pt[1]} tc rgb "{colors[idx-1]}" font ",6" offset character 0,{chroff} point pt 1 lc rgb "{colors[idx-1]}"')
        if crossings:
            for i, pt in enumerate(cpts):
                if pt is None:
                    continue
                val, lbl, col = crossings[i]
                labels.append(f'"{lbl},{100*pt[0]:.3f}%" at {2*pt[0]-1},{pt[1]} right tc rgb "{col}" font ",6" offset character 0,{chroff} point pt 1 lc rgb "{col}"')

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
    pmaps = ''
    if pmapf:
        pmaps = f' ({pmapf})'
    if args.xl is None:
        args.xl = f"Percentile"
    if args.yl is None:
        args.yl = f'LR {" - (LR_{" + titles[0] + "})" if comparing else ""}{pmaps}'
    if args.xl is not None:
        pf.write(f'set xlabel "{args.xl}"\n')
    if args.yl is not None:
        pf.write(f'set ylabel "{args.yl}"\n')

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
    for lab in labels:
        pf.write(f'set label {lab}\n')
    if args.veq and veqs:
        for name, val, col in veqs:
            plots.append(f'{val} title {name!r} lc rgbcolor "{col}"')
    pf.write(f'plot {", ".join(plots)}\n')
    pf.close()
elif args.mode == 'changeover':
    print('Writing data files...')
    if len(args.series) != 2:
        print('This mode only supports two series; aborting.')
        exit()
    raise NotImplementedError()
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
