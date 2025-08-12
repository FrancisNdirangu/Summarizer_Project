# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
# import torch
# import re
# import os

# os.environ["TRANSFORMERS_NO_TF"] = "1"

# # Load model
# MODEL_DIR = "./model"
# tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
# model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR)
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# model = model.to(device)

# # API input schema
# class TextInput(BaseModel):
#     text: str
#     max_length: int = 250
#     min_length: int = 100

# # Create app
# app = FastAPI(title="Summarizer API", description="Generate summaries with OCR cleaning and two-pass processing")

# # ---------- TEXT CLEANING ----------
# def clean_ocr_text(text: str) -> str:
#     """Clean OCR output to improve summarization quality."""
#     text = re.sub(r'\n+', '\n', text)  # Remove multiple newlines
#     text = re.sub(r'\s+', ' ', text)  # Normalize spaces
#     text = re.sub(r'\bPage\s*\d+\b', '', text, flags=re.IGNORECASE)  # Remove page numbers
#     text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)  # Remove standalone numbers
#     return text.strip()

# # ---------- CHUNKING ----------
# def chunk_text(text, tokenizer, max_tokens=1024, stride=50):
#     tokens = tokenizer.tokenize(text)
#     total_tokens = len(tokens)
#     chunks = []

#     for i in range(0, total_tokens, max_tokens - stride):
#         chunk = tokens[i:i + max_tokens]
#         chunk_text = tokenizer.convert_tokens_to_string(chunk)
#         chunks.append(chunk_text)

#     return chunks

# # ---------- SUMMARIZATION ----------
# def summarize_text(text, min_length, max_length):
#     """Summarize a single text input."""
#     inputs = tokenizer(
#         text,
#         return_tensors="pt",
#         max_length=1024,
#         truncation=True,
#         padding=True
#     ).to(device)

#     summary_ids = model.generate(
#         inputs["input_ids"],
#         max_length=max_length,
#         min_length=min_length,
#         length_penalty=2.0,
#         num_beams=4,
#         early_stopping=True
#     )

#     return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# # ---------- API ROUTES ----------
# @app.get("/")
# def root():
#     return {"message": "Welcome to the upgraded Summarizer API with OCR cleaning and two-pass summarization"}

# @app.post("/summarize")
# def summarize(input: TextInput):
#     if not input.text.strip():
#         raise HTTPException(status_code=400, detail="Input text cannot be empty")

#     # Step 1: Clean OCR text
#     cleaned_text = clean_ocr_text(input.text)

#     # Step 2: First pass summarization (chunked)
#     chunks = chunk_text(cleaned_text, tokenizer)
#     first_pass_summaries = [summarize_text(chunk, input.min_length, input.max_length) for chunk in chunks]

#     # Step 3: Second pass summarization
#     combined_text = " ".join(first_pass_summaries)
#     final_summary = summarize_text(combined_text, input.min_length, input.max_length)

#     return {
#         "summary": final_summary,
#         "first_pass_summaries": first_pass_summaries  # Optional: return intermediate summaries
#     }

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
import io
import requests
from bs4 import BeautifulSoup
import re

# Load model
MODEL_DIR = "./model"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

app = FastAPI(title="Summarization API Suite")

# --- Cleaning for OCR text ---
def clean_text(text: str) -> str:
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\bPage\s*\d+\b', '', text, flags=re.IGNORECASE)
    return text.strip()

# --- Chunking ---
def chunk_text(text, tokenizer, max_tokens=1024, stride=50):
    tokens = tokenizer.tokenize(text)
    total_tokens = len(tokens)
    chunks = []
    for i in range(0, total_tokens, max_tokens - stride):
        chunk = tokens[i:i + max_tokens]
        chunk_text_str = tokenizer.convert_tokens_to_string(chunk)
        chunks.append(chunk_text_str)
    return chunks

# --- Summarization ---
def summarize_text(text, min_length=100, max_length=250):
    inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True, padding=True).to(device)
    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=max_length,
        min_length=min_length,
        length_penalty=2.0,
        num_beams=4,
        early_stopping=True
    )
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# --- Pasted Text Endpoint ---
class TextInput(BaseModel):
    text: str
    min_length: int = 100
    max_length: int = 250

@app.post("/summarize-text")
def summarize_text_api(input: TextInput):
    if not input.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    return {"summary": summarize_text(input.text, input.min_length, input.max_length)}

# --- PDF Endpoint ---
@app.post("/summarize-pdf")
async def summarize_pdf(file: UploadFile = File(...), min_length: int = Form(100), max_length: int = Form(250)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are supported.")

    pdf_text = ""
    with fitz.open(stream=await file.read(), filetype="pdf") as pdf_doc:
        for page in pdf_doc:
            text = page.get_text()
            if text.strip():
                pdf_text += text
            else:
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                pdf_text += pytesseract.image_to_string(img)

    cleaned_text = clean_text(pdf_text)
    chunks = chunk_text(cleaned_text, tokenizer)

    first_pass = [summarize_text(chunk, min_length, max_length) for chunk in chunks]
    combined_summary = " ".join(first_pass)
    final_summary = summarize_text(combined_summary, min_length, max_length)

    return {"summary": final_summary}

# --- URL Endpoint ---
class URLInput(BaseModel):
    url: str
    min_length: int = 100
    max_length: int = 250

@app.post("/summarize-url")
def summarize_url_api(input: URLInput):
    try:
        response = requests.get(input.url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs = [p.get_text() for p in soup.find_all("p")]
    page_text = clean_text(" ".join(paragraphs))

    chunks = chunk_text(page_text, tokenizer)
    first_pass = [summarize_text(chunk, input.min_length, input.max_length) for chunk in chunks]
    combined_summary = " ".join(first_pass)
    final_summary = summarize_text(combined_summary, input.min_length, input.max_length)

    return {"summary": final_summary}

@app.get("/")
def root():
    return {"message": "Summarization API Suite: /summarize-text, /summarize-pdf, /summarize-url"}
