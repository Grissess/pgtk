import csv, argparse, os
import admonitions

__version__ = (0, 0, 1)

parser = argparse.ArgumentParser(description='Generates LRMix CSVs from non-contributor TSVs')

parser.add_argument('file', help='TSV input')
parser.add_argument('-o', '--output', help='Output CSV (defaults to file with .tsv replaced with .csv)')
parser.add_argument('-V', '--version', action='store_true', help='Instead of doing anything else, print out version and regulatory information')

args = parser.parse_args()

if args.version:
    print('Non-contributer TSV to LRMix CSV tool version', '.'.join(map(str, __version)))
    print(admonitions.LICENSE)
    exit()

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
LRMIX_HDR = ('SampleName', 'Marker')
ALLELE_HDR = tuple(f'Allele{i}' for i in range(1, 9))

base = os.path.splitext(args.file)[0]
out = csv.DictWriter(open(base + '.csv', 'w'), LRMIX_HDR + ALLELE_HDR)
out.writeheader()

for line in open(args.file):
    if not line.strip():
        continue
    loc, al1, al2 = [part.strip() for part in line.split('\t')]
    if loc == 'LOCUS':
        continue  # header line

    out.writerow({
        'SampleName': base,
        'Marker': LOCUS_MAP.get(loc, loc),
        'Allele1': str(al1),
        'Allele2': str(al2),
    })

