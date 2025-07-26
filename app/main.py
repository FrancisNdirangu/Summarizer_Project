# app/main.py
# app/main.py

from fastapi import FastAPI
from pydantic import BaseModel
from .summarizer import BARTSummarizer

app = FastAPI()

# Instantiate the summarizer
summarizer = BARTSummarizer()

# Pydantic model for input
class SummarizeRequest(BaseModel):
    text: str

# Health check endpoint
@app.get("/")
def root():
    return {"message": "API is running"}

# Summarization endpoint
@app.post("/summarize/")
def summarize_text(request: SummarizeRequest):
    summary = summarizer.summarize(request.text)
    return {"summary": summary}



