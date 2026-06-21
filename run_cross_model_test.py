import os
import re
import time
import csv
from typing import Optional

# --- AUTO-INSTALL DEPENDENCIES ---
try:
    import requests
except ImportError:
    print("Installing missing package: requests...")
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

try:
    import pandas as pd
except ImportError:
    print("Installing missing package: pandas...")
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "pandas"], check=True)
    import pandas as pd

# --- CONFIGURATION ---
TOGETHER_API_KEY = "YOUR_TOGETHER_KEY_HERE"
PROMPT_FILE = "results/prompt_list.csv"
OUTPUT_FOLDER = "results/cross_model_tests"

# --- EARLY KEY CHECK ---
if TOGETHER_API_KEY == "YOUR_TOGETHER_KEY_HERE":
    print("❌ ERROR: Paste your Together AI API key on line 13!")
    print("   Get it from: https://api.together.xyz/settings/api-keys")
    print("   Then replace 'YOUR_TOGETHER_KEY_HERE' with your key.")
    exit(1)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Models Configuration - Using Together AI model IDs
# NOTE: If a model ID fails, the script will log it and continue to the next model
MODELS = [
    {
        "name": "Meta_Llama-3.3-70B",
        # Try the most common ID format first
        "id_options": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "meta-llama/Llama-3.3-70B-Instruct",
            "togethercomputer/llama-3-70b-instruct"
        ],
        "type": "together"
    },
    {
        "name": "Google_Gemma-4-31B",
        "id_options": [
            "google/gemma-4-31b-it",
            "google/gemma-3-27b-it"
        ],
        "type": "together"
    },
    {
        "name": "Alibaba_Qwen2.5-7B",
        "id_options": [
            "Qwen/Qwen2.5-7B-Instruct-Turbo",
            "Qwen/Qwen2.5-7B-Instruct"
        ],
        "type": "together"
    }
]

def resolve_model_id(model_config: dict) -> Optional[str]:
    """Try multiple model ID formats until one works."""
    for model_id in model_config["id_options"]:
        # Quick test call with minimal tokens
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": model_id,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "temperature": 0.1
        }
        try:
            resp = requests.post(url, json=data, headers=headers, timeout=15)
