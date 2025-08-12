# import streamlit as st
# import requests
# import fitz  # PyMuPDF
# from PIL import Image
# import pytesseract
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# import io
# from transformers import AutoTokenizer
# import pandas as pd



# API_URL = "http://127.0.0.1:8000/summarize"
# MODEL_DIR = "./model"  # Path to tokenizer for chunking
# tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

# st.set_page_config(page_title="Text Summarizer", layout="centered")

# st.title("📝 PDF & Text Summarizer")
# st.write("Upload a PDF (with OCR fallback) or paste text to get a clean, two-pass summary.")

# # --- PDF Upload ---
# uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

# pdf_text = ""
# if uploaded_file is not None:
#     with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
#         for page_num, page in enumerate(pdf_doc, start=1):
#             text = page.get_text()

#             if text.strip():
#                 pdf_text += text
#             else:
#                 pix = page.get_pixmap(dpi=300)
#                 img = Image.open(io.BytesIO(pix.tobytes("png")))
#                 ocr_text = pytesseract.image_to_string(img)
#                 pdf_text += ocr_text

# # --- Text Input ---
# user_input = st.text_area("Enter text to summarize", value=pdf_text, height=300)

# # --- Sliders ---
# min_length = st.slider("Minimum summary length", min_value=20, max_value=300, value=100, step=10)
# max_length = st.slider("Maximum summary length", min_value=50, max_value=500, value=250, step=10)

# # --- Helper: Chunking (on UI side before feeding the model) ---
# def chunk_text(text, tokenizer, max_tokens=1024, stride=50):
#     tokens = tokenizer.tokenize(text)
#     total_tokens = len(tokens)
#     chunks = []
#     for i in range(0, total_tokens, max_tokens - stride):
#         chunk = tokens[i:i + max_tokens]
#         chunk_text = tokenizer.convert_tokens_to_string(chunk)
#         chunks.append(chunk_text)
#     return chunks

# # --- Summarize Button ---
# if st.button("Generate Summary"):
#     if not user_input.strip():
#         st.warning("Please enter some text or upload a PDF.")
#     elif min_length >= max_length:
#         st.error("⚠️ Minimum length must be less than maximum length.")
#     else:
#         # Pass 1: Chunk and summarize locally with progress bar
#         chunks = chunk_text(user_input, tokenizer)
#         first_pass_summaries = []
#         progress_bar = st.progress(0)
#         status_text = st.empty()

#         for i, chunk in enumerate(chunks, start=1):
#             status_text.text(f"Summarizing chunk {i} of {len(chunks)}...")
#             response = requests.post(API_URL, json={
#                 "text": chunk,
#                 "min_length": min_length,
#                 "max_length": max_length
#             })
#             if response.status_code == 200:
#                 first_pass_summaries.append(response.json()["summary"])
#             else:
#                 st.error(f"Error summarizing chunk {i}: {response.status_code}")
#                 break
#             progress_bar.progress(i / len(chunks))

#         status_text.text("Pass 1 complete — combining summaries...")

#         # Pass 2: Summarize all chunk summaries into final summary
#         combined_text = " ".join(first_pass_summaries)
#         response = requests.post(API_URL, json={
#             "text": combined_text,
#             "min_length": min_length,
#             "max_length": max_length
#         })

#         if response.status_code == 200:
#             final_summary = response.json()["summary"]

#             # Display final summary
#             st.subheader("📄 Final Summary")
#             st.text_area("Summary", final_summary, height=200)

#             # Display chunk summaries
#             st.subheader("🔍 Chunk Summaries")
#             for i, cs in enumerate(first_pass_summaries, start=1):
#                 st.markdown(f"**Chunk {i}**")
#                 st.write(cs)

#             # Prepare download data
#             chunk_summaries_text = "\n\n".join([f"Chunk {i}:\n{cs}" for i, cs in enumerate(first_pass_summaries, start=1)])
#             chunk_df = pd.DataFrame({
#                 "Chunk Number": list(range(1, len(first_pass_summaries) + 1)),
#                 "Summary": first_pass_summaries
#             })
#             csv_data = chunk_df.to_csv(index=False)

#             # Download buttons
#             st.download_button("⬇ Download Final Summary (TXT)", final_summary, file_name="final_summary.txt")
#             st.download_button("⬇ Download Chunk Summaries (TXT)", chunk_summaries_text, file_name="chunk_summaries.txt")
#             st.download_button("⬇ Download Chunk Summaries (CSV)", csv_data, file_name="chunk_summaries.csv", mime="text/csv")

#         else:
#             st.error("Error generating final summary.")

import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"  # Change if needed

st.set_page_config(page_title="Multi-Source Summarizer", layout="centered")
st.title("📝 Multi-Source Summarizer")
st.write("Summarize pasted text, PDFs, or webpage content.")

tab1, tab2, tab3 = st.tabs(["✏️ Paste Text", "📄 PDF Upload", "🌐 URL Content"])

# --- Tab 1: Text ---
with tab1:
    st.subheader("Summarize Pasted Text")
    text_input = st.text_area("Enter text here:", height=300)
    min_len_t1 = st.slider("Minimum summary length", 20, 300, 100, 10)
    max_len_t1 = st.slider("Maximum summary length", 50, 500, 250, 10)

    if st.button("Summarize Text", key="text_btn"):
        if not text_input.strip():
            st.warning("Please enter some text.")
        else:
            with st.spinner("Summarizing..."):
                res = requests.post(f"{API_BASE}/summarize-text", json={
                    "text": text_input,
                    "min_length": min_len_t1,
                    "max_length": max_len_t1
                })
                if res.status_code == 200:
                    summary = res.json()["summary"]
                    st.text_area("Summary", summary, height=200)
                    st.download_button("⬇ Download Summary", summary, file_name="text_summary.txt")
                else:
                    st.error(res.text)

# --- Tab 2: PDF ---
with tab2:
    st.subheader("Summarize PDF")
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
    min_len_t2 = st.slider("Minimum summary length", 20, 300, 100, 10, key="min_pdf")
    max_len_t2 = st.slider("Maximum summary length", 50, 500, 250, 10, key="max_pdf")

    if st.button("Summarize PDF", key="pdf_btn"):
        if pdf_file is None:
            st.warning("Please upload a PDF.")
        else:
            with st.spinner("Processing and summarizing PDF..."):
                files = {"file": (pdf_file.name, pdf_file, "application/pdf")}
                data = {"min_length": min_len_t2, "max_length": max_len_t2}
                res = requests.post(f"{API_BASE}/summarize-pdf", files=files, data=data)
                if res.status_code == 200:
                    summary = res.json()["summary"]
                    st.text_area("Summary", summary, height=200)
                    st.download_button("⬇ Download Summary", summary, file_name="pdf_summary.txt")
                else:
                    st.error(res.text)

# --- Tab 3: URL ---
with tab3:
    st.subheader("Summarize URL Content")
    url_input = st.text_input("Enter a URL")
    min_len_t3 = st.slider("Minimum summary length", 20, 300, 100, 10, key="min_url")
    max_len_t3 = st.slider("Maximum summary length", 50, 500, 250, 10, key="max_url")

    if st.button("Summarize URL", key="url_btn"):
        if not url_input.strip():
            st.warning("Please enter a URL.")
        else:
            with st.spinner("Fetching and summarizing content..."):
                res = requests.post(f"{API_BASE}/summarize-url", json={
                    "url": url_input,
                    "min_length": min_len_t3,
                    "max_length": max_len_t3
                })
                if res.status_code == 200:
                    summary = res.json()["summary"]
                    st.text_area("Summary", summary, height=200)
                    st.download_button("⬇ Download Summary", summary, file_name="url_summary.txt")
                else:
                    st.error(res.text)
