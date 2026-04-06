import json
import re
import os
import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# NOTE: "gemini-2.5-pro" does not exist yet. Using "gemini-1.5-pro" or "gemini-1.5-flash"
GEMINI_MODEL   = "gemini-1.5-flash" 

print(f"DEBUG: Initializing Gemini with Key: {'Found' if GEMINI_API_KEY else 'MISSING'}")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    _model = genai.GenerativeModel(GEMINI_MODEL)
else:
    print("ERROR: GEMINI_API_KEY environment variable is not set!")

class GeminiError(Exception):
    """Raised when Gemini cannot generate valid notes."""
    pass

# ... [_build_prompt function remains the same] ...

# ── Main entry point ──────────────────────────────────────────────────────────
def generate_notes_gemini(raga: dict, thala: dict, avartanams: int = 4) -> list:
    print(f"DEBUG: Starting Gemini generation for Raga: {raga['name']}")
    prompt = _build_prompt(raga, thala, avartanams)

    try:
        print(f"DEBUG: Sending prompt to {GEMINI_MODEL}...")
        response = _model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 500 # Increased from 50 (50 is too short for JSON)
            },
            request_options={"timeout": 25}
        )

        raw = response.text.strip()
        print(f"DEBUG: Raw response received: {raw[:100]}...") # Print first 100 chars

    except Exception as e:
        print(f"ERROR: Gemini API call failed: {str(e)}")
        raise GeminiError(f"Gemini API error: {e}")

    # Clean markdown
    raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        data = json.loads(raw)
        print("DEBUG: JSON parsed successfully.")
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON. Raw text was: {raw}")
        raise GeminiError(f"Gemini returned invalid JSON: {e}")

    try:
        validated_data = _validate(data, raga, thala, avartanams)
        print("DEBUG: Validation passed.")
        return validated_data
    except GeminiError as e:
        print(f"ERROR: Validation failed: {str(e)}")
        raise e