# client.py
import os
import json
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_KEY:
    raise RuntimeError("Environment variable 'OPENAI_API_KEY' is not set.")

async def parse_json_safe(content: str) -> dict:
    """Attempts to extract JSON from potentially messy LLM output."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON block in markdown
        start = content.find("```json")
        end = content.find("```", start + 7)
        if start != -1 and end != -1:
            try:
                return json.loads(content[start+7:end])
            except:
                pass
        
        # Try to find first { ... }
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(content[start:end+1])
            except:
                pass
        
        return {"error": "parse_failed", "raw": content}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_llm_async(system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini") -> tuple[str, dict]:
    """
    Makes an async LLM call with robust error handling.
    Returns: (raw_content, parsed_dict)
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1, # Low temp for consistency
        "max_tokens": 500
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            parsed = await parse_json_safe(content)
            
            return content, parsed
            
        except httpx.HTTPStatusError as e:
            error_msg = f"API Error: {e.response.status_code} - {e.response.text}"
            raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
