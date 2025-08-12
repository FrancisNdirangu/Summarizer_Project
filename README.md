# Insight Distiller — AI/ML Blog Summarizer

A production-ready project that fine-tunes **DistilBART** to generate concise, high‑quality summaries of AI/ML blogs, articles, and research abstracts. It ships with a **FastAPI** inference service, a **Streamlit** UI, and an optional **Public API Gateway** for external consumers.

---

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Modeling & Training](#modeling--training)
- [Evaluation](#evaluation)
- [Roadmap](#roadmap)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Problem:** AI/ML practitioners and learners are overwhelmed by the volume of new content. Reading full articles or relying on inconsistent summaries costs time and makes it hard to stay current.

**Goal:** Deliver short, accurate, and readable summaries that preserve technical meaning and help users scan more content, faster.

**Who is it for?** AI/ML practitioners, data scientists, students, and e‑learners.

**Success Criteria**
- Business: Time saved, higher perceived usefulness.
- Technical: Fine‑tuned model outperforms baseline DistilBART on ROUGE and BERTScore.

---

## Architecture

The system is split across three logical parts for clean separation of concerns:

```mermaid
flowchart LR
    subgraph UI[Streamlit UI]
      U1[Paste Text] -->|POST JSON| IA1[/Internal API: /summarize-text/]
      U2[Upload PDF] -->|Multipart| IA2[/Internal API: /summarize-pdf/]
      U3[Paste URL]  -->|POST JSON| IA3[/Internal API: /summarize-url/]
    end

    subgraph INT[Internal FastAPI (Summarization Engine)]
      M1[DistilBART (fine-tuned) in ./model]
      FN1[clean_text]:::fn
      FN2[chunk_text (1024 window, 50 overlap)]:::fn
      FN3[summarize_text (beam/length controls)]:::fn
      OCR[OCR Pipeline: PyMuPDF → Pillow → Tesseract]:::fn
      IA1 --> FN3 --> M1
      IA2 --> OCR --> FN1 --> FN2 --> FN3 --> M1
      IA3 --> FN1 --> FN2 --> FN3 --> M1
    end

    subgraph PUB[Public API Gateway (optional)]
      G1[/POST /api/summarize-text/ with X-API-Key/]
      G2[/POST /api/summarize-url/ with X-API-Key/]
      G3[/POST /api/summarize-pdf/ with X-API-Key/]
      G1-->IA1
      G2-->IA3
      G3-->IA2
    end

    Ext[External Clients] -->|X-API-Key| PUB

classDef fn fill:#f7f7f7,stroke:#bbb,stroke-width:1px;
```
**Flows**
- **Paste Text:** UI → `/summarize-text` (single-pass)
- **PDF:** UI → `/summarize-pdf` (extract → clean → chunk → first‑pass summaries → merge → second‑pass)
- **URL:** UI → `/summarize-url` (fetch → clean → chunk → two‑pass)

---

## Key Features
- **Three input modes:** raw text, PDF (with OCR fallback), or URL.
- **Two‑pass summarization** for long content (chunked first‑pass + final merge).
- **Chunking with overlap** to respect the 1,024‑token limit (window=1024, overlap=50).
- **Public API Gateway** with API key auth for third‑party integrations.
- **Metrics‑driven development** (ROUGE & BERTScore).

---

## Tech Stack
- **Modeling:** Hugging Face Transformers, Datasets, Torch, Accelerate
- **Serving:** FastAPI, Uvicorn
- **UI:** Streamlit
- **Scraping/Cleaning:** requests, feedparser, BeautifulSoup
- **OCR (PDF):** PyMuPDF, Pillow, Tesseract
- **Evaluation:** evaluate, bert-score, matplotlib (optional)

---

## Quickstart

> **Prereqs**
> - Python 3.10+
> - (Optional for PDF OCR) Tesseract installed and on PATH
> - GPU recommended for inference speed

```bash
# 1) Clone & enter
git clone https://github.com/<you>/insight-distiller.git
cd insight-distiller

# 2) Create venv & install
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3) Put your fine-tuned model in ./model (or update path in code)

# 4) Run the internal API (summarization engine)
uvicorn internal_api.main:app --reload --host 127.0.0.1 --port 8000

# 5) In a new terminal, run the Streamlit UI
streamlit run ui/app.py

# (Optional) 6) Run the Public API Gateway
export PUBLIC_API_KEY="change-me-in-prod"
uvicorn public_api.main:app --reload --host 127.0.0.1 --port 8080
```

Open the UI at the URL Streamlit prints (usually `http://localhost:8501`).  
By default, the UI talks to `http://127.0.0.1:8000` for the internal API.

---

## Configuration

Environment variables (examples):
- `PUBLIC_API_KEY` — required by the Public API Gateway
- `API_BASE` — UI base URL for the internal API (default: `http://127.0.0.1:8000`)
- `TESSDATA_PREFIX` — if you need to point Tesseract to its data directory

Model path:
- Default is `./model`. Update in code if you store elsewhere.

---

## API Reference

### Internal FastAPI (no auth; local only)
- `POST /summarize-text`
  - **Body (JSON):** `{ "text": "...", "min_length": 60, "max_length": 150 }`
  - **Returns:** `{ "summary": "..." }`
- `POST /summarize-pdf`
  - **Form:** multipart file (`file`), plus optional `min_length`/`max_length`
  - **Returns:** `{ "summary": "..." }`
- `POST /summarize-url`
  - **Body (JSON):** `{ "url": "https://..." , "min_length": 60, "max_length": 150 }`
  - **Returns:** `{ "summary": "..." }`

### Public API Gateway (optional; requires `X-API-Key`)
- `POST /api/summarize-text` (forwards to internal `/summarize-text`)
- `POST /api/summarize-pdf` (forwards to internal `/summarize-pdf`)
- `POST /api/summarize-url`  (forwards to internal `/summarize-url`)

#### Example cURL
```bash
# Text
curl -X POST http://127.0.0.1:8080/api/summarize-text   -H "Content-Type: application/json"   -H "X-API-Key: $PUBLIC_API_KEY"   -d '{"text":"...","min_length":60,"max_length":150}'

# URL
curl -X POST http://127.0.0.1:8080/api/summarize-url   -H "Content-Type: application/json"   -H "X-API-Key: $PUBLIC_API_KEY"   -d '{"url":"https://ai.googleblog.com/...", "min_length":80, "max_length":180}'
```

---

## Modeling & Training

- **Baseline:** `sshleifer/distilbart-cnn-12-6` (general news summarization).
- **Fine-tuning data:** AI/ML blogs & abstracts, with **reference summaries** generated using GPT‑4o for supervision.
- **Chunking strategy:** sliding window to respect the 1,024‑token limit.
  - **Window:** 1024 tokens
  - **Overlap:** 50 tokens
  - **Step:** 974 tokens (1024 − 50)
- **Typical training config:** 80/20 split, LR=2e‑5, 3–5 epochs, batch size 8–16.
- **Generation:** beam search or top‑k sampling; length constraints tuned per content type.

---

## Evaluation

**Target metric bands**

| Metric        | Acceptable | Good   | Excellent |
|---------------|------------|--------|-----------|
| ROUGE‑1       | 0.30–0.35  | 0.36–0.45 | > 0.45 |
| ROUGE‑2       | 0.08–0.12  | 0.13–0.20 | > 0.20 |
| ROUGE‑L       | 0.25–0.35  | 0.36–0.42 | > 0.42 |
| ROUGE‑Lsum    | 0.28–0.36  | 0.37–0.45 | > 0.45 |
| BERTScore‑F1  | 0.86–0.88  | 0.88–0.90 | > 0.90 |

**Baseline vs Fine‑tuned**

| Metric        | Baseline | Fine‑Tuned | Δ (FT‑Base) | Band (FT) |
|---------------|---------:|-----------:|------------:|-----------|
| ROUGE‑1       | 0.2921   | 0.5015     | +0.2094     | Excellent |
| ROUGE‑2       | 0.0630   | 0.2009     | +0.1379     | Excellent |
| ROUGE‑L       | 0.1711   | 0.3076     | +0.1365     | Acceptable |
| ROUGE‑Lsum    | 0.2009   | 0.3753     | +0.1744     | Good |
| BERTScore‑F1  | 0.8487   | 0.8917     | +0.0430     | Good |

**Interpretation**
- Big gains on **ROUGE‑1/2** → better coverage of key terms and phrases.
- **ROUGE‑L/Lsum** improvements → stronger multi‑sentence organization.
- **BERTScore‑F1** up → higher semantic faithfulness to references.

---

## Roadmap
- Collect human ratings in‑app to guide active learning.
- Explore **longer‑context models** or **hierarchical summarization** to reduce truncation.
- Calibrate generation settings per content type (blog vs abstract).
- Diversify and expand training data for robustness.
- Containerize (Docker) and deploy to Hugging Face Spaces or Render.

---

## Project Structure

```
.
├── internal_api/         # FastAPI app (summarization engine)
├── public_api/           # Optional API gateway (X-API-Key)
├── ui/                   # Streamlit app (3 tabs: Text, PDF, URL)
├── model/                # Fine-tuned model (local path)
├── data/                 # (Optional) datasets, artifacts
├── notebooks/            # (Optional) exploration & evaluation
├── requirements.txt
└── README.md
```

---

## Contributing
PRs are welcome! If you’re adding a new feature, please open an issue first to discuss scope and design.

---

## License
Choose a license (e.g., MIT). Add `LICENSE` to the repo and update this section accordingly.
