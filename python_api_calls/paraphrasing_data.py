import pandas as pd
import openai
import time
import math
import os
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv  # for loading .env file

# ========================
# LOAD ENV & API KEY
# ========================
load_dotenv()  # Load .env file
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise ValueError("❌ OPENAI_API_KEY not found in .env file.")

# ========================
# CONFIG
# ========================
INPUT_CSV = r"C:\Users\franc\Documents\phase5_project\Summarizer_Project\cleaned_merged_data_fixed.csv"
OUTPUT_CSV = "output_with_paraphrase_summary.csv"
TITLE_COLUMN = "Title"       # expected title column
CONTENT_COLUMN = "Content"   # expected content column
MODEL = "gpt-4o"             # or "gpt-4o-mini"
BATCH_SIZE = 5               # rows per API call
MAX_WORKERS = 3              # parallel threads
RATE_LIMIT_SLEEP = 0.5       # pause after API call

# Pricing per 1M tokens (USD)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4o": {"input": 5.000, "output": 15.000}
}

# ========================
# GLOBAL TRACKERS
# ========================
total_prompt_tokens = 0
total_completion_tokens = 0

# ========================
# FUNCTIONS
# ========================
def call_openai_batch(batch_titles, batch_contents):
    """Send batch to OpenAI and return paraphrased + summarized results + token usage."""
    prompt = (
        "You will receive multiple technical articles. Each entry has a title and content.\n"
        "For each entry:\n"
        "1. Paraphrase the content while keeping all technical details accurate.\n"
        "2. Summarize the paraphrased content for a general audience that may not be familiar with the topic.\n"
        "   Follow these strict summarization rules:\n"
        "- Use simple, everyday language (no jargon).\n"
        "- Explain complex ideas in plain terms (e.g., 'algorithm' → 'a set of rules a computer follows').\n"
        "- Do not exceed 200 words.\n"
        "- Maintain technical accuracy and the meaning of the original.\n"
        "- Use short sentences and logical structure.\n"
        "- Write for someone unfamiliar with the topic.\n"
        "Summarize the following content clearly and simply.\n"
        "3. Use the title as extra context to ensure both paraphrase and summary stay relevant.\n\n"
        "Return results in this JSON format:\n"
        "[{\"paraphrased\": \"...\", \"summary\": \"...\"}, ...]\n\n"
        "Entries:\n"
    )

    for idx, (title, content) in enumerate(zip(batch_titles, batch_contents), start=1):
        prompt += f"Entry {idx}:\nTitle: {title}\nContent: {content}\n\n"

    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that processes text while preserving technical fidelity."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        output_text = response.choices[0].message.content.strip()  # ✅ Updated for new SDK
        usage = response.usage

        try:
            results = json.loads(output_text)
        except json.JSONDecodeError:
            results = [{"paraphrased": "", "summary": ""} for _ in batch_contents]

        return results, usage.prompt_tokens, usage.completion_tokens

    except Exception as e:
        print(f"❌ Error: {e}")
        return [{"paraphrased": "", "summary": ""} for _ in batch_contents], 0, 0

def process_batch(batch_indices, batch_titles, batch_contents):
    """Worker function to process a batch and return results with token usage."""
    results, prompt_tokens, completion_tokens = call_openai_batch(batch_titles, batch_contents)
    time.sleep(RATE_LIMIT_SLEEP)
    return batch_indices, results, prompt_tokens, completion_tokens

# ========================
# LOAD DATA & RESUME LOGIC
# ========================
if os.path.exists(OUTPUT_CSV):
    print(f"🔄 Resuming from {OUTPUT_CSV}")
    df = pd.read_csv(OUTPUT_CSV)
else:
    df = pd.read_csv(INPUT_CSV)
    df["paraphrased"] = ""
    df["summary"] = ""

# Validate columns
if TITLE_COLUMN not in df.columns or CONTENT_COLUMN not in df.columns:
    raise ValueError(f"CSV must contain '{TITLE_COLUMN}' and '{CONTENT_COLUMN}' columns.")

remaining_indices = df[(df["paraphrased"] == "") | (df["summary"] == "")].index.tolist()

if not remaining_indices:
    print("✅ All rows already processed.")
    exit()

num_batches = math.ceil(len(remaining_indices) / BATCH_SIZE)
rows_remaining = len(remaining_indices)

# ========================
# PROCESS IN PARALLEL
# ========================
with tqdm(total=rows_remaining, desc="Processing rows", unit="row") as row_bar:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for b in range(num_batches):
            batch_indices = remaining_indices[b*BATCH_SIZE:(b+1)*BATCH_SIZE]
            batch_titles = df.loc[batch_indices, TITLE_COLUMN].fillna("").tolist()
            batch_contents = df.loc[batch_indices, CONTENT_COLUMN].fillna("").tolist()
            futures.append(executor.submit(process_batch, batch_indices, batch_titles, batch_contents))

        for future in as_completed(futures):
            batch_indices, results, prompt_tokens, completion_tokens = future.result()

            # Update token usage
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens

            # Save results to dataframe
            for idx, res in zip(batch_indices, results):
                df.at[idx, "paraphrased"] = res.get("paraphrased", "")
                df.at[idx, "summary"] = res.get("summary", "")

            df.to_csv(OUTPUT_CSV, index=False)
            row_bar.update(len(batch_indices))

            # Cost estimation
            input_cost = (total_prompt_tokens / 1_000_000) * MODEL_PRICING[MODEL]["input"]
            output_cost = (total_completion_tokens / 1_000_000) * MODEL_PRICING[MODEL]["output"]
            total_cost = input_cost + output_cost

            row_bar.set_postfix({
                "Prompt tokens": total_prompt_tokens,
                "Completion tokens": total_completion_tokens,
                "Est. cost $": f"{total_cost:.4f}"
            })

print("\n✅ All processing complete!")
print(f"📊 Total prompt tokens: {total_prompt_tokens}")
print(f"📊 Total completion tokens: {total_completion_tokens}")
print(f"💰 Estimated total cost: ${(total_prompt_tokens/1_000_000)*MODEL_PRICING[MODEL]['input'] + (total_completion_tokens/1_000_000)*MODEL_PRICING[MODEL]['output']:.4f}")
