import streamlit as st
from transformers import pipeline, AutoTokenizer
import torch
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Streamlit page configuration
st.set_page_config(page_title="AI Text Summarizer", page_icon="📝", layout="wide")

# Title and description
st.title("📝 Insight Distiller SummarAIzer")
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

# Input form
with st.form("summarization_form"):
    st.subheader("Input Article")
    input_text = st.text_area(
        "Enter the text to summarize (max 1000 words recommended):",
        height=400,
        placeholder="Paste your article here..."
    )
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
if submit_button and input_text:
    if st.session_state.summarizer is None:
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
elif submit_button and not input_text:
    st.warning("Please enter some text to summarize.")
# Footer
st.markdown("---")
