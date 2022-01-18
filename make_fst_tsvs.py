import csv, argparse, os
import admonitions

__version__ = (0, 0, 1)

parser = argparse.ArgumentParser(description='Generate FST TSVs from the validation study CSV')

parser.add_argument('--case', '-c', nargs='*', help='Just this/these case(s) (default all)')
parser.add_argument('--outdir', '-o', default='fst_tsvs', help='Directory under which case directories will be created')
parser.add_argument('--validation', default='validation_study.csv', help='Validation study CSV file (regardless of dropouts)')
parser.add_argument('--version', '-V', action='store_true', help='Instead of doing anything else, print out version and regulatory information')

args = parser.parse_args()

if args.version:
    print('Validation to FST TSV tool version', '.'.join(map(str, __version__)))
    print(admonitions.LICENSE)
    exit()

if args.validation not in (
        'validation_study.csv',
        'validation_study_dropouts.csv',
):
    print(admonitions.COMPLIANCE)
    print('--validation: potentially inaccurate study')

os.makedirs(args.outdir, exist_ok=True)

REPS = ('REP1', 'REP2', 'REP3')
CONTS = ('C1', 'C2', 'C3', 'C4')
LOCUS_MAP = {
    # validation study -> LRMix
    'D8': 'D8S1179',
    'D21': 'D21S11',
    'D7': 'D7S820',
    'CSF': 'CSF1PO',
    'D3': 'D3S1358',
    'TH01': 'TH01',
    'D13': 'D13S317',
    'D16': 'D16S539',
    'D2': 'D2S1338',
    'D19': 'D19S433',
    'vWA': 'VWA',
    'TPOX': 'TPOX',
    'D18': 'D18S51',
    'D5': 'D5S818',
    'FGA': 'FGA',
}

rdr = csv.DictReader(open(args.validation))
cases = {}
for row in rdr:
    cn = row['Case Name']
    if (not args.case) or cn in args.case:
        if cn not in cases:
            cases[cn] = []
        cases[cn].append(row)

print(f'Processing {len(cases)} cases...')

for cn, rows in cases.items():
    print(f'Case {cn}: ', end='')
    if not rows:
        print('No rows! Skipping.')
        continue

    basedir = os.path.join(args.outdir, cn)
    try:
        os.mkdir(basedir)
    except FileExistsError:
        print('(overwriting an existing dir) ', end='')

    # Evidence scan
    fo = open(os.path.join(basedir, 'evidence.tsv'), 'w')
    fo.write('\t'.join(['Locus', 'Replicate'] + [f'Allele {i+1}' for i in range(8)]) + '\n')
    for row in rows:
        locus = row['Locus']
        locus = LOCUS_MAP.get(locus, None)
        if locus is None:
            print(f'(WARN: skipping unknown locus {row["Locus"]}) ', end='')
            continue
        for rnum, rep in enumerate(REPS):
            alleles = row[rep]
            if not alleles:
                # FST needs an empty line, even in this case
                fo.write('\t'.join([locus, str(rnum + 1)]) + '\n')
                continue
            alleles = alleles.split(';')
            if len(alleles) > 8:
                print(f'(WARN: too many evidence alleles ({len(alleles)})) ', end='')
            fo.write('\t'.join([locus, str(rnum + 1)] + alleles) + '\n')
    fo.flush()
    fo.close()

    # Contributors scan
    for cnum, cont in enumerate(CONTS):
        fo = None
        matches = 0
        for row in rows:
            locus = row['Locus']
            locus = LOCUS_MAP.get(locus, None)
            if locus is None:
                continue  # Already complained
            alleles = row[cont]
            if not alleles:
                continue
            alleles = alleles.split(';')
            if len(alleles) != 2:
                print(f'(WARN: variant profile alleles for contributor {cnum+1} ({len(alleles)})) ', end='')
            matches += 1
            if fo is None:
                fo = open(os.path.join(basedir, f'contributor_{cnum+1}.tsv'), 'w')
                fo.write('\t'.join(['Locus'] + [f'Allele {i+1}' for i in range(2)]) + '\n')
            fo.write('\t'.join([locus] + alleles) + '\n')
        if fo is not None:
            if matches != len(rows):
                print(f'(WARN: contributor {cnum+1} may have incomplete data (matches {matches} of {len(rows)} rows)) ', end='')
            fo.flush()
            fo.close()

    # Parameters
    fo = open(os.path.join(basedir, 'parameters.txt'), 'w')
    exemplar = rows[0]
    fo.write(f'Contributors: {exemplar["Contributors"]}\n')
    fo.write(f'Deducible: {exemplar["D/ND"]}\n')
    fo.write(f'Quantity: {exemplar["Quant"]}\n')
    fo.write(f'KnownPn: {exemplar["Known Pn"]}\n')
    fo.flush()
    fo.close()

    print('Done.')

print('All done.')
