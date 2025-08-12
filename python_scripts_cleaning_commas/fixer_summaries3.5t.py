import csv

RAW = "final_summaries_4o.csv"
FIXED = "fixed_final_summaries_4o.csv"

with open(RAW, newline="", encoding="utf-8") as infile, \
     open(FIXED, "w", newline="", encoding="utf-8") as outfile:

    reader = csv.reader(infile)           # python's csv handles quoting better than pandas C engine
    writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
    
    # Try to detect the header case-insensitively
    header = next(reader)
    lower = [h.strip().lower() for h in header]
    try:
        c_idx = lower.index("content")
        s_idx = lower.index("summary")
    except ValueError:
        # If the header is broken, force two columns
        c_idx, s_idx = 0, 1
        # rewind and treat first line as data
        infile.seek(0)
        reader = csv.reader(infile)

    writer.writerow(["content", "summary"])

    for i, row in enumerate(reader, start=1):
        if not row:
            writer.writerow(["", ""])
            continue
        
        # If the row was split into too many pieces, just join everything
        # after the first index of each column (safest fallback)
        if len(row) <= max(c_idx, s_idx):
            # skip malformed
            continue
        
        content = row[c_idx]
        summary = row[s_idx]
        # If summary was accidentally split across multiple columns, rejoin them
        if len(row) > s_idx + 1:
            summary = ",".join(row[s_idx:])

        writer.writerow([content, summary])

print("✅ Wrote:", FIXED)
