from transformers import BartTokenizer, BartForConditionalGeneration, Trainer, TrainingArguments
from datasets import Dataset
import pandas as pd
from app.summarizer import MultiSummaryGenerator
from app.utils.data_utils import load_data, choose_best_summary

df = load_data("data/arxiv_ai_abstracts.csv")
generator = MultiSummaryGenerator()

best_records = []
for _, row in df.iterrows():
    summaries = generator.generate_multiple(row['text'], 3)
    best = choose_best_summary(row['text'], summaries)
    best_records.append({'text': row['text'], 'summary': best})

train_dataset = Dataset.from_pandas(pd.DataFrame(best_records))

tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")

def preprocess(examples):
    inputs = tokenizer(examples['text'], max_length=1024, truncation=True, padding="max_length")
    targets = tokenizer(examples['summary'], max_length=150, truncation=True, padding="max_length")
    inputs['labels'] = targets['input_ids']
    return inputs

tokenized = train_dataset.map(preprocess, batched=True)

model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

training_args = TrainingArguments(
    output_dir="./models/saved_model",
    num_train_epochs=2,
    per_device_train_batch_size=2,
    save_steps=500,
    save_total_limit=1,
    logging_dir="./logs",
)

trainer = Trainer(model=model, args=training_args, train_dataset=tokenized)
trainer.train()