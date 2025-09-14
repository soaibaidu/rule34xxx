import csv
from collections import defaultdict
import os

# CONFIGURATION
CSV_PATH = os.path.join(os.path.dirname(__file__), '../collections/srp_bitterroot_collection.csv')
COLLECTION_ABBR = 'SRP-BR'  # Change as needed
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '../collections/srp_bitterroot_collection.csv')

# FIELDS (update if your CSV has different headers)
CARD_ID_FIELD = 'Card ID'
TYPE_FIELD = 'Type'
SUBTYPE_FIELD = 'Subtype'

def main():
    # Read CSV
    with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    # Build index for (type, subtype)
    type_subtype_counter = defaultdict(int)
    card_ids = []

    def first_significant_letter(s):
        # Returns the first alphanumeric character (ignores whitespace and punctuation)
        for c in s:
            if c.isalnum():
                return c.upper()
        return ''


    for row in rows:
        type_val = row[TYPE_FIELD]
        subtype_val = row[SUBTYPE_FIELD]
        key = (type_val, subtype_val)
        type_subtype_counter[key] += 1
        index = type_subtype_counter[key]
        type_letter = first_significant_letter(type_val)
        subtype_letter = first_significant_letter(subtype_val)
        card_id = f"{COLLECTION_ABBR}-{index:03d}-{type_letter}-{subtype_letter}"
        row[CARD_ID_FIELD] = card_id
        card_ids.append(row)

    # Write output CSV
    fieldnames = reader.fieldnames
    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as outcsv:
        writer = csv.DictWriter(outcsv, fieldnames=fieldnames)
        writer.writeheader()
        for row in card_ids:
            writer.writerow(row)

    print(f"Generated card IDs written to {OUTPUT_PATH}")

if __name__ == '__main__':
    main()
