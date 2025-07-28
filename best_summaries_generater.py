import openai
import pandas as pd
from tqdm import tqdm

# Load your OpenAI API key
openai.api_key = "YOUR_API_KEY_HERE"  # Replace with your key or use environment variable

# File path and column to summarize
CSV_PATH = "your_articles.csv"
TEXT_COL = "Content"
OUTPUT_CSV = "summarized_articles.csv"

# Load data
df = pd.read_csv(CSV_PATH)

# Prompt template
def build_prompt(text):
    return f"""
You are a helpful AI assistant that writes abstractive summaries of technical content. Follow these rules:

✅ Use simple, everyday language (no jargon).
✅ Explain complex ideas in plain terms (e.g., “algorithm” → “set of rules a computer follows”).
✅ Do not exceed 200 words.
✅ Maintain technical accuracy and the meaning of the original.
✅ Use short sentences and logical structure.
✅ Write for someone unfamiliar with the topic.

Summarize the following content clearly and simply:

\"\"\"{text}\"\"\"
"""

# Generate summaries
summaries = []
for content in tqdm(df[TEXT_COL], desc="Summarizing"):
    prompt = build_prompt(content)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a summarization assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        summary = response["choices"][0]["message"]["content"]
    except Exception as e:
        summary = f"[ERROR]: {str(e)}"

    summaries.append(summary)

# Save the output
df["Summary"] = summaries
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Summaries saved to: {OUTPUT_CSV}")
