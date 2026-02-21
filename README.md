# Deployment Strategy Assistant

A conversational web chatbot for Deployment Strategy role queries, powered by Claude.

---

## Setup (one-time)

### 1. Install Python
Download from https://python.org (version 3.9 or newer).

### 2. Install dependencies
Open a terminal in this folder and run:
```
pip install -r requirements.txt
```

### 3. Add your API key
Set your Anthropic API key as an environment variable:

**Mac / Linux:**
```
export ANTHROPIC_API_KEY=your-key-here
```

**Windows:**
```
set ANTHROPIC_API_KEY=your-key-here
```

### 4. Add your PDFs
Drop any PDF documents (job descriptions, FAQs, policy docs, etc.) into the `documents/` folder. The chatbot will automatically read and reference them.

---

## Running the app

```
streamlit run app.py
```

A browser window will open automatically at `http://localhost:8501`.

---

## Publishing to the web (free)

1. Create a free account at https://streamlit.io
2. Connect your GitHub repository
3. Click **Deploy** — Streamlit hosts it for you

Set `ANTHROPIC_API_KEY` as a secret in the Streamlit dashboard under **Settings → Secrets**.

---

## Adding or updating documents

Just add or replace PDF files in the `documents/` folder and restart the app. No coding needed.
