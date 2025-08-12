import csv

RAW = r"C:\Users\franc\Documents\phase5_project\Summarizer_Project\cleaned_merged_data.csv"
FIXED = r"C:\Users\franc\Documents\phase5_project\Summarizer_Project\cleaned_merged_data_fixed.csv"

with open(RAW, newline="", encoding="utf-8") as infile, \
     open(FIXED, "w", newline="", encoding="utf-8") as outfile:
    
    reader = csv.reader(infile)
    writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
    
    # Write header
    writer.writerow(["Title", "Content"])
    
    skipped = 0
    for i, row in enumerate(reader, start=1):
        if not row:
            writer.writerow(["", ""])
            continue
        if len(row) == 1:
            writer.writerow([row[0], ""])
        else:
            title = row[0]
            content = ",".join(row[1:])  # merge all remaining into one string
            writer.writerow([title, content])
        if i % 500 == 0:
            print(f"✅ Processed {i} rows")

print("✅ Finished writing fixed CSV")
