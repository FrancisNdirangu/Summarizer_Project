from openai import OpenAI
import pandas as pd
from tqdm import tqdm

from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("api_key")


client = OpenAI(api_key=API_KEY)  # or use os.getenv("OPENAI_API_KEY")

models = client.models.list()
for m in models.data:
    print(m.id)
