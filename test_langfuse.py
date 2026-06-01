"""
test_langfuse.py — Verify Langfuse connection and trace delivery.
Run this before the app to confirm keys, region, and flush all work.
"""

from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe
import os

# ── Replace with your actual keys ─────────────────────────────────────────────
PUBLIC_KEY  = "your_pb_api_key_here"   # pk-lf-...
SECRET_KEY  = "your_sc_api_key_here"   # sk-lf-...
HOST        = "https://cloud.langfuse.com"   # EU region
# HOST      = "https://us.cloud.langfuse.com"  # uncomment if US region
# ──────────────────────────────────────────────────────────────────────────────

os.environ["LANGFUSE_PUBLIC_KEY"] = PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = SECRET_KEY
os.environ["LANGFUSE_HOST"]       = HOST

print(f"Testing Langfuse connection...")
print(f"Host:       {HOST}")
print(f"Public key: {PUBLIC_KEY[:12]}...")
print()

# ── Step 1: Test auth ──────────────────────────────────────────────────────────
try:
    lf = Langfuse()
    auth = lf.auth_check()
    if auth:
        print("✅ Auth check passed — keys are valid and host is reachable.")
    else:
        print("❌ Auth check failed — keys may be wrong or swapped.")
        print("   → Make sure pk-lf-... is Public Key and sk-lf-... is Secret Key.")
        exit(1)
except Exception as e:
    print(f"❌ Connection error: {e}")
    print("   → Check your HOST and internet connection.")
    exit(1)

# ── Step 2: Send a test trace and force flush ──────────────────────────────────
@observe()
def test_trace():
    langfuse_context.update_current_observation(
        name="langfuse-connection-test",
        input="test input",
        output="test output",
        metadata={"source": "test_langfuse.py"},
    )
    return "trace sent"

print("\nSending test trace...")
result = test_trace()

# Force flush — critical in short-lived scripts
lf.flush()

print("✅ Test trace sent and flushed!")
print()
print("Now check your Langfuse dashboard at:")
print(f"  {HOST.replace('https://', 'https://')}/traces")
print("You should see a trace named 'langfuse-connection-test'.")
print("If it appears → the app will work.")
print("If it doesn't → check that you're looking at the correct project.")
