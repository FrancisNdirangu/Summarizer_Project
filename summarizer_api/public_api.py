# public_api.py
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel
import os
import requests
from fastapi.responses import RedirectResponse




# ---------------- CONFIG ----------------
INTERNAL_BASE = "http://127.0.0.1:8000"  # URL of your internal summarizer API
API_KEY = os.getenv("PUBLIC_API_KEY", "mysecretkey")  # API key for authentication

# ---------------- APP ----------------
app = FastAPI(title="Public Summarization API", description="External API for text, PDF, and URL summarization")

# ---------------- MODELS ----------------
# class PublicTextInput(BaseModel):
#     text: str
#     min_length: int = 100
#     max_length: int = 250

class PublicURLInput(BaseModel):
    url: str
    min_length: int = 100
    max_length: int = 250

# ---------------- HELPERS ----------------
def check_api_key(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def forward_request(endpoint: str, payload: dict = None, files=None, data=None):
    try:
        res = requests.post(f"{INTERNAL_BASE}{endpoint}", json=payload, files=files, data=data)
        if res.status_code == 200:
            return res.json()
        else:
            raise HTTPException(status_code=res.status_code, detail=res.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- ROUTES ----------------
@app.post("/api/summarize-text")
# def public_summarize_text(input: PublicTextInput, x_api_key: str = Header(None)):
#     check_api_key(x_api_key)
#     return forward_request("/summarize-text", payload=input.dict())
def public_summarize_text(
    x_api_key: str = Header(None),
    text: str = Form(...),
    min_length: int = Form(100),
    max_length: int = Form(250)
):
    check_api_key(x_api_key)
    payload = {
        "text": text,
        "min_length": min_length,
        "max_length": max_length
    }
    return forward_request("/summarize-text", payload=payload)

@app.post("/api/summarize-url")
def public_summarize_url(input: PublicURLInput, x_api_key: str = Header(None)):
    check_api_key(x_api_key)
    return forward_request("/summarize-url", payload=input.dict())

@app.post("/api/summarize-pdf")
def public_summarize_pdf(
    x_api_key: str = Header(None),
    file: UploadFile = File(...),
    min_length: int = Form(100),
    max_length: int = Form(250)
):
    check_api_key(x_api_key)
    files = {"file": (file.filename, file.file, "application/pdf")}
    data = {"min_length": min_length, "max_length": max_length}
    return forward_request("/summarize-pdf", files=files, data=data)

# @app.get("/")
# def root():
#     return {"message": "Public Summarization API: Use /api/summarize-text, /api/summarize-pdf, /api/summarize-url"}

@app.get("/")
def root():
    return RedirectResponse(url="/docs")