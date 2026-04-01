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
GEMINI_MODEL   = "gemini-3-flash-preview"

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

TASK
────
Generate a note sequence for the raga "{raga["name"]}" (Melakarta #{raga["melakarta_number"]}) 
set to "{thala["name"]}" thala ({beats} beats per avartanam, grouping: {grouping}).

RESEARCH STEP — do this before generating
──────────────────────────────────────────
1. Research and find about "{raga["name"]}" from Carnatic musicology sources — 
   textbooks (e.g. Sambamurthy's "South Indian Music", T.V. Subba Rao's works), 
   published notations of kritis in this raga, or if direct info is scarce, 
   refer to sibling ragas sharing the same melakarta or similar note sets.
2. Identify:
   - Vadi (most important note)
   - Samvadi (second most important note)
   - Nyasa swaras (notes on which phrases can rest/end)
   - Characteristic phrases or gamakas (ornaments) typical of this raga
   - Any forbidden jumps or notes that are weak in this raga
   - Whether the raga is audava, shadava, or sampoorna in either direction
3. If you cannot find reliable information about "{raga["name"]}" from any 
   Carnatic source or sibling raga, respond ONLY with:
   CANNOT_FIND: <brief reason>
   Do NOT fabricate rules.

AVAILABLE NOTES (use ONLY these solfege labels)
────────────────────────────────────────────────
Scale: {scale_str}
Arohanam:  {aroha}
Avarohanam: {avaro}

COMPOSITION RULES
─────────────────
- Generate exactly {avartanams} avartanams (cycles), each with exactly {beats} notes.
- Each avartanam MUST start on S.
- The very last note of the last avartanam MUST be S.
- Weight the vadi and samvadi notes more heavily (they should appear more often).
- End phrases on nyasa swaras where possible.
- Respect arohanam for ascending runs and avarohanam for descending runs.
- Avoid jumps that are uncharacteristic of this raga.
- Each avartanam should be musically distinct but share the raga's character.
- Use S' (upper Sa) sparingly, only at phrase peaks.

OUTPUT FORMAT — return ONLY this JSON, no explanation, no markdown fences:
{{
  "raga": "{raga["name"]}",
  "source_notes": "one sentence: what Carnatic source or reasoning you used",
  "vadi": "<note>",
  "samvadi": "<note>",
  "nyasa": ["<note>", ...],
  "avartanams": [
    ["<note>", "<note>", ...],
    ["<note>", "<note>", ...],
    ["<note>", "<note>", ...],
    ["<note>", "<note>", ...]
  ]
}}

Each inner array must have exactly {beats} note strings.
Only use notes from this set: {json.dumps(notes_list + ["S'"])}
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
