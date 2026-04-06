import os
import json
import random
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
@app.route("/generate", methods=["POST"])

# ── Data ──────────────────────────────────────────────────────────────────────

THALAS = [
    {
        "name": "Adi",
        "beats": 8,
        "subdivisions": [4, 2, 2],
        "subdivision_names": ["Laghu", "Drutam", "Drutam"],
        "clap_pattern": ["Clap", "Finger1", "Finger2", "Finger3", "Clap", "Wave", "Clap", "Wave"],
        "description": "Most common thala in Carnatic music"
    },
    {
        "name": "Rupaka",
        "beats": 6,
        "subdivisions": [2, 4],
        "subdivision_names": ["Drutam", "Laghu"],
        "clap_pattern": ["Clap", "Wave", "Clap", "Finger1", "Finger2", "Finger3"],
        "description": "Common in devotional compositions"
    },
    {
        "name": "Misra Chapu",
        "beats": 7,
        "subdivisions": [3, 2, 2],
        "subdivision_names": ["Tisra", "Drutam", "Drutam"],
        "clap_pattern": ["Clap", "Finger1", "Finger2", "Clap", "Wave", "Clap", "Wave"],
        "description": "Asymmetric thala with 3+2+2 grouping"
    },
    {
        "name": "Khanda Chapu",
        "beats": 5,
        "subdivisions": [2, 3],
        "subdivision_names": ["Drutam", "Tisra"],
        "clap_pattern": ["Clap", "Wave", "Clap", "Finger1", "Finger2"],
        "description": "Asymmetric thala with 2+3 grouping"
    }
]

SHRUTIS = [
    {"name": "Sa (C)",  "key": "C",   "base_frequency_hz": 261.63},
    {"name": "C#/Db",  "key": "C#",  "base_frequency_hz": 277.18},
    {"name": "D",       "key": "D",   "base_frequency_hz": 293.66},
    {"name": "D#/Eb",  "key": "D#",  "base_frequency_hz": 311.13},
    {"name": "E (Ga)", "key": "E",   "base_frequency_hz": 329.63},
    {"name": "F",       "key": "F",   "base_frequency_hz": 349.23},
    {"name": "F#",      "key": "F#",  "base_frequency_hz": 369.99},
    {"name": "G",       "key": "G",   "base_frequency_hz": 392.00},
    {"name": "G#/Ab",  "key": "G#",  "base_frequency_hz": 415.30},
    {"name": "A",       "key": "A",   "base_frequency_hz": 440.00},
    {"name": "A#/Bb",  "key": "A#",  "base_frequency_hz": 466.16},
    {"name": "B",       "key": "B",   "base_frequency_hz": 493.88}
]

RAGAS = [
    {
        "name": "Kalyani",
        "melakarta_number": 65,
        "thaat": "Kalyan",
        "notes": {
            "Sa":   {"solfege": "S",  "semitone_offset": 0},
            "Ri2":  {"solfege": "R2", "semitone_offset": 2},
            "Ga3":  {"solfege": "G3", "semitone_offset": 4},
            "Ma2":  {"solfege": "M2", "semitone_offset": 6},
            "Pa":   {"solfege": "P",  "semitone_offset": 7},
            "Dha2": {"solfege": "D2", "semitone_offset": 9},
            "Ni3":  {"solfege": "N3", "semitone_offset": 11}
        },
        "arohanam":  ["Sa", "Ri2", "Ga3", "Ma2", "Pa", "Dha2", "Ni3", "Sa'"],
        "avarohanam": ["Sa'", "Ni3", "Dha2", "Pa", "Ma2", "Ga3", "Ri2", "Sa"]
    },
    {
        "name": "Shankarabharanam",
        "melakarta_number": 29,
        "thaat": "Bilawal",
        "notes": {
            "Sa":   {"solfege": "S",  "semitone_offset": 0},
            "Ri2":  {"solfege": "R2", "semitone_offset": 2},
            "Ga3":  {"solfege": "G3", "semitone_offset": 4},
            "Ma1":  {"solfege": "M1", "semitone_offset": 5},
            "Pa":   {"solfege": "P",  "semitone_offset": 7},
            "Dha2": {"solfege": "D2", "semitone_offset": 9},
            "Ni3":  {"solfege": "N3", "semitone_offset": 11}
        },
        "arohanam":  ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3", "Sa'"],
        "avarohanam": ["Sa'", "Ni3", "Dha2", "Pa", "Ma1", "Ga3", "Ri2", "Sa"]
    },
    {
        "name": "Mayamalavagowla",
        "melakarta_number": 15,
        "thaat": "Bhairav",
        "notes": {
            "Sa":   {"solfege": "S",  "semitone_offset": 0},
            "Ri1":  {"solfege": "R1", "semitone_offset": 1},
            "Ga3":  {"solfege": "G3", "semitone_offset": 4},
            "Ma1":  {"solfege": "M1", "semitone_offset": 5},
            "Pa":   {"solfege": "P",  "semitone_offset": 7},
            "Dha1": {"solfege": "D1", "semitone_offset": 8},
            "Ni3":  {"solfege": "N3", "semitone_offset": 11}
        },
        "arohanam":  ["Sa", "Ri1", "Ga3", "Ma1", "Pa", "Dha1", "Ni3", "Sa'"],
        "avarohanam": ["Sa'", "Ni3", "Dha1", "Pa", "Ma1", "Ga3", "Ri1", "Sa"]
    }
]

shruti_map = {s["key"]: s for s in SHRUTIS}
raga_map   = {r["name"]: r for r in RAGAS}
thala_map  = {t["name"]: t for t in THALAS}

# ── Local note generator (fallback) ──────────────────────────────────────────

def generate_notes_local(raga: dict, thala: dict, avartanams: int = 4) -> list:
    notes_ordered = list(raga["notes"].items())
    solfege_list  = [info["solfege"] for _, info in notes_ordered]
    full_scale    = solfege_list + ["S'"]
    beats_per_cycle = thala["beats"]
    total_beats     = beats_per_cycle * avartanams
    result          = []
    current_idx     = 0
    for beat in range(total_beats):
        is_last_beat   = (beat == total_beats - 1)
        is_cycle_start = (beat % beats_per_cycle == 0)
        if is_last_beat:
            result.append("S")
            continue
        if is_cycle_start:
            result.append(full_scale[0])
            current_idx = 0
            continue
        move = random.choices([-2, -1, -1, 1, 1, 2], weights=[1, 3, 3, 3, 3, 1])[0]
        current_idx = max(0, min(len(full_scale) - 1, current_idx + move))
        beat_in_cycle = beat % beats_per_cycle
        if beat_in_cycle >= beats_per_cycle - 2:
            current_idx = max(0, current_idx - 1)
        result.append(full_scale[current_idx])
    return [result[i * beats_per_cycle:(i + 1) * beats_per_cycle]
            for i in range(avartanams)]

# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ── API: data ─────────────────────────────────────────────────────────────────

@app.route("/api/thalas", methods=["GET"])
def get_thalas():
    return jsonify({"thalas": THALAS})

@app.route("/api/thalas/<string:name>", methods=["GET"])
def get_thala(name):
    t = next((t for t in THALAS if t["name"].lower() == name.lower()), None)
    return jsonify(t) if t else (jsonify({"error": f"Thala '{name}' not found"}), 404)

@app.route("/api/shrutis", methods=["GET"])
def get_shrutis():
    return jsonify({"shrutis": SHRUTIS})

@app.route("/api/shrutis/<string:key>", methods=["GET"])
def get_shruti(key):
    s = next((s for s in SHRUTIS if s["key"].lower() == key.lower()), None)
    return jsonify(s) if s else (jsonify({"error": f"Shruti '{key}' not found"}), 404)

@app.route("/api/ragas", methods=["GET"])
def get_ragas():
    return jsonify({"ragas": RAGAS})

@app.route("/api/ragas/<string:name>", methods=["GET"])
def get_raga(name):
    r = next((r for r in RAGAS if r["name"].lower() == name.lower()), None)
    return jsonify(r) if r else (jsonify({"error": f"Raga '{name}' not found"}), 404)

@app.route("/api/ragas/<string:name>/notes", methods=["GET"])
def get_raga_notes(name):
    raga = next((r for r in RAGAS if r["name"].lower() == name.lower()), None)
    if raga is None:
        return jsonify({"error": f"Raga '{name}' not found"}), 404
    shruti_key = request.args.get("shruti")
    if shruti_key:
        shruti = next((s for s in SHRUTIS if s["key"].lower() == shruti_key.lower()), None)
        if shruti is None:
            return jsonify({"error": f"Shruti '{shruti_key}' not found"}), 404
        base_hz = shruti["base_frequency_hz"]
        notes_with_freq = {}
        for note_name, note_data in raga["notes"].items():
            offset = note_data["semitone_offset"]
            freq = round(base_hz * (2 ** (offset / 12)), 2)
            notes_with_freq[note_name] = {**note_data, "frequency_hz": freq}
        return jsonify({"raga": raga["name"], "shruti": shruti_key,
                        "base_frequency_hz": base_hz, "notes": notes_with_freq})
    return jsonify({"raga": raga["name"], "notes": raga["notes"]})

# ── API: generate composition ─────────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def generate():
    body       = request.get_json(force=True)
    raga_name  = body.get("raga")
    thala_name = body.get("thala")
    use_gemini = body.get("use_gemini", False)

    raga  = raga_map.get(raga_name)
    thala = thala_map.get(thala_name)

    if not raga:
        return jsonify({"error": f"Raga '{raga_name}' not found"}), 404
    if not thala:
        return jsonify({"error": f"Thala '{thala_name}' not found"}), 404

    if use_gemini:
        try:
            from gemini_gen import generate_notes_gemini, GeminiError
            avartanams = generate_notes_gemini(raga, thala, avartanams=4)
            return jsonify({"avartanams": avartanams, "source": "gemini"})
        except Exception as e:
            avartanams = generate_notes_local(raga, thala, avartanams=4)
            return jsonify({"avartanams": avartanams, "source": "local",
                            "warning": str(e)})

    avartanams = generate_notes_local(raga, thala, avartanams=4)
    return jsonify({"avartanams": avartanams, "source": "local"})

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

