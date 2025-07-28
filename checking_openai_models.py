from openai import OpenAI
import pandas as pd
from tqdm import tqdm

api_key = "***REMOVED***"  # Replace with your key or use environment variable
client = OpenAI(api_key=api_key)  # or use os.getenv("OPENAI_API_KEY")

models = client.models.list()
for m in models.data:
    print(m.id)
