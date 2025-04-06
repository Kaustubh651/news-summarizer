import streamlit as st
from newspaper import Article
from transformers import pipeline
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import validators
import re
import json
import os

# --- Page Config ---
st.set_page_config(page_title="📰 News Summarizer to Google Sheets", layout="centered")
st.title("📰 News Summarizer & Google Sheet Saver")

# --- GSpread Initialization ---
@st.cache_resource
def init_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    # Load service account credentials securely
    key_path = "gen-lang-client-0709660306-d66c48c393e4.json"
    if not os.path.exists(key_path):
        st.error("❌ Service account JSON file not found.")
        st.stop()

    with open(key_path) as f:
        service_account_info = json.load(f)

    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)

    # Access or create the sheet
    sheet_name = "Project@KI"
    try:
        spreadsheet = client.open(sheet_name)
        sheet = spreadsheet.sheet1
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(sheet_name)
        sheet = spreadsheet.sheet1
        sheet.append_row(["Title", "Summary", "Top Image URL", "Timestamp"])

    return sheet, spreadsheet.id

# --- Load summarizer model ---
@st.cache_resource
def get_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")

# --- Extract article content ---
def extract_article_data(url):
    article = Article(url)
    article.download()
    article.parse()
    return {
        "title": article.title,
        "content": article.text,
        "top_image": article.top_image
    }

# --- Summarize content ---
def summarize_content(text, summarizer):
    text = re.sub(r"[^a-zA-Z0-9 ]", " ", text)
    summary = summarizer(text, max_length=130, min_length=30, do_sample=False)
    if summary and isinstance(summary, list) and isinstance(summary[0], dict):
        return summary[0].get("summary_text", "No summary found.")
    return "Could not generate summary."

# --- UI ---
url = st.text_input("🔗 Enter news article URL")

if st.button("Summarize and Save") and url:
    if not validators.url(url):
        st.warning("⚠️ Please enter a valid URL.")
    else:
        with st.spinner("📄 Extracting article..."):
            try:
                data = extract_article_data(url)
                if not data["content"]:
                    st.error("❌ No content found in article.")
                else:
                    summarizer = get_summarizer()
                    summary = summarize_content(data["content"], summarizer)

                    st.subheader("🧾 Summary")
                    st.write(summary)

                    if data["top_image"]:
                        st.image(data["top_image"], caption="Top Image")

                    sheet, sheet_id = init_gspread()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([data["title"], summary, data["top_image"], timestamp])
                    st.success("✅ Saved to Google Sheet!")

                    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                    st.markdown(f"[🔗 Open Sheet]({sheet_url})", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
