# streamlit_app.py

import streamlit as st
import requests
from newspaper import Article

# Set page config
st.set_page_config(page_title="Blog Summarizer", layout="wide")
st.title("AI Summarizer for Scientific Blogs")

# Function to extract blog content from URL
def extract_text_from_url(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        return None

# UI for input type selection
input_mode = st.radio("Choose input type:", ["Paste blog text", "Paste blog URL"])

blog_text = ""
if input_mode == "Paste blog text":
    blog_text = st.text_area("Paste your blog article or content here:", height=300)
elif input_mode == "Paste blog URL":
    blog_url = st.text_input("Paste the blog URL here:")
    if blog_url:
        st.info("Extracting content from the URL...")
        extracted = extract_text_from_url(blog_url)
        if extracted:
            blog_text = extracted
            st.success("✅ Blog content extracted successfully!")
            with st.expander("See extracted blog text"):
                st.write(blog_text)
        else:
            st.error("⚠️ Failed to extract content. Please check the URL.")

# Summarization button
if st.button("Summarize"):
    if blog_text.strip():
        with st.spinner("Summarizing..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/summarize/",
                    json={"text": blog_text}
                )

                st.write(f"**Status code:** {response.status_code}")
                st.write(f"**Raw response:** {response.text}")

                if response.status_code == 200:
                    summary = response.json().get("summary", "No summary returned.")
                    st.subheader("📝 Summary")
                    st.write(summary)
                else:
                    st.error("API returned an error.")
            except Exception as e:
                st.error(f"⚠️ Request failed: {e}")
    else:
        st.warning("⚠️ Please provide blog text or a valid URL.")


