from groq import Groq

API_KEY = "your_groq_api_key_here"  # Replace with your key from https://console.groq.com

MODEL = "llama-3.1-8b-instant"

print(f"Testing Groq API...")
print(f"Model: {MODEL}\n")

try:
    client = Groq(api_key=API_KEY)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Say hello and tell me which model you are in one sentence."}],
        max_tokens=100,
        temperature=0.7,
    )

    message = response.choices[0].message.content
    print("✅ API key is WORKING!\n")
    print(f"Groq says: {message}")
    print(f"\n📊 Usage — prompt tokens: {response.usage.prompt_tokens}, "
          f"completion tokens: {response.usage.completion_tokens}")

except Exception as e:
    error = str(e)
    if "401" in error or "invalid_api_key" in error.lower():
        print("❌ Invalid API key (401).")
        print("   → Get your free key at https://console.groq.com")
    elif "403" in error:
        print("❌ Access forbidden (403).")
        print("   → Check your plan at https://console.groq.com")
    elif "429" in error:
        print("❌ Rate limit hit. Wait a moment and try again.")
    elif "404" in error or "not found" in error.lower():
        print(f"❌ Model '{MODEL}' not found.")
        print("   → Check available models at https://console.groq.com/docs/models")
    else:
        print(f"❌ Error: {e}")
