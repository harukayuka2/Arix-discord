import os
import requests

# Default model can be overridden with the GEMINI_MODEL env var
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

BASE_URL_V1 = "https://generativelanguage.googleapis.com/v1"


def _extract_text_from_response(data: dict) -> str:
    # Try to extract common response shapes from the REST API
    candidates = data.get("candidates") or data.get("outputs")
    if not candidates:
        # Older shape: outputs -> content -> parts
        outputs = data.get("outputs")
        if outputs and isinstance(outputs, list) and len(outputs) > 0:
            out = outputs[0]
            content = out.get("content") if isinstance(out, dict) else None
            if content:
                parts = content.get("parts")
                if parts and len(parts) > 0:
                    return parts[0].get("text", "")
        return ""

    first = candidates[0]
    # nested candidate -> content -> parts -> text
    if isinstance(first, dict):
        content = first.get("content")
        if content:
            parts = content.get("parts")
            if parts and len(parts) > 0:
                return parts[0].get("text", "")
        # fallback
        return first.get("text", "")

    # If candidate is object-like with attributes, try common names
    try:
        if hasattr(first, "content"):
            content = getattr(first, "content")
            parts = getattr(content, "parts", None)
            if parts and len(parts) > 0:
                return getattr(parts[0], "text", "")
        if hasattr(first, "text"):
            return getattr(first, "text")
    except Exception:
        pass

    return ""


def generate_text(prompt: str, max_output_tokens: int = 512, model: str | None = None, api_key: str | None = None, personality: str | None = None) -> str:
    """Generate text using the Gemini REST v1 endpoint.

    - Uses `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) from environment if `api_key` not provided.
    - Calls the v1 endpoint (not v1beta) to avoid compatibility issues.
    - `personality`, if provided, is prepended as an instruction to the prompt.
    """
    model = model or MODEL
    api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY must be set (or pass api_key param)")

    final_prompt = prompt
    if personality:
        final_prompt = f"You are {personality}. Respond in that style.\n\n{prompt}"

    url = f"{BASE_URL_V1}/models/{model}:generateContent"
    payload = {
        "contents": [
            {"parts": [{"text": final_prompt}]}
        ]
    }

    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"{resp.status_code} {resp.reason}. {resp.text}")

    data = resp.json()
    text = _extract_text_from_response(data)

    # The REST v1 endpoint may not accept a direct `maxOutputTokens` field in the
    # top-level payload. Enforce an approximate token limit client-side by
    # mapping tokens -> characters (approx 1 token ~= 4 chars) and truncating.
    if max_output_tokens and isinstance(max_output_tokens, int) and max_output_tokens > 0:
        char_limit = max_output_tokens * 4
        if len(text) > char_limit:
            return text[:char_limit].rstrip() + "..."

    return text
