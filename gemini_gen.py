"""
gemini_gen.py
─────────────
Handles all Gemini API calls for raga-specific note generation.

HOW TO USE IN raga_explorer.py
────────────────────────────────
1. Import at the top:
       from gemini_gen import generate_notes_gemini, GeminiError
       

2. In _regenerate(), replace the direct _render_composition call with:

       def _regenerate(self):
           raga  = raga_map.get(self.raga_var.get())
           thala = thala_map.get(self.thala_var.get())
           if not raga or not thala:
               return
           self._set_status("Asking Gemini...", ACCENT)
           self.after(50, lambda: self._run_gemini(raga, thala))

       def _run_gemini(self, raga, thala):
           try:
               avartanams = generate_notes_gemini(raga, thala, avartanams=4)
               self._set_status("", BG)
               self._render_composition(raga, thala, avartanams=avartanams)
           except GeminiError as e:
               self._set_status(str(e), "#e05a6a")

3. Add a status label in _build_ui (after gen_hdr):
       self.status_lbl = tk.Label(self, text="", font=self.fn_small, bg=BG, fg=ACCENT)
       self.status_lbl.pack(anchor="w", padx=32)

   And add helper:
       def _set_status(self, msg, color):
           self.status_lbl.config(text=msg, fg=color)
           self.update_idletasks()

4. Update _render_composition signature to accept optional avartanams:
       def _render_composition(self, raga, thala, avartanams=None):
           if avartanams is None:
               avartanams = generate_notes(raga, thala, avartanams=4)
           ...rest unchanged...
"""

import json
import re
import os
import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-2.5-pro"

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)


class GeminiError(Exception):
    """Raised when Gemini cannot generate valid notes."""
    pass


# ── Prompt builder ────────────────────────────────────────────────────────────
def _build_prompt(raga: dict, thala: dict, avartanams: int) -> str:
    beats        = thala["beats"]
    total_beats  = beats * avartanams
    subdivs      = thala["subdivisions"]
    subdiv_names = thala["subdivision_names"]

    notes_list = [info["solfege"] for _, info in raga["notes"].items()]
    scale_str  = "  ".join(notes_list) + "  S'"

    aroha  = "  ".join(raga["arohanam"])
    avaro  = "  ".join(raga["avarohanam"])

    grouping = "  +  ".join(f"{n} ({s} beats)" for n, s in zip(subdiv_names, subdivs))

    return f"""
Generate Carnatic notes for raga {raga["name"]} in {thala["name"]} thala.

Use only these notes:
{scale_str}

Arohanam: {aroha}
Avarohanam: {avaro}

Rules:
- Generate {avartanams} avartanams
- Each avartanam must have {beats} notes
- Start and end on S

Return ONLY JSON:
{{
  "avartanams": [
    ["S","R","G","M","P","D","N","S"],
    ["S","N","D","P","M","G","R","S"]
  ]
}}
"""



# ── Validator ─────────────────────────────────────────────────────────────────
def _validate(data: dict, raga: dict, thala: dict, avartanams: int) -> list:
    """
    Validates Gemini's JSON response. Returns list of avartanams (list of lists).
    Raises GeminiError if invalid.
    """
    beats      = thala["beats"]
    valid_notes = set(
        info["solfege"] for _, info in raga["notes"].items()
    ) | {"S'"}

    if "avartanams" not in data:
        raise GeminiError("Gemini returned no avartanams field.")

    result = data["avartanams"]

    if len(result) != avartanams:
        raise GeminiError(
            f"Expected {avartanams} avartanams, got {len(result)}."
        )

    for i, cycle in enumerate(result):
        if len(cycle) != beats:
            raise GeminiError(
                f"Avartanam {i+1}: expected {beats} notes, got {len(cycle)}."
            )
        for note in cycle:
            if note not in valid_notes:
                raise GeminiError(
                    f"Avartanam {i+1}: invalid note '{note}' not in raga scale."
                )

    return result


# ── Main entry point ──────────────────────────────────────────────────────────
def generate_notes_gemini(raga: dict, thala: dict, avartanams: int = 4) -> list:
    prompt = _build_prompt(raga, thala, avartanams)

    try:
        response = _model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 50
            },
            request_options={"timeout": 25}
        )

        raw = response.text.strip()

    except Exception as e:
        raise GeminiError(f"Gemini API error: {e}")

    # Check for explicit "cannot find"
    if raw.upper().startswith("CANNOT_FIND"):
        reason = raw.split(":", 1)[-1].strip()
        raise GeminiError(f"Cannot find raga info: {reason}")

    # Clean markdown if any
    raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise GeminiError(f"Gemini returned invalid JSON: {e}")

    return _validate(data, raga, thala, avartanams)
