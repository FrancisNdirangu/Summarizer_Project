from openai import OpenAI
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
import os

# Load API key from .env
load_dotenv()
# API_KEY = os.getenv("OPENAI_API_KEY")  # Make sure your .env uses this exact key name

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# File path and column names
CSV_PATH = r"C:\Users\franc\Documents\phase5_project\Summarizer_Project\cleaned_merged_data_fixed.csv"
TITLE_COL = "Title"
CONTENT_COL = "Content"
OUTPUT_CSV = "final_summaries_4o.csv"

# Load dataset
# df = pd.read_csv(CSV_PATH)
df = pd.read_csv(
    CSV_PATH,
    engine="python",          # more tolerant parser
    on_bad_lines="skip"       # or "warn"
)



# Define prompt builder using both title and content
def build_prompt(title, content):
    return f"""
You are a helpful AI assistant that writes abstractive summaries of technical content. Follow these rules:

Use simple, everyday language (no jargon).
Explain complex ideas in plain terms (e.g., “algorithm” → “set of rules a computer follows”).
Do not exceed 200 words.
Maintain technical accuracy and the meaning of the original.
Use short sentences and logical structure.
Write for someone unfamiliar with the topic.

Summarize the following article based on its title and content:

Title: "{title}"

\"\"\"{content}\"\"\"
"""

# Generate summaries
summaries = []
for i, row in tqdm(df.iterrows(), total=len(df), desc="Summarizing"):
    try:
        prompt = build_prompt(row[TITLE_COL], row[CONTENT_COL])
        response = client.chat.completions.create(
            model="gpt-4o",  #"gpt-4o-mini",#gpt-4o",
            messages=[
                {"role": "system", "content": "You are a summarization assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        summary = response.choices[0].message.content
    except Exception as e:
        summary = f"[ERROR]: {str(e)}"
    
    summaries.append(summary)

# Save results
df["Summary"] = summaries
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Summaries saved to: {OUTPUT_CSV}")





# import pandas as pd
# from tqdm import tqdm
# from dotenv import load_dotenv
# import os
# import time
# from openai import OpenAI

# # Load API key
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # Paths
# CSV_PATH = r"C:\Users\franc\Documents\phase5_project\Summarizer_Project\cleaned_merged_data_fixed.csv"
# OUTPUT_CSV = "final_summaries_3.5turbo2.csv"
# TITLE_COL = "Title"
# CONTENT_COL = "Content"

# # Load data
# df = pd.read_csv(CSV_PATH, engine="python", on_bad_lines="skip")
# df = pd.read_csv(
#     CSV_PATH,
#     engine="python",
#     error_bad_lines=False,    # deprecated in newer versions
#     warn_bad_lines=True
# )

df["Summary"] = ""  # Add empty summary column if not exists

print("✅ Loaded rows:", len(df))


# # Resume from last saved summary if needed
# if os.path.exists(OUTPUT_CSV):
#     print("🔁 Resuming from existing output...")
#     prev_df = pd.read_csv(OUTPUT_CSV)
#     df["Summary"] = prev_df["Summary"]

# # Prompt builder
# def build_prompt(title, content):
#     return f"""
# You are a helpful AI assistant that writes abstractive summaries of technical content. Follow these rules:

# ✅ Use simple, everyday language (no jargon).
# ✅ Explain complex ideas in plain terms (e.g., “algorithm” → “set of rules a computer follows”).
# ✅ Do not exceed 200 words.
# ✅ Maintain technical accuracy and the meaning of the original.
# ✅ Use short sentences and logical structure.
# ✅ Write for someone unfamiliar with the topic.

# Summarize the following article based on its title and content:

# Title: "{title}"

# \"\"\"{content}\"\"\"
# """

# # Loop through only rows that have not been summarized
# for i, row in tqdm(df.iterrows(), total=len(df), desc="Summarizing"):
#     if pd.notna(row["Summary"]) and str(row["Summary"]).strip() != "":
#         continue  # Skip already summarized

#     try:
#         prompt = build_prompt(row[TITLE_COL], row[CONTENT_COL])
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are a summarization assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.5,
#             max_tokens=300
#         )
#         summary = response.choices[0].message.content.strip()
#     except Exception as e:
#         summary = f"[ERROR]: {str(e)}"
#         print(f"⚠️ Error at row {i}: {e}")
#         time.sleep(2)  # Backoff in case of rate limits

#     df.at[i, "Summary"] = summary

#     # Save after every 10 rows
#     if i % 10 == 0:
#         df.to_csv(OUTPUT_CSV, index=False)

# # Final save
# df.to_csv(OUTPUT_CSV, index=False)
# print(f"✅ Final summaries saved to: {OUTPUT_CSV}")
