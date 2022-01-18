import csv, argparse, os
import admonitions

__version__ = (0, 0, 1)

parser = argparse.ArgumentParser(description='Generate TSVs from a single CSV')

parser.add_argument('csv', help='CSV file to read')
parser.add_argument('--outdir', '-o', required=True, help='Directory under which the TSVs will be created')
parser.add_argument('--no-check-unique', action='store_true', help="Don't check for uniqueness of rows (drastically reduces memory usage)")
parser.add_argument('--floating-alleles', action='store_true', help='Try to set alleles to their integer values (to get rid of spurious .0s)')
parser.add_argument('--version', '-V', action='store_true', help='Instead of doing anyting else, print out version and regulatory information')

args = parser.parse_args()

if args.version:
    print('CSV to TSV converter tool version', '.'.join(map(str, __version__)))
    print(admonitions.LICENSE)
    exit()

os.makedirs(args.outdir, exist_ok=True)

header = None
seen = {}

for idx, row in enumerate(csv.reader(open(args.csv))):
    if header is None:
        header = row[1:]
        continue

    name, data = row[0], row[1:]
    if not args.no_check_unique:
        key = tuple(data)
        res = seen.get(key)
        if res is not None:
            print(f'WARN: row {idx} name {name} not unique; saw these values at rows/names {res}')
        else:
            seen[key] = set()
        seen[key].add((idx, name))

    loci = {}
    for locus, allele in zip(header, data):
        if locus not in loci:
            loci[locus] = []
        loci[locus].append(allele)

    fo = open(os.path.join(args.outdir, name + '.tsv'), 'w')
    fo.write('\t'.join(['Locus'] + [f'Allele {i+1}' for i in range(2)]) + '\n')
    for locus, alleles in loci.items():
        if args.floating_alleles:
            for idx, allele in enumerate(alleles):
                allele = float(allele)
                if allele == int(allele):
                    allele = int(allele)
                alleles[idx] = str(allele)
        if len(alleles) != 2:
            print(f'WARN: variant allele count {len(alleles)} for row {idx} name {name} locus {locus}: {alleles}')
        fo.write('\t'.join([locus] + alleles) + '\n')
    fo.flush()
    fo.close()
