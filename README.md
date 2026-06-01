# 🧥 H&M AI Fashion Advisor

Weather-aware, trend-driven outfit and store layout guide powered by **Groq (Llama 3.1)**, **LangChain**, **ChromaDB**, **OpenWeatherMap**, **Google Trends**, and optional **Langfuse** observability.

---

## 📁 Project Structure

```
SA_fashion/
├── ready_file.json        ← H&M product data (you provide this)
├── ingest.py              ← loads JSON into ChromaDB (run once)
├── app2.py                ← main Streamlit app (Groq + Langfuse)
├── app.py                 ← alternative app (Google Gemini)
├── requirements.txt
├── test_weather.py        ← test OpenWeatherMap API key
├── test_llm.py            ← test Gemini API key
├── test_langfuse.py       ← test Langfuse connection
└── chroma_db/             ← created automatically by ingest.py
```

---

## ⚙️ How It Works

```
User input (city, occasion, gender)
        │
        ├─► OpenWeatherMap API  →  live weather data
        ├─► Google Trends       →  trending fashion keywords
        ├─► ChromaDB (RAG)      →  relevant H&M products retrieved via semantic search
        │
        └─► Groq (Llama 3.1)   →  generates store layout & outfit guide
                │
                └─► Langfuse   →  traces prompt, response, tokens (optional)
```

---

## 🚀 Setup & Run

### 1. Create and activate conda environment

```bash
conda create -n fashion-langchain python=3.10
conda activate fashion-langchain
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Place your data file

Make sure `ready_file.json` is in the project folder. Expected format:

```json
[
  {
    "text": "Product: Strap top. Type: ...",
    "metadata": { "prod_name": "Strap top", "product_type_name": "Top", "colour_group_name": "Black", "garment_group_name": "Jersey Basic" }
  }
]
```

### 4. Ingest data into ChromaDB (run once)

```bash
python ingest.py
```

This creates the `chroma_db/` folder. Re-run only if your product data changes.

### 5. Launch the app

```bash
streamlit run app2.py
```

---

## 🔑 API Keys

Enter all keys in the app sidebar. They are never stored to disk.

| Key | Where to get it | Required |
|-----|----------------|----------|
| **Groq API Key** | [console.groq.com](https://console.groq.com) — free tier | ✅ Yes |
| **OpenWeatherMap Key** | [openweathermap.org/api](https://openweathermap.org/api) — free tier (1000 calls/day) | ✅ Yes |
| **Langfuse Public Key** | [cloud.langfuse.com](https://cloud.langfuse.com) — free tier | ⬜ Optional |
| **Langfuse Secret Key** | Same project as Public Key | ⬜ Optional |

> **Note:** OpenWeatherMap API keys take up to 2 hours to activate after creation.

---

## 📊 Langfuse Observability (Optional)

When Langfuse keys are provided, every generation is traced with:

- Full prompt sent to Groq
- Raw LLM response
- Token usage (input + output)
- Latency per step
- Model and parameters

**Setup:**
1. Create a free account at [cloud.langfuse.com](https://cloud.langfuse.com)
2. Create a project and copy the **Public Key** (`pk-lf-...`) and **Secret Key** (`sk-lf-...`)
3. Paste both into the Langfuse section of the sidebar
4. Select your region (EU: `cloud.langfuse.com` / US: `us.cloud.langfuse.com`)

To verify your keys work before running the app:

```bash
python test_langfuse.py
```

---

## 🧪 Testing Individual Components

Test each API independently before running the full app:

```bash
# Test OpenWeatherMap key
python test_weather.py

# Test Groq / Gemini LLM key
python test_llm.py

# Test Langfuse connection and trace delivery
python test_langfuse.py
```

---

## 🌐 Deploy for Free

### Hugging Face Spaces (recommended)
1. Create a Space at [huggingface.co/spaces](https://huggingface.co/spaces), choose **Streamlit** SDK
2. Upload all files including the `chroma_db/` folder
3. Add your API keys as **Secrets** in Space settings

### Render
1. Push to GitHub
2. New Web Service on [render.com](https://render.com)
3. Build command: `pip install -r requirements.txt && python ingest.py`
4. Start command: `streamlit run app2.py --server.port $PORT --server.address 0.0.0.0`
5. Add env vars for your API keys

---

## 🛠️ Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit |
| LLM | Groq API — Llama 3.1 8B Instant |
| RAG / Vector store | LangChain + ChromaDB |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Weather | OpenWeatherMap API |
| Trends | pytrends (Google Trends) |
| Observability | Langfuse |
