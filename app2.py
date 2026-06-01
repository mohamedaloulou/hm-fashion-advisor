"""
app2.py  —  H&M AI Fashion Advisor
Streamlit app that combines:
  - Live weather         (OpenWeatherMap API)
  - Google Trends        (pytrends)
  - RAG over H&M inventory (LangChain + Pinecone + HuggingFace Embeddings)
  - Layout guide generation (Groq API — free, CPU-friendly)
  - LLM Monitoring       (Langfuse — optional)
"""

import os
import time
import streamlit as st
import requests
from pytrends.request import TrendReq
from groq import Groq
from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe

# ── LangChain imports ──────────────────────────────────────────────────────────
from langchain_pinecone import PineconeVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# ── Constants ──────────────────────────────────────────────────────────────────
INDEX_NAME      = "hm-products"
TOP_K           = 8
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL      = "llama-3.1-8b-instant"

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="H&M AI Fashion Advisor",
    page_icon="🧥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', serif; }
section[data-testid="stSidebar"] { background: #0d0d0d; color: #f5f0e8; }
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] p { color: #f5f0e8 !important; }
.stApp { background: #f5f0e8; }
.card {
    background: white; border-radius: 12px; padding: 20px 24px;
    margin-bottom: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-left: 4px solid #c8a96e;
}
.pill {
    display: inline-block; background: #f0ebe0; border: 1px solid #c8a96e;
    border-radius: 20px; padding: 4px 14px; font-size: 0.78rem;
    margin: 3px; color: #5a4a35;
}
.trend-badge {
    background: #0d0d0d; color: #c8a96e; border-radius: 6px;
    padding: 3px 10px; font-size: 0.75rem; font-weight: 500;
    margin: 3px; display: inline-block;
}
.guide-box {
    background: #0d0d0d; color: #f5f0e8; border-radius: 14px;
    padding: 28px 32px; font-family: 'DM Sans', sans-serif;
    font-size: 0.97rem; line-height: 1.75; border: 1px solid #c8a96e;
}
.stButton > button {
    background: #0d0d0d; color: #c8a96e; border: 1px solid #c8a96e;
    border-radius: 8px; font-family: 'DM Sans', sans-serif;
    font-weight: 500; padding: 10px 28px; transition: all 0.2s;
}
.stButton > button:hover { background: #c8a96e; color: #0d0d0d; }
</style>
""", unsafe_allow_html=True)


# ── Groq client (module-level singleton) ───────────────────────────────────────
_groq_client = None

def get_groq_client(api_key: str) -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=api_key)
    return _groq_client


# ── Cached resources ───────────────────────────────────────────────────────────
@st.cache_resource
def get_vectorstore(_pinecone_api_key: str) -> PineconeVectorStore:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings,
        pinecone_api_key=_pinecone_api_key,
    )


@st.cache_resource
def get_retriever(_vectorstore: PineconeVectorStore):
    return _vectorstore.as_retriever(search_kwargs={"k": TOP_K})


# ── Helper functions ───────────────────────────────────────────────────────────
def fetch_weather(city: str, api_key: str) -> dict | None:
    try:
        geo_resp = requests.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={"q": city, "limit": 1, "appid": api_key},
            timeout=8,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if not geo_data:
            st.warning(f"City '{city}' not found.")
            return None
        lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "city":        data["name"],
            "temp_c":      round(data["main"]["temp"], 1),
            "feels_like":  round(data["main"]["feels_like"], 1),
            "description": data["weather"][0]["description"].capitalize(),
            "humidity":    data["main"]["humidity"],
            "wind_kph":    round(data["wind"]["speed"] * 3.6, 1),
        }
    except Exception as e:
        st.warning(f"Weather API error: {e}")
        return None


def fetch_trends(keywords: list[str]) -> list[str]:
    try:
        pytrends = TrendReq(hl="en-US", tz=360)
        pytrends.build_payload(keywords[:5], cat=185, timeframe="now 7-d")
        related = pytrends.related_queries()
        top_trends = []
        for kw in keywords:
            df = related.get(kw, {}).get("top")
            if df is not None and not df.empty:
                top_trends += df["query"].head(5).tolist()
        return list(dict.fromkeys(top_trends))[:10]
    except Exception as e:
        st.warning(f"Trends fetch error: {e}")
        return keywords


def format_docs(docs: list[Document]) -> str:
    return "\n".join(
        f"- {d.metadata.get('prod_name', '?')} "
        f"({d.metadata.get('product_type_name', '?')}, "
        f"{d.metadata.get('colour_group_name', '?')}) "
        f"— {d.metadata.get('garment_group_name', '?')}"
        for d in docs
    )


def build_prompt(weather: dict, trends: list[str], inventory_str: str,
                 city: str, gender: str, occasion: str) -> str:
    weather_str = (
        f"City: {weather['city']}\n"
        f"Temperature: {weather['temp_c']}°C (feels like {weather['feels_like']}°C)\n"
        f"Conditions: {weather['description']}\n"
        f"Humidity: {weather['humidity']}%  |  Wind: {weather['wind_kph']} km/h"
    )
    trends_str = ", ".join(trends) if trends else "no trend data"
    return f"""You are an expert fashion stylist and visual merchandiser for H&M.

## Current Weather in {city}
{weather_str}

## Trending Fashion Topics Right Now
{trends_str}

## Customer Profile
- Gender / Department preference: {gender}
- Occasion: {occasion}

## Available H&M Inventory (retrieved for this context)
{inventory_str}

## Your Task
Create a complete, actionable **store layout and outfit guide** that:
1. Recommends 2–3 complete outfit combinations using ONLY the products listed above.
2. Suggests how to display these items together in-store (mannequin styling, rack groupings, color stories).
3. Explains how the weather conditions influence each recommendation.
4. Ties in 2–3 of the trending topics above with specific styling notes.
5. Ends with a one-sentence visual theme for the window display.

Be specific, creative, and concise. Use bullet points and clear section headers."""


# ── Langfuse-traced Groq calls ─────────────────────────────────────────────────
@observe(as_type="generation")
def _groq_generation(**kwargs):
    """Inner function — traced as a single LLM generation in Langfuse."""
    messages     = kwargs.pop("messages")
    model        = kwargs.pop("model")
    max_tokens   = kwargs.pop("max_tokens", 1024)
    temperature  = kwargs.pop("temperature", 0.7)
    groq_api_key = kwargs.pop("groq_api_key")

    langfuse_context.update_current_observation(
        input=messages,
        model=model,
        model_parameters={"max_tokens": max_tokens, "temperature": temperature},
    )

    client   = get_groq_client(groq_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    output = response.choices[0].message.content

    langfuse_context.update_current_observation(
        output=output,
        usage_details={
            "input":  response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
        },
    )
    return output


@observe()
def call_groq(prompt: str, api_key: str) -> str:
    """Outer function — traced as a full fashion advisor trace in Langfuse."""
    for attempt in range(3):
        try:
            return _groq_generation(
                messages=[{"role": "user", "content": prompt}],
                model=GROQ_MODEL,
                max_tokens=1024,
                temperature=0.7,
                groq_api_key=api_key,
            )
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise e


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")

    groq_key      = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    weather_key   = st.text_input("OpenWeatherMap API Key", type="password", placeholder="abc123...")
    pinecone_key  = st.text_input("Pinecone API Key", type="password", placeholder="pcsk_...")

    st.markdown("---")
    st.markdown("### 📍 Location & Profile")
    city     = st.text_input("City", value="London")
    gender   = st.selectbox("Department Focus", ["Ladieswear", "Menswear", "Both"])
    occasion = st.selectbox("Occasion", ["Everyday / Casual", "Work / Office", "Evening / Party", "Sport / Active", "Weekend"])

    st.markdown("---")
    st.markdown("### 🔍 Trend Seeds")
    seed_input = st.text_input("Trend keywords (comma-separated)", value="fashion, summer outfit, streetwear")
    seeds = [s.strip() for s in seed_input.split(",") if s.strip()]

    st.markdown("---")
    st.markdown("### 📊 Langfuse Monitoring")
    langfuse_public = st.text_input("Langfuse Public Key", type="password", placeholder="pk-lf-...")
    langfuse_secret = st.text_input("Langfuse Secret Key", type="password", placeholder="sk-lf-...")
    langfuse_host   = st.selectbox(
        "Langfuse Region",
        ["https://cloud.langfuse.com", "https://us.cloud.langfuse.com"],
        help="EU: cloud.langfuse.com — US: us.cloud.langfuse.com. Check your browser URL when logged in."
    )
    st.caption("Optional — get free keys at cloud.langfuse.com")

    st.markdown("---")
    st.caption("Get a free Groq API key at console.groq.com")
    st.caption("Get a free Pinecone API key at pinecone.io")
    st.caption("Run `python ingest.py` once locally to populate Pinecone.")


# ── Main UI ────────────────────────────────────────────────────────────────────
st.markdown("# 🧥 H&M AI Fashion Advisor")
st.markdown("*Weather-aware · Trend-driven · Inventory-grounded*")
st.markdown("---")

generate = st.button("✨ Generate Layout Guide", use_container_width=True)

if generate:
    if not groq_key or not weather_key or not pinecone_key:
        st.error("Please enter Groq, OpenWeatherMap, and Pinecone API keys in the sidebar.")
        st.stop()

    # ── Activate Langfuse if keys provided ────────────────────────────────
    # Must set env vars before @observe decorators fire, so we set them
    # as early as possible and use st.session_state to persist across reruns.
    if langfuse_public and langfuse_secret:
        os.environ["LANGFUSE_PUBLIC_KEY"] = langfuse_public
        os.environ["LANGFUSE_SECRET_KEY"] = langfuse_secret
        os.environ["LANGFUSE_HOST"]       = langfuse_host
        # Cache a single flushing client in session state
        if "lf_client" not in st.session_state:
            st.session_state["lf_client"] = Langfuse(
                public_key=langfuse_public,
                secret_key=langfuse_secret,
                host=langfuse_host,
            )

    col1, col2, col3 = st.columns(3)

    # ── Step 1: Weather ────────────────────────────────────────────────────
    with col1:
        with st.spinner("Fetching weather..."):
            weather = fetch_weather(city, weather_key)
        if not weather:
            st.error("Could not fetch weather. Check your API key and city name.")
            st.stop()
        st.markdown(
            f"""<div class="card">
            <h4>🌤️ {weather['city']}</h4>
            <p style="font-size:2rem;margin:4px 0"><b>{weather['temp_c']}°C</b></p>
            <p>{weather['description']}</p>
            <p>💧 {weather['humidity']}% &nbsp;|&nbsp; 💨 {weather['wind_kph']} km/h</p>
            <p>Feels like <b>{weather['feels_like']}°C</b></p>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Step 2: Trends ─────────────────────────────────────────────────────
    with col2:
        with st.spinner("Fetching Google Trends..."):
            trends = fetch_trends(seeds)
        badges = "".join(f'<span class="trend-badge">{t}</span>' for t in trends)
        st.markdown(
            f'<div class="card"><h4>📈 Trending Now</h4>{badges}</div>',
            unsafe_allow_html=True,
        )

    # ── Step 3: RAG — retrieve inventory ──────────────────────────────────
    with col3:
        with st.spinner("Searching inventory..."):
            try:
                vectorstore   = get_vectorstore(pinecone_key)
                retriever     = get_retriever(vectorstore)
                rag_query     = f"{weather['description']} {occasion} {gender} {' '.join(trends[:3])}"
                docs          = retriever.invoke(rag_query)
                inventory_str = format_docs(docs)
            except Exception as e:
                st.error(f"Pinecone error: {e}\n\nCheck your Pinecone API key and make sure you ran `python ingest.py`.")
                st.stop()

        pills = "".join(
            f'<span class="pill">{d.metadata.get("prod_name","?")} · {d.metadata.get("colour_group_name","?")}</span>'
            for d in docs
        )
        st.markdown(
            f'<div class="card"><h4>🗂️ Matched Inventory ({len(docs)})</h4>{pills}</div>',
            unsafe_allow_html=True,
        )

    # ── Step 4: Groq + Langfuse — generate guide ──────────────────────────
    st.markdown("---")
    st.markdown("### 🪄 AI Layout & Outfit Guide")

    with st.spinner("Styling your guide..."):
        prompt = build_prompt(weather, trends, inventory_str, city, gender, occasion)
        try:
            guide = call_groq(prompt, groq_key)
        except Exception as e:
            st.error(f"Groq API error: {e}")
            st.stop()

    # ── Force Langfuse flush so traces are sent before Streamlit ends ──────
    if langfuse_public and langfuse_secret:
        try:
            st.session_state["lf_client"].flush()
        except Exception:
            pass

    st.markdown(
        f'<div class="guide-box">{guide.replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )

    if langfuse_public and langfuse_secret:
        st.success("✅ This generation was logged to Langfuse.")

    with st.expander("🔍 View raw prompt sent to Groq"):
        st.code(prompt, language="markdown")

else:
    st.markdown(
        """
        <div style="text-align:center; padding: 60px 20px; color:#5a4a35;">
            <p style="font-size:4rem">🧥</p>
            <h3 style="font-family:'Playfair Display',serif">Ready to style your store?</h3>
            <p>Fill in your API keys and city in the sidebar, then hit <b>Generate Layout Guide</b>.</p>
            <br>
            <p style="font-size:0.85rem; opacity:0.6">
                Powered by Groq (Llama 3.1) · OpenWeatherMap · Google Trends · LangChain · Pinecone · Langfuse
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )