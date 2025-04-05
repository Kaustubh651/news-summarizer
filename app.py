import nltk
nltk.download('punkt', quiet=True)  # download punkt tokenizer silently


import streamlit as st
from newspaper import Article

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import json

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

# Article extraction
def extract_article(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.title, article.text, article.top_image

# Summarization using Sumy
def summarize_text(text, sentence_count=3):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, sentence_count)
    return ' '.join([str(sentence) for sentence in summary])

# Check for duplicate article
def is_duplicate(sheet, title):
    rows = sheet.get_all_values()
    existing_titles = [row[0] for row in rows[1:]]
    return title in existing_titles

# Streamlit UI
st.set_page_config(page_title="News Summarizer to Google Sheet", layout="centered")
st.title("📰 News Summarizer & Google Sheet Saver")

url = st.text_input("Paste a news article URL")

if st.button("Summarize and Save") and url:
    with st.spinner("Extracting article..."):
        try:
            title, content, top_image = extract_article(url)
            summary = summarize_text(content)

            st.subheader("📌 Title")
            st.write(title)

            st.subheader("🧾 Summary")
            st.write(summary)

            if top_image:
                st.image(top_image, caption="Top Image", use_column_width=True)

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
