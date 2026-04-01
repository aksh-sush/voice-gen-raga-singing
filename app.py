from flask import Flask, jsonify
from gemini_gen import generate_notes_gemini

app = Flask(__name__)

@app.route("/")
def home():
    return "AI Singer Backend Running 🚀"


@app.route("/generate")
def generate():
    raga = {
        "name": "Shankarabharanam",
        "melakarta_number": 29,
        "notes": {},
        "arohanam": ["S","R","G","M","P","D","N","S'"],
        "avarohanam": ["S'","N","D","P","M","G","R","S"]
    }

    thala = {
        "name": "Adi",
        "beats": 8,
        "subdivisions": [4,2,2],
        "subdivision_names": ["Laghu","Drutam","Drutam"]
    }

    result = generate_notes_gemini(raga, thala)

    return jsonify({
        "status": "success",
        "generated_notes": result
    })


if __name__ == "__main__":
    app.run()
