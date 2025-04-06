import os
import streamlit as st
from newspaper import Article
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import validators

# Constants
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_NAME = "Project@KI"
WORKSHEET_NAME = "Articles"

# Page setup
st.set_page_config(page_title="News Summarizer to Google Sheet", layout="centered")
st.title("📰 News Summarizer & Google Sheet Saver")

# Load credentials from Streamlit secrets
SERVICE_ACCOUNT_INFO = st.secrets["service_account"]

@st.cache_resource
def init_gspread():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    try:
        sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open(SPREADSHEET_NAME).add_worksheet(title=WORKSHEET_NAME, rows="100", cols="4")
        sheet.append_row(["Title", "Summary", "Top Image URL", "Timestamp"])

    # Ensure headers are in place
    if not sheet.row_values(1):
        sheet.append_row(["Title", "Summary", "Top Image URL", "Timestamp"])
    return sheet

@st.cache_resource
def load_summarizer():
    model_name = "sshleifer/distilbart-cnn-12-6"
    summarizer = pipeline("summarization", model=model_name, tokenizer=model_name)
    return summarizer

def extract_article(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.title.strip(), article.text.strip(), article.top_image

def summarize_text(text, summarizer, max_len=130, min_len=30):
    input_len = len(text.split())
    if input_len < 60:
        max_len = 60
    return summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)[0]['summary_text']

def is_duplicate(sheet, title):
    rows = sheet.get_all_values()
    existing_titles = [row[0] for row in rows[1:] if row]
    return title in existing_titles

# --- UI Input ---
url = st.text_input("Paste a news article URL")

if st.button("Summarize and Save") and url:
    if not validators.url(url):
        st.warning("⚠️ Please enter a valid URL.")
    else:
        with st.spinner("🔍 Extracting and summarizing article..."):
            try:
                title, content, top_image = extract_article(url)

                if not content:
                    st.error("❌ Unable to extract any content from the article.")
                else:
                    summarizer = load_summarizer()
                    try:
                        summary = summarize_text(content, summarizer)
                    except Exception:
                        st.warning("⚠️ Failed to summarize content. Showing partial text.")
                        summary = content[:500] + "..."

                    with st.expander("🔎 View Summary"):
                        st.subheader("📌 Title")
                        st.write(title)

                        st.subheader("🧾 Summary")
                        st.write(summary)

                        if top_image:
                            st.image(top_image, caption="Top Image", use_container_width=True)

                    sheet = init_gspread()

                    if is_duplicate(sheet, title):
                        st.warning("⚠️ This article already exists in the Google Sheet.")
                    else:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        sheet.append_row([title, summary, top_image if top_image else "", timestamp])
                        st.success("✅ Article successfully added to Google Sheet!")

                    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.spreadsheet.id}"
                    st.markdown(f"[🔗 Open Google Sheet]({sheet_url})", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"❌ An error occurred:\n\n{str(e)}")
