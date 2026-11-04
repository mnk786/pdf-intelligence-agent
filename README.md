# 📄 PDF Intelligence Agent (BLAST Framework)

A professional, document-grounded AI agent that lets you upload any PDF and chat with it in real-time with verified page citations and zero hallucination rules.

Powered by **Google Gemini 2.5 Flash** and built with **Streamlit**.

---

## ✨ Features

- **Drag-and-Drop Upload:** Ingest single or multi-page documents (contracts, manuals, books, research papers).
- **Page-Level Grounding:** Automatically segments pages so the assistant cites exact source pages (`[Page 3]`, `[Pages 5-6]`).
- **Professional Behavior Rules:** Strict adherence to facts present in the PDF; refuses to speculate or hallucinate.
- **Real-Time Streaming:** Responses stream word-by-word.
- **Client & Personal Ready:** Clean configuration sidebar with temperature control, model picker, and session reset.

---

## 🚀 Quick Start

### 1. Configure Your Gemini API Key
Get a free API key at [Google AI Studio](https://aistudio.google.com/).

Create a `.env` file in the project root:
```bash
cp .env.example .env
```
Open `.env` and paste your key:
```env
GEMINI_API_KEY=AIzaSy...
```
*(Alternatively, you can also paste the API key directly into the application's sidebar at runtime).*

### 2. Launch the Application
Run the helper script:
```bash
./run.sh
```
Or run directly with the virtual environment:
```bash
.venv/bin/streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`.
