import os
import sys
import asyncio
import streamlit as st
from newspaper import Article
from transformers import pipeline
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Fix for Windows asyncio error (can be safely used cross-platform)
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Set Streamlit page config
st.set_page_config(page_title="News Summarizer to Google Sheet", layout="centered")
st.title("📰 News Summarizer & Google Sheet Saver")

# Setup scope and credentials using Streamlit Secrets
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_INFO = st.secrets["service_account"]

@st.cache_resource
def init_gspread():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    SPREADSHEET_NAME = "Project@KI"

    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        sheet = client.create(SPREADSHEET_NAME).sheet1
        sheet.append_row(["Title", "Summary", "Top Image URL"])
    return sheet

@st.cache_resource
def load_summarizer():
    os.environ["HUGGINGFACE_HUB_TOKEN"] = st.secrets["huggingface"]["token"]
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def extract_article(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.title, article.text, article.top_image

def summarize_text(text, summarizer, max_len=130, min_len=30):
    return summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)[0]['summary_text']

def is_duplicate(sheet, title):
    rows = sheet.get_all_values()
    existing_titles = [row[0] for row in rows[1:]]
    return title in existing_titles

# App Input
url = st.text_input("Paste a news article URL")

if st.button("Summarize and Save") and url:
    with st.spinner("Extracting article..."):
        try:
            title, content, top_image = extract_article(url)
            if not content.strip():
                st.error("❌ Could not extract any text from the article.")
            else:
                summarizer = load_summarizer()
                summary = summarize_text(content, summarizer)

                st.subheader("📌 Title")
                st.write(title)

                st.subheader("🧾 Summary")
                st.write(summary)

                if top_image:
                    st.image(top_image, caption="Top Image", use_container_width=True)

                sheet = init_gspread()
                if is_duplicate(sheet, title):
                    st.warning("⚠️ This article already exists in the sheet.")
                else:
                    sheet.append_row([title, summary, top_image])
                    st.success("✅ Article added to Google Sheet!")

                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.spreadsheet.id}"
                st.markdown(f"[🔗 Open Google Sheet]({sheet_url})", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
