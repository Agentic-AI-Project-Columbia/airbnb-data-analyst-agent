import csv

print("=== calendar.csv ===")
with open(r"Sample Data\calendar.csv", encoding="utf-8") as f:
    r = csv.DictReader(f)
    print(f"Columns: {r.fieldnames}")
    total = 0
    price_non_empty = 0
    adj_price_non_empty = 0
    samples = []
    for row in r:
        total += 1
        if row.get("price", "").strip():
            price_non_empty += 1
            if len(samples) < 5:
                samples.append(row["price"])
        if row.get("adjusted_price", "").strip():
            adj_price_non_empty += 1
    print(f"Total rows: {total:,}")
    print(f"Rows with non-empty 'price': {price_non_empty:,}")
    print(f"Rows with non-empty 'adjusted_price': {adj_price_non_empty:,}")
    if samples:
        print(f"Sample price values: {samples}")
    else:
        print("No price values found!")

print()
print("=== File name check ===")
import os
data_dir = "Sample Data"
for f in os.listdir(data_dir):
    print(f"  {f}")
