import streamlit as st
import requests

st.set_page_config(page_title="OCR Demo", layout="centered")

st.title("📄 OCR Extraction Demo")

uploaded = st.file_uploader("Upload image or PDF", type=["png","jpg","jpeg","pdf"])

API_URL = "http://127.0.0.1:8000"

if uploaded:

    st.success("File uploaded")

    files = {"file": (uploaded.name, uploaded.getvalue())}

    if uploaded.name.lower().endswith(".pdf"):
        url = f"{API_URL}/extract/pdf"
    else:
        url = f"{API_URL}/extract/image"

    if st.button("Extract"):

        with st.spinner("Processing..."):

            res = requests.post(url, files=files)

            if res.status_code == 200:
                data = res.json()

                st.subheader("Document Type")
                st.write(data.get("doc_type"))

                st.subheader("Fields")
                st.json(data.get("fields"))

                st.subheader("Meta")
                st.json(data.get("meta"))

            else:
                st.error("API error")