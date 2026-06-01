# 🧥 H&M AI Fashion Advisor

Weather-aware, trend-driven outfit and store layout guide powered by **Groq (Llama 3.1)**, **LangChain**, **Pinecone**, **OpenWeatherMap**, **Google Trends**, and optional **Langfuse** observability.

> **Branch: `first_version`** — uses Pinecone as the hosted vector store instead of local ChromaDB, making it fully deployable to cloud platforms with no local files needed.

---

## 📁 Project Structure

```
SA_fashion/
├── ready_file.json        ← H&M product data
├── ingest.py              ← embeds JSON and pushes vectors to Pinecone (run once locally)
├── app2.py                ← main Streamlit app (Groq + Pinecone + Langfuse)
├── requirements.txt
├── test_weather.py        ← test OpenWeatherMap API key
├── test_llm.py            ← test Groq API key
├── test_langfuse.py       ← test Langfuse connection
└── .env                   ← local secrets (never committed)
```

---

## ⚙️ How It Works

```
User input (city, occasion, gender)
        │
        ├─► OpenWeatherMap API  →  live weather data
        ├─► Google Trends       →  trending fashion keywords
        ├─► Pinecone (RAG)      →  relevant H&M products retrieved via semantic search
        │
        └─► Groq (Llama 3.1)   →  generates store layout & outfit guide
                │
                └─► Langfuse   →  traces prompt, response, tokens (optional)
```

**Why Pinecone instead of ChromaDB:**
- No local `chroma_db/` folder needed on the server
- Vectors are stored permanently in the cloud — ingest once, deploy anywhere
- Build command on Render is just `pip install -r requirements.txt`

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

### 3. Set up your `.env` file

Create a `.env` file in the project root:

```env
PINECONE_API_KEY=your_pinecone_api_key_here
```

### 4. Create a Pinecone index

1. Sign up free at [pinecone.io](https://www.pinecone.io)
2. Create an index with these settings:
   - **Name:** `hm-products`
   - **Dimensions:** `384`
   - **Metric:** `cosine`
   - **Cloud/Region:** `AWS / us-east-1`
3. Copy your API key from the dashboard

### 5. Ingest data into Pinecone (run once locally)

```bash
python ingest.py
```

This reads `ready_file.json`, embeds all products using `all-MiniLM-L6-v2`, and pushes them to your Pinecone index in batches. Re-run only if your product data changes.

### 6. Launch the app

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
| **Pinecone API Key** | [pinecone.io](https://www.pinecone.io) — free tier (2GB, 1 index) | ✅ Yes |
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

# Test Groq API key
python test_llm.py

# Test Langfuse connection and trace delivery
python test_langfuse.py
```

---

## 🌐 Deploy for Free

### Render (recommended for this branch)
1. Push this branch to GitHub
2. New Web Service on [render.com](https://render.com)
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app2.py --server.port $PORT --server.address 0.0.0.0`
5. Add these environment variables in Render dashboard:
   - `GROQ_API_KEY`
   - `OPENWEATHERMAP_API_KEY`
   - `PINECONE_API_KEY`
   - `LANGFUSE_PUBLIC_KEY` *(optional)*
   - `LANGFUSE_SECRET_KEY` *(optional)*

> No `python ingest.py` in the build command — vectors already live in Pinecone from your local run.

### Hugging Face Spaces
1. Create a Space at [huggingface.co/spaces](https://huggingface.co/spaces), choose **Streamlit** SDK
2. Push this branch
3. Add your API keys as **Secrets** in Space settings

---

## 🛠️ Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit |
| LLM | Groq API — Llama 3.1 8B Instant |
| RAG | LangChain |
| Vector store | Pinecone (hosted, free tier) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Weather | OpenWeatherMap API |
| Trends | pytrends (Google Trends) |
| Observability | Langfuse |
