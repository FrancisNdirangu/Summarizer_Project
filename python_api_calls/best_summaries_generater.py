from openai import OpenAI
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
import os

load_dotenv()
# API_KEY = os.getenv("api_key")

# Load your OpenAI API key
client = OpenAI()  # or use os.getenv("OPENAI_API_KEY")
# File path and column to summarize
CSV_PATH = r"C:\Users\franc\Documents\phase5_project\Summarizer_Project\cleaned_merged_data.csv"
TEXT_COL = "Content"
OUTPUT_CSV = "summarized_articles_automated.csv"

df = pd.read_csv(CSV_PATH)

def build_prompt(text):
    return f"""
You are a helpful AI assistant that writes abstractive summaries of technical content. Follow these rules:

Use simple, everyday language (no jargon).
Explain complex ideas in plain terms (e.g., “algorithm” → “set of rules a computer follows”).
Do not exceed 200 words.
Maintain technical accuracy and the meaning of the original.
Use short sentences and logical structure.
Write for someone unfamiliar with the topic.

Summarize the following content clearly and simply:

\"\"\"{text}\"\"\"
"""

summaries = []

for content in tqdm(df[TEXT_COL], desc="Summarizing"):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a summarization assistant."},
                {"role": "user", "content": build_prompt(content)}
            ],
            temperature=0.5,
            max_tokens=300
        )
        summary = response.choices[0].message.content
    except Exception as e:
        summary = f"[ERROR]: {str(e)}"
    
    summaries.append(summary)

df["Summary"] = summaries
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Summaries saved to: {OUTPUT_CSV}")
