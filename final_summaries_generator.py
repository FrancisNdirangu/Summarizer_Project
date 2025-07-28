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
CSV_PATH = r"C:\Users\franc\Documents\phase5_project\Summarizer_Project\scraped_files\towards_data_science_100_articles.csv"
TITLE_COL = "Title"
CONTENT_COL = "Content"
OUTPUT_CSV = "summarized_articles_automated.csv"

# Load dataset
df = pd.read_csv(CSV_PATH)

# Define prompt builder using both title and content
def build_prompt(title, content):
    return f"""
You are a helpful AI assistant that writes abstractive summaries of technical content. Follow these rules:

✅ Use simple, everyday language (no jargon).
✅ Explain complex ideas in plain terms (e.g., “algorithm” → “set of rules a computer follows”).
✅ Do not exceed 200 words.
✅ Maintain technical accuracy and the meaning of the original.
✅ Use short sentences and logical structure.
✅ Write for someone unfamiliar with the topic.

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
            model="gpt-4o",
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
