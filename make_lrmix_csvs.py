import csv, argparse, os
import admonitions

__version__ = (0, 0, 1)

parser = argparse.ArgumentParser(description='Generates LRMix CSVs from the validation study CSV')

parser.add_argument('case', type=int, help='Case number to convert')
parser.add_argument('-o', '--outdir', help='Output directory (defaults to case number)')
parser.add_argument('--validation', default='validation_study_dropouts.csv', help='Validation study CSV file')
parser.add_argument('-V', '--version', action='store_true', help='Instead of doing anything else, print out version and regulatory information')
parser.add_argument('-v', '--verbose', action='store_true', help='Be verbose about actions')

args = parser.parse_args()

if args.version:
    print('Validation to LRMix CSV tool version', '.'.join(map(str, __version__)))
    print(admonitions.LICENSE)
    exit()

if args.outdir is None:
    args.outdir = str(args.case)

if args.validation != 'validation_study_dropouts.csv':
    print(admonitions.COMPLIANCE)
    print('--validation: potentially inaccurate study')

try:
    os.mkdir(args.outdir)
except FileExistsError:
    print('(case directory already exists! Check for stale files!)')

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
REPS = ('REP1', 'REP2', 'REP3')
CONTS = ('C1', 'C2', 'C3', 'C4')
DROPOUTS = ('PHET1', 'PHET2', 'PHOM')
LRMIX_HDR = ('SampleName', 'Marker')
ALLELE_HDR = tuple(f'Allele{i}' for i in range(1, 9))

rdr = csv.DictReader(open(args.validation))
caserows = [row for row in rdr if row['Case Name'] == str(args.case)]
if args.verbose:
    print(f'Found {len(caserows)} rows: {caserows}')

for obj in REPS + CONTS:
    objev = [(row['Locus'], row[obj]) for row in caserows]
    if not any(i[1] for i in objev):
        if args.verbose:
            print(f'no data for object {obj}')
        continue

    out = csv.DictWriter(open(os.path.join(args.outdir, f'{obj}.csv'), 'w'), LRMIX_HDR + ALLELE_HDR)
    out.writeheader()

    for loc, alleles in objev:
        if (not alleles) or alleles in ('NEG', 'INC'):
            alleles = []
        else:
            alleles = alleles.split(';')

        allmap = dict(zip(ALLELE_HDR, alleles))
        allmap.update({'SampleName': obj, 'Marker': LOCUS_MAP[loc]})

        out.writerow(allmap)

    del out

out = csv.DictWriter(open(os.path.join(args.outdir, 'dropouts.csv'), 'w'), ('Marker',) + DROPOUTS)
out.writeheader()

products = {do: 1.0 for do in DROPOUTS}
sums = {do: 0.0 for do in DROPOUTS}
mins = {do: None for do in DROPOUTS}
maxs = {do: None for do in DROPOUTS}
cntr = 0
for row in caserows:
    cntr += 1
    outrow = {'Marker': LOCUS_MAP[row['Locus']]}
    for do in DROPOUTS:
        val = float(row[do])
        outrow[do] = val
        products[do] *= val
        sums[do] += val
        if mins[do] is None or val < mins[do]:
            mins[do] = val
        if maxs[do] is None or val > maxs[do]:
            maxs[do] = val
    out.writerow(outrow)

gmeans = {do: products[do]**(1/cntr) for do in DROPOUTS}
gmeans['Marker'] = '_GEOM_MEAN_'
ameans = {do: sums[do] / cntr for do in DROPOUTS}
ameans['Marker'] = '_ARITH_MEAN_'
mins['Marker'] = '_MIN_'
maxs['Marker'] = '_MAX_'

for row in (gmeans, ameans, mins, maxs):
    out.writerow(row)

out = open(os.path.join(args.outdir, 'presumed_cn'), 'w')
quant = float(caserows[0]['Quant'])
if quant <= 100:
    out.write('lcn\n')
else:
    out.write('hcn\n')
