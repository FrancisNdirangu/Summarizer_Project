import streamlit as st
from transformers import pipeline, AutoTokenizer
import torch
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Streamlit page configuration
st.set_page_config(page_title="AI Text Summarizer", page_icon="📝", layout="wide")

# Title and description
st.title("Insight Distiller SummarAIzer")
st.markdown("""
    Enter a text article below and generate a concise summary using a DistilBART model.
    Adjust the summary length as needed. This app is designed for AI, ML and Data Science content but works with any text.
""")

# Model and tokenizer paths
model_path = "sshleifer/distilbart-cnn-12-6"  # Use Hugging Face model; update to "./distilbart-finetuned/final_model" if you have the fine-tuned model

# Initialize session state for summarizer
if 'summarizer' not in st.session_state:
    try:
        with st.spinner("Loading the summarization model..."):
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            st.session_state.summarizer = pipeline(
                "summarization",
                model=model_path,
                tokenizer=tokenizer,
                device=-1  # Force CPU
            )
        st.success("Model loaded successfully!")
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        logging.error(f"Model loading error: {e}")
        st.session_state.summarizer = None

# Function to extract text from URL
def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Extract text from paragraphs, headings, and articles
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article'])
        text = ' '.join(element.get_text(strip=True) for element in text_elements)
        return text if text else "No readable text found on the webpage."
    except Exception as e:
        logging.error(f"URL text extraction error: {e}")
        return f"Error extracting text from URL: {str(e)}"

# Function to extract text from PDF using PyPDF2
def extract_text_from_pdf(file):
    try:
        if not file or not hasattr(file, 'read'):
            return "Invalid file uploaded. Please upload a valid PDF."
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        if pdf_reader.is_encrypted:
            return "Error: Uploaded PDF is encrypted. Please provide an unencrypted PDF."
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
        return text.strip() if text.strip() else "No readable text found in the PDF."
    except PyPDF2.errors.PdfReadError as e:
        logging.error(f"PDF read error: {e}")
        return f"Error: Invalid PDF format - {str(e)}"
    except Exception as e:
        logging.error(f"PDF text extraction error: {e}")
        return f"Error extracting text from PDF: {str(e)}"

# Input form
with st.form("summarization_form"):
    st.subheader("Choose Your Input")
    
    # Input type selection
    input_type = st.radio("Select input type:", ("Text Article", "URL", "PDF Upload"), horizontal=True)
    
    # Initialize input_text
    input_text = ""
    
    # Layout for input fields
    col1, col2 = st.columns([2, 1])  # Create two columns for input and settings
    
    with col1:
        st.markdown("**Input Content**")
        if input_type == "Text Article":
            input_text = st.text_area(
                "Enter the text to summarize (max 1000 words recommended):",
                height=400,
                placeholder="Paste your article or text content here..."
            )
        elif input_type == "URL":
            url_input = st.text_input(
                "Enter the URL to summarize:",
                placeholder="Paste a link to a blog, article, or webpage (e.g., https://news.example.com/story)"
            )
            if url_input:
                with st.spinner("Fetching text from URL..."):
                    input_text = extract_text_from_url(url_input)
                st.text_area(
                    "Extracted Text (read-only):",
                    input_text,
                    height=400,
                    disabled=True,
                    placeholder="Text from the URL will appear here after fetching..."
                )
        elif input_type == "PDF Upload":
            pdf_file = st.file_uploader(
                "Upload a PDF to summarize:",
                type=["pdf"],
                key="pdf_uploader",
                help="Drag and drop or click to upload a PDF document (e.g., research paper, report)"
            )
            if pdf_file:
                with st.spinner("Extracting text from PDF..."):
                    input_text = extract_text_from_pdf(pdf_file)
                st.text_area(
                    "Extracted Text (read-only):",
                    input_text,
                    height=400,
                    disabled=True,
                    placeholder="Text extracted from your PDF will appear here..."
                )
    
    with col2:
        st.subheader("Summary Settings")
        max_length = st.slider(
            "Maximum summary length (words):",
            min_value=30,
            max_value=250,
            value=150,
            step=10
        )
        min_length = st.slider(
            "Minimum summary length (words):",
            min_value=15,
            max_value=150,
            value=30,
            step=5
        )
        submit_button = st.form_submit_button("Generate Summary")

# Process submission
if submit_button:
    if not input_text or "Error extracting text" in input_text or "Invalid file" in input_text:
        st.warning("Please provide a valid input (text, URL, or PDF) with readable content.")
    elif st.session_state.summarizer is None:
        st.error("Model not loaded. Please check the model path and try again.")
    else:
        try:
            with st.spinner("Generating summary..."):
                summary = st.session_state.summarizer(
                    input_text,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )[0]["summary_text"]
                word_count = len(summary.split())
                
                st.subheader("Generated Summary")
                st.write(summary)
                st.info(f"Summary word count: {word_count}")
                
                st.download_button(
                    label="Download Summary",
                    data=summary,
                    file_name="summary.txt",
                    mime="text/plain"
                )
        except Exception as e:
            st.error(f"Error generating summary: {str(e)}")
            logging.error(f"Summary generation error: {e}")

# Footer
st.markdown("---")