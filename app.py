from flask import Flask, request, jsonify, render_template, make_response, url_for, send_from_directory # Import send_from_directory
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime
import traceback
import mimetypes
import time # Import time for potential delay
from gtts import gTTS

load_dotenv()
app = Flask(__name__)

# Define PROOF_DIR as an absolute path for maximum robustness and consistency
PROOF_DIR = os.path.abspath(os.path.join(app.root_path, 'doc', 'proofs'))

# NEW: Define AUDIO_OUTPUT_DIR in the project root
AUDIO_OUTPUT_DIR = os.path.abspath(os.path.join(app.root_path, 'audio_files'))

# Ensure directories exist at startup
os.makedirs(PROOF_DIR, exist_ok=True)
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True) # Ensure the new audio directory exists

print(f"Flask App Root Path: {app.root_path}")
print(f"Absolute PROOF_DIR: {PROOF_DIR}")
print(f"Absolute AUDIO_OUTPUT_DIR: {AUDIO_OUTPUT_DIR}")


# Route to serve files from the 'doc/proofs' directory (no change here)
@app.route('/proofs/<path:filename>')
def serve_proof(filename):
    if not os.path.isdir(PROOF_DIR):
        print(f"Error: Proof directory not found at {PROOF_DIR}")
        return "Internal Server Error: Proofs directory missing.", 500
    
    full_filepath = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to serve file: {filename} from full path: {full_filepath}")
    
    if not os.path.exists(full_filepath):
        print(f"Error: Requested file not found on disk at {full_filepath}")
        return "Not Found", 404

    try:
        mimetype, _ = mimetypes.guess_type(filename)
        if mimetype is None:
            if filename.endswith('.pdf'):
                mimetype = 'application/pdf'
            elif filename.endswith('.png'):
                mimetype = 'image/png'
            elif filename.endswith('.json'):
                mimetype = 'application/json'
            else:
                mimetype = 'application/octet-stream'

        with open(full_filepath, 'rb') as f:
            file_content = f.read()

        response = make_response(file_content)
        response.headers['Content-Type'] = mimetype
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-Content-Type-Options"] = "nosniff"

        print(f"Successfully prepared response headers for {filename}. Mimetype: {mimetype}, Disposition: {response.headers['Content-Disposition']}")
        return response
    except Exception as e:
        print(f"Error serving file {filename} from {PROOF_DIR}: {e}")
        traceback.print_exc()
        return "Internal Server Error: Failed to serve file.", 500


# NEW ROUTE TO SERVE AUDIO FILES FROM THE NEW DIRECTORY
@app.route('/audio_files/<path:filename>')
def serve_audio_file(filename):
    # send_from_directory securely serves files from a given directory.
    # The first argument is the directory path, the second is the filename.
    return send_from_directory(AUDIO_OUTPUT_DIR, filename)


HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
VALID_SCENARIOS = ["late for work", "missed class", "forgot anniversary", "missed deadline", "didn't text back"]

def get_excuse_from_huggingface(prompt):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {"max_length": 100, "temperature": 0.7, "top_p": 0.9}
    }
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    try:
        response = session.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        raw_text = result[0].get("generated_text", "No generated text found") if isinstance(result, list) else result.get("generated_text", "No generated text found")
        if "[/INST]" in raw_text:
            excuse = raw_text.split("[/INST]")[1].strip()
        else:
            excuse = raw_text.strip()
        excuse = excuse.replace('"', '').strip()
        print(f"Hugging Face API returned excuse: {excuse}")
        return excuse if excuse else "Error generating excuse, please try again later."
    except requests.exceptions.RequestException as e:
        print(f"Error calling Hugging Face API: {e}")
        traceback.print_exc()
        return None

def generate_doctor_doc(excuse_id, scenario):
    os.makedirs(PROOF_DIR, exist_ok=True)
    filename = f"doctor_doc_{excuse_id}.pdf"
    full_path = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to generate doctor note at: {full_path}") # Log where we try to save
    prompt = f"""
    [INST] Generate a concise, realistic medical detail for a doctor's note supporting the scenario '{scenario}'.
    Keep it under 50 words, professional, and believable (e.g., minor illness or issue). Do not include the excuse itself. [/INST]

    """
    medical_detail = get_excuse_from_huggingface(prompt)
    medical_detail = medical_detail.replace('"', '').strip() if medical_detail else "Unknown medical issue."
    try:
        c = canvas.Canvas(full_path, pagesize=letter)
        c.setFont("Helvetica", 14)
        c.drawString(50, 750, "Doctor's Note")
        c.drawString(50, 720, "Patient: Staff Member")
        c.drawString(50, 690, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        c.drawString(50, 660, f"Reason: {scenario.replace('_', ' ').title()}")
        c.setFont("Helvetica", 12)
        lines = simpleSplit(f"Details: {medical_detail}", "Helvetica", 12, 450)
        for i, line in enumerate(lines[:3]):
            c.drawString(50, 630 - i * 15, line)
        c.drawString(50, 570, "Doctor: Dr. John Smith")
        c.drawString(50, 540, "Facility: City Health Clinic")
        c.save() # This is where the file is written
        print(f"Finished writing doctor note to: {full_path}")
        
        if os.path.exists(full_path):
            print(f"Confirmation: PDF file EXISTS immediately after creation at: {full_path}")
        else:
            print(f"Warning: PDF file DOES NOT EXIST immediately after creation at: {full_path}. This is unexpected!")
        
        return full_path
    except Exception as e:
        print(f"CRITICAL ERROR generating PDF for {scenario} (excuse_id: {excuse_id}): {e}")
        traceback.print_exc()
        return None

def get_font_path():
    font_paths = [
        "arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    print("Warning: Arial.ttf not found. Using default font.")
    return None

ARIAL_FONT_PATH = get_font_path()

def wrap_text(draw, text, font, max_width):
    lines = []
    if not text:
        return [""]
    words = text.split(' ')
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            if not current_line:
                lines.append(word) 
                current_line = []
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines


def generate_chat_screenshot(excuse_id, excuse, scenario):
    os.makedirs(PROOF_DIR, exist_ok=True)
    filename = f"chat_screenshot_{excuse_id}.png"
    full_path = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to generate chat screenshot at: {full_path}")
    
    img_width = 600
    img_height = 400 
    img = Image.new("RGB", (img_width, img_height), color="white")
    draw = ImageDraw.Draw(img)

    font_size = 18
    font = ImageFont.load_default()
    if ARIAL_FONT_PATH:
        try:
            font = ImageFont.truetype(ARIAL_FONT_PATH, font_size)
        except IOError as e:
            print(f"Could not load specified font '{ARIAL_FONT_PATH}': {e}. Using default font.")
            traceback.print_exc()
            font = ImageFont.load_default()
        except Exception as e:
            print(f"Unexpected error loading font '{ARIAL_FONT_PATH}': {e}. Using default font.")
            traceback.print_exc()
            font = ImageFont.load_default()
            
    margin = 30
    current_y = 30
    line_height = font_size + 5

    friend_text = f"Friend: Sorry, I'm {scenario.replace('_', ' ')}!"
    wrapped_friend_lines = wrap_text(draw, friend_text, font, img_width - 2 * margin)
    for line in wrapped_friend_lines:
        draw.text((margin, current_y), line, fill="black", font=font)
        current_y += line_height
    
    current_y += line_height * 1.5

    you_text = f"You: {excuse}"
    wrapped_you_lines = wrap_text(draw, you_text, font, img_width - 2 * margin)
    for line in wrapped_you_lines:
        draw.text((margin, current_y), line, fill="blue", font=font)
        current_y += line_height

    current_y += line_height * 1.5

    final_friend_text = "Friend: No worries, take care!"
    wrapped_final_friend_lines = wrap_text(draw, final_friend_text, font, img_width - 2 * margin)
    for line in wrapped_final_friend_lines:
        draw.text((margin, current_y), line, fill="black", font=font)
        current_y += line_height

    if current_y > img_height:
        new_img_height = current_y + margin
        new_img = Image.new("RGB", (img_width, new_img_height), color="white")
        new_img.paste(img, (0, 0))
        img = new_img
        draw = ImageDraw.Draw(img)

    try:
        img.save(full_path)
        print(f"Successfully generated chat screenshot: {full_path}")
        if os.path.exists(full_path):
            print(f"Confirmation: PNG file EXISTS immediately after creation at: {full_path}")
        else:
            print(f"Warning: PNG file DOES NOT EXIST immediately after creation at: {full_path}. This is unexpected!")
        return full_path
    except Exception as e:
        print(f"CRITICAL ERROR generating PNG for {scenario} (excuse_id: {excuse_id}): {e}")
        traceback.print_exc()
        return None

def generate_location_log(excuse_id, scenario):
    os.makedirs(PROOF_DIR, exist_ok=True)
    filename = f"location_log_{excuse_id}.json"
    full_path = os.path.join(PROOF_DIR, filename)
    print(f"Attempting to generate location log at: {full_path}")
    log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": 37.7749,
        "longitude": -122.4194,
        "place": f"Related to {scenario.replace('_', ' ').title()}"
    }
    try:
        with open(full_path, "w") as f:
            json.dump(log, f, indent=2)
        print(f"Successfully generated location log: {full_path}")
        if os.path.exists(full_path):
            print(f"Confirmation: JSON file EXISTS immediately after creation at: {full_path}")
        else:
            print(f"Warning: JSON file DOES NOT EXIST immediately after creation at: {full_path}. This is unexpected!")
        return full_path
    except Exception as e:
        print(f"CRITICAL ERROR generating JSON for {scenario} (excuse_id: {excuse_id}): {e}")
        traceback.print_exc()
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_excuse():
    data = request.get_json()
    scenario = data.get("scenario", "generic situation")
    user_role = data.get("user_role", "generic")
    recipient = data.get("recipient", "generic")
    urgency = data.get("urgency", "medium")
    believability = data.get("believability", "5")
    if scenario not in VALID_SCENARIOS:
        return jsonify({"excuse": "Invalid scenario provided.", "excuse_id": None}), 400
    prompt = f"""
    [INST] Generate a concise, realistic, and believable excuse for:
    - Scenario: {scenario}
    - User Role: {user_role}
    - Recipient: {recipient}
    - Urgency: {urgency}
    - Believability: {believability}/10 (1=simple, 10=highly detailed)
    Keep it under 50 words and match the tone to the recipient. [/INST]
    """
    excuse = get_excuse_from_huggingface(prompt)
    if excuse is None:
        return jsonify({"excuse": "Failed to get excuse from AI. Please try again.", "excuse_id": None}), 500
    excuse_id = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"Generated excuse ID: {excuse_id}")
    return jsonify({"excuse": excuse, "excuse_id": excuse_id})

# Updated /speak_excuse endpoint to save to AUDIO_OUTPUT_DIR
@app.route("/speak_excuse", methods=["POST"])
def speak_excuse():
    data = request.get_json()
    excuse_text = data.get("excuse", "")
    excuse_id = data.get("excuse_id", datetime.now().strftime("%Y%m%d%H%M%S_%f"))

    if not excuse_text:
        return jsonify({"error": "No excuse text provided"}), 400

    try:
        tts = gTTS(text=excuse_text, lang='en')
        audio_filename = f"excuse_{excuse_id}.mp3"
        audio_filepath = os.path.join(AUDIO_OUTPUT_DIR, audio_filename) # Use new directory
        
        print(f"Attempting to save audio to: {audio_filepath}")
        tts.save(audio_filepath)
        
        if os.path.exists(audio_filepath):
            print(f"SUCCESS: Audio file '{audio_filename}' found on disk at {audio_filepath}")
        else:
            print(f"ERROR: Audio file '{audio_filename}' NOT FOUND on disk at {audio_filepath} after tts.save()")
            return jsonify({"error": "Failed to save audio file to disk."}), 500

        # Now, generate the URL using the new custom route
        audio_url = url_for('serve_audio_file', filename=audio_filename) # Use the new route name
        print(f"Generated audio URL: {audio_url}")
        return jsonify({"audio_url": audio_url})
    except Exception as e:
        print(f"Error generating speech: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/generate_proof/<excuse_id>", methods=["POST"])
def generate_proof(excuse_id):
    data = request.get_json() or {}
    proof_type = data.get("proof_type", "doctor_note")
    excuse = data.get("excuse", "")
    scenario = data.get("scenario", "generic situation")
    print(f"\n--- Attempting to generate proof: excuse_id={excuse_id}, proof_type={proof_type}, scenario={scenario} ---")
    proof_path = None
    try:
        if proof_type == "doctor_note":
            proof_path = generate_doctor_doc(excuse_id, scenario)
        elif proof_type == "chat_screenshot":
            proof_path = generate_chat_screenshot(excuse_id, excuse, scenario)
        elif proof_type == "location_log":
            proof_path = generate_location_log(excuse_id, scenario)
        else:
            print(f"Error: Invalid proof type '{proof_type}' requested.")
            return jsonify({"error": "Invalid proof type."}), 400

        if not proof_path:
            print(f"CRITICAL: Proof generation function returned None for {proof_type}. This indicates a failure within the generation process itself. Check logs above for details.")
            return jsonify({"error": "Failed to generate proof file (internal generation error). Check server logs for exact reason."}), 500

        print(f"Proof file path returned by generator: {proof_path}")
        
        time.sleep(0.1)

        file_exists = os.path.exists(proof_path)
        print(f"Result of os.path.exists('{proof_path}'): {file_exists}")

        if not file_exists:
            print(f"CRITICAL: Proof file NOT FOUND on disk at {proof_path} even after generation reported success. This is likely a path mismatch or a rare race condition.")
            return jsonify({"error": f"Proof file was not found on the server at {proof_path} after creation attempt. Path mismatch or race condition."}), 500

        file_basename = os.path.basename(proof_path)
        print(f"Successfully located generated proof file. Sending proof_url: /proofs/{file_basename}")
        return jsonify({"proof_url": f"/proofs/{file_basename}"})
    except Exception as e:
        print(f"UNHANDLED ERROR in /generate_proof/<excuse_id> route: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate proof due to an unexpected server error: ({e}). Please check server logs for details."}), 500

if __name__ == "__main__":
    app.run(debug=True)