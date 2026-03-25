# config.py — ALL settings live here. Change model, key, weights in ONE place.

import os

# Read OpenAI API key from environment. Supports both OPENAI_API_KEY and OPEN_AI_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
MODEL = "gpt-4.1"
# MODEL = "gemini-2.5-flash"                  # ← swap model here only
# GEMINI_API_KEY = ""

SLA = dict(Critical=2, High=4, Medium=8, Low=24)
