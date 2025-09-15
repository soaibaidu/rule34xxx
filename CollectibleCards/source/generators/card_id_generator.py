import csv
from collections import defaultdict
import argparse


# FIELDS (update if your CSV has different headers)
SET_FIELD = 'Set/Edition'  # Update if your CSV uses a different header
CARD_ID_FIELD = 'Card ID'
TYPE_FIELD = 'Type'
SUBTYPE_FIELD = 'Subtype'

# Mapping from set/edition names to abbreviations
COLLECTION_ABBR_MAP = {
    'srp_bitterroot': 'SRP-BR',
    'srp_players': 'SRP-PL',
    # Add more mappings as needed
}

def main():
    parser = argparse.ArgumentParser(description="Generate card IDs for one or more collection CSVs.")
    parser.add_argument('--csv', type=str, required=True, help='Comma-separated list of input CSV file paths')
    parser.add_argument('--output', type=str, default=None, help='Output CSV file path (default: overwrite input, or comma-separated list for multiple)')
    args = parser.parse_args()

    csv_paths = [p.strip() for p in args.csv.split(',') if p.strip()]
    output_paths = None
    if args.output:
        output_paths = [p.strip() for p in args.output.split(',') if p.strip()]
        if len(output_paths) != len(csv_paths):
            raise ValueError("Number of output paths must match number of input CSVs, or leave --output blank to overwrite inputs.")

    for i, csv_path in enumerate(csv_paths):
        output_path = output_paths[i] if output_paths else csv_path

        # Read CSV
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

        # Build index for (type, subtype)
        type_subtype_counter = defaultdict(int)
        card_ids = []

    # Static maps for type and subtype abbreviations
    TYPE_ABBREV_MAP = {
        'artifact': 'A',
        'creature': 'C',
        'land': 'L',
        'spell': 'S',
        # Add more as needed
    }
    SUBTYPE_ABBREV_MAP = {
        'aura': 'A',
        'admin': 'ADM',
        'communityrep': 'CR',
        'dual': 'D',
        'developer': 'DEV',
        'elite': 'E',
        'equipment': 'EQ',
        'founder': 'FN',
        'global': 'G',
        'mutant': 'MT',
        'myth': 'MY',
        'omni': 'O',
        'relic': 'RL',
        'ritual': 'RT',
        'specialist': 'SP',
        'unit': 'U',
        'utility': 'UT',
        'veteran': 'VET',
        'wildcard': 'WLD',
        # Add more as needed
    }

    def first_significant_letter(s, is_type=True):
        # Use the appropriate map if available, else 'XXX'
        key = str(s).strip().lower()
        if is_type:
            if key in TYPE_ABBREV_MAP:
                return TYPE_ABBREV_MAP[key]
        else:
            if key in SUBTYPE_ABBREV_MAP:
                return SUBTYPE_ABBREV_MAP[key]
        return 'XXX'

    for row in rows:
        type_val = row[TYPE_FIELD]
        subtype_val = row[SUBTYPE_FIELD]
        key = (type_val, subtype_val)
        type_subtype_counter[key] += 1
        index = type_subtype_counter[key]
        type_letter = first_significant_letter(type_val, is_type=True)
        subtype_letter = first_significant_letter(subtype_val, is_type=False)
        # Get collection abbreviation from set/edition field
        set_val = row.get(SET_FIELD, '').strip().lower().replace(' ', '_').replace(':', '')
        collection_abbr = COLLECTION_ABBR_MAP.get(set_val, set_val.upper())
        card_id = f"{collection_abbr}-{index:03d}-{type_letter}-{subtype_letter}"
        row[CARD_ID_FIELD] = card_id
        card_ids.append(row)


    # Write output CSV
    fieldnames = rows[0].keys() if rows else []
    with open(output_path, 'w', newline='', encoding='utf-8') as outcsv:
        writer = csv.DictWriter(outcsv, fieldnames=fieldnames)
        writer.writeheader()
        for row in card_ids:
            writer.writerow(row)

    print(f"Generated card IDs written to {output_path}")

if __name__ == '__main__':
    main()
